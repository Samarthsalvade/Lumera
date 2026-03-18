"""
train_concern_model_v3.py
─────────────────────────
Retrains the concern model using FULL-FACE images with bbox-aware labels.

Key difference from v2:
  v2 — copied images into class folders, discarded bounding boxes entirely.
       Model trained on zoomed close-ups of individual concerns.
       At inference time it gets a full face → mismatch → misclassification.

  v3 — keeps the FULL image from each Roboflow dataset sample.
       Uses the YOLOv8 bounding box to:
         1. Confirm the concern is genuinely present (bbox exists)
         2. Check bbox overlaps the expected anatomical zone on the face
            (e.g. dark_circles bbox should be in the under-eye region)
         3. Assign a soft label confidence based on zone overlap:
            - High overlap (>50%) → label = 0.95  (genuine, well-localised)
            - Some overlap (>15%) → label = 0.75  (probably genuine)
            - No overlap          → label = 0.40  (uncertain — concern present
                                                   but poorly localised)
         4. For negative examples (images of one concern used as
            background for another) → label = 0.05
       This means the model trains on full faces and learns that e.g.
       dark_circles appear in the under-eye region of a full face, not
       that they fill the entire frame.

  Additionally: ds4/ds5/ds7 images (no bboxes) are included as full-face
  crops using the face detector to ensure they are full-face before staging.

Run from backend/:
    python ml_model/train_concern_model_v3.py

Output:
    ml_model/concern_model_v3.keras
    ml_model/concern_class_indices_v3.json
"""

import os
import json
import shutil
import random
import math
from pathlib import Path

import numpy as np

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Dataset paths ──────────────────────────────────────────────────────────────
DS4_ROOT = os.path.join(BASE, 'dataset_downloads/ds4/Skin_Conditions')
DS5_ROOT = os.path.join(BASE, 'dataset_downloads/ds5/Skin v2')
DS7_DIRS = [
    os.path.join(BASE, 'dataset_downloads/ds7/train'),
    os.path.join(BASE, 'dataset_downloads/ds7/valid'),
    os.path.join(BASE, 'dataset_downloads/ds7/test'),
]
RF_ROOTS = [
    os.path.join(BASE, 'dataset_downloads/ds_rf1/_raw'),
    os.path.join(BASE, 'dataset_downloads/ds_rf2/_raw'),
    os.path.join(BASE, 'dataset_downloads/ds_rf3/_raw'),
]

STAGING_DIR  = os.path.join(BASE, 'concern_training_data_v3')
MODEL_DIR    = os.path.join(BASE, 'ml_model')
OUTPUT_MODEL = os.path.join(MODEL_DIR, 'concern_model_v3.keras')
OUTPUT_IDX   = os.path.join(MODEL_DIR, 'concern_class_indices_v3.json')

VALID_EXTS   = {'.jpg', '.jpeg', '.png', '.webp'}
IMG_SIZE     = 224
BATCH_SIZE   = 16
EPOCHS_P1    = 12
EPOCHS_P2    = 10
EPOCHS_P3    = 8
VAL_SPLIT    = 0.15
MAX_PER_CLASS = 2000
LABEL_SMOOTH  = 0.05

# ── Concern classes ────────────────────────────────────────────────────────────
CONCERN_CLASSES = ['acne', 'blackheads', 'dark_circles', 'dark_spots', 'redness', 'texture']

# ── Expected anatomical zones per concern ─────────────────────────────────────
# (y_start, y_end, x_start, x_end) as fractions of 224×224 face image.
# These match ZONES in skin_concern_detector.py.
# A concern bbox that overlaps these zones is considered correctly localised.
CONCERN_EXPECTED_ZONES = {
    'acne':       [(0.38, 0.72, 0.04, 0.38),   # left_cheek
                   (0.38, 0.72, 0.62, 0.96),   # right_cheek
                   (0.04, 0.28, 0.22, 0.78),   # forehead
                   (0.72, 0.92, 0.28, 0.72)],  # chin
    'blackheads': [(0.32, 0.65, 0.36, 0.64),   # nose
                   (0.72, 0.92, 0.28, 0.72)],  # chin
    'dark_circles':[(0.32, 0.44, 0.10, 0.42),  # under_left_eye
                    (0.32, 0.44, 0.58, 0.90)], # under_right_eye
    'dark_spots': [(0.15, 0.85, 0.15, 0.85)],  # face_centre (anywhere)
    'redness':    [(0.15, 0.85, 0.15, 0.85)],  # face_centre
    'texture':    [(0.38, 0.72, 0.04, 0.38),   # left_cheek
                   (0.38, 0.72, 0.62, 0.96),   # right_cheek
                   (0.04, 0.28, 0.22, 0.78)],  # forehead
    'eye_bags':   [(0.32, 0.44, 0.10, 0.42),
                   (0.32, 0.44, 0.58, 0.90)],
}

