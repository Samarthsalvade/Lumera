"""
train_model.py  (v2 — improved architecture)
─────────────────────────────────────────────
Luméra skin type classifier — fixed for TF 2.21 / Keras 3.x

Architecture improvements over v1:
  1. Multi-scale feature fusion — fine features from block_6_expand_relu
     (28×28, good for subtle texture differences) combined with coarse
     features from the final block (7×7, good for overall skin tone).
  2. Squeeze-and-Excitation (SE) block on coarse features — the model
     learns which MobileNetV2 channels matter for skin type classification
     rather than giving equal weight to all 1280 channels.
  3. Deeper classification head: Dense(512→256→128) with BatchNorm +
     Dropout at each stage provides more capacity for skin type separation,
     especially for the easily confused combination/normal/oily boundary.
  4. Label smoothing (ε=0.10) on categorical_crossentropy — prevents
     over-confident softmax outputs on ambiguous cases (combination skin
     is genuinely between normal and oily; hard targets hurt calibration).
  5. Third fine-tune phase with cosine LR decay for final convergence.
"""

import os
import json
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNetV2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# ── Config ─────────────────────────────────────────────────────────────────────
DATA_DIR       = 'training_data'
MODEL_DIR      = 'ml_model'
IMG_SIZE       = (224, 224)
BATCH_SIZE     = 32
PHASE1_EPOCHS  = 15
PHASE2_EPOCHS  = 10
PHASE3_EPOCHS  = 8
SEED           = 42
VAL_SPLIT      = 0.20
LABEL_SMOOTH   = 0.10   # ε for categorical label smoothing

SKIN_TYPES = ['combination', 'dry', 'normal', 'oily', 'sensitive']


# ── Augmentation ───────────────────────────────────────────────────────────────
@tf.function
def augment(image, label):
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_brightness(image, max_delta=0.15)
    image = tf.image.random_contrast(image, lower=0.85, upper=1.15)
    image = tf.image.random_saturation(image, lower=0.85, upper=1.15)
    image = tf.image.random_hue(image, max_delta=0.05)
    image = tf.clip_by_value(image, 0.0, 1.0)
    return image, label


@tf.function
def normalise_train(image, label):
    image = tf.cast(image, tf.float32) / 255.0
    n_classes = tf.cast(tf.shape(label)[0], tf.float32)
    label = label * (1.0 - LABEL_SMOOTH) + LABEL_SMOOTH / n_classes
    return image, label
 
 
@tf.function
def normalise_val(image, label):
    # Hard labels for honest val accuracy measurement — DO NOT smooth
    image = tf.cast(image, tf.float32) / 255.0
    return image, label


# ── Dataset ────────────────────────────────────────────────────────────────────
def load_dataset(data_dir, validation_split, seed):
    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=validation_split,
        subset='training',
        seed=seed,
        image_size=IMG_SIZE,
        batch_size=None,
        label_mode='categorical',
        class_names=SKIN_TYPES,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=validation_split,
        subset='validation',
        seed=seed,
        image_size=IMG_SIZE,
        batch_size=None,
        label_mode='categorical',
        class_names=SKIN_TYPES,
    )

    class_names = train_ds.class_names

    print("  Counting class distribution (takes ~30s)…")
    class_counts = {name: 0 for name in class_names}
    for _, label in train_ds:
        idx = tf.argmax(label).numpy()
        class_counts[class_names[idx]] += 1

    train_ds = (train_ds
                .map(normalise_train, num_parallel_calls=tf.data.AUTOTUNE)
                .map(augment,   num_parallel_calls=tf.data.AUTOTUNE)
                .shuffle(2048, seed=seed)
                .batch(BATCH_SIZE)
                .prefetch(tf.data.AUTOTUNE))

    val_ds = (val_ds
              .map(normalise_val, num_parallel_calls=tf.data.AUTOTUNE)
              .batch(BATCH_SIZE)
              .prefetch(tf.data.AUTOTUNE))

    return train_ds, val_ds, class_names, class_counts


