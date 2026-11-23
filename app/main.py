# SPDX-License-Identifier: AGPL-3.0-or-later
"""API FastAPI + service des fichiers statiques de la PWA."""
import asyncio, json, logging, os, shutil, sqlite3, tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from . import auth, config, db, importer, plan_service as PS, recipes as R, seed_recipes, shopping as SH
from . import ingredients as I
from .settings import family_eq, get_settings, put_settings

log = logging.getLogger("menu")
logging.basicConfig(level=logging.INFO)
STATIC = Path(__file__).parent / "static"


def backup_db() -> Path | None:
    """Copie cohérente de la base (API de sauvegarde SQLite), une par jour, les N dernières conservées."""
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.BACKUP_DIR / f"menu-{config.today().isoformat()}.db"
    if dest.exists():
        return None
    src, dst = db.connect(), sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close(); src.close()
    for old in sorted(config.BACKUP_DIR.glob("menu-*.db"))[:-config.BACKUP_KEEP]:
        old.unlink()
    return dest


async def _backup_loop():
    while True:
        try:
            await asyncio.to_thread(backup_db)
        except Exception:
            log.exception("Sauvegarde automatique en échec")
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = db.connect()
    db.migrate(conn)
    auth.init_user(conn)
    I.seed_catalog(conn)
    if os.getenv("SEED_RECIPES", "true").lower() != "false":
        n = seed_recipes.load_seed(conn, I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall()))
        if n:
            log.info("Bibliothèque de départ chargée : %d recettes", n)
    conn.close()
    log.info("Cookie de session Secure=%s (mettre COOKIE_SECURE=false uniquement pour un test en HTTP)", config.COOKIE_SECURE)
    task = asyncio.create_task(_backup_loop())
    yield
    task.cancel()


app = FastAPI(title="Menus de la famille", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
api = APIRouter(prefix="/api", dependencies=[Depends(auth.require_auth)])
db_dep = Depends(auth.get_db)


def catalog(conn) -> I.Catalog:
    return I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())


# ---------- authentification ----------
class Login(BaseModel):
    username: str = ""
    password: str


@app.post("/api/login")
def login(body: Login, request: Request, response: Response, conn=db_dep):
    ip = request.client.host if request.client else "?"
    auth.check_rate(ip)
    row = conn.execute("SELECT id, pw_hash FROM users WHERE username=?", (body.username or config.APP_USERNAME,)).fetchone()
    if not row or not auth.verify_password(body.password, row["pw_hash"]):
        auth.record_fail(ip)
        raise HTTPException(401, "Identifiant ou mot de passe incorrect")
    auth.new_session(conn, row["id"], response)
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response, conn=db_dep):
    tok = request.cookies.get(auth.COOKIE)
    if tok:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (auth._th(tok),))
        conn.commit()
    response.delete_cookie(auth.COOKIE, path="/")
    return {"ok": True}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@api.get("/me")
def me():
    return {"ok": True}


# ---------- réglages ----------
@api.get("/settings")
def settings_get(conn=db_dep):
    s = get_settings(conn)
    return {**s, "family_eq": family_eq(s)}


@api.put("/settings")
def settings_put(body: dict[str, Any], conn=db_dep):
    s = put_settings(conn, body)
    return {**s, "family_eq": family_eq(s)}


# ---------- planning ----------
def _plan_call(fn, *a, **k):
    try:
        return fn(*a, **k)
    except PS.PlanError as e:
        raise HTTPException(400, str(e))


class Replace(BaseModel):
    reason: str
    ingredient: str | None = None
    regenerate_following: bool = True


class Following(BaseModel):
    regenerate_following: bool = True


class Slot(BaseModel):
    day: str
    slot: str


@api.get("/plan")
def plan_get(days: int | None = None, conn=db_dep):
    if days is not None and not 1 <= days <= 21:
        raise HTTPException(400, "days doit être entre 1 et 21")
    PS.ensure_plan(conn, days)
    return PS.get_plan(conn, days)


@api.post("/plan/generate")
def plan_generate(days: int | None = None, conn=db_dep):
    PS.generate_all(conn, days)
    return PS.get_plan(conn, days)


