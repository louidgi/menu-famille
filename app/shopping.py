# SPDX-License-Identifier: AGPL-3.0-or-later
"""Stock, consommation des repas passés, liste de courses dérivée (besoins du planning − stock)."""
import json, math
from datetime import date, timedelta
from . import config, recipes as R, ingredients as I
from .settings import get_settings, family_eq

AISLES = ["Fruits et légumes", "Boucherie", "Poissonnerie", "Crèmerie", "Boulangerie", "Épicerie", "Conserves",
          "Surgelés", "Boissons", "Hygiène et maison", "Divers"]
EPS = 1e-6


def add_stock(conn, name: str, delta: float) -> None:
    conn.execute("INSERT INTO stock(ingredient, qty, updated_at) VALUES(?, MAX(0, ?), ?) "
                 "ON CONFLICT(ingredient) DO UPDATE SET qty = MAX(0, qty + ?), updated_at = excluded.updated_at",
                 (name, delta, config.now().isoformat(), delta))


def set_stock(conn, name: str, qty: float) -> None:
    conn.execute("INSERT INTO stock(ingredient, qty, updated_at) VALUES(?,?,?) "
                 "ON CONFLICT(ingredient) DO UPDATE SET qty=excluded.qty, updated_at=excluded.updated_at",
                 (name, max(0.0, qty), config.now().isoformat()))


def process_past(conn) -> None:
    """Déduit du stock les repas passés (une seule fois) et la consommation quotidienne des produits récurrents."""
    today = config.today()
    fam = family_eq(get_settings(conn))
    rows = conn.execute("SELECT p.id, p.recipe_id, r.servings FROM plan p JOIN recipes r ON r.id=p.recipe_id "
                        "WHERE p.day < ? AND p.consumed=0 AND p.status='planned'", (today.isoformat(),)).fetchall()
    for p in rows:
        for ri in R.recipe_ingredients(conn, p["recipe_id"]):
            if not ri["is_basic"] and not ri["optional"] and ri["qty"] is not None:
                add_stock(conn, ri["ingredient"], -ri["qty"] * fam / p["servings"])
        conn.execute("UPDATE plan SET consumed=1 WHERE id=?", (p["id"],))
    conn.execute("UPDATE plan SET consumed=1 WHERE day < ? AND consumed=0", (today.isoformat(),))
    row = conn.execute("SELECT value FROM meta WHERE key='recurrent_day'").fetchone()
    last = date.fromisoformat(row["value"]) if row else today
    days = min((today - last).days, 60)  # plafonné : une longue absence ne vide pas le stock à l'infini
    if days > 0:
        for ing in conn.execute("SELECT name, weekly_qty FROM ingredients WHERE is_recurrent=1 AND weekly_qty>0"):
            add_stock(conn, ing["name"], -ing["weekly_qty"] / 7 * days)
    conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('recurrent_day',?)", (today.isoformat(),))
    conn.execute("DELETE FROM plan WHERE day < ?", ((today - timedelta(days=120)).isoformat(),))
    conn.execute("DELETE FROM ops WHERE created_at < ?", ((config.now() - timedelta(days=30)).isoformat(),))
    conn.commit()


def needs(conn) -> tuple[dict, int]:
    today = config.today()
    s = get_settings(conn)
    fam = family_eq(s)
    only_locked = " AND p.locked=1" if s["shopping_locked_only"] else ""   # constante, pas d'entrée utilisateur
    need: dict[str, float] = {}
    last = today
    for p in conn.execute("SELECT p.day, p.recipe_id, r.servings FROM plan p JOIN recipes r ON r.id=p.recipe_id "
                          "WHERE p.day >= ? AND p.status='planned' AND p.consumed=0" + only_locked,
                          (today.isoformat(),)):
        last = max(last, date.fromisoformat(p["day"]))
        for ri in R.recipe_ingredients(conn, p["recipe_id"]):
            if not ri["is_basic"] and not ri["optional"] and ri["qty"] is not None:
                need[ri["ingredient"]] = need.get(ri["ingredient"], 0) + ri["qty"] * fam / p["servings"]
    horizon = max(7, (last - today).days + 1)
    for ing in conn.execute("SELECT name, weekly_qty FROM ingredients WHERE is_recurrent=1 AND weekly_qty>0"):
        need[ing["name"]] = need.get(ing["name"], 0) + ing["weekly_qty"] / 7 * horizon
    return need, horizon


def _buy(ing: dict, missing: float) -> tuple[int | None, float, float]:
    """(nombre de paquets ou None si vrac, quantité à acheter, prix estimé)."""
    if ing.get("pack_qty"):
        packs = max(1, math.ceil(missing / ing["pack_qty"] - EPS))
        qty = packs * ing["pack_qty"]
        price = packs * ing["price"] if ing.get("price") is not None else qty * I.price_per_base(ing)
        return packs, qty, round(price, 2)
    step = I.pack_info(ing)[0]
    qty = max(step, math.ceil(missing / step - EPS) * step)
    return None, qty, round(qty * I.price_per_base(ing), 2)