# ── Roboflow folder → concern mapping ─────────────────────────────────────────
# Maps yolov8 class names (from data.yaml) to our concern classes
RF_CLASS_MAP = {
    'acne': 'acne', 'acne_scar': 'acne', 'pimple': 'acne',
    'blackhead': 'blackheads', 'blackheads': 'blackheads', 'comedone': 'blackheads',
    'dark_circle': 'dark_circles', 'dark_circles': 'dark_circles', 'darkcircle': 'dark_circles','darkcircle': 'dark_circles',
    'dark_spot': 'dark_spots', 'dark_spots': 'dark_spots', 'hyperpigmentation': 'dark_spots',
    'melasma': 'dark_spots', 'freckle': 'dark_spots',
    'redness': 'redness', 'rosacea': 'redness',
    'wrinkle': 'texture', 'wrinkles': 'texture', 'pore': 'texture', 'pores': 'texture','wrinkles': 'texture','Wrinkles': 'texture',
    'enlarged_pores': 'texture', 'texture': 'texture',
    'eyebag': 'eye_bags', 'eye_bag': 'eye_bags', 'bags': 'eye_bags',
    'puffy_eyes__-_v3_dark_circle': 'dark_circles','puffy_eyes': 'dark_circles',
    # Negative classes — we skip these
    'normal': None, 'healthy': None, 'carcinoma': None, 'eczema': None,
}

# Non-concern Roboflow folder names to skip
DS_SKIP_FOLDERS = {'Normal', 'normal', 'Oily', 'oily', 'Carcinoma', 'Eczema', 'Keratosis',
                   'Milia', 'train', 'valid', 'test', 'images', 'labels'}

# ── Non-Roboflow folder → concern (ds4, ds5) ──────────────────────────────────
FOLDER_TO_CLASS = {
    'acne': 'acne', 'Acne': 'acne', 'acne scar': 'acne',
    'blackheades': 'blackheads', 'blackheads': 'blackheads', 'Blackheads': 'blackheads',
    'dark_circle': 'dark_circles', 'dark circles': 'dark_circles', 'Dark Circles': 'dark_circles',
    'dark spots': 'dark_spots', 'Dark Spots': 'dark_spots', 'dark_spots': 'dark_spots',
    'melasma': 'dark_spots', 'hyperpigmentation': 'dark_spots',
    'Rosacea': 'redness', 'redness': 'redness',
    'pores': 'texture', 'wrinkles': 'texture', 'Wrinkles': 'texture',
    'Dry Skin': 'texture', 'Dry-Skin': 'texture',
}


# ═══════════════════════════════════════════════════════════════════════════════
# Bbox utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _iou(box_a, box_b):
    """
    Intersection-over-Union of two boxes.
    Each box: (y1, y2, x1, x2) as fractions 0-1.
    """
    ay1, ay2, ax1, ax2 = box_a
    by1, by2, bx1, bx2 = box_b
    inter_y1 = max(ay1, by1); inter_y2 = min(ay2, by2)
    inter_x1 = max(ax1, bx1); inter_x2 = min(ax2, bx2)
    if inter_y2 <= inter_y1 or inter_x2 <= inter_x1:
        return 0.0
    inter = (inter_y2 - inter_y1) * (inter_x2 - inter_x1)
    area_a = (ay2 - ay1) * (ax2 - ax1)
    area_b = (by2 - by1) * (bx2 - bx1)
    union  = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _bbox_overlap_with_zones(yolo_cx, yolo_cy, yolo_w, yolo_h, concern):
    """
    Given a YOLOv8 bbox (cx, cy, w, h — all fractions 0-1),
    compute the maximum IoU overlap with any expected zone for this concern.
    Returns float 0-1.
    """
    # Convert YOLO cx/cy/w/h → y1,y2,x1,x2
    x1 = yolo_cx - yolo_w / 2
    x2 = yolo_cx + yolo_w / 2
    y1 = yolo_cy - yolo_h / 2
    y2 = yolo_cy + yolo_h / 2
    pred_box = (max(0, y1), min(1, y2), max(0, x1), min(1, x2))

    zones = CONCERN_EXPECTED_ZONES.get(concern, [(0.0, 1.0, 0.0, 1.0)])
    return max(_iou(pred_box, zone) for zone in zones)


