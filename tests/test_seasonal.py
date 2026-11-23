# SPDX-License-Identifier: AGPL-3.0-or-later
from app import ingredients as I, recipes as R, seed_recipes as S
from app.seed_seasonal import SEED_SEASONAL

PACK = S.parse_seed(SEED_SEASONAL)
TITLES = [d["title"] for d in PACK]


def _cat(conn):
    return I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())


def _count(conn):
    return conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]


def test_vingt_recettes_aux_titres_uniques_et_distincts_du_lot_de_depart():
    assert len(PACK) == 20 and len(set(TITLES)) == 20
    assert not set(TITLES) & {d["title"] for d in S.parse_seed()}


def test_chaque_recette_est_complete_et_valide():
    for d in PACK:
        assert d["ingredients"] and len(d["steps"]) >= 3, d["title"]
        assert d["protein"] in R.PROTEINS and d["carb"] in R.CARBS, d["title"]
        assert d["meals"] in ("d", "l", "dl") and d["months"], d["title"]


def test_chaque_mois_a_au_moins_quatre_recettes_de_saison():
    for m in range(1, 13):
        assert sum(m in d["months"] for d in PACK) >= 4, m


def test_plages_de_mois_qui_franchissent_le_nouvel_an():
    by = {d["title"]: d["months"] for d in PACK}
    assert by["Raclette et charcuterie"] == [12, 1, 2]
    assert by["Gratin de pâtes, brocoli et poulet"] == [10, 11, 12, 1, 2, 3]


def test_aucun_ingredient_du_lot_n_est_inconnu_ni_sans_quantite(conn):
    marks = ",".join("?" * len(TITLES))
    unknown = conn.execute(
        f"SELECT DISTINCT ri.ingredient FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id "
        f"JOIN ingredients i ON i.name=ri.ingredient WHERE r.title IN ({marks}) AND i.verified=0", TITLES).fetchall()
    assert not unknown, [u[0] for u in unknown]          # sinon : à ajouter à catalog_seed.CATALOG
    no_qty = conn.execute(
        f"SELECT r.title, ri.raw FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id "
        f"JOIN ingredients i ON i.name=ri.ingredient WHERE r.title IN ({marks}) AND i.is_basic=0 "
        f"AND ri.qty IS NULL", TITLES).fetchall()
    assert not no_qty, [tuple(x) for x in no_qty]         # sinon : absent de la liste de courses


def test_rapprochements_delicats(conn):
    def ings(title):
        return {r[0] for r in conn.execute(
                    "SELECT ri.ingredient FROM recipe_ingredients ri JOIN recipes r ON r.id=ri.recipe_id WHERE r.title=?", (title,))}
    rac = ings("Raclette et charcuterie")
    assert {"fromage à raclette", "charcuterie", "pomme de terre"} <= rac and "gruyère râpé" not in rac
    assert "pomme" in ings("Filet mignon aux pommes et purée") and "pomme de terre" in ings("Filet mignon aux pommes et purée")
    assert "chou-fleur" not in ings("Potée de chou et saucisses") and "chou vert" in ings("Potée de chou et saucisses")


def test_base_existante_recoit_le_lot_une_seule_fois(conn):
    marks = ",".join("?" * len(TITLES))
    conn.execute(f"DELETE FROM recipes WHERE title IN ({marks})", TITLES)       # simule une base d'avant cette version
    conn.execute("DELETE FROM meta WHERE key='seed_seasonal_v1'")
    conn.commit()
    before = _count(conn)
    assert before == 40
    assert S.load_seed(conn, _cat(conn)) == 20
    assert S.load_seed(conn, _cat(conn)) == 0
    assert _count(conn) == before + 20


def test_recette_archivee_ou_renommee_n_est_pas_rechargee(conn):
    conn.execute("UPDATE recipes SET archived=1 WHERE title='Raclette et charcuterie'")
    conn.execute("UPDATE recipes SET title='Ma tartiflette' WHERE title='Tartiflette'")
    conn.commit()
    n = _count(conn)
    assert S.load_seed(conn, _cat(conn)) == 0 and _count(conn) == n