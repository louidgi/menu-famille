# SPDX-License-Identifier: AGPL-3.0-or-later
import random
from datetime import date, timedelta
from app.planner import Cand, generate

D0 = date(2026, 11, 16)  # un lundi


def mk(i, protein, carb="autre", meals="dl", minutes=30, cost=6.0, months=(), ings=()):
    f = frozenset(ings) | {f"ing{i}"}
    return Cand(i, f"r{i}", protein, carb, meals, minutes, tuple(months), cost, ings=f, ings_nb=f)


def pool():
    out, i = [], 0
    for p in ("poulet", "boeuf", "porc", "poisson", "veggie", "oeuf") * 3:
        for c in ("pates", "riz", "pdt"):
            i += 1
            out.append(mk(i, p, c))
    return out


def week(n=7, slot="dinner"):
    return [(D0 + timedelta(days=i), slot) for i in range(n)]


def test_remplit_tout_et_sans_doublon():
    res = generate(week(), pool(), {}, [], frozenset(), set(), rng=random.Random(1))
    assert len(res) == 7 and all(res.values())
    assert len({c.id for c in res.values()}) == 7


def test_pas_deux_fois_la_meme_proteine_de_suite():
    for seed in range(20):
        res = generate(week(), pool(), {}, [], frozenset(), set(), rng=random.Random(seed))
        seq = [res[s].protein for s in sorted(res)]
        assert all(a != b for a, b in zip(seq, seq[1:])), (seed, seq)


def test_au_moins_un_poisson_et_un_veggie_sur_la_semaine():
    for seed in range(20):
        res = generate(week(), pool(), {}, [], frozenset(), set(), rng=random.Random(seed))
        prots = [c.protein for c in res.values()]
        assert "poisson" in prots and "veggie" in prots, (seed, prots)


def test_ingredient_refuse_jamais_choisi():
    refused = frozenset(f"ing{i}" for i in range(1, 40))  # 39 recettes sur 54 interdites : une violation serait quasi certaine
    for seed in range(10):
        res = generate(week(), pool(), {}, [], refused, set(), rng=random.Random(seed))
        assert len(res) == 7 and not any(c.ings & refused for c in res.values())


def test_repas_deja_fixes_sont_respectes_et_influencent_les_voisins():
    p = pool()
    fixed_c = next(c for c in p if c.protein == "poisson")
    fixed = {(D0 + timedelta(days=3), "dinner"): fixed_c}
    slots = [s for s in week() if s[0] != D0 + timedelta(days=3)]
    for seed in range(15):
        res = generate(slots, p, fixed, [], frozenset(), set(), rng=random.Random(seed))
        assert fixed_c.id not in {c.id for c in res.values()}
        assert res[(D0 + timedelta(days=2), "dinner")].protein != "poisson"
        assert res[(D0 + timedelta(days=4), "dinner")].protein != "poisson"


def test_historique_recent_pas_repete():
    p = pool()
    recent = [(D0 - timedelta(days=2), p[0]), (D0 - timedelta(days=5), p[1])]
    res = generate(week(), p, {}, recent, frozenset(), set(), rng=random.Random(2))
    assert p[0].id not in {c.id for c in res.values()} and p[1].id not in {c.id for c in res.values()}


def test_trop_cher_force_un_remplacant_moins_cher():
    p = [mk(1, "porc", cost=9.0), mk(2, "boeuf", cost=5.0), mk(3, "poisson", cost=12.0), mk(4, "veggie", cost=4.0)]
    res = generate([(D0, "dinner")], p, {}, [], frozenset(), set(), max_cost=6.0, avoid_ids={1}, rng=random.Random(0))
    assert res[(D0, "dinner")].cost < 6.0


def test_dejeuner_vs_diner():
    p = [mk(1, "porc", meals="d"), mk(2, "boeuf", meals="l")]
    res = generate([(D0, "lunch"), (D0, "dinner")], p, {}, [], frozenset(), set(), rng=random.Random(0))
    assert res[(D0, "lunch")].id == 2 and res[(D0, "dinner")].id == 1


def test_jours_charges_preferent_le_rapide():
    p = [mk(i, "porc" if i % 2 else "boeuf", minutes=90 if i < 10 else 20) for i in range(1, 20)]
    wins = 0
    for seed in range(20):
        res = generate([(D0, "dinner")], p, {}, [], frozenset(), {0}, rng=random.Random(seed))  # lundi chargé
        wins += res[(D0, "dinner")].minutes <= 30
    assert wins >= 18


def test_saison_penalisee():
    p = [mk(i, "porc" if i % 2 else "boeuf", months=(6, 7, 8)) for i in range(1, 6)] + [mk(10, "veggie")]
    res = generate([(D0, "dinner")], p, {}, [], frozenset(), set(), rng=random.Random(0))
    assert res[(D0, "dinner")].id == 10  # novembre : les recettes d'été sont écartées au profit de la recette de saison


def test_pool_trop_petit_assouplit_les_repetitions_plutot_que_de_laisser_vide():
    p = [mk(1, "porc"), mk(2, "poisson")]
    res = generate(week(4), p, {}, [], frozenset(), set(), rng=random.Random(0))
    assert all(res.values())


def test_aucun_candidat_donne_none():
    p = [mk(1, "porc")]
    res = generate([(D0, "dinner")], p, {}, [], frozenset({"ing1"}), set(), rng=random.Random(0))
    assert res[(D0, "dinner")] is None


def test_budget_prefere_le_moins_cher():
    p = [mk(i, ("porc", "boeuf", "poisson", "veggie")[i % 4], cost=3.0 if i % 2 else 12.0) for i in range(1, 25)]
    cheap = generate(week(), p, {}, [], frozenset(), set(), budget=25.0, rng=random.Random(1), tries=60)
    free = generate(week(), p, {}, [], frozenset(), set(), rng=random.Random(1), tries=60)
    assert sum(c.cost for c in cheap.values()) <= sum(c.cost for c in free.values())
