"""
merge_datasets.py
─────────────────
Run from backend/ after downloading datasets into dataset_downloads/.
Scans all subdirectories, maps folder names to skin type labels,
and copies images into training_data/ without duplicates.

Usage:
    cd backend
    python merge_datasets.py
"""

import os
import shutil
import hashlib
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DOWNLOAD_DIR  = 'dataset_downloads'
TRAINING_DIR  = 'training_data'
VALID_EXTS    = {'.jpg', '.jpeg', '.png', '.webp'}
MIN_FILE_SIZE = 2_000    # bytes — skip corrupt/tiny files

# ── Folder name → skin type mapping ──────────────────────────────────────────
# Covers all folder names found across your 3 downloaded datasets
LABEL_MAP = {
    # ── English ───────────────────────────────────────────────────────────────
    'normal':           'normal',
    'oily':             'oily',
    'dry':              'dry',
    'combination':      'combination',
    'sensitive':        'sensitive',

    # ── Indonesian (ds2: berminyak=oily, kering=dry, normal=normal) ───────────
    'berminyak':        'oily',      # Indonesian: "oily"
    'kering':           'dry',       # Indonesian: "dry"

    # ── Explicitly SKIP these — skin diseases, not skin types ─────────────────
    # ds4 folders — do not map, will be ignored
    'carcinoma':        None,
    'keratosis':        None,
    'acne':             None,
    'eczema':           None,
    'rosacea':          None,
    'milia':            None,
    'berjerawat':       None,        # Indonesian: "acne"
}

SKIN_TYPES = ['normal', 'oily', 'dry', 'combination', 'sensitive']

# Folder names to skip entirely (parent containers, not label folders)
SKIP_FOLDERS = {
    'oily-dry-skin-types', 'skin2', 'skin_type_classification_dataset',
    'skin_conditions', 'dataset_downloads',
    'train', 'valid', 'test',   # split folders — we merge all splits
    'ds1', 'ds2', 'ds3', 'ds4',
}


def file_hash(path: str) -> str:
    """MD5 hash of first 8KB — fast duplicate detection."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        h.update(f.read(8192))
    return h.hexdigest()


def ensure_dirs():
    for skin in SKIN_TYPES:
        os.makedirs(os.path.join(TRAINING_DIR, skin), exist_ok=True)


def collect_existing_hashes() -> set:
    """Build a set of hashes for all existing training images."""
    hashes = set()
    for skin in SKIN_TYPES:
        folder = os.path.join(TRAINING_DIR, skin)
        if not os.path.exists(folder):
            continue
        for f in os.listdir(folder):
            fp = os.path.join(folder, f)
            if os.path.isfile(fp) and Path(fp).suffix.lower() in VALID_EXTS:
                hashes.add(file_hash(fp))
    return hashes


def resolve_label(folder_name: str):
    """
    Return skin type label for a folder name, or None to skip.
    Returns False if the folder name is unrecognised (warn user).
    """
    key = folder_name.lower().strip()

    # Explicit skip
    if key in SKIP_FOLDERS:
        return None

    # Direct map (including None = explicit skip)
    if key in LABEL_MAP:
        return LABEL_MAP[key]

    # Partial match against skin type names
    for skin in SKIN_TYPES:
        if skin in key:
            return skin

    # Unrecognised — return False so we can warn
    return False


def merge():
    ensure_dirs()
    all_hashes = collect_existing_hashes()

    counters   = {s: 0 for s in SKIN_TYPES}
    skipped    = 0
    unmatched  = set()

    for root, dirs, files in os.walk(DOWNLOAD_DIR):
        folder_name = os.path.basename(root)
        label = resolve_label(folder_name)

        if label is None:
            # Explicit skip (container folder or disease class)
            continue

        if label is False:
            # Unrecognised folder — warn if it has images
            imgs = [f for f in files if Path(f).suffix.lower() in VALID_EXTS]
            if imgs:
                unmatched.add(f"{folder_name} ({len(imgs)} images, path: {root})")
            continue

        # Valid label — copy images
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in VALID_EXTS:
                continue

            src = os.path.join(root, fname)

            if os.path.getsize(src) < MIN_FILE_SIZE:
                skipped += 1
                continue

            h = file_hash(src)
            if h in all_hashes:
                skipped += 1
                continue
            all_hashes.add(h)

            dest_dir  = os.path.join(TRAINING_DIR, label)
            safe_name = f"merged_{label}_{counters[label]:06d}{ext}"
            dest      = os.path.join(dest_dir, safe_name)

            shutil.copy2(src, dest)
            counters[label] += 1

    # ── Report ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("📊  MERGE COMPLETE")
    print("=" * 55)

    total_added = sum(counters.values())
    for skin in SKIN_TYPES:
        existing = len([
            f for f in os.listdir(os.path.join(TRAINING_DIR, skin))
            if Path(f).suffix.lower() in VALID_EXTS
        ])
        added = counters[skin]
        flag  = '✅' if existing >= 400 else ('⚠️ ' if existing >= 100 else '❌')
        print(f"  {flag}  {skin:12s}: +{added:4d} added  →  {existing:4d} total")

    print(f"\n  Total added  : {total_added}")
    print(f"  Skipped      : {skipped} (duplicates or too small)")

    if unmatched:
        print(f"\n⚠️  Unrecognised folders — add to LABEL_MAP if needed:")
        for name in sorted(unmatched):
            print(f"     {name}")
    else:
        print("\n✅  All folders recognised — no unmatched classes.")

    print("\n  Next steps:")
    print("    python audit_data.py        ← check for corrupt images")
    print("    python ml_model/train_model.py  ← train the model")
    print("=" * 55 + "\n")


if __name__ == '__main__':
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"❌  '{DOWNLOAD_DIR}/' folder not found.")
        print("    Download datasets first — see download_datasets.md")
        exit(1)
    merge()