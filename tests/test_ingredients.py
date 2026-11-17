# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from app import ingredients as I

ANY = object()  # « ne pas vérifier »


@pytest.mark.parametrize("line,qty,unit,canonical", [
    ("350 g d'aubergine", 350, "g", "aubergine"),
    ("500g de carottes", 500, "g", "carotte"),                      # pas d'espace entre nombre et unité
    ("6 c.à.s d'huile d'olive", 6, "cs", "huile d'olive"),           # abréviations de cuillères
    ("1 c.c de coriandre en grain", 1, "cc", "coriandre"),
    ("2 cuillères à café de curry", 2, "cc", "curry"),
    ("1 1/2 c. à soupe de farine", 1.5, "cs", "farine"),             # nombre + fraction
    ("1/2 oignon", 0.5, None, "oignon"),                             # bug corrigé : lu « 1 » au début
    ("½ citron", 0.5, None, "citron"),
    ("1/4 de botte de coriandre", 0.25, ANY, "coriandre"),
    ("un peu de sel", None, None, "sel"),                            # bug corrigé : lu « 1 sel »
    ("2 à 3 gousses d'ail", 3, "gousse", "ail"),                     # fourchette : borne haute
    ("un oeuf", 1, None, "oeuf"),
    ("4 steaks hachés", 4, None, "boeuf haché"),
    ("20 cl de crème fraîche épaisse", 20, "cl", "crème fraîche"),
    ("3 jus d'orange", 3, None, "jus d'orange"),
])
def test_parse_et_rapprochement(conn, line, qty, unit, canonical):
    p = I.parse_line(line)
    assert p["qty"] == qty
    if unit is not ANY:
        assert p["unit"] == unit
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    assert cat.match(p["name"])[0] == canonical


def test_homonyme_trompeur_est_signale_a_verifier(conn):
    """« vinaigrette citron » ne doit pas devenir silencieusement « citron »."""
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    name, sure = cat.match(I.parse_line("10 cl de vinaigrette citron")["name"])
    assert name == "citron" and sure is False


def test_ingredient_inconnu_cree_un_ingredient_a_verifier(conn):
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    name, qty, status = I.resolve(conn, cat, I.parse_line("200 g de topinambours"))
    assert status == "unknown" and qty == 200
    assert conn.execute("SELECT verified FROM ingredients WHERE name=?", (name,)).fetchone()["verified"] == 0


@pytest.mark.parametrize("qty,unit,name,expected", [
    (1, "kg", "pomme de terre", 1000), (50, "cl", "lait", 500), (1, None, "oignon", 120),    # pièce -> grammes
    (3, "cs", "farine", 3 * 15 * 0.55), (4, None, "oeuf", 4), (300, "g", "cuisse de poulet", 300 / 100.0),
])
def test_conversions_vers_l_unite_de_base(conn, qty, unit, name, expected):
    row = dict(conn.execute("SELECT * FROM ingredients WHERE name=?", (name,)).fetchone())
    assert I.to_base(qty, unit, row) == pytest.approx(expected)
