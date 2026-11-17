# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persistance des recettes, mise à l'échelle pour la famille, estimation de coût, affichage des quantités."""
import json, math
from . import config
from . import ingredients as I

PROTEINS = ["volaille", "boeuf", "porc", "poisson", "oeuf", "veggie", "autre"]
CARBS = ["pates", "riz", "pdt", "semoule", "pain", "autre"]


def save_recipe(conn, cat: I.Catalog, d: dict, recipe_id: int | None = None) -> int:
    """d : title, steps[list], ingredients[list de str ou {raw, ingredient}], + champs optionnels."""
    cols = dict(
        title=d["title"].strip(), source_url=d.get("source_url"), source_type=d.get("source_type", "manual"),
        image_url=d.get("image_url"), servings=float(d.get("servings") or 4), prep_min=d.get("prep_min"),
        cook_min=d.get("cook_min"), meals=d.get("meals", "dl"),
        protein=d.get("protein", "autre") if d.get("protein") in PROTEINS else "autre",
        carb=d.get("carb", "autre") if d.get("carb") in CARBS else "autre",
        months=json.dumps(d.get("months", [])), tags=json.dumps(d.get("tags", []), ensure_ascii=False),
        steps=json.dumps(d.get("steps", []), ensure_ascii=False),
    )
    if recipe_id is None:
        cur = conn.execute(
            f"INSERT INTO recipes({','.join(cols)},created_at) VALUES({','.join('?' * len(cols))},?)",
            (*cols.values(), config.now().isoformat()))
        recipe_id = cur.lastrowid
    else:
        conn.execute(f"UPDATE recipes SET {','.join(k + '=?' for k in cols)} WHERE id=?", (*cols.values(), recipe_id))
        conn.execute("DELETE FROM recipe_ingredients WHERE recipe_id=?", (recipe_id,))
    for item in d.get("ingredients", []):
        raw = item if isinstance(item, str) else item["raw"]
        parsed = I.parse_line(raw)
        forced = None if isinstance(item, str) else item.get("ingredient")
        if forced:
            if forced not in cat.rows:
                conn.execute("INSERT OR IGNORE INTO ingredients(name,aliases,aisle,kind,verified) VALUES(?,?,?,?,0)",
                             (forced, "[]", "Divers", "g" if parsed["unit"] in I.MASS else
                              "ml" if parsed["unit"] in I.VOL else "piece"))
                cat.rows[forced] = dict(conn.execute("SELECT * FROM ingredients WHERE name=?", (forced,)).fetchone())
            name, qty = forced, I.to_base(parsed["qty"], parsed["unit"], cat.rows[forced])
        else:
            name, qty, _ = I.resolve(conn, cat, parsed)
        conn.execute("INSERT INTO recipe_ingredients(recipe_id,ingredient,qty,unit,raw,optional) VALUES(?,?,?,?,?,?)",
                     (recipe_id, name, qty, cat.rows[name]["kind"], raw.strip(), int(parsed["optional"])))
    conn.commit()
    return recipe_id


def recipe_ingredients(conn, recipe_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT ri.*, i.aisle, i.is_basic, i.kind, i.price, i.pack_qty, i.verified FROM recipe_ingredients ri "
        "JOIN ingredients i ON i.name = ri.ingredient WHERE ri.recipe_id=? ORDER BY ri.id", (recipe_id,))]


def fmt_qty(q: float | None, kind: str) -> str:
    if q is None:
        return ""
    if kind == "g":
        if q >= 1000:
            return f"{round(q / 1000 * 20) / 20:g} kg".replace(".", ",")
        step = 5 if q < 100 else 10 if q < 500 else 25
        return f"{max(step, round(q / step) * step):g} g"
    if kind == "ml":
        if q >= 1000:
            return f"{round(q / 1000 * 20) / 20:g} L".replace(".", ",")
        if q >= 100:
            return f"{round(q / 5) * 5 / 10:g} cl".replace(".", ",")
        return f"{max(5, round(q / 5) * 5):g} ml"
    h = round(q * 2) / 2
    h = max(h, 0.5)
    whole = int(h)
    return (f"{whole} " if whole else "") + ("½" if h - whole else "") if h != whole else f"{whole}"


def scaled_lines(rows: list[dict], factor: float) -> list[dict]:
    out = []
    for r in rows:
        q = None if r["qty"] is None else r["qty"] * factor
        out.append({"ingredient": r["ingredient"], "raw": r["raw"], "aisle": r["aisle"], "basic": bool(r["is_basic"]),
                    "optional": bool(r["optional"]), "qty": q, "kind": r["kind"],
                    "text": "au goût" if r["is_basic"] else (fmt_qty(q, r["kind"]) if q is not None else ""),
                    "verified": bool(r["verified"])})
    return out


def est_cost(rows: list[dict], factor: float) -> float:
    """Coût de consommation (hors basiques) : quantité utilisée × prix par unité de base. Estimation."""
    total = 0.0
    for r in rows:
        if r["is_basic"] or r["optional"] or r["qty"] is None:
            continue
        total += r["qty"] * factor * I.price_per_base(r)
    return round(total, 2)


def recipe_summary(row) -> dict:
    return {"id": row["id"], "title": row["title"], "protein": row["protein"], "carb": row["carb"],
            "prep_min": row["prep_min"], "cook_min": row["cook_min"], "image_url": row["image_url"],
            "source_type": row["source_type"], "rating": row["rating"], "favorite": bool(row["favorite"])}