@api.post("/plan/add")
def plan_add(body: Slot, conn=db_dep):
    return {"id": _plan_call(PS.add_meal, conn, body.day, body.slot)}


@api.post("/plan/{pid}/replace")
def plan_replace(pid: int, body: Replace, conn=db_dep):
    return _plan_call(PS.replace_meal, conn, pid, body.reason, body.ingredient, body.regenerate_following)


@api.post("/plan/{pid}/skip")
def plan_skip(pid: int, body: Following, conn=db_dep):
    return _plan_call(PS.skip_meal, conn, pid, body.regenerate_following)


@api.post("/plan/{pid}/restore")
def plan_restore(pid: int, conn=db_dep):
    _plan_call(PS.restore_meal, conn, pid)
    return {"ok": True}


@api.post("/plan/{pid}/lock")
def plan_lock(pid: int, body: dict[str, bool], conn=db_dep):
    _plan_call(PS.set_lock, conn, pid, bool(body.get("locked")))
    return {"ok": True}


@api.post("/plan/{pid}/set_recipe")
def plan_set_recipe(pid: int, body: dict[str, Any], conn=db_dep):
    return _plan_call(PS.set_recipe, conn, pid, int(body["recipe_id"]), bool(body.get("regenerate_following", False)))


# ---------- recettes ----------
class RecipeIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    steps: list[str] = []
    ingredients: list[str | dict[str, Any]] = []
    servings: float = 4
    prep_min: int | None = None
    cook_min: int | None = None
    meals: str = "dl"
    protein: str = "autre"
    carb: str = "autre"
    months: list[int] = []
    tags: list[str] = []
    source_url: str | None = None
    source_type: str = "manual"
    image_url: str | None = None


class ImportIn(BaseModel):
    url: str
    html: str | None = None


@api.get("/recipes")
def recipes_list(q: str = "", conn=db_dep):
    like = f"%{q.strip().lower()}%"
    rows = conn.execute("SELECT * FROM recipes WHERE archived=0 AND lower(title) LIKE ? ORDER BY favorite DESC, title", (like,))
    return [R.recipe_summary(r) for r in rows]


@api.post("/recipes/import")
def recipes_import(body: ImportIn, conn=db_dep):
    try:
        html = body.html or importer.fetch_html(body.url.strip())
        return importer.draft_from_html(conn, html, body.url.strip())
    except importer.ImportError_ as e:
        raise HTTPException(422, str(e))


@api.post("/recipes")
def recipes_create(body: RecipeIn, conn=db_dep):
    return {"id": R.save_recipe(conn, catalog(conn), body.model_dump())}


@api.get("/recipes/{rid}")
def recipe_get(rid: int, conn=db_dep):
    r = conn.execute("SELECT * FROM recipes WHERE id=? AND archived=0", (rid,)).fetchone()
    if not r:
        raise HTTPException(404, "Recette introuvable")
    s = get_settings(conn)
    factor = family_eq(s) / r["servings"]
    rows = R.recipe_ingredients(conn, rid)
    return {**R.recipe_summary(r), "steps": json.loads(r["steps"]), "source_url": r["source_url"], "servings": r["servings"],
            "family_portions": family_eq(s), "factor": round(factor, 3), "months": json.loads(r["months"]),
            "meals": r["meals"], "ingredients": R.scaled_lines(rows, factor), "cost": R.est_cost(rows, factor),
            "raw_ingredients": [x["raw"] for x in rows]}


@api.put("/recipes/{rid}")
def recipe_update(rid: int, body: RecipeIn, conn=db_dep):
    if not conn.execute("SELECT 1 FROM recipes WHERE id=?", (rid,)).fetchone():
        raise HTTPException(404, "Recette introuvable")
    R.save_recipe(conn, catalog(conn), body.model_dump(), recipe_id=rid)
    return {"id": rid}


@api.delete("/recipes/{rid}")
def recipe_delete(rid: int, conn=db_dep):
    conn.execute("UPDATE recipes SET archived=1 WHERE id=?", (rid,))  # archivée : l'historique du planning reste cohérent
    conn.commit()
    return {"ok": True}


