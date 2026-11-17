# SPDX-License-Identifier: AGPL-3.0-or-later
"""Compte unique, sessions en base (révocables), limitation des tentatives."""
import hashlib, hmac, secrets, time
from datetime import timedelta
from fastapi import Cookie, Depends, HTTPException, Request, Response
from . import config
from .db import connect

COOKIE = "mf_session"
_fails: dict[str, list[float]] = {}  # en mémoire : remis à zéro au redémarrage (acceptable ici)


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${h.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, h = stored.split("$")
        calc = hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p))
        return hmac.compare_digest(calc.hex(), h)
    except Exception:
        return False


def init_user(conn) -> None:
    if not config.APP_PASSWORD:
        raise RuntimeError("APP_PASSWORD n'est pas défini : refus de démarrer sans mot de passe.")
    row = conn.execute("SELECT id, pw_hash FROM users WHERE username=?", (config.APP_USERNAME,)).fetchone()
    if row is None:
        conn.execute("DELETE FROM users")
        conn.execute("INSERT INTO users(username, pw_hash) VALUES(?,?)",
                     (config.APP_USERNAME, hash_password(config.APP_PASSWORD)))
    elif not verify_password(config.APP_PASSWORD, row["pw_hash"]):
        # Le mot de passe de l'environnement a changé : il fait foi, les sessions sont révoquées.
        conn.execute("UPDATE users SET pw_hash=? WHERE id=?", (hash_password(config.APP_PASSWORD), row["id"]))
        conn.execute("DELETE FROM sessions")
    conn.commit()


def _th(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def set_cookie(response: Response, token: str) -> None:
    response.set_cookie(COOKIE, token, max_age=config.SESSION_DAYS * 86400, httponly=True,
                        samesite="lax", secure=config.COOKIE_SECURE, path="/")


def new_session(conn, user_id: int, response: Response) -> None:
    token = secrets.token_urlsafe(32)
    exp = config.now() + timedelta(days=config.SESSION_DAYS)
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (config.now().isoformat(),))
    conn.execute("INSERT INTO sessions VALUES(?,?,?,?)",
                 (_th(token), user_id, exp.isoformat(), config.now().isoformat()))
    conn.commit()
    set_cookie(response, token)


def check_rate(ip: str) -> None:
    recent = [t for t in _fails.get(ip, []) if time.time() - t < 900]
    _fails[ip] = recent
    if len(recent) >= 5:
        raise HTTPException(429, "Trop de tentatives. Réessayez dans 15 minutes.")


def record_fail(ip: str) -> None:
    _fails.setdefault(ip, []).append(time.time())


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def require_auth(request: Request, response: Response, conn=Depends(get_db),
                 mf_session: str | None = Cookie(default=None)):
    if not mf_session:
        raise HTTPException(401, "Non connecté")
    row = conn.execute("SELECT user_id, expires_at FROM sessions WHERE token_hash=?", (_th(mf_session),)).fetchone()
    if row is None or row["expires_at"] < config.now().isoformat():
        raise HTTPException(401, "Session expirée")
    # session glissante : prolongée tant qu'on s'en sert
    exp = config.now() + timedelta(days=config.SESSION_DAYS)
    if row["expires_at"] < (config.now() + timedelta(days=config.SESSION_DAYS / 2)).isoformat():
        conn.execute("UPDATE sessions SET expires_at=? WHERE token_hash=?", (exp.isoformat(), _th(mf_session)))
        conn.commit()
        set_cookie(response, mf_session)
    return row["user_id"]
