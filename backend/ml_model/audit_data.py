"""
audit_data.py
─────────────
Run before training to catch problems in training_data/:
  - Corrupt / unreadable images
  - Images that are too small (< 50x50px)
  - Non-face images (very dark, very uniform — likely mislabelled)
  - Class balance report

Usage:
    cd backend
    python audit_data.py

Outputs:
    - Prints a report to the console
    - Saves a list of suspect files to ml_model/audit_suspects.txt
"""

import os
import cv2
import numpy as np
from pathlib import Path

DATA_DIR   = 'training_data'
OUTPUT_DIR = 'ml_model'
SKIN_TYPES = ['normal', 'oily', 'dry', 'combination', 'sensitive']
VALID_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}

MIN_DIM       = 50       # px — smaller than this is too low res
MAX_DARK_MEAN = 15.0     # images darker than this are likely corrupt/black
MIN_STD       = 8.0      # images with very low std are uniform/blank


def audit():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suspects = []
    counts   = {}

    print("\n" + "=" * 60)
    print("🔍  LUMÉRA — TRAINING DATA AUDIT")
    print("=" * 60)

    for skin in SKIN_TYPES:
        folder = os.path.join(DATA_DIR, skin)
        if not os.path.exists(folder):
            print(f"\n❌  {skin}: folder missing")
            counts[skin] = 0
            continue

        files = [f for f in os.listdir(folder)
                 if Path(f).suffix.lower() in VALID_EXTS]
        counts[skin] = len(files)

        corrupt = 0; too_small = 0; suspect_img = 0

        for fname in files:
            fpath = os.path.join(folder, fname)

            # Unreadable
            img = cv2.imread(fpath)
            if img is None:
                suspects.append(f"[CORRUPT]  {fpath}")
                corrupt += 1
                continue

            h, w = img.shape[:2]

            # Too small
            if h < MIN_DIM or w < MIN_DIM:
                suspects.append(f"[SMALL {w}x{h}]  {fpath}")
                too_small += 1
                continue

            # Blank / very dark
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(float)
            mean_val = float(np.mean(gray))
            std_val  = float(np.std(gray))

            if mean_val < MAX_DARK_MEAN:
                suspects.append(f"[DARK mean={mean_val:.1f}]  {fpath}")
                suspect_img += 1
            elif std_val < MIN_STD:
                suspects.append(f"[UNIFORM std={std_val:.1f}]  {fpath}")
                suspect_img += 1

        flag = '✅' if counts[skin] >= 400 else ('⚠️ ' if counts[skin] >= 100 else '❌')
        print(f"\n  {flag}  {skin:12s}: {counts[skin]:4d} images")
        if corrupt:    print(f"       ❌  Corrupt     : {corrupt}")
        if too_small:  print(f"       ⚠️   Too small   : {too_small}")
        if suspect_img:print(f"       ⚠️   Suspect     : {suspect_img}")

    # ── Class balance ─────────────────────────────────────────────────────────
    total = sum(counts.values())
    print(f"\n{'─'*40}")
    print(f"  TOTAL: {total} images\n")
    print("  Class balance:")
    max_count = max(counts.values()) if counts else 1
    for skin in SKIN_TYPES:
        c   = counts.get(skin, 0)
        bar = '█' * int(c / max_count * 20)
        pct = c / total * 100 if total else 0
        print(f"    {skin:12s} {bar:<20s} {c:4d} ({pct:.1f}%)")

    # ── Recommendations ───────────────────────────────────────────────────────
    print(f"\n  Recommendations:")
    for skin in SKIN_TYPES:
        c = counts.get(skin, 0)
        if c < 100:
            print(f"    🔴  {skin}: CRITICAL — need at least 400 images (have {c})")
        elif c < 400:
            diff = 400 - c
            print(f"    🟡  {skin}: add ~{diff} more images for best results")
        else:
            print(f"    🟢  {skin}: good ({c} images)")

    # ── Save suspect list ─────────────────────────────────────────────────────
    suspect_path = os.path.join(OUTPUT_DIR, 'audit_suspects.txt')
    with open(suspect_path, 'w') as f:
        f.write('\n'.join(suspects))

    if suspects:
        print(f"\n  ⚠️  {len(suspects)} suspect files saved to: {suspect_path}")
        print("     Review and delete them before training.")
    else:
        print(f"\n  ✅  No suspect files found — data looks clean!")

    print("=" * 60 + "\n")


if __name__ == '__main__':
    audit()