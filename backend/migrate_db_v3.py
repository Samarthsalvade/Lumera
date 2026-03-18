"""
migrate_db_v3.py
────────────────
Adds v3 columns and creates new tables.
Run ONCE from backend/:
    python migrate_db_v3.py
"""
import sqlite3, os

DB_PATHS = ['instance/lumera.db', 'lumera.db']
DB_PATH  = next((p for p in DB_PATHS if os.path.exists(p)), None)

if not DB_PATH:
    print("❌  Database not found. Start the app once first to create it.")
    exit(1)

print(f"✓  Found database: {DB_PATH}")
conn   = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ── Add skin_concerns column to analyses ──────────────────────────────────────
cursor.execute("PRAGMA table_info(analyses)")
existing = {row[1] for row in cursor.fetchall()}
if 'skin_concerns' not in existing:
    cursor.execute("ALTER TABLE analyses ADD COLUMN skin_concerns TEXT DEFAULT '{}'")
    print("✅  Added column: analyses.skin_concerns")
else:
    print("ℹ️   Already exists: analyses.skin_concerns")

# ── Create new tables (idempotent) ────────────────────────────────────────────
cursor.executescript("""
CREATE TABLE IF NOT EXISTS skin_concerns (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id         INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    concern_type        TEXT    NOT NULL,
    confidence          REAL    NOT NULL,
    severity            TEXT,
    notes               TEXT,
    annotated_image_b64 TEXT    DEFAULT '',
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS product_recommendations (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name     TEXT NOT NULL,
    brand            TEXT NOT NULL,
    skin_types       TEXT NOT NULL,
    concerns         TEXT NOT NULL,
    key_ingredients  TEXT NOT NULL,
    description      TEXT,
    price_range      TEXT,
    url              TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routines (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    routine_type  TEXT NOT NULL,
    name          TEXT NOT NULL,
    based_on_scan INTEGER REFERENCES analyses(id),
    description   TEXT,
    is_active     BOOLEAN DEFAULT 1,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routine_steps (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id       INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    "order"          INTEGER NOT NULL,
    product_type     TEXT NOT NULL,
    instruction      TEXT NOT NULL,
    duration_seconds INTEGER,
    key_ingredient   TEXT,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

# Verify
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = {row[0] for row in cursor.fetchall()}
for t in ['skin_concerns', 'product_recommendations', 'routines', 'routine_steps']:
    flag = '✅' if t in tables else '❌'
    print(f"  {flag}  Table: {t}")

conn.close()
print("\n✅  Migration v3 complete.")