# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from app import importer, config
from app.importer import ImportError_

import os
FX = "tests/fixtures/"
LOCAL = "tests/local_fixtures/"   # vraies pages Marmiton / 750g : non versionnées (contenu de tiers), tests ignorés si absentes
real = pytest.mark.skipif(not os.path.exists(LOCAL + "marmiton.html"), reason="pages réelles non présentes (tests/local_fixtures)")
URL = "https://exemple-recettes.test/gratin"


def html(name, base=FX):
    return open(base + name, encoding="utf-8").read()


def test_page_synthetique_formats_francais(conn):
    d = importer.draft_from_html(conn, html("recette-exemple.html"), URL)
    assert d["title"] == "Gratin d'exemple" and d["servings"] == 4 and d["prep_min"] == 15 and d["cook_min"] == 30
    by = {l["raw"]: l for l in d["ingredients"]}
    assert by["500g de carottes"]["ingredient"] == "carotte" and by["500g de carottes"]["qty"] == 500
    assert by["6 c.à.s d'huile d'olive"]["unit"] == "cs" and by["6 c.à.s d'huile d'olive"]["status"] == "ok"
    assert by["10 cl de vinaigrette citron"]["status"] == "check"          # homonyme trompeur signalé
    assert by["1/2 oignon"]["qty"] == 0.5
    # intertitres retirés, phrase coupée recollée
    assert d["steps"] == ["Coupez les carottes en rondelles, les aubergines en dés.", "Faites cuire le tout 30 minutes à feu doux."]


@real
def test_marmiton_page_reelle(conn):
    d = importer.draft_from_html(conn, html("marmiton.html", LOCAL), "https://www.marmiton.org/recettes/recette_ratatouille_23223.aspx")
    assert d["title"] == "Ratatouille" and d["servings"] == 4
    assert len(d["ingredients"]) >= 8 and d["steps"]
    by = {l["raw"]: l for l in d["ingredients"]}
    assert by["350 g d'aubergine"]["ingredient"] == "aubergine" and by["350 g d'aubergine"]["qty"] == 350
    assert not any(l["status"] == "unknown" for l in d["ingredients"])
    assert all(len(s) > 15 for s in d["steps"])


@real
def test_750g_page_reelle_sans_intertitres_etape(conn):
    d = importer.draft_from_html(conn, html("750g.html", LOCAL), "https://www.750g.com/x_r1.htm")
    assert d["title"].startswith("Salade de carottes") and d["servings"] == 6
    assert not any(s.lower().startswith("étape") for s in d["steps"])


def test_page_sans_recette_message_clair(conn):
    with pytest.raises(ImportError_) as e:
        importer.draft_from_html(conn, "<html><body><p>Bonjour</p></body></html>", "https://exemple-inconnu.fr/page")
    assert "à la main" in str(e.value)


def test_enregistrement_du_brouillon_cree_recette_et_ingredients(conn):
    from app import recipes as R, ingredients as I
    d = importer.draft_from_html(conn, html("recette-exemple.html"), URL)
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    d["ingredients"] = [{"raw": l["raw"], "ingredient": l["ingredient"]} if l["ingredient"] else l["raw"] for l in d["ingredients"]]
    rid = R.save_recipe(conn, cat, d)
    rows = R.recipe_ingredients(conn, rid)
    assert len(rows) == len(d["ingredients"]) and any(r["ingredient"] == "aubergine" and r["qty"] == 350 for r in rows)
    assert any(r["ingredient"] == "oignon" and r["qty"] == pytest.approx(60) for r in rows)    # 1/2 oignon = 60 g


def test_clean_steps_recolle_les_phrases_coupees():
    assert importer.clean_steps(["Coupez les tomates en quartiers,", "les aubergines en rondelles.", "Étape 2 : Cuisson", "Faites cuire."]) == [
        "Coupez les tomates en quartiers, les aubergines en rondelles.", "Faites cuire."]


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x.fr/a", "http://127.0.0.1:8000/", "http://localhost/",
                                 "http://192.168.1.10/", "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "javascript:alert(1)"])
def test_ssrf_refuse_adresses_privees_et_schemas(url):
    with pytest.raises(ImportError_):
        importer.check_url(url)