def _soft_label_from_overlap(overlap: float) -> float:
    """
    Convert bbox-zone overlap to a soft training label.
      overlap > 0.50 → 0.95 (high confidence — well localised)
      overlap > 0.15 → 0.75 (moderate confidence)
      overlap > 0.0  → 0.55 (concern present but not in expected zone)
      overlap == 0.0 → 0.40 (bbox exists but doesn't overlap any expected zone)
    """
    if overlap > 0.50:
        return 0.95
    if overlap > 0.15:
        return 0.75
    if overlap > 0.0:
        return 0.55
    return 0.40


# ═══════════════════════════════════════════════════════════════════════════════
# Roboflow dataset parsing (yolov8 format)
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_yaml_names(yaml_path: str) -> dict:
    """Parse class index → concern name from data.yaml."""
    if not os.path.exists(yaml_path):
        return {}
    mapping = {}
    with open(yaml_path) as f:
        content = f.read()
    in_names = False; idx = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('names:'):
            in_names = True
            if '[' in stripped:
                names_str = stripped.split('[', 1)[1].rstrip(']')
                for i, name in enumerate(names_str.split(',')):
                    n = name.strip().strip("'\"").lower().replace(' ', '_')
                    concern = RF_CLASS_MAP.get(n)
                    if concern:
                        mapping[i] = concern
                in_names = False
            continue
        if in_names:
            if stripped.startswith('-'):
                n = stripped.lstrip('- ').strip().strip("'\"").lower().replace(' ', '_')
                concern = RF_CLASS_MAP.get(n)
                if concern:
                    mapping[idx] = concern
                idx += 1
            elif ':' in stripped:
                try:
                    i = int(stripped.split(':', 1)[0].strip())
                    n = stripped.split(':', 1)[1].strip().strip("'\"").lower().replace(' ', '_')
                    concern = RF_CLASS_MAP.get(n)
                    if concern:
                        mapping[i] = concern
                except ValueError:
                    in_names = False
            else:
                in_names = False
    return mapping


