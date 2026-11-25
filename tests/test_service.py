# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import timedelta
import pytest
from app import plan_service as PS, shopping as SH, config, recipes as R, ingredients as I
from app.settings import get_settings, family_eq


def rows(conn):
    return [dict(r) for r in conn.execute("SELECT * FROM plan ORDER BY day, slot")]


def test_ensure_plan_remplit_diners_et_dejeuners_du_week_end(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    r = rows(conn)
    dinners = [x for x in r if x["slot"] == "dinner"]
    lunches = [x for x in r if x["slot"] == "lunch"]
    assert len(dinners) == 7 and len(lunches) == 2  # samedi + dimanche
    assert all(x["recipe_id"] for x in r)
    before = [(x["day"], x["slot"], x["recipe_id"]) for x in r]
    PS.ensure_plan(conn, 7)
    assert [(x["day"], x["slot"], x["recipe_id"]) for x in rows(conn)] == before  # idempotent


def test_remplacer_avec_ingredient_refuse_regenere_les_suivants_sans_toucher_aux_verrouilles(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    r = rows(conn)
    target, locked_later = r[2], r[5]
    conn.execute("UPDATE plan SET locked=1 WHERE id=?", (locked_later["id"],))
    conn.commit()
    before = {x["id"]: x["recipe_id"] for x in r}
    ing = R.recipe_ingredients(conn, target["recipe_id"])[0]["ingredient"]
    res = PS.replace_meal(conn, target["id"], "refuse_ingredient", ingredient=ing, rng=rng)
    after = {x["id"]: x["recipe_id"] for x in rows(conn)}
    assert conn.execute("SELECT 1 FROM refused WHERE name=?", (ing,)).fetchone()
    assert after[target["id"]] != before[target["id"]]
    for x in r[:2]:  # avant le repas modifié : intact
        assert after[x["id"]] == before[x["id"]]
    assert after[locked_later["id"]] == before[locked_later["id"]]  # verrouillé : intact
    # le repas remplacé et tous les suivants évitent l'ingrédient refusé
    for x in r[2:]:
        if x["id"] == locked_later["id"]:
            continue
        names = {i["ingredient"] for i in R.recipe_ingredients(conn, after[x["id"]])}
        assert ing not in names
    assert conn.execute("SELECT locked FROM plan WHERE id=?", (target["id"],)).fetchone()["locked"] == 1
    assert res["regenerated"] >= 1


def test_trop_cher_choisit_moins_cher_et_ne_persiste_pas(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    fam = family_eq(get_settings(conn))
    cost = lambda rid: R.est_cost(R.recipe_ingredients(conn, rid), fam / 4)
    target = rows(conn)[0]
    old = cost(target["recipe_id"])
    PS.replace_meal(conn, target["id"], "too_expensive", rng=rng)
    new = conn.execute("SELECT recipe_id FROM plan WHERE id=?", (target["id"],)).fetchone()["recipe_id"]
    assert cost(new) < old
    assert conn.execute("SELECT COUNT(*) c FROM refused").fetchone()["c"] == 0  # rien de mémorisé


def test_absence_marque_skipped_et_sort_des_courses(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    need_before, _ = SH.needs(conn)
    target = rows(conn)[1]
    PS.skip_meal(conn, target["id"], rng=rng)
    r = conn.execute("SELECT * FROM plan WHERE id=?", (target["id"],)).fetchone()
    assert r["status"] == "skipped" and r["recipe_id"] is None
    PS.ensure_plan(conn, 7)  # ne recrée pas un repas sur un créneau « absent »
    assert conn.execute("SELECT status FROM plan WHERE id=?", (target["id"],)).fetchone()["status"] == "skipped"
    PS.restore_meal(conn, target["id"], rng=rng)
    assert conn.execute("SELECT recipe_id FROM plan WHERE id=?", (target["id"],)).fetchone()["recipe_id"]


def test_repas_passes_refuses(conn, rng, clock):
    PS.ensure_plan(conn, 3, rng=rng)
    first = rows(conn)[0]
    clock.advance(1)
    with pytest.raises(PS.PlanError):
        PS.skip_meal(conn, first["id"])


def test_courses_agregent_et_ignorent_les_basiques(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    lst = SH.compute_list(conn)
    names = {i["ingredient"] for i in lst["items"]}
    assert not names & {"sel", "poivre", "huile d'olive", "farine", "thym"}
    assert "lait" in names  # récurrent
    assert lst["total_est"] > 20 and all(i["buy_qty"] >= i["missing"] - 1e-6 for i in lst["items"] if i["status"] == "todo")
    assert len(names) == len(lst["items"])  # une ligne par ingrédient


def test_achat_en_quantite_differente_garde_le_surplus_en_stock(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    item = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "lait")
    SH.apply_ops(conn, [{"op_id": "a1", "type": "buy", "ingredient": "lait", "qty": item["missing"] + 3000}])
    lst = SH.compute_list(conn)
    lait = next(i for i in lst["items"] if i["ingredient"] == "lait")
    assert lait["status"] == "done"
    stock = conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone()["qty"]
    assert stock == pytest.approx(item["missing"] + 3000)


def test_ops_idempotentes_apres_coupure_reseau(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    op = {"op_id": "dup-1", "type": "buy", "ingredient": "lait", "qty": 1000}
    SH.apply_ops(conn, [op])
    r2 = SH.apply_ops(conn, [op, op])
    assert r2["applied"] == 0
    assert conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone()["qty"] == 1000


def test_archiver_masque_jusqua_ce_que_le_besoin_augmente(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    SH.apply_ops(conn, [{"op_id": "x1", "type": "archive", "ingredient": "lait"}])
    lait = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "lait")
    assert lait["status"] == "archived"
    # le besoin de lait augmente (horizon plus long) : l'article réapparaît
    PS.ensure_plan(conn, 14, rng=rng)
    lait = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "lait")
    assert lait["status"] == "todo"


def test_consommation_des_repas_passes_une_seule_fois(conn, rng, clock):
    PS.ensure_plan(conn, 7, rng=rng)
    first = rows(conn)[0]
    ings = [i for i in R.recipe_ingredients(conn, first["recipe_id"]) if not i["is_basic"] and i["qty"]]
    for i in ings:
        SH.set_stock(conn, i["ingredient"], 100000)
    clock.advance(1)
    SH.process_past(conn)
    SH.process_past(conn)  # deuxième appel : sans effet
    fam = family_eq(get_settings(conn))
    i0 = ings[0]
    got = conn.execute("SELECT qty FROM stock WHERE ingredient=?", (i0["ingredient"],)).fetchone()["qty"]
    expected = 100000 - i0["qty"] * fam / 4
    if i0["ingredient"] in ("lait", "céréales", "café"):
        pytest.skip("récurrent : décrément quotidien en plus")
    assert got == pytest.approx(expected)


def test_produit_recurrent_decroit_chaque_jour(conn, clock):
    SH.set_stock(conn, "lait", 5000)
    SH.process_past(conn)  # initialise l'horloge des récurrents
    clock.advance(2)
    SH.process_past(conn)
    assert conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone()["qty"] == pytest.approx(5000 - 2 * 5000 / 7)


def test_basique_bientot_fini_entre_dans_la_liste(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    SH.apply_ops(conn, [{"op_id": "s1", "type": "low", "ingredient": "sel"}])
    sel = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "sel")
    assert sel["status"] == "todo"
    SH.apply_ops(conn, [{"op_id": "s2", "type": "buy", "ingredient": "sel", "qty": 1000}])
    assert not any(i["ingredient"] == "sel" and i["status"] == "todo" for i in SH.compute_list(conn)["items"])


def test_ingredient_refuse_exclut_les_recettes_a_la_generation(conn, rng):
    conn.execute("INSERT INTO refused(name) VALUES('champignon')")
    conn.commit()
    PS.generate_all(conn, 14, rng=rng)
    for r in rows(conn):
        assert "champignon" not in {i["ingredient"] for i in R.recipe_ingredients(conn, r["recipe_id"])}


def test_get_plan_structure(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    p = PS.get_plan(conn, 7)
    assert len(p["days"]) == 7 and p["total_cost"] > 0
    assert p["days"][0]["weekday"] == "lundi" and p["days"][0]["free_slots"] == ["lunch"]


def test_meme_operation_envoyee_en_parallele_n_est_appliquee_qu_une_fois(conn, tmp_path):
    """Reproduit le bug trouvé au test de l'interface : deux requêtes simultanées portant le même op_id."""
    import threading
    from app import db
    PS.ensure_plan(conn, 7)
    errors, results = [], []

    def worker():
        c = db.connect()
        try:
            results.append(SH.apply_ops(c, [{"op_id": "course-1", "type": "buy", "ingredient": "lait", "qty": 1000}]))
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))
        finally:
            c.close()

    threads = [threading.Thread(target=worker) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors, errors
    assert sum(r["applied"] for r in results) == 1
    assert conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone()["qty"] == 1000


def test_meme_operation_deux_fois_dans_le_meme_lot(conn):
    r = SH.apply_ops(conn, [{"op_id": "z", "type": "buy", "ingredient": "lait", "qty": 500}] * 2)
    assert r["applied"] == 1 and r["skipped"] == 1


def test_ajout_article_inconnu_cree_un_article_a_verifier(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    assert SH.apply_ops(conn, [{"op_id": "n1", "type": "add", "ingredient": "  Papier  Alu "}])["applied"] == 1
    it = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "papier alu")
    assert it["status"] == "todo" and it["verified"] is False and it["aisle"] == "Divers"
    SH.apply_ops(conn, [{"op_id": "n2", "type": "add", "ingredient": "papier alu"}])
    assert conn.execute("SELECT COUNT(*) c FROM ingredients WHERE name='papier alu'").fetchone()["c"] == 1  # pas de doublon


def test_ajout_par_alias_reutilise_l_ingredient_du_catalogue(conn):
    before = conn.execute("SELECT COUNT(*) c FROM ingredients").fetchone()["c"]
    SH.apply_ops(conn, [{"op_id": "a1", "type": "add", "ingredient": "Œufs"}])
    assert conn.execute("SELECT COUNT(*) c FROM ingredients").fetchone()["c"] == before
    assert next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "oeuf")["status"] == "todo"


REC = {"lait", "céréales", "café"}   # récurrents : toujours présents
def _todo(conn):
    return {i["ingredient"] for i in SH.compute_list(conn)["items"] if i["status"] == "todo"} - REC

def test_courses_suivent_le_verrouillage(conn, rng):
    from app.settings import put_settings
    PS.ensure_plan(conn, 7, rng=rng)
    put_settings(conn, {"shopping_locked_only": True})
    assert _todo(conn) == set()
    first = rows(conn)[0]
    PS.set_lock(conn, first["id"], True)
    expected = {i["ingredient"] for i in R.recipe_ingredients(conn, first["recipe_id"])
                if not i["is_basic"] and not i["optional"]} - REC
    assert _todo(conn) == expected
    PS.set_lock(conn, first["id"], False)
    assert _todo(conn) == set()

def test_migration_jours_charges_vers_creneaux(conn):
    conn.execute("INSERT INTO settings(key,value) VALUES('busy_days','[2]')")
    conn.commit()
    s = get_settings(conn)
    assert s["busy_slots"]["2"] == {"lunch": True, "dinner": True} and s["busy_slots"]["0"] == {"lunch": False, "dinner": False}
    from app.settings import put_settings, busy_set
    put_settings(conn, {"busy_slots": {"2": {"lunch": True, "dinner": False}}})
    assert busy_set(get_settings(conn)) == {(2, "lunch")}

def test_courses_indiquent_les_recettes_concernees(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    first = rows(conn)[0]
    ing = next(i for i in R.recipe_ingredients(conn, first["recipe_id"]) if not i["is_basic"] and not i["optional"] and i["qty"])
    item = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == ing["ingredient"])
    assert first["recipe_id"] in {u["id"] for u in item["uses"]}
    for it in SH.compute_list(conn)["items"]:          # chaque lien désigne bien une recette qui contient l'ingrédient
        for u in it["uses"]:
            assert it["ingredient"] in {i["ingredient"] for i in R.recipe_ingredients(conn, u["id"])}

def test_annuler_un_achat_restitue_exactement_le_stock(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    stock = lambda: (conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone() or {"qty": 0})["qty"]
    base = stock()
    item = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "lait")
    SH.apply_ops(conn, [{"op_id": "b1", "type": "buy", "ingredient": "lait", "qty": item["buy_qty"]}])
    assert stock() > base
    # le client envoie ici volontairement une quantité fausse (le besoin) : le serveur doit l'ignorer
    SH.apply_ops(conn, [{"op_id": "u1", "type": "unbuy", "ingredient": "lait", "qty": item["required"]}])
    assert stock() == pytest.approx(base)
    lait = next(i for i in SH.compute_list(conn)["items"] if i["ingredient"] == "lait")
    assert lait["status"] == "todo"

def test_annuler_un_achat_en_autre_quantite(conn, rng):
    PS.ensure_plan(conn, 7, rng=rng)
    SH.apply_ops(conn, [{"op_id": "b2", "type": "buy", "ingredient": "lait", "qty": 7777}])
    SH.apply_ops(conn, [{"op_id": "u2", "type": "unbuy", "ingredient": "lait", "qty": 1}])
    assert conn.execute("SELECT qty FROM stock WHERE ingredient='lait'").fetchone()["qty"] == pytest.approx(0)

def test_achats_historises_annules_et_estimation(conn, clock):
    for i in range(3):
        SH.apply_ops(conn, [{"op_id": f"b{i}", "type": "buy", "ingredient": "lait", "qty": 1000}])
        if i < 2:
            clock.advance(14)
    assert SH.estimate_weekly(conn, "lait")["weekly_qty"] == pytest.approx(500)   # 2000 consommés en 28 jours
    SH.apply_ops(conn, [{"op_id": "u1", "type": "unbuy", "ingredient": "lait", "qty": 1000}])
    assert SH.estimate_weekly(conn, "lait")["weekly_qty"] == pytest.approx(1000 / 14 * 7)   # dernier lot annulé : 1000 sur 14 j


def test_estimation_impossible_sans_assez_d_achats(conn, clock):
    assert SH.estimate_weekly(conn, "lait")["weekly_qty"] is None
    SH.apply_ops(conn, [{"op_id": "e1", "type": "buy", "ingredient": "lait", "qty": 1000}])
    clock.advance(3)
    SH.apply_ops(conn, [{"op_id": "e2", "type": "buy", "ingredient": "lait", "qty": 1000}])
    assert SH.estimate_weekly(conn, "lait")["weekly_qty"] is None     # moins de 7 jours d'écart


def test_saisie_avec_quantite_en_tete_ne_cree_pas_d_ingredient_bizarre(conn):
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    assert I.find_or_create(conn, cat, "10 yaourt") == "yaourt"
