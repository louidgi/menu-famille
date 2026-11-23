# SPDX-License-Identifier: AGPL-3.0-or-later
"""Planning : lecture, génération, remplacement, absence, régénération des repas suivants."""
import json, random
from datetime import date, timedelta
from . import config, planner as P, recipes as R, ingredients as I
from .settings import get_settings, family_eq, busy_set
from .shopping import process_past, add_stock

WEEKDAYS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


class PlanError(Exception):
    pass


def load_cands(conn, fam: float, only_ids=None) -> dict[int, P.Cand]:
    out = {}
    for r in conn.execute("SELECT * FROM recipes WHERE archived=0"):
        if only_ids is not None and r["id"] not in only_ids:
            continue
        rows = R.recipe_ingredients(conn, r["id"])
        out[r["id"]] = P.Cand(
            id=r["id"], title=r["title"], protein=r["protein"], carb=r["carb"], meals=r["meals"],
            minutes=(r["prep_min"] or 0) + (r["cook_min"] or 0) or 60, months=tuple(json.loads(r["months"])),
            cost=R.est_cost(rows, fam / r["servings"]), rating=r["rating"], favorite=bool(r["favorite"]),
            ings=frozenset(x["ingredient"] for x in rows), ings_nb=frozenset(x["ingredient"] for x in rows if not x["is_basic"]))
    return out


def _context(conn, cands, lo: date, hi: date, exclude_ids=()):
    fixed, recent = {}, []
    for p in conn.execute("SELECT * FROM plan WHERE day >= ? AND day <= ? AND recipe_id IS NOT NULL",
                          ((lo - timedelta(days=30)).isoformat(), (hi + timedelta(days=30)).isoformat())):
        c = cands.get(p["recipe_id"])
        if c is None or p["id"] in exclude_ids:
            continue
        d = date.fromisoformat(p["day"])
        if d < config.today():
            recent.append((d, c))
        fixed[(d, p["slot"])] = c
    return fixed, recent


def _stock_names(conn) -> frozenset:
    return frozenset(r["ingredient"] for r in conn.execute("SELECT ingredient FROM stock WHERE qty>0"))


def _refused(conn) -> frozenset:
    return frozenset(r["name"] for r in conn.execute("SELECT name FROM refused"))


def enabled_slots(settings: dict, start: date, days: int) -> list[tuple]:
    out = []
    for i in range(days):
        d = start + timedelta(days=i)
        m = settings["meals"][str(d.weekday())]
        for slot in ("lunch", "dinner"):
            if m.get(slot):
                out.append((d, slot))
    return out


def _fill(conn, slots, *, exclude_ids=(), max_cost=None, avoid_ids=frozenset(), rng=None):
    """Choisit une recette pour chaque créneau en tenant compte des repas conservés autour."""
    s = get_settings(conn)
    fam = family_eq(s)
    cands = load_cands(conn, fam)
    if not slots:
        return {}
    lo, hi = min(d for d, _ in slots), max(d for d, _ in slots)
    fixed, recent = _context(conn, cands, lo, hi, exclude_ids)
    budget = None
    if s.get("weekly_budget"):
        budget = float(s["weekly_budget"]) * max(1, (hi - lo).days + 1) / 7
        budget -= sum(c.cost for (d, sl), c in fixed.items() if lo <= d <= hi)
    return P.generate(slots, list(cands.values()), {k: v for k, v in fixed.items() if k not in set(slots)}, recent,
                      _refused(conn), busy_set(s), in_stock=_stock_names(conn), budget=budget,
                      max_cost=max_cost, avoid_ids=avoid_ids, no_repeat_days=s["no_repeat_days"], rng=rng)


def ensure_plan(conn, days: int | None = None, rng=None) -> None:
    """Complète le planning (sans toucher à l'existant) pour les `days` prochains jours."""
    process_past(conn)
    s = get_settings(conn)
    days = days or s["plan_days"]
    today = config.today()
    have = {(r["day"], r["slot"]) for r in conn.execute("SELECT day, slot FROM plan WHERE day >= ?", (today.isoformat(),))}
    missing = [(d, sl) for d, sl in enabled_slots(s, today, days) if (d.isoformat(), sl) not in have]
    for (d, sl), c in _fill(conn, missing, rng=rng).items():
        conn.execute("INSERT OR IGNORE INTO plan(day, slot, recipe_id) VALUES(?,?,?)",
                     (d.isoformat(), sl, c.id if c else None))
    conn.commit()