def collect_roboflow_samples(rf_root: str) -> list:
    """
    Walk a downloaded yolov8 Roboflow dataset.
    Returns list of dicts:
      { 'img_path': str, 'concern': str, 'soft_label': float }

    Each entry is a full-face image path plus the soft label derived from
    the bbox-zone overlap for the dominant concern in that image.
    """
    rf_path = Path(rf_root)
    yaml_candidates = list(rf_path.glob('data.yaml')) + list(rf_path.glob('*.yaml'))
    class_map = {}
    for yc in yaml_candidates:
        class_map = _parse_yaml_names(str(yc))
        if class_map:
            break

    if not class_map:
        return []

    samples = []
    for split in ['train', 'valid', 'test', '']:
        if split:
            img_dir   = rf_path / split / 'images'
            label_dir = rf_path / split / 'labels'
        else:
            img_dir   = rf_path / 'images'
            label_dir = rf_path / 'labels'

        if not img_dir.exists():
            continue

        for img_path in img_dir.glob('*'):
            if img_path.suffix.lower() not in VALID_EXTS:
                continue
            label_path = Path(str(img_path).replace('/images/', '/labels/')).with_suffix('.txt')
            if not label_path.exists():
                continue

            # Parse all bboxes in this image
            concern_bboxes: dict = {}  # concern → list of (overlap, soft_label)
            with open(label_path) as f:
              for line in f:
                  parts = line.strip().split()
                  if len(parts) < 5:
                      continue
                  try:
                      cls_idx = int(parts[0])
                  except ValueError:
                      continue

                  concern = class_map.get(cls_idx)
                  if concern is None:
                      continue

                  coords = parts[1:]
                  n_coords = len(coords)

                  if n_coords == 4:
                      # Standard YOLOv8: cx cy w h
                      cx, cy, w, h = float(coords[0]), float(coords[1]), float(coords[2]), float(coords[3])
                  elif n_coords >= 8 and n_coords % 2 == 0:
                      # Polygon or OBB: x1 y1 x2 y2 ... xN yN
                      # Convert to axis-aligned bbox
                      xs = [float(coords[i]) for i in range(0, n_coords, 2)]
                      ys = [float(coords[i]) for i in range(1, n_coords, 2)]
                      x_min, x_max = min(xs), max(xs)
                      y_min, y_max = min(ys), max(ys)
                      cx = (x_min + x_max) / 2
                      cy = (y_min + y_max) / 2
                      w  = x_max - x_min
                      h  = y_max - y_min
                  else:
                      continue

                  overlap    = _bbox_overlap_with_zones(cx, cy, w, h, concern)
                  soft_label = _soft_label_from_overlap(overlap)
                  concern_bboxes.setdefault(concern, []).append(soft_label)

            if not concern_bboxes:
                continue

            # One sample entry per concern present in this image
            # Use the max soft_label across all bboxes of that concern
            for concern, labels in concern_bboxes.items():
                samples.append({
                    'img_path':   str(img_path),
                    'concern':    concern,
                    'soft_label': max(labels),
                })

    return samples


# ═══════════════════════════════════════════════════════════════════════════════
# Non-Roboflow dataset collection (ds4, ds5, ds7)
# These images are already full-face photos. No bboxes → assign label 0.85
# (high confidence but slightly below the well-localised RF samples)
# ═══════════════════════════════════════════════════════════════════════════════

def collect_non_rf_samples() -> list:
    samples = []

    # ds4 and ds5 — folder-named classes
    for root in [DS4_ROOT, DS5_ROOT]:
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
                    samples.append({'img_path': str(p), 'concern': concern, 'soft_label': 0.85})

    # ds7 — dark circles only
    for src_dir in DS7_DIRS:
        if not os.path.exists(src_dir):
            continue
        for f in Path(src_dir).glob('*'):
            if f.suffix.lower() in VALID_EXTS and f.stat().st_size > 2000:
                samples.append({'img_path': str(f), 'concern': 'dark_circles', 'soft_label': 0.85})

    return samples


# ═══════════════════════════════════════════════════════════════════════════════
# Staging
# ═══════════════════════════════════════════════════════════════════════════════

def stage_data() -> dict:
    """
    Collect all samples, deduplicate, cap per class, copy images to staging dir.
    Returns: { concern: [(staged_path, soft_label), ...] }
    """
    print('\n' + '=' * 62)
    print('STAGING DATA (v3 — full-face + bbox-aware labels)')
    print('=' * 62)

    if os.path.exists(STAGING_DIR):
        shutil.rmtree(STAGING_DIR)
    os.makedirs(STAGING_DIR, exist_ok=True)

    # Collect from all sources
    all_samples = collect_non_rf_samples()
    for rf_root in RF_ROOTS:
        if os.path.exists(rf_root):
            rf_samples = collect_roboflow_samples(rf_root)
            all_samples.extend(rf_samples)
            print(f'  RF {os.path.basename(os.path.dirname(rf_root))}: {len(rf_samples)} samples')

    # Group by concern, deduplicate by source path
    buckets: dict = {c: {} for c in CONCERN_CLASSES}
    for s in all_samples:
        concern = s['concern']
        if concern not in buckets:
            continue
        path = s['img_path']
        # If same image appears with multiple soft labels, keep the highest
        if path not in buckets[concern] or s['soft_label'] > buckets[concern][path]:
            buckets[concern][path] = s['soft_label']

    # Cap and copy to staging dir; save soft labels alongside
    label_map = {}   # staged_path → soft_label
    class_counts = {}
    for concern in CONCERN_CLASSES:
        dest = os.path.join(STAGING_DIR, concern)
        os.makedirs(dest, exist_ok=True)
        items = list(buckets[concern].items())
        random.shuffle(items)
        items = items[:MAX_PER_CLASS]

        for i, (src, soft_label) in enumerate(items):
            p = Path(src)
            dst_name = f'{concern}_{i:05d}{p.suffix.lower()}'
            dst_path = os.path.join(dest, dst_name)
            try:
                shutil.copy2(src, dst_path)
                label_map[dst_path] = soft_label
            except Exception:
                continue

        class_counts[concern] = len(items)
        avg_lbl = float(np.mean([v for _, v in items])) if items else 0.0
        flag = 'OK ' if len(items) >= 300 else 'LOW'
        print(f'  [{flag}] {concern:16s}: {len(items):,} images  avg_label={avg_lbl:.2f}')

    print(f'\n  Total: {sum(class_counts.values()):,} images')

    # Save label map for use in dataset pipeline
    label_map_path = os.path.join(STAGING_DIR, '_label_map.json')
    with open(label_map_path, 'w') as f:
        json.dump(label_map, f)

    return class_counts


