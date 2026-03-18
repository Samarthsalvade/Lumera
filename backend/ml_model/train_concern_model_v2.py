"""
train_concern_model.py  (v2 — improved architecture)
──────────────────────────────────────────────────────
Trains a MobileNetV2 multi-class skin concern classifier.

Concern classes:
  acne, blackheads, dark_circles, dark_spots, eye_bags, redness, texture

Architecture improvements over v1:
  1. Squeeze-and-Excitation (SE) block on the coarse feature maps —
     recalibrates which of MobileNetV2's 1280 channels actually matter for
     skin concerns instead of treating all channels equally after GAP.
  2. Multi-scale feature fusion — concatenates fine features (28×28 from
     block_6, good for blackheads/texture detail) with coarse features
     (7×7 from final block, good for redness/dark circles/global tone).
  3. Deeper shared head: Dense(512→256→128) with BatchNorm + Dropout at
     each stage, giving the model more capacity to learn concern-specific
     feature combinations.
  4. Per-concern prediction branches — each concern gets its own
     Dense(32) → Dense(1, sigmoid) pathway, so acne and texture don't have
     to share the same weight vector for their final decision boundary.
  5. Label smoothing (ε=0.05) on binary_crossentropy — prevents the model
     from collapsing to 0.0 / 1.0 extremes, which improves calibration and
     reduces over-confidence on novel images.

Run from backend/:
    python ml_model/train_concern_model.py

Output:
    ml_model/concern_model.keras
    ml_model/concern_class_indices.json
"""

import os, json, shutil, random
import numpy as np
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOLDER_TO_CLASS = {
    'acne': 'acne', 'Acne': 'acne', 'acne scar': 'acne',
    'papules': 'acne', 'pustules': 'acne', 'nodules': 'acne',
    'blackheades': 'blackheads', 'blackheads': 'blackheads',
    'Blackheads': 'blackheads', 'blackhead': 'blackheads',
    'Black Heads': 'blackheads', 'comedones': 'blackheads',
    'dark_circle': 'dark_circles', 'dark circles': 'dark_circles',
    'Dark Circle': 'dark_circles', 'Dark Circles': 'dark_circles',
    'Dark circle': 'dark_circles',
    'dark spots': 'dark_spots', 'Dark Spots': 'dark_spots',
    'dark_spots': 'dark_spots', 'darkspot': 'dark_spots',
    'melasma': 'dark_spots', 'hyperpigmentation': 'dark_spots',
    'freckle': 'dark_spots',
    'bags': 'eye_bags', 'Eyebag': 'eye_bags', 'eyebag': 'eye_bags',
    'Eye Bag': 'eye_bags', 'Eye Bags': 'eye_bags', 'EyeBags': 'eye_bags',
    'Rosacea': 'redness', 'redness': 'redness', 'Redness': 'redness',
    'skinredness': 'redness', 'Skin Redness': 'redness', 'Red Skin': 'redness',
    'pores': 'texture', 'wrinkles': 'texture', 'Wrinkles': 'texture',
    'wrinkle': 'texture', 'enlarged_pores': 'texture',
    'Enlarged Pores': 'texture', 'Open Pores': 'texture',
    'Dry Skin': 'texture', 'Dry-Skin': 'texture',
    'Carcinoma': None, 'Eczema': None, 'Keratosis': None, 'Milia': None,
    'Normal': None, 'normal': None, 'Oily': None, 'oily': None,
    'whitehead': None, 'Whitehead': None, 'Whiteheads': None, 'vascular': None,
    'train': None, 'valid': None, 'test': None,
}

DS7_DARK_CIRCLES = [
    os.path.join(BASE, 'dataset_downloads/ds7/train'),
    os.path.join(BASE, 'dataset_downloads/ds7/valid'),
    os.path.join(BASE, 'dataset_downloads/ds7/test'),
]