# ── Model ──────────────────────────────────────────────────────────────────────
def build_model(num_classes=5):
    """
    MobileNetV2 backbone with:
      - Multi-scale feature fusion (fine 28×28 + SE-recalibrated coarse 7×7)
      - Deeper classification head (512→256→128 with BN + Dropout)
      - Softmax output with label-smoothed categorical_crossentropy
    """
    # ── Feature extractor exposing two spatial resolutions ────────────────────
    base = MobileNetV2(
        input_shape=(*IMG_SIZE, 3),
        include_top=False,
        weights='imagenet',
    )
    base.trainable = False

    # fine:   28×28 spatial map — captures pore/texture detail
    # coarse: 7×7 spatial map  — captures overall skin tone and distribution
    fine_output   = base.get_layer('block_6_expand_relu').output
    coarse_output = base.output
    feature_extractor = keras.Model(
        inputs=base.input,
        outputs=[fine_output, coarse_output],
        name='feature_extractor',
    )
    feature_extractor.trainable = False

    # ── Input ─────────────────────────────────────────────────────────────────
    inputs = keras.Input(shape=(*IMG_SIZE, 3), name='input_image')

    # MobileNetV2 expects [-1, +1]; undo our /255 normalisation inside the model
    # so inference code only needs to pass [0, 1] float input (same as v1).
    x_scaled = tf.keras.applications.mobilenet_v2.preprocess_input(inputs * 255.0)

    # ── Multi-scale features ──────────────────────────────────────────────────
    fine_feat, coarse_feat = feature_extractor(x_scaled, training=False)

    # Fine branch: pool 28×28 and project to 128-d
    fine_gap = layers.GlobalAveragePooling2D(name='fine_gap')(fine_feat)
    fine_gap = layers.BatchNormalization(name='fine_bn')(fine_gap)
    fine_gap = layers.Dense(128, activation='relu', name='fine_proj')(fine_gap)
    fine_gap = layers.Dropout(0.25, name='fine_drop')(fine_gap)

    # Coarse branch: Squeeze-and-Excitation before pooling
    #   Step 1 — Squeeze: pool to a channel descriptor
    coarse_gap = layers.GlobalAveragePooling2D(name='coarse_gap')(coarse_feat)
    #   Step 2 — Excitation: learn per-channel importance weights
    se = layers.Dense(
        64, activation='relu', name='se_squeeze',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(coarse_gap)
    se = layers.Dense(
        coarse_gap.shape[-1], activation='sigmoid', name='se_excite',
    )(se)
    #   Step 3 — Scale: reweight channels by learned importance
    coarse_recal = layers.Multiply(name='se_recalibrate')([coarse_gap, se])
    coarse_recal = layers.BatchNormalization(name='coarse_bn')(coarse_recal)
    coarse_proj  = layers.Dense(256, activation='relu', name='coarse_proj')(coarse_recal)
    coarse_proj  = layers.Dropout(0.30, name='coarse_drop')(coarse_proj)

    # Fuse both scales
    fused = layers.Concatenate(name='multi_scale_fusion')([fine_gap, coarse_proj])

    # ── Classification head ───────────────────────────────────────────────────
    # Dense(512) gives the model capacity to learn cross-scale combinations
    # that separate skin types (e.g. combination has T-zone oiliness but
    # dry cheeks — a pattern that spans both fine and coarse features).
    x = layers.Dense(
        512, activation='relu', name='head_fc1',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(fused)
    x = layers.BatchNormalization(name='head_bn1')(x)
    x = layers.Dropout(0.40, name='head_drop1')(x)

    x = layers.Dense(
        256, activation='relu', name='head_fc2',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(x)
    x = layers.BatchNormalization(name='head_bn2')(x)
    x = layers.Dropout(0.35, name='head_drop2')(x)

    x = layers.Dense(128, activation='relu', name='head_fc3')(x)
    x = layers.BatchNormalization(name='head_bn3')(x)
    x = layers.Dropout(0.25, name='head_drop3')(x)

    out = layers.Dense(num_classes, activation='softmax', name='skin_type_output')(x)

    return keras.Model(inputs, out, name='lumera_skin_v2'), base, feature_extractor


# ── Class weights ──────────────────────────────────────────────────────────────
def compute_class_weights(class_counts, class_names):
    counts  = np.array([class_counts[c] for c in class_names], dtype=float)
    total   = counts.sum()
    n       = len(class_names)
    weights = np.clip(total / (n * counts), 1.0, 10.0)
    return {i: float(w) for i, w in enumerate(weights)}


# ── Plot ───────────────────────────────────────────────────────────────────────
def save_plot(histories, phase_labels, out_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    acc   = sum([h.history['accuracy']     for h in histories], [])
    vacc  = sum([h.history['val_accuracy'] for h in histories], [])
    loss  = sum([h.history['loss']         for h in histories], [])
    vloss = sum([h.history['val_loss']     for h in histories], [])
    ep    = range(1, len(acc) + 1)

    # Phase boundary markers
    boundaries = []
    cumulative = 0
    for h in histories[:-1]:
        cumulative += len(h.history['accuracy'])
        boundaries.append(cumulative)

    for ax, tr, va, title in [(ax1, acc, vacc, 'Accuracy'), (ax2, loss, vloss, 'Loss')]:
        ax.plot(ep, tr, 'b-', label='Train')
        ax.plot(ep, va, 'r-', label='Validation')
        for b, lbl in zip(boundaries, phase_labels[1:]):
            ax.axvline(b + 0.5, color='green', linestyle='--', alpha=0.6, label=lbl)
        ax.set_title(title); ax.legend(); ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"✓ Plot saved: {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("LUMÉRA — SKIN TYPE MODEL TRAINING  (v2)")
    print("=" * 60)

    print("\n  Dataset summary:")
    for skin in SKIN_TYPES:
        folder = os.path.join(DATA_DIR, skin)
        if not os.path.exists(folder):
            print(f"  ✗  {skin}: MISSING — cannot train")
            return
        imgs = [f for f in os.listdir(folder)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        flag = 'OK' if len(imgs) >= 100 else 'LOW'
        print(f"  [{flag}] {skin:12s}: {len(imgs)} images")

    print("\n  Loading dataset…")
    train_ds, val_ds, class_names, class_counts = load_dataset(
        DATA_DIR, VAL_SPLIT, SEED
    )
    print(f"  Classes : {class_names}")
    print(f"  Counts  : {class_counts}")

    class_weights = compute_class_weights(class_counts, class_names)
    print(f"  Weights : { {class_names[i]: f'{w:.1f}x' for i, w in class_weights.items()} }")

    print("\n  Building model (v2 — multi-scale SE + deeper head)…")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model, base_model, feature_extractor = build_model(num_classes=len(class_names))
    model.summary(line_length=100)

    # Saves to best_model_v2.keras so the original best_model.keras is untouched.
    # ml_service.py will try the v2 path first and fall back to v1 if not found.
    ckpt = os.path.join(MODEL_DIR, 'best_model_v2.keras')

    def make_callbacks():
        return [
            keras.callbacks.EarlyStopping(
                patience=5, restore_best_weights=True, verbose=1,
                monitor='val_accuracy'),
            keras.callbacks.ReduceLROnPlateau(
                factor=0.5, patience=3, verbose=1, min_lr=1e-7),
            keras.callbacks.ModelCheckpoint(
                ckpt, save_best_only=True, monitor='val_accuracy', verbose=1),
        ]

    # ── Phase 1: frozen base ──────────────────────────────────────────────────
    print(f"\n  Phase 1 — frozen base ({PHASE1_EPOCHS} epochs, LR=1e-3)")
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss=keras.losses.CategoricalCrossentropy(),
        metrics=['accuracy'],
    )
    h1 = model.fit(train_ds, epochs=PHASE1_EPOCHS, validation_data=val_ds,
                   class_weight=class_weights, callbacks=make_callbacks(), verbose=1)

    # ── Phase 2: fine-tune top 30 layers ─────────────────────────────────────
    print(f"\n  Phase 2 — fine-tune top 30 layers ({PHASE2_EPOCHS} epochs, LR=1e-4)")
    base_model.trainable       = True
    feature_extractor.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(1e-4),
        loss=keras.losses.CategoricalCrossentropy(),
        metrics=['accuracy'],
    )
    h2 = model.fit(train_ds, epochs=PHASE2_EPOCHS, validation_data=val_ds,
                   class_weight=class_weights, callbacks=make_callbacks(), verbose=1)

    # ── Phase 3: deep fine-tune with cosine decay ─────────────────────────────
    # Unlocks top 60 layers and uses cosine LR decay so the final convergence
    # is smooth — prevents oscillation that can degrade classification of the
    # sensitive class (only 80 images; easily overfit with a fixed LR).
    print(f"\n  Phase 3 — fine-tune top 60 layers ({PHASE3_EPOCHS} epochs, cosine LR)")
    for layer in base_model.layers[:-60]:
        layer.trainable = False
    for layer in base_model.layers[-60:]:
        layer.trainable = True

    steps_per_epoch = len(list(train_ds))
    lr_schedule = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=5e-5,
        decay_steps=PHASE3_EPOCHS * steps_per_epoch,
        alpha=0.002,
    )
    model.compile(
        optimizer=keras.optimizers.Adam(lr_schedule),
        loss=keras.losses.CategoricalCrossentropy(),
        metrics=['accuracy'],
    )
    h3 = model.fit(train_ds, epochs=PHASE3_EPOCHS, validation_data=val_ds,
                   class_weight=class_weights, callbacks=make_callbacks(), verbose=1)

    # ── Save ──────────────────────────────────────────────────────────────────
    print("\n  Saving…")
    model.save(ckpt)
    print(f"  Saved: {ckpt}")

    idx_path = os.path.join(MODEL_DIR, 'class_indices.json')
    with open(idx_path, 'w') as f:
        json.dump({name: i for i, name in enumerate(class_names)}, f, indent=2)
    print(f"  Saved: {idx_path}")

    save_plot(
        [h1, h2, h3],
        ['Phase 1', 'Phase 2 start', 'Phase 3 start'],
        os.path.join(MODEL_DIR, 'training_history.png'),
    )

    # ── Final metrics ─────────────────────────────────────────────────────────
    val_loss, val_acc = model.evaluate(val_ds, verbose=0)
    print(f"\n  Val accuracy : {val_acc*100:.2f}%")
    print(f"  Val loss     : {val_loss:.4f}")

    # Per-class breakdown
    y_true_all, y_pred_all = [], []
    for imgs, labels in val_ds:
        preds = model.predict(imgs, verbose=0)
        y_pred_all.extend(np.argmax(preds, axis=1).tolist())
        # Round smoothed labels back to hard targets for metric reporting
        y_true_all.extend(np.argmax(labels.numpy(), axis=1).tolist())

    print("\n  Per-class accuracy:")
    for i, name in enumerate(class_names):
        mask    = [t == i for t in y_true_all]
        correct = sum(p == i for p, m in zip(y_pred_all, mask) if m)
        total   = sum(mask)
        acc_cls = correct / total if total > 0 else 0.0
        print(f"    {name:12s}: {acc_cls*100:5.1f}%  (n={total})  {'#'*int(acc_cls*30)}")

    print("\n" + "=" * 60)
    print("  Done. Restart Flask to load the new model.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
