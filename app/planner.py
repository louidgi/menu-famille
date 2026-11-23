# SPDX-License-Identifier: AGPL-3.0-or-later
"""Génération de menus : fonctions pures (pas de base de données), testables avec une graine aléatoire.
Glouton chronologique avec contraintes dures (type de repas, aliments refusés, répétitions) et score
souple (variété des protéines et féculents, poisson, légumineuses/végétarien, jours chargés, saison, coût, notes, stock).
On répète N tirages aléatoires et on garde le meilleur (budget compris)."""
import random
from dataclasses import dataclass, field
from datetime import date

SLOT_IDX = {"lunch": 0, "dinner": 1}
RED_MEAT = {"boeuf"}


@dataclass(frozen=True)
class Cand:
    id: int
    title: str
    protein: str
    carb: str
    meals: str            # 'd', 'l' ou 'dl'
    minutes: int
    months: tuple         # () = toute l'année
    cost: float           # estimation pour la famille
    rating: int = 0
    favorite: bool = False
    ings: frozenset = field(default_factory=frozenset)      # tous les ingrédients (pour les refus)
    ings_nb: frozenset = field(default_factory=frozenset)   # hors basiques (pour le stock)


Slot = tuple  # (date, 'lunch'|'dinner')


def _k(slot: Slot):
    return (slot[0].toordinal(), SLOT_IDX[slot[1]])


def _near(ctx, day: date, span: int):
    return [c for (d, _, c) in ctx if abs((d - day).days) <= span]


def _score(c: Cand, slot: Slot, ctx, busy, in_stock, w_cost=0.25) -> float:
    day = slot[0]
    s = 0.6 * c.rating + (1.0 if c.favorite else 0.0) - w_cost * c.cost
    before = [(d, i, x) for (d, i, x) in ctx if (d.toordinal(), i) < _k(slot)]
    after = [(d, i, x) for (d, i, x) in ctx if (d.toordinal(), i) > _k(slot)]
    for nb in ([max(before, key=lambda t: (t[0].toordinal(), t[1]))[2]] if before else []) + \
              ([min(after, key=lambda t: (t[0].toordinal(), t[1]))[2]] if after else []):
        if nb.protein == c.protein and c.protein != "autre":
            s -= 3.0
        if nb.carb == c.carb and c.carb != "autre":
            s -= 1.5
    win = _near(ctx, day, 3)
    fish = sum(1 for x in win if x.protein == "poisson")
    if c.protein == "poisson":
        s += 1.5 if fish == 0 else (-3.0 if fish >= 2 else 0.0)
    if c.protein == "veggie" and not any(x.protein == "veggie" for x in win):
        s += 1.0
    if c.protein in RED_MEAT and sum(1 for x in win if x.protein in RED_MEAT) >= 2:
        s -= 3.0
    if (day.weekday(), slot[1]) in busy:
        s += 1.0 if c.minutes <= 30 else (-3.0 if c.minutes > 35 else 0.0)
    if c.months and day.month not in c.months:
        s -= 4.0
    s += min(1.5, 0.3 * len(c.ings_nb & in_stock))
    return s


def generate(slots, cands, fixed, recent, refused, busy, *, in_stock=frozenset(), budget=None,
             max_cost=None, avoid_ids=frozenset(), no_repeat_days=21, rng=None, tries=25):
    """slots : [(date, slot)] à remplir ; fixed : {(date, slot): Cand} repas conservés ;
    recent : [(date, Cand)] historique ; busy : jours de semaine chargés ; budget : plafond total sur ces repas.
    Retourne {(date, slot): Cand | None}."""
    rng = rng or random.Random()
    slots = sorted(slots, key=_k)
    usable = [c for c in cands if not (c.ings & refused) and c.id not in avoid_ids]
    if max_cost is not None:
        usable = [c for c in usable if c.cost < max_cost]
    base_ctx = [(d, SLOT_IDX[sl], c) for (d, sl), c in fixed.items() if c] + [(d, 0, c) for d, c in recent]
    best, best_val = None, None
    for _ in range(tries):
        ctx, out, total, cost = list(base_ctx), {}, 0.0, 0.0
        for slot in slots:
            kind = "d" if slot[1] == "dinner" else "l"
            pool = [c for c in usable if kind in c.meals]
            for window in (no_repeat_days, 7, 0):   # on assouplit les répétitions si le choix est trop mince
                used = {x.id for (d, _, x) in ctx if abs((d - slot[0]).days) < window} if window else set()
                ok = [c for c in pool if c.id not in used]
                if ok:
                    break
            if not ok:
                out[slot] = None
                continue
            scored = [(_score(c, slot, ctx, busy, in_stock) + rng.uniform(0, 1.2), c) for c in ok]
            sc, pick = max(scored, key=lambda t: t[0])
            out[slot] = pick
            ctx.append((slot[0], SLOT_IDX[slot[1]], pick))
            total += sc
            cost += pick.cost
        if budget is not None and cost > budget:
            total -= 0.5 * (cost - budget)
        if best_val is None or total > best_val:
            best, best_val = out, total
    return best or {}
