"""
download_concern_datasets.py  (fixed)
──────────────────────────────────────
All three Roboflow datasets are object-detection projects.
Downloads them in yolov8 format (which always works), then
extracts just the images into the flat folder structure that
train_concern_model_v2.py expects.

Bounding box label files are discarded — we only need the images
since our model is a classifier, not a detector.

Run from backend/:
    python download_concern_datasets.py
"""

import os
import shutil
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = os.path.join(BASE, 'dataset_downloads')

# ── Roboflow datasets (all object-detection → use yolov8 format) ──────────────
RF_DATASETS = [
    {
        'label':    'Acne + Dark Circles + Wrinkles (3607 images)',
        'workspace':'facialanalysis',
        'project':  'acne-darkcircles-wrinkles',
        'version':  1,
        'dest':     'ds_rf1',
    },
    {
        'label':    'Dark Circles dedicated (1114 images)',
        'workspace':'skin-condition-detection',
        'project':  'dark-circles-19mqw',
        'version':  1,
        'dest':     'ds_rf2',
    },
    {
        'label':    'Facial Health full suite',
        'workspace':'testing-rfihx',
        'project':  'facial-health',
        'version':  1,
        'dest':     'ds_rf3',
    },
]

# Map folder names / label names from YOLO label files to concern classes.
# YOLOv8 datasets store class names in data.yaml — we parse that to know
# which images belong to which concern.
LABEL_TO_CONCERN = {
    'acne':              'acne',
    'acne_scar':         'acne',
    'dark_circle':       'dark_circles',
    'dark_circles':      'dark_circles',
    'darkcircle':        'dark_circles',
    'wrinkle':           'texture',
    'wrinkles':          'texture',
    'blackhead':         'blackheads',
    'blackheads':        'blackheads',
    'dark_spot':         'dark_spots',
    'dark_spots':        'dark_spots',
    'redness':           'redness',
    'rosacea':           'redness',
    'eyebag':            'eye_bags',
    'eye_bag':           'eye_bags',
    'pore':              'texture',
    'pores':             'texture',
}


def _parse_yaml_names(yaml_path: str) -> dict:
    """
    Parse class index → concern mapping from a YOLOv8 data.yaml.
    Returns {class_index: concern_name} for known concerns, skips unknowns.
    """
    mapping = {}
    if not os.path.exists(yaml_path):
        return mapping
    with open(yaml_path) as f:
        content = f.read()

    # Find the 'names:' section — handles both list and dict YAML styles
    in_names = False
    idx = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith('names:'):
            in_names = True
            # Inline list: names: [acne, wrinkles, ...]
            if '[' in stripped:
                names_str = stripped.split('[', 1)[1].rstrip(']')
                for i, name in enumerate(names_str.split(',')):
                    name = name.strip().strip("'\"").lower().replace(' ', '_')
                    concern = LABEL_TO_CONCERN.get(name)
                    if concern:
                        mapping[i] = concern
                in_names = False
            continue
        if in_names:
            if stripped.startswith('-'):
                # List item: - acne
                name = stripped.lstrip('- ').strip().strip("'\"").lower().replace(' ', '_')
                concern = LABEL_TO_CONCERN.get(name)
                if concern:
                    mapping[idx] = concern
                idx += 1
            elif ':' in stripped:
                # Dict style: 0: acne
                parts = stripped.split(':', 1)
                try:
                    i = int(parts[0].strip())
                    name = parts[1].strip().strip("'\"").lower().replace(' ', '_')
                    concern = LABEL_TO_CONCERN.get(name)
                    if concern:
                        mapping[i] = concern
                except ValueError:
                    in_names = False
            else:
                in_names = False
    return mapping


