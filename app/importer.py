# SPDX-License-Identifier: AGPL-3.0-or-later
"""Import d'une recette depuis une URL (ou du code source collé) via recipe-scrapers 15.x.
On télécharge nous-mêmes la page (scrape_html) : plus de dépendance au téléchargement intégré, déprécié."""
import ipaddress, re, socket
from urllib.parse import urljoin, urlparse
import requests
from recipe_scrapers import scrape_html
from recipe_scrapers._exceptions import (ElementNotFoundInHtml, FieldNotProvidedByWebsiteException,
                                         NoSchemaFoundInWildMode, WebsiteNotImplementedError)
from . import config, ingredients as I

UA = "Mozilla/5.0 (compatible; MenuFamille/1.0; usage personnel auto-hébergé)"
MAX_BYTES = 3 * 1024 * 1024


class ImportError_(Exception):
    """Erreur présentable à l'utilisateur."""


def check_url(url: str) -> None:
    """Refuse les schémas non http(s) et les adresses privées/locales (protection SSRF).
    Limite connue : un nom de domaine qui change de réponse entre ce contrôle et la requête (DNS rebinding) n'est pas couvert."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ImportError_("Adresse invalide : elle doit commencer par http:// ou https://")
    if config.ALLOW_PRIVATE_FETCH:
        return
    try:
        infos = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ImportError_("Nom de domaine introuvable")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ImportError_("Cette adresse pointe vers un réseau privé : import refusé")


def fetch_html(url: str) -> str:
    cur = url
    for _ in range(4):  # redirections suivies à la main, chaque étape est revalidée
        check_url(cur)
        try:
            r = requests.get(cur, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"},
                             timeout=15, allow_redirects=False, stream=True)
        except requests.RequestException:
            raise ImportError_("Le site ne répond pas. Vous pouvez coller le code source de la page ou saisir la recette à la main.")
        if r.is_redirect or r.status_code in (301, 302, 303, 307, 308):
            cur = urljoin(cur, r.headers.get("Location", ""))
            r.close()
            continue
        if r.status_code in (401, 403, 429, 503):
            r.close()
            raise ImportError_("Le site refuse l'accès automatique (protection anti-robot). "
                               "Collez le code source de la page, ou saisissez la recette à la main.")
        if r.status_code >= 400:
            r.close()
            raise ImportError_(f"Le site a répondu avec une erreur ({r.status_code}).")
        data = b""
        for chunk in r.iter_content(65536):
            data += chunk
            if len(data) > MAX_BYTES:
                r.close()
                raise ImportError_("Page trop volumineuse")
        r.encoding = r.encoding or r.apparent_encoding
        return data.decode(r.encoding or "utf-8", errors="replace")
    raise ImportError_("Trop de redirections")


_HEAD = re.compile(r"^\s*[ée]tape\s*\d+\s*[:\-–.]?", re.I)


def clean_steps(steps: list[str]) -> list[str]:
    """Retire les intertitres « Étape 1 : … » et recolle les phrases coupées en plein milieu."""
    lines = [s.strip() for s in steps if s and s.strip()]
    lines = [s for i, s in enumerate(lines) if not (_HEAD.match(s) and len(s) < 90 and i + 1 < len(lines))]
    out: list[str] = []
    for s in lines:
        if out and not re.search(r"[.!?:;…)]\s*$", out[-1]) and s[:1].islower():
            out[-1] = out[-1] + " " + s
        else:
            out.append(s)
    return out


PROTEIN_HINTS = {"volaille": {"blanc de poulet", "cuisse de poulet", "escalope de dinde", "cordon bleu"},
                 "boeuf": {"boeuf haché"}, "porc": {"filet mignon de porc", "lardons", "jambon blanc", "saucisse"},
                 "poisson": {"cabillaud", "saumon", "thon"}}
CARB_HINTS = {"pates": {"pâtes", "gnocchi", "feuilles de lasagne"}, "riz": {"riz"}, "pdt": {"pomme de terre"},
              "semoule": {"semoule"}}


def _guess(names: set[str], hints: dict, default: str) -> str:
    for k, v in hints.items():
        if names & v:
            return k
    return default


def _int(s) -> int | None:
    m = re.search(r"\d+", str(s or ""))
    return int(m.group()) if m else None


def draft_from_html(conn, html: str, url: str) -> dict:
    """Brouillon de recette à relire avant enregistrement (rien n'est écrit en base)."""
    try:
        sc = scrape_html(html, org_url=url, supported_only=False)
        title = sc.title()
        raw_ings = sc.ingredients()
    except (WebsiteNotImplementedError, NoSchemaFoundInWildMode):
        raise ImportError_("Aucune recette structurée trouvée sur cette page. Saisissez-la à la main.")
    except (ElementNotFoundInHtml, FieldNotProvidedByWebsiteException, Exception):
        raise ImportError_("La page a été lue mais la recette n'a pas pu être extraite "
                           "(le site a peut-être changé de format). Saisissez-la à la main.")

    def opt(fn):
        try:
            return fn()
        except Exception:
            return None

    steps = clean_steps(opt(sc.instructions_list) or [])
    cat = I.Catalog(conn.execute("SELECT * FROM ingredients").fetchall())
    lines, names = [], set()
    for raw in raw_ings:
        p = I.parse_line(raw)
        name, sure = cat.match(p["name"])
        names.add(name or "")
        lines.append({"raw": raw, "ingredient": name, "status": "unknown" if name is None else ("ok" if sure else "check"),
                      "qty": p["qty"], "unit": p["unit"]})
    prep, cook, total = opt(sc.prep_time), opt(sc.cook_time), opt(sc.total_time)
    if not prep and not cook and total:
        cook = total
    return {"title": title, "source_url": opt(sc.canonical_url) or url, "source_type": "import",
            "image_url": opt(sc.image), "servings": _int(opt(sc.yields)) or 4, "prep_min": prep, "cook_min": cook,
            "steps": steps, "ingredients": lines, "protein": _guess(names, PROTEIN_HINTS, "veggie" if names else "autre"),
            "carb": _guess(names, CARB_HINTS, "autre"), "meals": "dl", "months": [], "tags": []}