def _regen_following(conn, after: tuple, rng=None) -> int:
    """Régénère les repas non verrouillés situés après `after` (date, slot)."""
    rows = conn.execute("SELECT * FROM plan WHERE day >= ? AND locked=0 AND status='planned' AND consumed=0 ORDER BY day",
                        (config.today().isoformat(),)).fetchall()
    todo = [r for r in rows if (date.fromisoformat(r["day"]).toordinal(), P.SLOT_IDX[r["slot"]]) >
            (after[0].toordinal(), P.SLOT_IDX[after[1]])]
    slots = [(date.fromisoformat(r["day"]), r["slot"]) for r in todo]
    res = _fill(conn, slots, exclude_ids={r["id"] for r in todo}, rng=rng)
    for r in todo:
        c = res.get((date.fromisoformat(r["day"]), r["slot"]))
        conn.execute("UPDATE plan SET recipe_id=? WHERE id=?", (c.id if c else None, r["id"]))
    conn.commit()
    return len(todo)


def _row(conn, plan_id: int):
    r = conn.execute("SELECT * FROM plan WHERE id=?", (plan_id,)).fetchone()
    if r is None:
        raise PlanError("Repas introuvable")
    if date.fromisoformat(r["day"]) < config.today():
        raise PlanError("Ce repas est passé")
    return r


def _key(r):
    return (date.fromisoformat(r["day"]), r["slot"])


def generate_all(conn, days: int | None = None, rng=None) -> None:
    """Régénère tout le planning à venir sauf les repas verrouillés, absences et repas passés."""
    s = get_settings(conn)
    today = config.today().isoformat()
    conn.execute("DELETE FROM plan WHERE day >= ? AND locked=0 AND status='planned'", (today,))
    conn.commit()
    ensure_plan(conn, days or s["plan_days"], rng=rng)


def replace_meal(conn, plan_id: int, reason: str, ingredient: str | None = None,
                 regenerate_following: bool = True, rng=None) -> dict:
    r = _row(conn, plan_id)
    old_id = r["recipe_id"]
    max_cost = None
    if reason == "refuse_ingredient":
        if not ingredient:
            raise PlanError("Précisez l'ingrédient refusé")
        cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
        name, _ = cat.match(ingredient)
        name = name or ingredient.strip().lower()
        conn.execute("INSERT OR IGNORE INTO refused(name) VALUES(?)", (name,))
    elif reason == "too_expensive" and old_id:
        old = load_cands(conn, family_eq(get_settings(conn)), only_ids={old_id}).get(old_id)
        max_cost = old.cost if old else None  # ne vaut que pour ce remplacement
    elif reason != "other":
        raise PlanError("Motif inconnu")
    res = _fill(conn, [_key(r)], exclude_ids={r["id"]}, max_cost=max_cost,
                avoid_ids=frozenset({old_id} if old_id else ()), rng=rng)
    new = res.get(_key(r))
    if new is None:
        raise PlanError("Aucune autre recette ne convient (aliments refusés, budget ou bibliothèque trop petite)")
    conn.execute("UPDATE plan SET recipe_id=?, status='planned', locked=1 WHERE id=?", (new.id, plan_id))
    conn.commit()
    regenerated = _regen_following(conn, _key(r), rng=rng) if regenerate_following else 0
    return {"new_recipe_id": new.id, "regenerated": regenerated}


def skip_meal(conn, plan_id: int, regenerate_following: bool = True, rng=None) -> dict:
    r = _row(conn, plan_id)
    conn.execute("UPDATE plan SET status='skipped', recipe_id=NULL, locked=1 WHERE id=?", (plan_id,))
    conn.commit()
    return {"regenerated": _regen_following(conn, _key(r), rng=rng) if regenerate_following else 0}