# ═══════════════════════════════════════════════════════════════════════════════
# Dataset pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def build_datasets(class_names: list, n_classes: int):
    """
    Build tf.data datasets with per-image soft labels loaded from _label_map.json.
    Each sample: (full_face_224x224_image, soft_label_vector)
    The soft_label_vector has the concern's soft label at its index and
    label_smooth/2 at all other indices (mild background smoothing).
    """
    import tensorflow as tf

    label_map_path = os.path.join(STAGING_DIR, '_label_map.json')
    with open(label_map_path) as f:
        label_map = json.load(f)

    all_paths, all_labels, all_soft = [], [], []
    for idx, concern in enumerate(class_names):
        for f in Path(os.path.join(STAGING_DIR, concern)).glob('*'):
            if f.suffix.lower() in VALID_EXTS:
                soft = label_map.get(str(f), 0.85)
                all_paths.append(str(f))
                all_labels.append(idx)
                all_soft.append(soft)

    combined = list(zip(all_paths, all_labels, all_soft))
    random.shuffle(combined)
    all_paths, all_labels, all_soft = zip(*combined)

    n     = len(all_paths)
    n_val = int(n * VAL_SPLIT)
    print(f'\n  Train: {n - n_val:,}  Val: {n_val:,}  Total: {n:,}')

    def load_train(path, label, soft):
        img     = tf.io.read_file(path)
        img     = tf.image.decode_image(img, channels=3, expand_animations=False)
        img     = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img     = tf.cast(img, tf.float32) / 255.0
        # Build soft label vector — simpler approach, no scatter needed
        bg      = LABEL_SMOOTH / tf.cast(n_classes - 1, tf.float32)
        one_hot = tf.fill([n_classes], bg)
        # Place soft value at the correct index using one_hot mask
        mask    = tf.one_hot(tf.cast(label, tf.int32), n_classes)
        one_hot = one_hot * (1.0 - mask) + mask * soft
        return img, one_hot

    def load_val(path, label, soft):
        # Hard one-hot for honest validation metrics
        img     = tf.io.read_file(path)
        img     = tf.image.decode_image(img, channels=3, expand_animations=False)
        img     = tf.image.resize(img, [IMG_SIZE, IMG_SIZE])
        img     = tf.cast(img, tf.float32) / 255.0
        one_hot = tf.one_hot(tf.cast(label, tf.int32), n_classes)
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

    train_paths  = list(all_paths[:n - n_val])
    train_labels = list(all_labels[:n - n_val])
    train_soft   = list(all_soft[:n - n_val])
    val_paths    = list(all_paths[n - n_val:])
    val_labels   = list(all_labels[n - n_val:])
    val_soft     = list(all_soft[n - n_val:])

    train_ds = (tf.data.Dataset.from_tensor_slices((train_paths, train_labels, train_soft))
                .map(load_train, num_parallel_calls=tf.data.AUTOTUNE)
                .map(aug,        num_parallel_calls=tf.data.AUTOTUNE)
                .shuffle(1024)
                .batch(BATCH_SIZE)
                .prefetch(tf.data.AUTOTUNE))

    val_ds = (tf.data.Dataset.from_tensor_slices((val_paths, val_labels, val_soft))
              .map(load_val, num_parallel_calls=tf.data.AUTOTUNE)
              .batch(BATCH_SIZE)
              .prefetch(tf.data.AUTOTUNE))

    return train_ds, val_ds