SCAN_ROOTS = [
    os.path.join(BASE, 'dataset_downloads/ds4/Skin_Conditions'),
    os.path.join(BASE, 'dataset_downloads/ds5/Skin v2'),
    os.path.join(BASE, 'dataset_downloads/ds_rf1'),
    os.path.join(BASE, 'dataset_downloads/ds_rf2'),
    os.path.join(BASE, 'dataset_downloads/ds_rf3'),
]

STAGING_DIR   = os.path.join(BASE, 'concern_training_data')
MODEL_DIR     = os.path.join(BASE, 'ml_model')

# Saves to _v2 paths so the original concern_model.keras is never overwritten.
# ml_service / skin_concern_detector will try the v2 path first, falling back
# to the original if the v2 file does not exist yet.
OUTPUT_MODEL  = os.path.join(MODEL_DIR, 'concern_model_v2.keras')
OUTPUT_IDX    = os.path.join(MODEL_DIR, 'concern_class_indices_v2.json')

VALID_EXTS    = {'.jpg', '.jpeg', '.png', '.webp'}
IMG_SIZE      = 224
BATCH_SIZE    = 16
EPOCHS_P1     = 12
EPOCHS_P2     = 10
VAL_SPLIT     = 0.15
MAX_PER_CLASS = 2000

# Label smoothing factor — positive labels become (1 - ε), negatives become ε.
# Prevents the model collapsing to 0/1 extremes and improves calibration.
LABEL_SMOOTH  = 0.05


# ── Data collection & staging (unchanged from v1) ─────────────────────────────

def collect_images():
    buckets = {}
    for src_dir in DS7_DARK_CIRCLES:
        if not os.path.exists(src_dir):
            continue
        for f in Path(src_dir).glob('*'):
            if f.suffix.lower() in VALID_EXTS and f.stat().st_size > 2000:
                buckets.setdefault('dark_circles', []).append(f)
    for root in SCAN_ROOTS:
        if not os.path.exists(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            folder  = os.path.basename(dirpath)
            concern = FOLDER_TO_CLASS.get(folder)
            if concern is None:
                continue
            for fname in filenames:
                p = Path(dirpath) / fname
                if p.suffix.lower() in VALID_EXTS and p.stat().st_size > 2000:
                    buckets.setdefault(concern, []).append(p)
    return buckets


def stage_data():
    print("\n" + "=" * 60)
    print("STAGING DATA")
    print("=" * 60)
    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    buckets      = collect_images()
    class_counts = {}
    for concern, images in sorted(buckets.items()):
        dest = os.path.join(STAGING_DIR, concern)
        os.makedirs(dest, exist_ok=True)
        seen, dedup = set(), []
        for p in images:
            if p.name not in seen:
                seen.add(p.name)
                dedup.append(p)
        random.shuffle(dedup)
        dedup = dedup[:MAX_PER_CLASS]
        for i, src in enumerate(dedup):
            shutil.copy2(src, os.path.join(dest, f'{concern}_{i:05d}{src.suffix.lower()}'))
        class_counts[concern] = len(dedup)
        flag = 'OK ' if len(dedup) >= 300 else 'LOW'
        print(f"  [{flag}] {concern:15s}: {len(dedup):,} images")
    print(f"\n  Total: {sum(class_counts.values()):,} images across {len(class_counts)} classes")
    return class_counts


# ── Dataset pipeline ──────────────────────────────────────────────────────────

def build_datasets(class_names, n_classes):
    import tensorflow as tf
    all_paths, all_labels = [], []
    for idx, concern in enumerate(class_names):
        for f in Path(os.path.join(STAGING_DIR, concern)).glob('*'):
            if f.suffix.lower() in VALID_EXTS:
                all_paths.append(str(f))
                all_labels.append(idx)
    combined = list(zip(all_paths, all_labels))
    random.shuffle(combined)
    all_paths, all_labels = zip(*combined)
    n     = len(all_paths)
    n_val = int(n * VAL_SPLIT)
    print(f"\n  Train: {n - n_val:,}  Val: {n_val:,}  Total: {n:,}")

    def load_train(path, label):
        img     = tf.io.read_file(path)
        img     = tf.image.decode_image(img, channels=3, expand_animations=False)
        img     = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img     = tf.cast(img, tf.float32) / 255.0
        one_hot = tf.one_hot(label, n_classes)
        one_hot = one_hot * (1.0 - LABEL_SMOOTH) + LABEL_SMOOTH / n_classes
        return img, one_hot

    def load_val(path, label):
        img     = tf.io.read_file(path)
        img     = tf.image.decode_image(img, channels=3, expand_animations=False)
        img     = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img     = tf.cast(img, tf.float32) / 255.0
        one_hot = tf.one_hot(label, n_classes)   # hard labels only
        return img, one_hot

    def aug(img, label):
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.15)
        img = tf.image.random_contrast(img, 0.85, 1.15)
        img = tf.image.random_saturation(img, 0.85, 1.15)
        img = tf.image.random_hue(img, 0.04)
        crop_frac = tf.random.uniform([], 0.88, 1.0)
        crop_size = tf.cast(tf.cast(IMG_SIZE, tf.float32) * crop_frac, tf.int32)
        img = tf.image.random_crop(img, tf.stack([crop_size, crop_size, 3]))
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        return tf.clip_by_value(img, 0.0, 1.0), label

    def make_ds(paths, labels, training):
        loader = load_train if training else load_val
        ds = (tf.data.Dataset.from_tensor_slices((list(paths), list(labels)))
              .map(loader, num_parallel_calls=tf.data.AUTOTUNE))
        if training:
            ds = ds.map(aug, num_parallel_calls=tf.data.AUTOTUNE).shuffle(1024)
        return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    return (make_ds(all_paths[:n-n_val], all_labels[:n-n_val], True),
            make_ds(all_paths[n-n_val:], all_labels[n-n_val:], False))


