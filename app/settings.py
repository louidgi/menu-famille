# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from copy import deepcopy

DEFAULTS = {
    "plan_days": 7,
    "adults": 2,
    "children_coeffs": [0.5, 0.6, 0.7],  # 3, 4 et 7 ans, en fraction de portion d'adulte (réglable)
    "meals": {str(d): {"lunch": d in (5, 6), "dinner": True} for d in range(7)},  # 0 = lundi
    "busy_days": [0, 3],
    "weekly_budget": None,
    "no_repeat_days": 21,
}


def get_settings(conn) -> dict:
    s = deepcopy(DEFAULTS)
    for r in conn.execute("SELECT key, value FROM settings"):
        if r["key"] in s:
            s[r["key"]] = json.loads(r["value"])
    return s


def put_settings(conn, patch: dict) -> dict:
    for k, v in patch.items():
        if k in DEFAULTS:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
    conn.commit()
    return get_settings(conn)


def family_eq(s: dict) -> float:
    """Nombre de portions d'adulte à préparer."""
    return float(s["adults"]) + sum(s["children_coeffs"])