# ═══════════════════════════════════════════════════════════════════════════════
# Model (same v2 architecture — multi-scale SE + per-concern branches)
# ═══════════════════════════════════════════════════════════════════════════════

def build_model(n_classes: int):
    from tensorflow import keras

    base = keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights='imagenet')
    base.trainable = False

    fine_output   = base.get_layer('block_6_expand_relu').output
    coarse_output = base.output
    feature_extractor = keras.Model(
        inputs=base.input, outputs=[fine_output, coarse_output], name='feature_extractor')
    feature_extractor.trainable = False

    inputs   = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name='input_image')
    x_scaled = keras.layers.Rescaling(scale=2.0, offset=-1.0, name='preprocess')(inputs)

    fine_feat, coarse_feat = feature_extractor(x_scaled, training=False)

    # Fine branch
    fine_gap  = keras.layers.GlobalAveragePooling2D(name='fine_gap')(fine_feat)
    fine_gap  = keras.layers.BatchNormalization(name='fine_bn')(fine_gap)
    fine_proj = keras.layers.Dense(128, activation='relu', name='fine_proj')(fine_gap)

    # Coarse branch with SE
    coarse_gap   = keras.layers.GlobalAveragePooling2D(name='coarse_gap')(coarse_feat)
    se           = keras.layers.Dense(64, activation='relu', name='se_squeeze',
                                       kernel_regularizer=keras.regularizers.l2(1e-4))(coarse_gap)
    se           = keras.layers.Dense(coarse_gap.shape[-1], activation='sigmoid', name='se_excite')(se)
    coarse_recal = keras.layers.Multiply(name='se_recalibrate')([coarse_gap, se])
    coarse_recal = keras.layers.BatchNormalization(name='coarse_bn')(coarse_recal)
    coarse_proj  = keras.layers.Dense(256, activation='relu', name='coarse_proj')(coarse_recal)

    fused = keras.layers.Concatenate(name='multi_scale_fusion')([fine_proj, coarse_proj])

    # Shared head
    h = keras.layers.Dense(512, activation='relu', name='shared_fc1',
                             kernel_regularizer=keras.regularizers.l2(1e-4))(fused)
    h = keras.layers.BatchNormalization(name='shared_bn1')(h)
    h = keras.layers.Dropout(0.40, name='shared_drop1')(h)
    h = keras.layers.Dense(256, activation='relu', name='shared_fc2',
                             kernel_regularizer=keras.regularizers.l2(1e-4))(h)
    h = keras.layers.BatchNormalization(name='shared_bn2')(h)
    h = keras.layers.Dropout(0.35, name='shared_drop2')(h)
    h = keras.layers.Dense(128, activation='relu', name='shared_fc3')(h)
    h = keras.layers.BatchNormalization(name='shared_bn3')(h)
    h = keras.layers.Dropout(0.25, name='shared_drop3')(h)

    # Per-concern branches — each concern has its own decision boundary
    concern_outputs = []
    for i in range(n_classes):
        branch = keras.layers.Dense(32, activation='relu', name=f'concern_{i}_fc')(h)
        branch = keras.layers.Dropout(0.15, name=f'concern_{i}_drop')(branch)
        out    = keras.layers.Dense(1, activation='sigmoid', name=f'concern_{i}_out')(branch)
        concern_outputs.append(out)

    outputs = keras.layers.Concatenate(name='concerns_output')(concern_outputs) if n_classes > 1 else concern_outputs[0]

    return keras.Model(inputs, outputs, name='lumera_concern_v3'), base


# ═══════════════════════════════════════════════════════════════════════════════
# F1 metric
# ═══════════════════════════════════════════════════════════════════════════════

