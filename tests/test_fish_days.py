# SPDX-License-Identifier: AGPL-3.0-or-later
import random
from datetime import date, timedelta
from app import config, plan_service as PS
from app.planner import Cand, generate, _score
from app.settings import get_settings, put_settings

D0 = date(2026, 11, 16)          # un lundi
FRI = D0 + timedelta(days=4)
FISH = frozenset({4})            # vendredi


def mk(i, protein, carb="autre", meals="dl", cost=6.0):
    f = frozenset({f"ing{i}"})
    return Cand(i, f"r{i}", protein, carb, meals, 30, (), cost, ings=f, ings_nb=f)


def pool():
    out, i = [], 0
    for p in ("poulet", "boeuf", "porc", "poisson", "veggie", "oeuf") * 3:
        for c in ("pates", "riz", "pdt"):
            i += 1
            out.append(mk(i, p, c))
    return out


def week(n=7):
    return [(D0 + timedelta(days=i), "dinner") for i in range(n)]


# ---------- planificateur (fonctions pures) ----------
def test_vendredi_toujours_poisson():
    for seed in range(20):
        res = generate(week(), pool(), {}, [], frozenset(), set(), fish_days=FISH, rng=random.Random(seed))
        assert res[(FRI, "dinner")].protein == "poisson", seed


def test_les_autres_jours_ne_sont_pas_tous_du_poisson():
    for seed in range(20):
        res = generate(week(), pool(), {}, [], frozenset(), set(), fish_days=FISH, rng=random.Random(seed))
        assert any(c.protein != "poisson" for (d, _), c in res.items() if d != FRI), seed


def test_plusieurs_vendredis_restent_poisson_meme_avec_peu_de_recettes():
    p = [mk(1, "poisson"), mk(2, "poisson"), mk(3, "porc"), mk(4, "boeuf")]
    slots = [(D0 + timedelta(days=4 + 7 * k), "dinner") for k in range(3)]
    res = generate(slots, p, {}, [], frozenset(), set(), fish_days=FISH, rng=random.Random(0))
    assert all(c.protein == "poisson" for c in res.values())   # on répète du poisson plutôt que de changer


def test_sans_poisson_utilisable_on_ne_laisse_pas_vide():
    p = [mk(i, "porc") for i in range(1, 5)]
    res = generate([(FRI, "dinner")], p, {}, [], frozenset(), set(), fish_days=FISH, rng=random.Random(0))
    assert res[(FRI, "dinner")] is not None


def test_poisson_refuse_donne_quand_meme_une_recette():
    p = pool()
    refused = frozenset(f"ing{c.id}" for c in p if c.protein == "poisson")
    res = generate([(FRI, "dinner")], p, {}, [], refused, set(), fish_days=FISH, rng=random.Random(0))
    assert res[(FRI, "dinner")] is not None and res[(FRI, "dinner")].protein != "poisson"


def test_mode_sans_poisson_exclut_le_poisson():
    for seed in range(20):
        res = generate([(FRI, "dinner")], pool(), {}, [], frozenset(), set(), fish_days=FISH, no_fish=True,
                       rng=random.Random(seed))
        assert res[(FRI, "dinner")].protein != "poisson", seed


def test_veille_et_lendemain_d_un_jour_poisson_penalisent_le_poisson():
    c = mk(1, "poisson")
    thu, sat, wed = ((D0 + timedelta(days=n), "dinner") for n in (3, 5, 2))
    base = lambda slot, fd: _score(c, slot, [], set(), frozenset(), fish_days=fd)
    assert base(thu, FISH) < base(thu, frozenset())
    assert base(sat, FISH) < base(sat, frozenset())
    assert base(wed, FISH) == base(wed, frozenset())                       # pas voisin du vendredi
    assert base((FRI, "dinner"), FISH) == base((FRI, "dinner"), frozenset())   # le jour poisson lui-même


def test_sans_fish_days_comportement_inchange():
    a = generate(week(), pool(), {}, [], frozenset(), set(), rng=random.Random(3))
    b = generate(week(), pool(), {}, [], frozenset(), set(), fish_days=frozenset(), rng=random.Random(3))
    assert {k: v.id for k, v in a.items()} == {k: v.id for k, v in b.items()}


# ---------- service (base de test, bibliothèque de départ) ----------
def _plan_row(conn, offset, slot="dinner"):
    d = (config.today() + timedelta(days=offset)).isoformat()
    return conn.execute("SELECT * FROM plan WHERE day=? AND slot=?", (d, slot)).fetchone()


def _protein(conn, recipe_id):
    return conn.execute("SELECT protein FROM recipes WHERE id=?", (recipe_id,)).fetchone()["protein"]


def test_reglage_par_defaut_est_le_vendredi(conn):
    assert get_settings(conn)["fish_days"] == [4]


def test_reglage_fish_days_est_valide(conn):
    put_settings(conn, {"fish_days": [4, "x", 9, 2, 4, -1]})
    assert get_settings(conn)["fish_days"] == [2, 4]
    put_settings(conn, {"fish_days": []})
    assert get_settings(conn)["fish_days"] == []


def test_les_vendredis_du_planning_sont_au_poisson(conn, rng):
    PS.ensure_plan(conn, 21, rng=rng)
    for off in (4, 11, 18):                      # le 16/11/2026 est un lundi
        assert _protein(conn, _plan_row(conn, off)["recipe_id"]) == "poisson", off


def test_remplacer_sans_la_case_reste_au_poisson(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    row = _plan_row(conn, 4)
    PS.replace_meal(conn, row["id"], "other", regenerate_following=False, rng=rng)
    new = _plan_row(conn, 4)["recipe_id"]
    assert new != row["recipe_id"] and _protein(conn, new) == "poisson"


def test_remplacer_avec_la_case_donne_une_recette_sans_poisson(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    row = _plan_row(conn, 4)
    PS.replace_meal(conn, row["id"], "other", regenerate_following=False, rng=rng, allow_non_fish=True)
    new = _plan_row(conn, 4)
    assert _protein(conn, new["recipe_id"]) != "poisson" and new["locked"] == 1


def test_remplacement_sans_poisson_survit_aux_regenerations(conn, rng):
    PS.ensure_plan(conn, 14, rng=rng)
    row = _plan_row(conn, 4)
    PS.replace_meal(conn, row["id"], "other", regenerate_following=False, rng=rng, allow_non_fish=True)
    chosen = _plan_row(conn, 4)["recipe_id"]
    PS.replace_meal(conn, _plan_row(conn, 0)["id"], "other", rng=rng)        # régénère les repas suivants non verrouillés
    for _ in range(3):
        PS.generate_all(conn, 14, rng=rng)
        assert _plan_row(conn, 4)["recipe_id"] == chosen
    assert _protein(conn, _plan_row(conn, 11)["recipe_id"]) == "poisson"     # l'autre vendredi reste au poisson


def test_choix_manuel_d_une_recette_sans_poisson_le_vendredi(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    rid = conn.execute("SELECT id FROM recipes WHERE protein='boeuf' LIMIT 1").fetchone()["id"]
    row = _plan_row(conn, 4)
    PS.set_recipe(conn, row["id"], rid)
    PS.generate_all(conn, 7, rng=rng)
    assert _plan_row(conn, 4)["recipe_id"] == rid