def _extract_images_by_concern(raw_dir: str, dest_base: str, dataset_label: str):
    """
    Walk a downloaded YOLOv8 dataset directory.
    For each image, look at its label file to find the dominant class,
    then copy the image to dest_base/<concern>/.

    If no label file exists (image with no annotations), skip it.
    If multiple classes appear in one label file, use the most frequent one.
    """
    raw_path = Path(raw_dir)
    yaml_candidates = list(raw_path.glob('data.yaml')) + list(raw_path.glob('*.yaml'))
    class_map = {}
    for yc in yaml_candidates:
        class_map = _parse_yaml_names(str(yc))
        if class_map:
            break

    if not class_map:
        print(f'    WARNING: Could not parse class names from {raw_dir}')
        print(f'    Copying all images to a holding folder for manual review.')
        holding = os.path.join(dest_base, '_unlabelled')
        os.makedirs(holding, exist_ok=True)
        for img in raw_path.rglob('*'):
            if img.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp'}:
                shutil.copy2(img, holding)
        return

    print(f'    Class map from yaml: {class_map}')

    copied = {}
    skipped = 0

    # YOLOv8 layout: images/train/*.jpg  labels/train/*.txt
    for img_path in raw_path.rglob('*.jpg'):
        # Find corresponding label file
        label_path = Path(str(img_path).replace('/images/', '/labels/').replace('\\images\\', '\\labels\\')).with_suffix('.txt')
        if not label_path.exists():
            # Also try sibling labels/ dir at the split level
            alt = img_path.parent.parent / 'labels' / img_path.parent.name / img_path.with_suffix('.txt').name
            if alt.exists():
                label_path = alt
            else:
                skipped += 1
                continue

        # Count class occurrences in the label file
        class_counts = {}
        with open(label_path) as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    try:
                        cls_idx = int(parts[0])
                        class_counts[cls_idx] = class_counts.get(cls_idx, 0) + 1
                    except ValueError:
                        pass

        if not class_counts:
            skipped += 1
            continue

        # Use the most frequently annotated class in this image
        dominant_cls = max(class_counts, key=class_counts.get)
        concern = class_map.get(dominant_cls)
        if concern is None:
            skipped += 1
            continue

        dest_dir = os.path.join(dest_base, concern)
        os.makedirs(dest_dir, exist_ok=True)
        dest_file = os.path.join(dest_dir, f'{concern}_{img_path.stem}{img_path.suffix}')
        shutil.copy2(img_path, dest_file)
        copied[concern] = copied.get(concern, 0) + 1

    # Also handle .jpeg and .png
    for ext in ['*.jpeg', '*.png']:
        for img_path in raw_path.rglob(ext):
            label_path = Path(str(img_path).replace('/images/', '/labels/').replace('\\images\\', '\\labels\\')).with_suffix('.txt')
            if not label_path.exists():
                continue
            class_counts = {}
            with open(label_path) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        try:
                            cls_idx = int(parts[0])
                            class_counts[cls_idx] = class_counts.get(cls_idx, 0) + 1
                        except ValueError:
                            pass
            if not class_counts:
                continue
            dominant_cls = max(class_counts, key=class_counts.get)
            concern = class_map.get(dominant_cls)
            if concern is None:
                continue
            dest_dir = os.path.join(dest_base, concern)
            os.makedirs(dest_dir, exist_ok=True)
            dest_file = os.path.join(dest_dir, f'{concern}_{img_path.stem}{img_path.suffix}')
            shutil.copy2(img_path, dest_file)
            copied[concern] = copied.get(concern, 0) + 1

    if copied:
        for concern, n in sorted(copied.items()):
            print(f'      → {concern}: {n} images')
    else:
        print(f'      WARNING: No images matched known concern classes.')
    if skipped:
        print(f'      Skipped (no label / unknown class): {skipped}')


def download_roboflow():
    try:
        from roboflow import Roboflow
        import os as _os
        api_key = _os.environ.get('ROBOFLOW_API_KEY', '')
        if not api_key:
            # Try reading from .env
            env_path = _os.path.join(BASE, '.env')
            if _os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        if line.startswith('ROBOFLOW_API_KEY='):
                            api_key = line.split('=', 1)[1].strip().strip('"\'')
        if not api_key:
            print('  ERROR: ROBOFLOW_API_KEY not found.')
            print('  Add it to backend/.env as: ROBOFLOW_API_KEY=your_key_here')
            return
        rf = Roboflow(api_key=api_key)
    except ImportError:
        print('  roboflow package not installed: pip install roboflow')
        return

    for ds in RF_DATASETS:
        print(f'\n[{ds["label"]}]')
        dest = os.path.join(DOWNLOADS, ds['dest'])
        raw  = os.path.join(dest, '_raw')
        os.makedirs(raw, exist_ok=True)

        try:
            project = rf.workspace(ds['workspace']).project(ds['project'])
            version = project.version(ds['version'])
            # yolov8 format works for all object-detection projects
            version.download('yolov8', location=raw, overwrite=True)
            print(f'  Downloaded to {raw}')
            print(f'  Extracting images by concern class...')
            _extract_images_by_concern(raw, dest, ds['label'])
        except Exception as e:
            print(f'  FAILED: {e}')
            print(f'  Try accepting dataset terms at: '
                  f'https://universe.roboflow.com/{ds["workspace"]}/{ds["project"]}')


def check_results():
    print('\n' + '=' * 60)
    print('RESULTS')
    print('=' * 60)
    concern_totals = {}
    for ds_folder in ['ds_rf1', 'ds_rf2', 'ds_rf3']:
        ds_path = os.path.join(DOWNLOADS, ds_folder)
        if not os.path.exists(ds_path):
            continue
        for concern_dir in sorted(Path(ds_path).iterdir()):
            if concern_dir.is_dir() and not concern_dir.name.startswith('_'):
                n = len(list(concern_dir.glob('*.*')))
                concern_totals[concern_dir.name] = concern_totals.get(concern_dir.name, 0) + n

    if concern_totals:
        print('\n  Images extracted per concern (across all rf datasets):')
        for concern, n in sorted(concern_totals.items()):
            flag = 'OK ' if n >= 300 else 'LOW'
            print(f'  [{flag}] {concern:16s}: {n:,}')
    else:
        print('  No images extracted yet.')


if __name__ == '__main__':
    print('=' * 60)
    print('DOWNLOADING CONCERN DATASETS FROM ROBOFLOW')
    print('(object-detection projects → yolov8 format → extract images)')
    print('=' * 60)
    os.makedirs(DOWNLOADS, exist_ok=True)
    download_roboflow()
    check_results()
    print('\n' + '=' * 60)
    print('DONE')
    print('Then run: python train_concern_model_v2.py')
    print('=' * 60)