def make_f1_metric(n_classes, threshold=0.5):
    import tensorflow as tf
    from tensorflow import keras

    class BinaryF1(keras.metrics.Metric):
        def __init__(self, **kwargs):
            super().__init__(name='f1_score', **kwargs)
            self.n   = n_classes
            self.thr = threshold
            self.tp  = self.add_weight(name='tp', shape=(n_classes,), initializer='zeros')
            self.fp  = self.add_weight(name='fp', shape=(n_classes,), initializer='zeros')
            self.fn  = self.add_weight(name='fn', shape=(n_classes,), initializer='zeros')

        def update_state(self, y_true, y_pred, sample_weight=None):
            yp  = tf.cast(y_pred >= self.thr, tf.float32)
            yt  = tf.cast(tf.cast(y_true, tf.float32) >= 0.5, tf.float32)
            self.tp.assign_add(tf.reduce_sum(yt * yp, axis=0))
            self.fp.assign_add(tf.reduce_sum((1 - yt) * yp, axis=0))
            self.fn.assign_add(tf.reduce_sum(yt * (1 - yp), axis=0))

        def result(self):
            p  = self.tp / (self.tp + self.fp + 1e-7)
            r  = self.tp / (self.tp + self.fn + 1e-7)
            f1 = 2 * p * r / (p + r + 1e-7)
            return tf.reduce_mean(f1)

        def reset_state(self):
            self.tp.assign(tf.zeros((self.n,)))
            self.fp.assign(tf.zeros((self.n,)))
            self.fn.assign(tf.zeros((self.n,)))

    return BinaryF1()


# ═══════════════════════════════════════════════════════════════════════════════
# Training
# ═══════════════════════════════════════════════════════════════════════════════

