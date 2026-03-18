"""
train_model.py
──────────────
Luméra skin type classifier — fixed for TF 2.21 / Keras 3.x
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

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR      = 'training_data'
MODEL_DIR     = 'ml_model'
IMG_SIZE      = (224, 224)
BATCH_SIZE    = 32
PHASE1_EPOCHS = 15
PHASE2_EPOCHS = 10
SEED          = 42
VAL_SPLIT     = 0.20

SKIN_TYPES = ['combination', 'dry', 'normal', 'oily', 'sensitive']


# ── Augmentation — pure TF ops only, NO Keras layer instantiation ─────────────
@tf.function
def augment(image, label):
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_brightness(image, max_delta=0.15)
    image = tf.image.random_contrast(image, lower=0.85, upper=1.15)
    image = tf.image.random_saturation(image, lower=0.85, upper=1.15)
    image = tf.image.random_hue(image, max_delta=0.05)
    # Rotation via contrib or tfa if available, otherwise skip
    # (flip + brightness covers most of the augmentation benefit anyway)
    image = tf.clip_by_value(image, 0.0, 1.0)
    return image, label


@tf.function
def normalise(image, label):
    return tf.cast(image, tf.float32) / 255.0, label


# ── Dataset ───────────────────────────────────────────────────────────────────
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

    # Count images per class for class weights
    print("  Counting class distribution (takes ~30s)…")
    class_counts = {name: 0 for name in class_names}
    for _, label in train_ds:
        idx = tf.argmax(label).numpy()
        class_counts[class_names[idx]] += 1

    train_ds = (train_ds
                .map(normalise, num_parallel_calls=tf.data.AUTOTUNE)
                .map(augment,   num_parallel_calls=tf.data.AUTOTUNE)
                .batch(BATCH_SIZE)
                .prefetch(tf.data.AUTOTUNE))

    val_ds = (val_ds
              .map(normalise, num_parallel_calls=tf.data.AUTOTUNE)
              .batch(BATCH_SIZE)
              .prefetch(tf.data.AUTOTUNE))

    return train_ds, val_ds, class_names, class_counts


# ── Model ─────────────────────────────────────────────────────────────────────
def build_model(num_classes=5):
    inputs = keras.Input(shape=(*IMG_SIZE, 3))

    # MobileNetV2 expects [-1, 1] — undo our /255 normalisation
    x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs * 255.0)

    base = MobileNetV2(
        input_shape=(*IMG_SIZE, 3),
        include_top=False,
        weights='imagenet'
    )
    base.trainable = False

    x   = base(x, training=False)
    x   = layers.GlobalAveragePooling2D()(x)
    x   = layers.BatchNormalization()(x)
    x   = layers.Dense(256, activation='relu')(x)
    x   = layers.Dropout(0.4)(x)
    x   = layers.Dense(128, activation='relu')(x)
    x   = layers.Dropout(0.3)(x)
    out = layers.Dense(num_classes, activation='softmax')(x)

    return keras.Model(inputs, out), base


# ── Class weights ─────────────────────────────────────────────────────────────
def compute_class_weights(class_counts, class_names):
    counts  = np.array([class_counts[c] for c in class_names], dtype=float)
    total   = counts.sum()
    n       = len(class_names)
    weights = np.clip(total / (n * counts), 1.0, 10.0)
    return {i: float(w) for i, w in enumerate(weights)}


# ── Plot ──────────────────────────────────────────────────────────────────────
def save_plot(h1, h2, out_path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    acc   = h1.history['accuracy']     + h2.history['accuracy']
    vacc  = h1.history['val_accuracy'] + h2.history['val_accuracy']
    loss  = h1.history['loss']         + h2.history['loss']
    vloss = h1.history['val_loss']     + h2.history['val_loss']
    ep    = range(1, len(acc) + 1)
    ft    = len(h1.history['accuracy'])

    for ax, tr, va, title in [(ax1, acc, vacc, 'Accuracy'), (ax2, loss, vloss, 'Loss')]:
        ax.plot(ep, tr, 'b-', label='Train')
        ax.plot(ep, va, 'r-', label='Validation')
        ax.axvline(ft + 0.5, color='green', linestyle='--', label='Fine-tune start')
        ax.set_title(title); ax.legend(); ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"✓ Plot saved: {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("\n" + "=" * 60)
    print("🧴  LUMÉRA — SKIN TYPE MODEL TRAINING")
    print("=" * 60)

    print("\n📊  Dataset summary:")
    for skin in SKIN_TYPES:
        folder = os.path.join(DATA_DIR, skin)
        if not os.path.exists(folder):
            print(f"  ❌  {skin}: MISSING — cannot train")
            return
        imgs = [f for f in os.listdir(folder)
                if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        flag = '✅' if len(imgs) >= 100 else '⚠️ '
        print(f"  {flag}  {skin:12s}: {len(imgs)} images")

    print("\n📂  Loading dataset…")
    train_ds, val_ds, class_names, class_counts = load_dataset(
        DATA_DIR, VAL_SPLIT, SEED
    )
    print(f"  Classes : {class_names}")
    print(f"  Counts  : {class_counts}")

    class_weights = compute_class_weights(class_counts, class_names)
    print(f"  Weights : { {class_names[i]: f'{w:.1f}x' for i,w in class_weights.items()} }")

    print("\n🏗️   Building model…")
    os.makedirs(MODEL_DIR, exist_ok=True)
    model, base_model = build_model(num_classes=len(class_names))
    model.summary(line_length=80)

    # ── Phase 1: frozen base ──────────────────────────────────────────────────
    print(f"\n🔥  Phase 1 — head only ({PHASE1_EPOCHS} epochs)")
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss='categorical_crossentropy',
        metrics=['accuracy'],
    )
    cb1 = [
        keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True, verbose=1),
        keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3, verbose=1),
    ]
    h1 = model.fit(train_ds, epochs=PHASE1_EPOCHS, validation_data=val_ds,
                   class_weight=class_weights, callbacks=cb1, verbose=1)

    # ── Phase 2: fine-tune top layers ─────────────────────────────────────────
    print(f"\n🔬  Phase 2 — fine-tune top 30 layers ({PHASE2_EPOCHS} epochs)")
    base_model.trainable = True
    for layer in base_model.layers[:-30]:
        layer.trainable = False

    model.compile(
        optimizer=keras.optimizers.Adam(1e-4),
        loss='categorical_crossentropy',
        metrics=['accuracy'],
    )
    ckpt = os.path.join(MODEL_DIR, 'best_model.keras')
    cb2 = [
        keras.callbacks.EarlyStopping(patience=5, restore_best_weights=True, verbose=1),
        keras.callbacks.ReduceLROnPlateau(factor=0.5, patience=3, verbose=1),
        keras.callbacks.ModelCheckpoint(ckpt, save_best_only=True,
                                        monitor='val_accuracy', verbose=1),
    ]
    h2 = model.fit(train_ds, epochs=PHASE2_EPOCHS, validation_data=val_ds,
                   class_weight=class_weights, callbacks=cb2, verbose=1)

    # ── Save ──────────────────────────────────────────────────────────────────
    print("\n💾  Saving…")
    model.save(ckpt)
    print(f"✅  {ckpt}")

    h5 = os.path.join(MODEL_DIR, 'skin_type_model.h5')
    model.save(h5)
    print(f"✅  {h5}")

    idx_path = os.path.join(MODEL_DIR, 'class_indices.json')
    with open(idx_path, 'w') as f:
        json.dump({name: i for i, name in enumerate(class_names)}, f, indent=2)
    print(f"✅  {idx_path}")

    save_plot(h1, h2, os.path.join(MODEL_DIR, 'training_history.png'))

    # ── Final metrics ─────────────────────────────────────────────────────────
    val_loss, val_acc = model.evaluate(val_ds, verbose=0)
    print(f"\n📈  Val accuracy : {val_acc*100:.2f}%")
    print(f"    Val loss     : {val_loss:.4f}")
    print("\n" + "=" * 60)
    print("✅  Done! Restart Flask to load the new model.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()