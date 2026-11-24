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
    "shopping_locked_only": False,   # courses = repas verrouillés seulement
    "busy_slots": {str(d): {"lunch": False, "dinner": d in (0, 3)} for d in range(7)},  # 0 = lundi
    "fish_days": [4],   # jours « poisson » par défaut (0 = lundi) ; vendredi
}

def get_settings(conn) -> dict:
    s = deepcopy(DEFAULTS)
    stored = {r["key"]: json.loads(r["value"]) for r in conn.execute("SELECT key, value FROM settings")}
    for k in s:
        if k in stored:
            s[k] = stored[k]
    # Migration : ancien réglage « jours chargés » (midi et soir) tant que busy_slots n'a pas été enregistré
    if "busy_slots" not in stored and "busy_days" in stored:
        old = set(stored["busy_days"])
        s["busy_slots"] = {str(d): {"lunch": d in old, "dinner": d in old} for d in range(7)}
    return s


def busy_set(s: dict) -> set:
    """{(jour_de_semaine, 'lunch'|'dinner')} des repas chargés."""
    return {(int(d), sl) for d, m in s["busy_slots"].items() for sl, v in m.items() if v}

def put_settings(conn, patch: dict) -> dict:
    for k, v in patch.items():
        if k == "fish_days":   # int() est appelé ailleurs : on refuse tout ce qui n'est pas un jour valide
            v = sorted({int(x) for x in v if str(x).isdigit() and 0 <= int(x) <= 6})
        if k in DEFAULTS:
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (k, json.dumps(v)))
    conn.commit()
    return get_settings(conn)


def family_eq(s: dict) -> float:
    """Nombre de portions d'adulte à préparer."""
    return float(s["adults"]) + sum(s["children_coeffs"])