@api.post("/recipes/{rid}/rate")
def recipe_rate(rid: int, body: dict[str, Any], conn=db_dep):
    rating = max(-1, min(1, int(body.get("rating", 0))))
    conn.execute("UPDATE recipes SET rating=?, favorite=? WHERE id=?", (rating, int(bool(body.get("favorite"))), rid))
    conn.commit()
    return {"ok": True}


# ---------- ingrédients refusés, catalogue, stock ----------
@api.get("/refused")
def refused_list(conn=db_dep):
    return [r["name"] for r in conn.execute("SELECT name FROM refused ORDER BY name")]


@api.post("/refused")
def refused_add(body: dict[str, str], conn=db_dep):
    name, _ = catalog(conn).match(body.get("name", ""))
    name = name or body.get("name", "").strip().lower()
    if not name:
        raise HTTPException(400, "Nom vide")
    conn.execute("INSERT OR IGNORE INTO refused(name) VALUES(?)", (name,))
    conn.commit()
    return {"name": name}


@api.delete("/refused/{name}")
def refused_del(name: str, conn=db_dep):
    conn.execute("DELETE FROM refused WHERE name=?", (name,))
    conn.commit()
    return {"ok": True}


@api.get("/ingredients")
def ingredients_list(conn=db_dep):
    return [dict(r) for r in conn.execute("SELECT * FROM ingredients ORDER BY verified, aisle, name")]


EDITABLE = {"aisle", "price", "pack_qty", "pack_label", "is_basic", "is_recurrent", "weekly_qty", "verified"}


@api.put("/ingredients/{name}")
def ingredient_update(name: str, body: dict[str, Any], conn=db_dep):
    sets = {k: v for k, v in body.items() if k in EDITABLE}
    if not sets or not conn.execute("SELECT 1 FROM ingredients WHERE name=?", (name,)).fetchone():
        raise HTTPException(400, "Rien à modifier")
    conn.execute(f"UPDATE ingredients SET {','.join(k + '=?' for k in sets)} WHERE name=?", (*sets.values(), name))
    conn.commit()
    return {"ok": True}


@api.get("/stock")
def stock_list(conn=db_dep):
    SH.process_past(conn)
    return [dict(r) for r in conn.execute(
        "SELECT s.ingredient, s.qty, i.kind, i.aisle, i.is_recurrent, i.is_basic FROM stock s "
        "JOIN ingredients i ON i.name=s.ingredient WHERE s.qty>0 ORDER BY i.aisle, s.ingredient")]


@api.put("/stock/{name}")
def stock_set(name: str, body: dict[str, float], conn=db_dep):
    if not conn.execute("SELECT 1 FROM ingredients WHERE name=?", (name,)).fetchone():
        raise HTTPException(404, "Ingrédient inconnu")
    SH.set_stock(conn, name, float(body.get("qty", 0)))
    conn.commit()
    return {"ok": True}


# ---------- courses ----------
class Ops(BaseModel):
    ops: list[dict[str, Any]]


@api.get("/shopping")
def shopping_get(conn=db_dep):
    PS.ensure_plan(conn)
    return SH.compute_list(conn)


@api.post("/shopping/ops")
def shopping_ops(body: Ops, conn=db_dep):
    res = SH.apply_ops(conn, body.ops)
    return {**res, "list": SH.compute_list(conn)}


@api.get("/backup")
def backup_download(conn=db_dep):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    dst = sqlite3.connect(path)
    conn.backup(dst)
    dst.close()
    return FileResponse(path, filename=f"menu-{config.today().isoformat()}.db",
                        background=__import__("starlette.background", fromlist=["x"]).BackgroundTask(os.unlink, path))


app.include_router(api)


@app.middleware("http")
async def no_cache_shell(request: Request, call_next):
    resp = await call_next(request)
    if request.url.path in ("/", "/sw.js", "/index.html", "/manifest.webmanifest"):
        resp.headers["Cache-Control"] = "no-cache"
    if request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