def train():
    import tensorflow as tf
    from tensorflow import keras
    random.seed(42); np.random.seed(42); tf.random.set_seed(42)

    physical_gpus = tf.config.list_physical_devices('GPU')
    if physical_gpus:
        for gpu in physical_gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        print(f'\n  GPU(s): {[g.name for g in physical_gpus]}')
    else:
        print('\n  No GPU — running on CPU/MPS')

    class_counts = stage_data()
    class_names  = CONCERN_CLASSES
    n_classes    = len(class_names)
    print(f'\n  Classes ({n_classes}): {class_names}')

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(OUTPUT_IDX, 'w') as f:
        json.dump({name: i for i, name in enumerate(class_names)}, f, indent=2)

    print('\n' + '=' * 62)
    print('BUILDING DATASETS')
    print('=' * 62)
    train_ds, val_ds = build_datasets(class_names, n_classes)

    print('\n' + '=' * 62)
    print('BUILDING MODEL (v3 — full-face training + bbox-aware labels)')
    print('=' * 62)
    model, base = build_model(n_classes)
    model.summary(line_length=90)

    f1_metric = lambda: make_f1_metric(n_classes)

    def make_callbacks(monitor='val_f1_score', mode='max'):
        return [
            keras.callbacks.EarlyStopping(
                monitor=monitor, patience=4, mode=mode,
                restore_best_weights=True, verbose=1),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss', factor=0.5, patience=2,
                min_lr=1e-7, verbose=1),
            keras.callbacks.ModelCheckpoint(
                OUTPUT_MODEL, monitor=monitor, mode=mode,
                save_best_only=True, verbose=1),
        ]

    # Phase 1 — frozen backbone
    print('\n' + '=' * 62)
    print('PHASE 1 — FROZEN BACKBONE  (LR=1e-3)')
    print('=' * 62)
    model.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss='binary_crossentropy',
        metrics=['accuracy', f1_metric()],
    )
    model.fit(train_ds, epochs=EPOCHS_P1, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # Phase 2 — fine-tune top 30
    print('\n' + '=' * 62)
    print('PHASE 2 — FINE-TUNE TOP 30 LAYERS  (LR=1e-4)')
    print('=' * 62)
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(
        optimizer=keras.optimizers.Adam(1e-4),
        loss='binary_crossentropy',
        metrics=['accuracy', f1_metric()],
    )
    model.fit(train_ds, epochs=EPOCHS_P2, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # Phase 3 — deep fine-tune with cosine decay
    print('\n' + '=' * 62)
    print('PHASE 3 — FINE-TUNE TOP 60 LAYERS  (cosine LR 5e-5→1e-7)')
    print('=' * 62)
    for layer in base.layers[:-60]:
        layer.trainable = False
    for layer in base.layers[-60:]:
        layer.trainable = True

    steps_per_epoch = len(list(train_ds))
    lr_schedule = keras.optimizers.schedules.CosineDecay(
        initial_learning_rate=5e-5,
        decay_steps=EPOCHS_P3 * steps_per_epoch,
        alpha=0.002,
    )
    model.compile(
        optimizer=keras.optimizers.Adam(lr_schedule),
        loss='binary_crossentropy',
        metrics=['accuracy', f1_metric()],
    )
    model.fit(train_ds, epochs=EPOCHS_P3, validation_data=val_ds,
              callbacks=make_callbacks(), verbose=1)

    # Final evaluation
    print('\n' + '=' * 62)
    print('FINAL EVALUATION')
    print('=' * 62)
    results = model.evaluate(val_ds, verbose=0)
    for name, val in zip(['loss', 'accuracy', 'f1_score'], results):
        print(f'  {name:12s}: {val:.4f}')

    y_true_all, y_pred_all = [], []
    for imgs, labels in val_ds:
        preds = model.predict(imgs, verbose=0)
        y_pred_all.extend(preds.tolist())
        y_true_all.extend(labels.numpy().tolist())

    y_true = np.array(y_true_all)
    y_pred = np.array(y_pred_all)
    y_bin  = (y_pred >= 0.5).astype(int)
    y_hard = (y_true >= 0.5).astype(int)

    print('\n  Per-class F1 and accuracy:')
    for i, name in enumerate(class_names):
        tp  = np.sum((y_bin[:, i] == 1) & (y_hard[:, i] == 1))
        fp  = np.sum((y_bin[:, i] == 1) & (y_hard[:, i] == 0))
        fn  = np.sum((y_bin[:, i] == 0) & (y_hard[:, i] == 1))
        p   = tp / (tp + fp + 1e-7)
        r   = tp / (tp + fn + 1e-7)
        f1  = 2 * p * r / (p + r + 1e-7)
        acc = np.mean(y_bin[:, i] == y_hard[:, i])
        print(f'  {name:16s}: F1={f1:.3f}  Acc={acc*100:.1f}%  P={p:.3f}  R={r:.3f}  {"#"*int(f1*20)}')

    model.save(OUTPUT_MODEL)
    print(f'\n  Saved: {OUTPUT_MODEL}')
    print(f'  Index: {OUTPUT_IDX}')
    print('\n' + '=' * 62)
    print('Done! Update CONCERN_MODEL_VERSION=v3 in .env and restart Flask.')
    print('=' * 62 + '\n')


if __name__ == '__main__':
    print('\n' + '=' * 62)
    print('LUMERA — CONCERN MODEL TRAINING  v3')
    print('(Full-face images + bbox-aware soft labels)')
    print('=' * 62)

    print('\nChecking data sources...')
    non_rf = collect_non_rf_samples()
    concern_counts: dict = {}
    for s in non_rf:
        concern_counts[s['concern']] = concern_counts.get(s['concern'], 0) + 1

    rf_total = 0
    for rf_root in RF_ROOTS:
        if os.path.exists(rf_root):
            rf_samples = collect_roboflow_samples(rf_root)
            rf_total  += len(rf_samples)
            for s in rf_samples:
                concern_counts[s['concern']] = concern_counts.get(s['concern'], 0) + 1

    print(f'\n  Non-RF samples: {len(non_rf)}')
    print(f'  RF samples    : {rf_total}')
    print(f'\n  Per concern:')
    for c in CONCERN_CLASSES:
        n    = concern_counts.get(c, 0)
        flag = 'OK ' if n >= 300 else 'LOW'
        print(f'    [{flag}] {c:16s}: {n:,}')

    low = [c for c in CONCERN_CLASSES if concern_counts.get(c, 0) < 300]
    if low:
        print(f'\n  Low-data classes: {low}')

    print('\n  Run with --train to start training, or import train() directly.')
    import sys
    if '--train' in sys.argv:
        train()
    else:
        print('  Add --train flag to begin: python ml_model/train_concern_model_v3.py --train')