"""
train_concern_model.py
──────────────────────
Trains a MobileNetV2 multi-class skin concern classifier.

Concern classes:
  acne, blackheads, dark_circles, dark_spots, eye_bags, redness, texture

eye_bags and lip_hyperpigmentation also retain CV signal fallback.

Run from backend/:
    python train_concern_model.py

Output:
    ml_model/concern_model.keras
    ml_model/concern_class_indices.json
"""

import os, json, shutil, random
import numpy as np
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

BASE = os.path.dirname(os.path.abspath(__file__))

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
    # Explicitly skip
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

STAGING_DIR  = os.path.join(BASE, 'concern_training_data')
MODEL_DIR    = os.path.join(BASE, 'ml_model')
OUTPUT_MODEL = os.path.join(MODEL_DIR, 'concern_model.keras')
OUTPUT_IDX   = os.path.join(MODEL_DIR, 'concern_class_indices.json')

VALID_EXTS   = {'.jpg', '.jpeg', '.png', '.webp'}
IMG_SIZE     = 224
BATCH_SIZE   = 16
EPOCHS_P1    = 10
EPOCHS_P2    = 8
VAL_SPLIT    = 0.15
MAX_PER_CLASS = 2000


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
    print("\n" + "=" * 55)
    print("STAGING DATA")
    print("=" * 55)
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

    def load(path, label):
        img = tf.io.read_file(path)
        img = tf.image.decode_image(img, channels=3, expand_animations=False)
        img = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img = tf.cast(img, tf.float32) / 255.0
        # One-hot label for binary_crossentropy with sigmoid output
        one_hot = tf.one_hot(label, n_classes)
        return img, one_hot

    def aug(img, label):
        img = tf.image.random_flip_left_right(img)
        img = tf.image.random_brightness(img, 0.15)
        img = tf.image.random_contrast(img, 0.85, 1.15)
        img = tf.image.random_saturation(img, 0.85, 1.15)
        img = tf.image.random_hue(img, 0.04)
        return tf.clip_by_value(img, 0.0, 1.0), label

    def make_ds(paths, labels, training):
        ds = (tf.data.Dataset.from_tensor_slices((list(paths), list(labels)))
              .map(load, num_parallel_calls=tf.data.AUTOTUNE))
        if training:
            ds = ds.map(aug, num_parallel_calls=tf.data.AUTOTUNE)
        return ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)

    return (make_ds(all_paths[:n-n_val], all_labels[:n-n_val], True),
            make_ds(all_paths[n-n_val:], all_labels[n-n_val:], False))


def build_model(n_classes):
    from tensorflow import keras
    base    = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights='imagenet')
    base.trainable = False
    inputs  = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    # Rescaling replaces Lambda — serializes cleanly without safe_mode=False
    x       = keras.layers.Rescaling(scale=2.0, offset=-1.0, name='preprocess')(inputs)
    x       = base(x, training=False)
    x       = keras.layers.GlobalAveragePooling2D()(x)
    x       = keras.layers.BatchNormalization()(x)
    x       = keras.layers.Dense(256, activation='relu')(x)
    x       = keras.layers.Dropout(0.4)(x)
    x       = keras.layers.Dense(128, activation='relu')(x)
    x       = keras.layers.Dropout(0.3)(x)
    # sigmoid not softmax — each concern is independent (multi-label)
    # a face can have acne AND dark circles AND texture issues simultaneously
    outputs = keras.layers.Dense(n_classes, activation='sigmoid')(x)
    return keras.Model(inputs, outputs), base


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

    print("\n" + "=" * 55)
    print("BUILDING DATASETS")
    print("=" * 55)
    train_ds, val_ds = build_datasets(class_names, n_classes)

    model, base = build_model(n_classes)

    def make_callbacks():
        return [
            keras.callbacks.EarlyStopping(
                monitor='val_accuracy', patience=4,
                restore_best_weights=True, verbose=1),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=2,
                min_lr=1e-7, verbose=1),
            keras.callbacks.ModelCheckpoint(
                OUTPUT_MODEL, monitor='val_accuracy',
                save_best_only=True, verbose=1),
        ]

    print("\n" + "=" * 55)
    print("PHASE 1 — FROZEN BASE  (LR=1e-3)")
    print("=" * 55)
    # binary_crossentropy treats each output neuron independently (multi-label)
    model.compile(optimizer=keras.optimizers.Adam(1e-3),
                  loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(train_ds, epochs=EPOCHS_P1, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    print("\n" + "=" * 55)
    print("PHASE 2 — FINE-TUNE TOP 30 LAYERS  (LR=1e-4)")
    print("=" * 55)
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(optimizer=keras.optimizers.Adam(1e-4),
                  loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(train_ds, epochs=EPOCHS_P2, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    print("\n" + "=" * 55)
    print("FINAL EVALUATION")
    print("=" * 55)
    loss, acc = model.evaluate(val_ds, verbose=0)
    print(f"  Val accuracy : {acc * 100:.2f}%")
    print(f"  Val loss     : {loss:.4f}")

    # Per-class: sigmoid output — threshold at 0.5 for presence/absence
    y_true_oh, y_pred_prob = [], []
    for imgs, labels in val_ds:
        y_pred_prob.extend(model.predict(imgs, verbose=0).tolist())
        y_true_oh.extend(labels.numpy().tolist())
    y_true_oh   = np.array(y_true_oh)    # (N, n_classes) one-hot
    y_pred_prob = np.array(y_pred_prob)  # (N, n_classes) sigmoid probs
    y_pred_bin  = (y_pred_prob >= 0.5).astype(int)

    print("\n  Per-class accuracy (threshold=0.5):")
    for i, name in enumerate(class_names):
        correct = np.mean(y_pred_bin[:, i] == y_true_oh[:, i].astype(int))
        print(f"    {name:15s}: {correct*100:5.1f}%  {'#'*int(correct*30)}")

    print(f"\n  Model : {OUTPUT_MODEL}")
    print(f"  Index : {OUTPUT_IDX}")


if __name__ == '__main__':
    print("\n" + "=" * 55)
    print("LUMERA — CONCERN MODEL TRAINING")
    print("=" * 55)
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
            print(f"  Low-data classes (will get extra weight): {low}")
        train()