# SPDX-License-Identifier: AGPL-3.0-or-later
"""Configuration par variables d'environnement (voir .env.example)."""
import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "menu.db"
BACKUP_DIR = DATA_DIR / "backups"

APP_USERNAME = os.getenv("APP_USERNAME", "famille")
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
# Derrière un proxy HTTPS : true. En HTTP simple (test local) : false, sinon le
# navigateur refuse silencieusement le cookie de session.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").strip().lower() != "false"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "30"))
TZ_NAME = os.getenv("TZ", "Europe/Paris")
BACKUP_KEEP = int(os.getenv("BACKUP_KEEP", "7"))
# Autoriser l'import d'URL vers des adresses privées (désactivé : protection SSRF)
ALLOW_PRIVATE_FETCH = os.getenv("ALLOW_PRIVATE_FETCH", "false").lower() == "true"


def now() -> datetime:
    return datetime.now(ZoneInfo(TZ_NAME))


def today() -> date:
    return now().date()
