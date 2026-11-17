# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from fastapi.testclient import TestClient
from app import config, importer


@pytest.fixture
def client(tmp_path, monkeypatch, clock):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "menu.db")
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(config, "APP_PASSWORD", "mdp-test")
    from app import auth
    auth._fails.clear()
    from app.main import app
    with TestClient(app) as c:
        yield c


def login(c, pw="mdp-test"):
    return c.post("/api/login", json={"password": pw})


def test_api_protegee(client):
    for path in ("/api/plan", "/api/shopping", "/api/recipes", "/api/settings", "/api/backup"):
        assert client.get(path).status_code == 401
    assert client.get("/healthz").status_code == 200


def test_login_mauvais_mot_de_passe_puis_limitation(client):
    assert login(client, "faux").status_code == 401
    for _ in range(5):
        login(client, "faux")
    assert login(client).status_code == 429  # même avec le bon mot de passe : verrouillé 15 min


def test_session_cookie_et_deconnexion(client):
    r = login(client)
    assert r.status_code == 200 and "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/api/me").status_code == 200
    client.post("/api/logout")
    assert client.get("/api/me").status_code == 401


def test_session_expiree(client, clock):
    login(client)
    clock.advance(31)
    assert client.get("/api/me").status_code == 401


def test_changer_le_mot_de_passe_en_env_revoque_les_sessions(client, monkeypatch, tmp_path):
    login(client)
    from app import auth, db
    monkeypatch.setattr(config, "APP_PASSWORD", "nouveau")
    c = db.connect(); auth.init_user(c); c.close()
    assert client.get("/api/me").status_code == 401
    assert login(client, "nouveau").status_code == 200


def test_parcours_complet(client):
    login(client)
    plan = client.get("/api/plan?days=7").json()
    assert len(plan["days"]) == 7 and plan["total_cost"] > 0
    first = next(e for d in plan["days"] for e in d["entries"])
    r = client.post(f"/api/plan/{first['id']}/replace", json={"reason": "refuse_ingredient", "ingredient": "champignons"})
    assert r.status_code == 200
    assert "champignon" in client.get("/api/refused").json()
    rid = client.get("/api/plan").json()["days"][0]["entries"][0]["recipe"]["id"]
    rec = client.get(f"/api/recipes/{rid}").json()
    assert rec["steps"] and rec["ingredients"] and rec["family_portions"] == pytest.approx(3.8)
    shop = client.get("/api/shopping").json()
    assert shop["count_todo"] > 5
    it = shop["items"][0]
    out = client.post("/api/shopping/ops", json={"ops": [{"op_id": "t1", "type": "buy", "ingredient": it["ingredient"], "qty": it["buy_qty"]}]}).json()
    assert out["applied"] == 1
    assert next(i for i in out["list"]["items"] if i["ingredient"] == it["ingredient"])["status"] == "done"


def test_erreurs_metier_en_400(client):
    login(client)
    assert client.post("/api/plan/9999/skip", json={}).status_code == 400
    assert client.post("/api/plan/9999/replace", json={"reason": "autre"}).status_code == 400


def test_import_url_et_enregistrement(client, monkeypatch):
    login(client)
    html = open("tests/fixtures/recette-exemple.html", encoding="utf-8").read()
    monkeypatch.setattr(importer, "fetch_html", lambda url: html)
    d = client.post("/api/recipes/import", json={"url": "https://exemple-recettes.test/gratin"}).json()
    assert d["title"] == "Gratin d'exemple"
    d["ingredients"] = [{"raw": l["raw"], "ingredient": l["ingredient"]} if l["ingredient"] else l["raw"] for l in d["ingredients"]]
    rid = client.post("/api/recipes", json=d).json()["id"]
    assert client.get(f"/api/recipes/{rid}").json()["title"] == "Gratin d'exemple"


def test_import_echec_message_utilisateur(client):
    login(client)
    r = client.post("/api/recipes/import", json={"url": "http://127.0.0.1/x"})
    assert r.status_code == 422 and "privé" in r.json()["detail"]


def test_sauvegarde_telechargeable_et_quotidienne(client, tmp_path):
    login(client)
    r = client.get("/api/backup")
    assert r.status_code == 200 and r.content[:15] == b"SQLite format 3"
    from app.main import backup_db
    assert backup_db() is not None or list((tmp_path / "backups").glob("menu-*.db"))


def test_saisie_manuelle_recette(client):
    login(client)
    rid = client.post("/api/recipes", json={"title": "Crêpes", "servings": 4, "protein": "veggie", "carb": "autre", "meals": "d",
                                              "ingredients": ["250 g de farine", "50 cl de lait", "3 oeufs"], "steps": ["Mélanger.", "Cuire."]}).json()["id"]
    ing = {i["ingredient"]: i for i in client.get(f"/api/recipes/{rid}").json()["ingredients"]}
    assert set(ing) == {"farine", "lait", "oeuf"}
