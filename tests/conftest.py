# SPDX-License-Identifier: AGPL-3.0-or-later
import os, random, sys
from datetime import date, datetime
from zoneinfo import ZoneInfo
import pytest

os.environ.setdefault("DATA_DIR", "/tmp/mf-tests")
os.environ.setdefault("APP_PASSWORD", "test-password")
os.environ.setdefault("COOKIE_SECURE", "false")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import config, db, ingredients as I, seed_recipes  # noqa: E402


class Clock:
    def __init__(self):
        self.day = date(2026, 11, 16)  # un lundi

    def advance(self, n):
        from datetime import timedelta
        self.day += timedelta(days=n)


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(config, "today", lambda: c.day)
    monkeypatch.setattr(config, "now", lambda: datetime(c.day.year, c.day.month, c.day.day, 12, 0, tzinfo=ZoneInfo("Europe/Paris")))
    return c


@pytest.fixture
def conn(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "menu.db")
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    c = db.connect()
    db.migrate(c)
    I.seed_catalog(c)
    cat = I.Catalog(c.execute("SELECT * FROM ingredients").fetchall())
    seed_recipes.load_seed(c, cat)
    yield c
    c.close()


@pytest.fixture
def rng():
    return random.Random(42)