# ── Model architecture ────────────────────────────────────────────────────────

def build_model(n_classes):
    """
    MobileNetV2 backbone with:
      - Multi-scale feature fusion (fine 28×28 + coarse 7×7)
      - Squeeze-and-Excitation recalibration on coarse features
      - Deeper shared head (512→256→128) with BN + Dropout
      - Per-concern prediction branches (32→1 each) with sigmoid
    """
    from tensorflow import keras

    # ── Base model ────────────────────────────────────────────────────────────
    base = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3),
        include_top=False,
        weights='imagenet',
    )
    base.trainable = False

    # Build a sub-model that exposes two intermediate outputs:
    #   fine:   block_6_expand_relu  → 28×28×192  (fine-grained; good for texture/blackheads)
    #   coarse: final conv output    → 7×7×1280   (global; good for redness/dark-circles)
    fine_output   = base.get_layer('block_6_expand_relu').output
    coarse_output = base.output
    feature_extractor = keras.Model(
        inputs=base.input,
        outputs=[fine_output, coarse_output],
        name='feature_extractor',
    )
    feature_extractor.trainable = False

    # ── Input + preprocessing ─────────────────────────────────────────────────
    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name='input_image')
    # Rescaling replaces Lambda — serializes cleanly without safe_mode=False
    x_scaled = keras.layers.Rescaling(scale=2.0, offset=-1.0, name='preprocess')(inputs)

    # ── Multi-scale feature extraction ───────────────────────────────────────
    fine_feat, coarse_feat = feature_extractor(x_scaled, training=False)

    # Fine features: pool the 28×28 spatial map
    fine_gap = keras.layers.GlobalAveragePooling2D(name='fine_gap')(fine_feat)
    fine_gap = keras.layers.BatchNormalization(name='fine_bn')(fine_gap)
    fine_proj = keras.layers.Dense(128, activation='relu', name='fine_proj')(fine_gap)

    # Coarse features: Squeeze-and-Excitation recalibration before pooling.
    # SE block: learns which of the 1280 channels are important for skin concerns
    # rather than averaging all channels equally.
    coarse_gap = keras.layers.GlobalAveragePooling2D(name='coarse_gap')(coarse_feat)
    se = keras.layers.Dense(
        64, activation='relu', name='se_squeeze',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(coarse_gap)
    se = keras.layers.Dense(
        coarse_gap.shape[-1], activation='sigmoid', name='se_excite',
    )(se)
    coarse_recal = keras.layers.Multiply(name='se_recalibrate')([coarse_gap, se])
    coarse_recal = keras.layers.BatchNormalization(name='coarse_bn')(coarse_recal)
    coarse_proj  = keras.layers.Dense(256, activation='relu', name='coarse_proj')(coarse_recal)

    # Fuse fine + coarse into a single feature vector
    fused = keras.layers.Concatenate(name='multi_scale_fusion')([fine_proj, coarse_proj])

    # ── Shared concern head ───────────────────────────────────────────────────
    # Three Dense blocks with BN + Dropout give the model capacity to learn
    # combinations of multi-scale features that co-occur with each concern.
    h = keras.layers.Dense(
        512, activation='relu', name='shared_fc1',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(fused)
    h = keras.layers.BatchNormalization(name='shared_bn1')(h)
    h = keras.layers.Dropout(0.40, name='shared_drop1')(h)

    h = keras.layers.Dense(
        256, activation='relu', name='shared_fc2',
        kernel_regularizer=keras.regularizers.l2(1e-4),
    )(h)
    h = keras.layers.BatchNormalization(name='shared_bn2')(h)
    h = keras.layers.Dropout(0.35, name='shared_drop2')(h)

    h = keras.layers.Dense(
        128, activation='relu', name='shared_fc3',
    )(h)
    h = keras.layers.BatchNormalization(name='shared_bn3')(h)
    h = keras.layers.Dropout(0.25, name='shared_drop3')(h)

    # ── Per-concern prediction branches ──────────────────────────────────────
    # Each concern gets its own Dense(32) → Dense(1, sigmoid) branch.
    # This means acne, texture, redness etc. each learn their own decision
    # boundary from the shared features rather than sharing weights in one
    # Dense(n_classes) layer.
    concern_outputs = []
    for i in range(n_classes):
        branch = keras.layers.Dense(
            32, activation='relu', name=f'concern_{i}_fc',
        )(h)
        branch = keras.layers.Dropout(0.15, name=f'concern_{i}_drop')(branch)
        out    = keras.layers.Dense(
            1, activation='sigmoid', name=f'concern_{i}_out',
        )(branch)
        concern_outputs.append(out)

    # Concatenate all per-concern outputs → (batch, n_classes)
    if n_classes > 1:
        outputs = keras.layers.Concatenate(name='concerns_output')(concern_outputs)
    else:
        outputs = concern_outputs[0]

    return keras.Model(inputs, outputs, name='lumera_concern_v2'), base


# ── Training ──────────────────────────────────────────────────────────────────

def train():
    import tensorflow as tf
    from tensorflow import keras
    random.seed(42); np.random.seed(42); tf.random.set_seed(42)

    class_counts = stage_data()
    class_names  = sorted(class_counts.keys())
    n_classes    = len(class_names)
    print(f"\n  Classes ({n_classes}): {class_names}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(OUTPUT_IDX, 'w') as f:
        json.dump({name: i for i, name in enumerate(class_names)}, f, indent=2)

    print("\n" + "=" * 60)
    print("BUILDING DATASETS")
    print("=" * 60)
    train_ds, val_ds = build_datasets(class_names, n_classes)

    print("\n" + "=" * 60)
    print("BUILDING MODEL (v2 — multi-scale SE + per-concern branches)")
    print("=" * 60)
    model, base = build_model(n_classes)
    model.summary(line_length=100)

    def make_callbacks(monitor_metric='val_accuracy'):
        return [
            keras.callbacks.EarlyStopping(
                monitor=monitor_metric, patience=5,
                restore_best_weights=True, verbose=1),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=3,
                min_lr=1e-7, verbose=1),
            keras.callbacks.ModelCheckpoint(
                OUTPUT_MODEL, monitor=monitor_metric,
                save_best_only=True, verbose=1),
        ]

    # ── Phase 1: frozen base ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 1 — FROZEN BASE  (LR=1e-3, label_smooth=0.05)")
    print("=" * 60)
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss='binary_crossentropy',
        metrics=['accuracy'],
    )
    model.fit(train_ds, epochs=EPOCHS_P1, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # ── Phase 2: fine-tune top 30 base layers ────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2 — FINE-TUNE TOP 30 LAYERS  (LR=1e-4)")
    print("=" * 60)
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(
        optimizer=keras.optimizers.Adam(1e-4),
        loss='binary_crossentropy',
        metrics=['accuracy'],
    )
    model.fit(train_ds, epochs=EPOCHS_P2, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # ── Phase 3: very gentle fine-tune of top 60 layers ──────────────────────
    # Extra phase with cosine decay allows the per-concern branches to settle
    # without destabilising the earlier base layers.
    print("\n" + "=" * 60)
    print("PHASE 3 — DEEP FINE-TUNE TOP 60 LAYERS  (LR=5e-5, cosine decay)")
    print("=" * 60)
    for layer in base.layers[:-60]:
        layer.trainable = False
    for layer in base.layers[-60:]:
        layer.trainable = True

    # Cosine decay: smoothly reduces LR from 5e-5 → 1e-7 over 8 epochs
    steps_per_epoch = len(list(train_ds))
    lr_schedule = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=5e-5,
        decay_steps=8 * steps_per_epoch,
        alpha=0.002,
    )
    model.compile(
        optimizer=keras.optimizers.Adam(lr_schedule),
        loss='binary_crossentropy',
        metrics=['accuracy'],
    )
    model.fit(train_ds, epochs=8, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # ── Final evaluation ──────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("FINAL EVALUATION")
    print("=" * 60)
    loss, acc = model.evaluate(val_ds, verbose=0)
    print(f"  Val accuracy : {acc * 100:.2f}%")
    print(f"  Val loss     : {loss:.4f}")

    y_true_oh, y_pred_prob = [], []
    for imgs, labels in val_ds:
        y_pred_prob.extend(model.predict(imgs, verbose=0).tolist())
        y_true_oh.extend(labels.numpy().tolist())
    y_true_oh   = np.array(y_true_oh)
    y_pred_prob = np.array(y_pred_prob)

    # Use 0.5 on the raw sigmoid output (label smoothing only affects training)
    y_pred_bin = (y_pred_prob >= 0.5).astype(int)
    # True labels: smooth targets → round back to binary for metric
    y_true_bin = (y_true_oh >= 0.5).astype(int)

    print("\n  Per-class accuracy (threshold=0.5):")
    for i, name in enumerate(class_names):
        correct = np.mean(y_pred_bin[:, i] == y_true_bin[:, i])
        print(f"    {name:15s}: {correct*100:5.1f}%  {'#'*int(correct*30)}")

    print(f"\n  Model : {OUTPUT_MODEL}")
    print(f"  Index : {OUTPUT_IDX}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("LUMERA — CONCERN MODEL TRAINING  (v2)")
    print("=" * 60)
    print("\nChecking data sources...")
    buckets = collect_images()
    if not buckets:
        print("\n  No images found. Run download_concern_datasets.py first.")
    else:
        for concern, imgs in sorted(buckets.items()):
            flag = 'OK ' if len(imgs) >= 300 else 'LOW'
            print(f"  [{flag}] {concern:15s}: {len(imgs):,} images")
        print(f"\n  Total: {sum(len(v) for v in buckets.values()):,} images")
        low = [c for c, imgs in buckets.items() if len(imgs) < 300]
        if low:
            print(f"  Low-data classes (consider gathering more): {low}")
        train()
