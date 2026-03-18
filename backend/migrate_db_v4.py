"""
migrate_db_v4.py
────────────────
Adds annotated_image_b64 TEXT column to skin_concerns table.
Run once from backend/:  python migrate_db_v4.py
"""

import sqlite3
import os

DB_PATH = os.path.join('instance', 'lumera.db')


def migrate():
    if not os.path.exists(DB_PATH):
        print(f'[ERROR] Database not found at {DB_PATH}')
        print('Make sure you run this from the backend/ directory.')
        return

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # Check existing columns
    cur.execute("PRAGMA table_info(skin_concerns)")
    existing = {row[1] for row in cur.fetchall()}

    if 'annotated_image_b64' in existing:
        print('[SKIP] annotated_image_b64 column already exists in skin_concerns.')
    else:
        cur.execute("ALTER TABLE skin_concerns ADD COLUMN annotated_image_b64 TEXT DEFAULT ''")
        print('[OK] Added annotated_image_b64 to skin_concerns.')

    conn.commit()
    conn.close()
    print('[DONE] Migration v4 complete.')


if __name__ == '__main__':
    migrate()