def compute_list(conn) -> dict:
    process_past(conn)
    today = config.today().isoformat()
    need, _ = needs(conn)
    stock = {r["ingredient"]: r["qty"] for r in conn.execute("SELECT * FROM stock")}
    state = {r["ingredient"]: dict(r) for r in conn.execute("SELECT * FROM shop_state")}
    ings = {r["name"]: dict(r) for r in conn.execute("SELECT * FROM ingredients")}
    names = set(need) | {n for n, s in state.items() if s["forced"] or s["checked_on"] == today or s["archived_need"] is not None}
    items = []
    for n in names:
        ing, st = ings[n], state.get(n, {})
        req, have = need.get(n, 0.0), stock.get(n, 0.0)
        missing = max(0.0, req - have)
        forced = bool(st.get("forced"))
        if forced:
            missing = max(missing, 1e-3)
        archived = st.get("archived_need") is not None
        if archived and req > st["archived_need"] + EPS:
            conn.execute("UPDATE shop_state SET archived_need=NULL WHERE ingredient=?", (n,))
            archived = False
        if missing > EPS:
            status = "archived" if archived else "todo"
        elif st.get("checked_on") == today:
            status = "done"
        else:
            continue
        packs, buy_qty, price = _buy(ing, missing if missing > EPS else 0.0) if status != "done" else (None, 0, 0)
        items.append({"ingredient": n, "aisle": ing["aisle"], "status": status, "kind": ing["kind"],
                      "required": round(req, 2), "in_stock": round(have, 2), "missing": round(missing, 2),
                      "packs": packs, "pack_label": ing["pack_label"], "buy_qty": buy_qty,
                      "buy_text": R.fmt_qty(buy_qty, ing["kind"]) if status != "done" else "",
                      "need_text": R.fmt_qty(missing, ing["kind"]) if status != "done" else R.fmt_qty(req, ing["kind"]),
                      "price": price, "basic": bool(ing["is_basic"]), "verified": bool(ing["verified"])})
    conn.commit()
    order = {a: i for i, a in enumerate(AISLES)}
    items.sort(key=lambda x: (order.get(x["aisle"], 99), x["ingredient"]))
    todo = [i for i in items if i["status"] == "todo"]
#    return {"items": items, "total_est": round(sum(i["price"] for i in todo), 2), "count_todo": len(todo)}

    s = get_settings(conn)
    locked = conn.execute("SELECT COUNT(*) FROM plan p JOIN recipes r ON r.id=p.recipe_id WHERE p.day>=? "
                          "AND p.status='planned' AND p.locked=1", (today,)).fetchone()[0]
    return {"items": items, "total_est": round(sum(i["price"] for i in todo), 2), "count_todo": len(todo),
            "locked_only": bool(s["shopping_locked_only"]), "locked_meals": locked}


def apply_ops(conn, ops: list[dict]) -> dict:
    """Opérations idempotentes (op_id) : rejouables sans risque après une coupure réseau."""
    today = config.today().isoformat()
    done, skipped = 0, 0
    cat = None
    for op in ops:
        op_id, kind, name = str(op.get("op_id", "")), op.get("type"), op.get("ingredient")
        if op_id and name and kind in ("add", "low"):   # saisie libre : on crée l'article s'il est inconnu
            if cat is None:
                cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
            name = I.find_or_create(conn, cat, str(name))
        if not op_id or not name or not conn.execute("SELECT 1 FROM ingredients WHERE name=?", (name,)).fetchone():
            skipped += 1
            continue
        # Insertion atomique : si deux requêtes portant le même op_id arrivent en parallèle, une seule l'emporte.
        if conn.execute("INSERT OR IGNORE INTO ops(op_id, created_at) VALUES(?,?)", (op_id, config.now().isoformat())).rowcount == 0:
            skipped += 1
            continue
        conn.execute("INSERT OR IGNORE INTO shop_state(ingredient) VALUES(?)", (name,))
        qty = float(op.get("qty") or 0)
        if kind == "buy":
            add_stock(conn, name, max(0.0, qty))
            conn.execute("UPDATE shop_state SET checked_on=?, forced=0, archived_need=NULL WHERE ingredient=?", (today, name))
        elif kind == "unbuy":
            add_stock(conn, name, -max(0.0, qty))
            conn.execute("UPDATE shop_state SET checked_on=NULL WHERE ingredient=?", (name,))
        elif kind == "have":  # « déjà à la maison » : le stock couvre le besoin, sans achat
            need, _ = needs(conn)
            have = conn.execute("SELECT qty FROM stock WHERE ingredient=?", (name,)).fetchone()
            add_stock(conn, name, max(0.0, need.get(name, 0) - (have["qty"] if have else 0)))
            conn.execute("UPDATE shop_state SET checked_on=?, forced=0 WHERE ingredient=?", (today, name))
        elif kind == "archive":
            need, _ = needs(conn)
            conn.execute("UPDATE shop_state SET archived_need=?, forced=0 WHERE ingredient=?", (need.get(name, 0.0), name))
        elif kind == "unarchive":
            conn.execute("UPDATE shop_state SET archived_need=NULL WHERE ingredient=?", (name,))
        elif kind in ("low", "add"):
            conn.execute("UPDATE shop_state SET forced=1, archived_need=NULL WHERE ingredient=?", (name,))
        else:
            conn.execute("DELETE FROM ops WHERE op_id=?", (op_id,))
            skipped += 1
            continue
        done += 1
    conn.commit()
    return {"applied": done, "skipped": skipped}