def restore_meal(conn, plan_id: int, rng=None) -> None:
    r = _row(conn, plan_id)
    new = _fill(conn, [_key(r)], exclude_ids={r["id"]}, rng=rng).get(_key(r))
    conn.execute("UPDATE plan SET status='planned', recipe_id=?, locked=0 WHERE id=?", (new.id if new else None, plan_id))
    conn.commit()


def add_meal(conn, day: str, slot: str, rng=None) -> int:
    d = date.fromisoformat(day)
    if d < config.today() or slot not in P.SLOT_IDX:
        raise PlanError("Créneau invalide")
    conn.execute("INSERT OR IGNORE INTO plan(day, slot) VALUES(?,?)", (day, slot))
    r = conn.execute("SELECT * FROM plan WHERE day=? AND slot=?", (day, slot)).fetchone()
    new = _fill(conn, [(d, slot)], exclude_ids={r["id"]}, rng=rng).get((d, slot))
    conn.execute("UPDATE plan SET status='planned', recipe_id=?, locked=1 WHERE id=?", (new.id if new else None, r["id"]))
    conn.commit()
    return r["id"]


def set_lock(conn, plan_id: int, locked: bool) -> None:
    _row(conn, plan_id)
    conn.execute("UPDATE plan SET locked=? WHERE id=?", (int(locked), plan_id))
    conn.commit()


def set_recipe(conn, plan_id: int, recipe_id: int, regenerate_following: bool = False, rng=None) -> dict:
    """Choix manuel d'une recette de la bibliothèque (le repas est alors verrouillé)."""
    r = _row(conn, plan_id)
    if not conn.execute("SELECT 1 FROM recipes WHERE id=? AND archived=0", (recipe_id,)).fetchone():
        raise PlanError("Recette introuvable")
    conn.execute("UPDATE plan SET recipe_id=?, status='planned', locked=1 WHERE id=?", (recipe_id, plan_id))
    conn.commit()
    return {"regenerated": _regen_following(conn, _key(r), rng=rng) if regenerate_following else 0}


def get_plan(conn, days: int | None = None) -> dict:
    s = get_settings(conn)
    days = days or s["plan_days"]
    today = config.today()
    fam = family_eq(s)
    rows = conn.execute("SELECT p.*, r.title, r.protein, r.carb, r.prep_min, r.cook_min, r.image_url, r.source_type, "
                        "r.rating, r.favorite, r.servings FROM plan p LEFT JOIN recipes r ON r.id=p.recipe_id "
                        "WHERE p.day >= ? AND p.day <= ? ORDER BY p.day", (today.isoformat(),
                                                                          (today + timedelta(days=days - 1)).isoformat())).fetchall()
    costs = {}
    by_day: dict[str, list] = {}
    total = 0.0
    for p in rows:
        cost = None
        if p["recipe_id"]:
            if p["recipe_id"] not in costs:
                costs[p["recipe_id"]] = R.est_cost(R.recipe_ingredients(conn, p["recipe_id"]), fam / p["servings"])
            cost = costs[p["recipe_id"]]
            total += cost
        by_day.setdefault(p["day"], []).append({
            "id": p["id"], "slot": p["slot"], "status": p["status"], "locked": bool(p["locked"]),
            "cost": cost, "recipe": None if not p["recipe_id"] else {
                "id": p["recipe_id"], "title": p["title"], "protein": p["protein"], "carb": p["carb"],
                "minutes": (p["prep_min"] or 0) + (p["cook_min"] or 0), "image_url": p["image_url"],
                "rating": p["rating"], "favorite": bool(p["favorite"])}})
    out_days = []
    for i in range(days):
        d = today + timedelta(days=i)
        ents = sorted(by_day.get(d.isoformat(), []), key=lambda e: P.SLOT_IDX[e["slot"]])
        used = {e["slot"] for e in ents}
        out_days.append({"date": d.isoformat(), "weekday": WEEKDAYS[d.weekday()], "entries": ents,
                         "free_slots": [x for x in ("lunch", "dinner") if x not in used]})
    budget = s.get("weekly_budget")
    return {"days": out_days, "total_cost": round(total, 2),
            "budget": None if not budget else round(float(budget) * days / 7, 2)}
