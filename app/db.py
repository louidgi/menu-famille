# SPDX-License-Identifier: AGPL-3.0-or-later
"""SQLite : connexion, schéma versionné."""
import sqlite3
from . import config

SCHEMA_V1 = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE ingredients (
    name TEXT PRIMARY KEY, aliases TEXT NOT NULL DEFAULT '[]', aisle TEXT NOT NULL DEFAULT 'Divers',
    kind TEXT NOT NULL DEFAULT 'g',            -- unité de base : g | ml | piece
    piece_g REAL, density REAL NOT NULL DEFAULT 1.0,
    pack_qty REAL, pack_label TEXT, price REAL,  -- prix estimé d'un paquet (ou d'une unité de pas)
    is_basic INTEGER NOT NULL DEFAULT 0, is_recurrent INTEGER NOT NULL DEFAULT 0,
    weekly_qty REAL, verified INTEGER NOT NULL DEFAULT 1);
CREATE TABLE recipes (
    id INTEGER PRIMARY KEY, title TEXT NOT NULL, source_url TEXT, source_type TEXT NOT NULL,
    image_url TEXT, servings REAL NOT NULL DEFAULT 4, prep_min INTEGER, cook_min INTEGER,
    meals TEXT NOT NULL DEFAULT 'dl',           -- d=dîner, l=déjeuner
    protein TEXT NOT NULL DEFAULT 'autre', carb TEXT NOT NULL DEFAULT 'autre',
    months TEXT NOT NULL DEFAULT '[]', tags TEXT NOT NULL DEFAULT '[]', steps TEXT NOT NULL DEFAULT '[]',
    rating INTEGER NOT NULL DEFAULT 0, favorite INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE recipe_ingredients (
    id INTEGER PRIMARY KEY, recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient TEXT NOT NULL REFERENCES ingredients(name), qty REAL, unit TEXT,
    raw TEXT NOT NULL, optional INTEGER NOT NULL DEFAULT 0);
CREATE INDEX idx_ri_recipe ON recipe_ingredients(recipe_id);
CREATE TABLE refused (name TEXT PRIMARY KEY);
CREATE TABLE plan (
    id INTEGER PRIMARY KEY, day TEXT NOT NULL, slot TEXT NOT NULL CHECK (slot IN ('lunch','dinner')),
    recipe_id INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','skipped')),
    locked INTEGER NOT NULL DEFAULT 0, consumed INTEGER NOT NULL DEFAULT 0, note TEXT,
    UNIQUE (day, slot));
CREATE TABLE stock (ingredient TEXT PRIMARY KEY REFERENCES ingredients(name), qty REAL NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL);
CREATE TABLE shop_state (ingredient TEXT PRIMARY KEY REFERENCES ingredients(name),
    archived_need REAL, checked_on TEXT, forced INTEGER NOT NULL DEFAULT 0);
CREATE TABLE ops (op_id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
"""

SCHEMA_V2 = "ALTER TABLE shop_state ADD COLUMN bought_qty REAL;"   # NULL = inconnu (achats d'avant la migration)


MIGRATIONS = [SCHEMA_V1, SCHEMA_V2] # ajouter ici les migrations suivantes, jamais modifier les anciennes


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    has_meta = conn.execute("SELECT 1 FROM sqlite_master WHERE name='meta'").fetchone()
    version = 0
    if has_meta:
        row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        version = int(row["value"]) if row else 0
    if version > len(MIGRATIONS):
        raise RuntimeError(f"Base en version {version}, plus récente que l'application ({len(MIGRATIONS)}).")
    for i in range(version, len(MIGRATIONS)):
        conn.executescript(MIGRATIONS[i])
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(i + 1),))
        conn.commit()
