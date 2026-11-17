# SPDX-License-Identifier: AGPL-3.0-or-later
"""Analyse des lignes d'ingrédients françaises, rapprochement avec le catalogue, conversion d'unités."""
import json, math, re, unicodedata
from . import catalog_seed as cs

STOP = {"de", "d", "du", "des", "la", "le", "les", "l", "et", "au", "aux", "a", "en", "un", "une", "ou", "bien"}
MASS = {"g": 1.0, "kg": 1000.0, "mg": 0.001}
VOL = {"ml": 1.0, "cl": 10.0, "dl": 100.0, "l": 1000.0, "cs": 15.0, "cc": 5.0, "verre": 200.0}
COUNT_WORDS = {"pincee", "sachet", "gousse", "tranche", "botte", "boite", "branche", "brin", "feuille",
               "pot", "paquet", "brique", "tete", "bocal", "piece"}
UNIT_SYN = {
    "g": "g", "gr": "g", "gramme": "g", "grammes": "g", "kg": "kg", "mg": "mg",
    "ml": "ml", "cl": "cl", "dl": "dl", "l": "l", "litre": "l", "litres": "l",
    "cs": "cs", "cc": "cc", "verre": "verre", "verres": "verre",
    "pincée": "pincee", "pincées": "pincee", "pincee": "pincee",
    "sachet": "sachet", "sachets": "sachet", "gousse": "gousse", "gousses": "gousse",
    "tranche": "tranche", "tranches": "tranche", "botte": "botte", "bottes": "botte",
    "boîte": "boite", "boîtes": "boite", "boite": "boite", "boites": "boite",
    "branche": "branche", "branches": "branche", "brin": "brin", "brins": "brin",
    "feuille": "feuille", "feuilles": "feuille", "pot": "pot", "pots": "pot",
    "paquet": "paquet", "paquets": "paquet", "brique": "brique", "briques": "brique",
}
FR_NUM = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "demi": 0.5, "demie": 0.5}
FRAC = {"½": " 0.5", "¼": " 0.25", "¾": " 0.75", "⅓": " 0.33"}
CS_RE = re.compile(r"\bc(?:uill?[eè]res?|uil\.?)?\.?\s*[àa]\.?\s*s(?:oupe)?\b\.?")
CC_RE = re.compile(r"\bc(?:uill?[eè]res?|uil\.?)?\.?\s*[àa]\.?\s*c(?:af[eé])?\b\.?|\bc\.c\b\.?")
NUM_RE = re.compile(r"^\s*(\d+(?:[.,]\d+)?)(?:\s*(?:à|a|-|ou)\s*(\d+(?:[.,]\d+)?))?(?:\s+(\d+)/(\d+))?")
SLASH_RE = re.compile(r"^\s*(\d+)/(\d+)")
UNIT_RE = re.compile(r"^\s*(" + "|".join(sorted(map(re.escape, UNIT_SYN), key=len, reverse=True)) + r")\b\.?")
LEAD_RE = re.compile(r"^\s*(?:de la |de l'|de l’|d'|d’|du |des |de |la |le |les )")


def fold(s: str) -> str:
    s = s.lower().replace("œ", "oe").replace("’", "'")
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t[-1] in "sx" else t


def tokens(s: str) -> list[str]:
    return [_stem(t) for t in fold(s).split() if t not in STOP]


DESCRIPTORS = {_stem(w) for w in (
    "filet", "morceau", "pave", "tranche", "cuisse", "blanc", "escalope", "gousse", "branche", "brin",
    "feuille", "botte", "bouquet", "pot", "boite", "tete", "noix", "des", "de", "lamelle", "rondelle",
    "quartier", "pilon", "haut", "bloc", "bout", "poignee", "zeste", "jus", "gros", "petit", "grand",
    "beau", "belle", "frais", "fraiche", "surgele", "surgelee")}


def parse_line(raw: str) -> dict:
    """'6 c.à.s d'huile d'olive' -> {qty: 6, unit: 'cs', name: "huile d'olive", ...}"""
    s = raw.strip().lower().replace("’", "'")
    optional = "facultatif" in s or "optionnel" in s
    s = re.sub(r"\([^)]*\)", " ", s)
    for k, v in FRAC.items():
        s = s.replace(k, v)
    s = CS_RE.sub(" cs ", s)
    s = CC_RE.sub(" cc ", s)
    s = re.sub(r"\s+", " ", s).strip()
    qty = None
    m = SLASH_RE.match(s)
    if m:
        qty = int(m.group(1)) / int(m.group(2))
        s = s[m.end():]
    elif (m := NUM_RE.match(s)):
        qty = float((m.group(2) or m.group(1)).replace(",", "."))
        if m.group(3):
            qty += int(m.group(3)) / int(m.group(4))
        s = s[m.end():]
    elif re.match(r"^(un peu|quelques|une poignée|une noix)\b", s):
        s = re.sub(r"^(un peu|quelques|une poignée|une noix)\s*", "", s)  # quantité vague : pas de chiffre
    else:
        w = s.split(" ", 1)
        if w[0] in FR_NUM:
            qty = FR_NUM[w[0]]
            s = w[1] if len(w) > 1 else ""
    unit = None
    um = UNIT_RE.match(s)
    if um and (qty is not None or um.group(1) in ("pincée", "pincee", "pincées")):
        unit = UNIT_SYN[um.group(1)]
        s = s[um.end():]
    s = LEAD_RE.sub("", s.strip()).strip(" ,.-")
    s = re.sub(r"\s*(?:facultatif|optionnel)\s*", " ", s).strip(" ,.-")
    return {"qty": qty, "unit": unit, "name": s, "optional": optional, "raw": raw.strip()}


class Catalog:
    """Rapprochement d'un libellé libre avec une entrée du catalogue (ensemble de mots contenu, le plus long gagne)."""

    def __init__(self, rows):
        self.rows = {r["name"]: dict(r) for r in rows}
        self.phrases = []  # (frozenset(tokens), name)
        for r in self.rows.values():
            for p in [r["name"], *json.loads(r["aliases"] or "[]")]:
                t = frozenset(tokens(p))
                if t:
                    self.phrases.append((t, r["name"]))

    def match(self, label: str) -> tuple[str | None, bool]:
        """(nom canonique, sûr ?). Pas sûr si le premier mot du libellé (le nom principal en français)
        n'est pas couvert par l'entrée trouvée : « vinaigrette citron » ne doit pas devenir « citron »."""
        toks_list = tokens(label)
        toks = set(toks_list)
        best, best_t, best_n = None, frozenset(), 0
        for t, name in self.phrases:
            if t <= toks and len(t) > best_n:
                best, best_t, best_n = name, t, len(t)
        if best is None:
            return None, False
        head = toks_list[0] if toks_list else ""
        return best, (head in best_t or head in DESCRIPTORS)

    def exact(self, label: str) -> str | None:
        """Nom canonique si le libellé correspond EXACTEMENT (mêmes mots, casse/accents/pluriel ignorés)
        à un nom ou un alias. Plus strict que match() : pour la saisie libre d'un article."""
        toks = frozenset(tokens(label))
        if not toks:
            return None
        for t, name in self.phrases:
            if t == toks:
                return name
        return None


def to_base(qty: float | None, unit: str | None, ing: dict) -> float | None:
    """Convertit (qty, unit) vers l'unité de base de l'ingrédient (g, ml ou piece). Approximatif : voir README."""
    if qty is None:
        return None
    dens = ing.get("density") or 1.0
    pg = ing.get("piece_g") or 100.0  # poids de pièce par défaut si inconnu
    if unit in MASS:
        v, kind = qty * MASS[unit], "g"
    elif unit in VOL:
        v, kind = qty * VOL[unit], "ml"
    else:
        v, kind = qty, "piece"
    target = ing["kind"]
    if kind == target:
        return v
    if kind == "piece":
        g = v * pg
        return g if target == "g" else g / dens
    g = v if kind == "g" else v * dens
    return g if target == "g" else (g / dens if target == "ml" else g / pg)


def pack_info(ing: dict) -> tuple[float, str | None]:
    step = ing.get("pack_qty") or cs.DEFAULT_STEP[ing["kind"]]
    return step, ing.get("pack_label")


def price_per_base(ing: dict) -> float:
    p = ing.get("price")
    if p is None:
        return cs.DEFAULT_PRICE[ing["kind"]]
    if ing.get("pack_qty"):
        return p / ing["pack_qty"]
    return p / (1000.0 if ing["kind"] in ("g", "ml") else 1.0)


def seed_catalog(conn) -> None:
    """Ajoute les entrées manquantes (n'écrase jamais une modification de l'utilisateur)."""
    for line in cs.CATALOG.strip().splitlines():
        f = [x.strip() for x in line.split("|")]
        name, aliases, aisle, kind, pg, dens, pq, pl, price, flags = f
        num = lambda x: None if x in ("", "-") else float(x)
        rec = None
        for fl in filter(None, flags.split(",")):
            if fl.startswith("R:"):
                rec = float(fl[2:])
        conn.execute(
            "INSERT OR IGNORE INTO ingredients(name,aliases,aisle,kind,piece_g,density,pack_qty,pack_label,price,"
            "is_basic,is_recurrent,weekly_qty,verified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (name, json.dumps([a for a in aliases.split(";") if a], ensure_ascii=False), aisle, kind,
             num(pg), float(dens), num(pq), None if pl in ("", "-") else pl, num(price),
             1 if "B" in flags.split(",") else 0, 1 if rec else 0, rec))
    conn.commit()


def resolve(conn, catalog: Catalog, parsed: dict) -> tuple[str, float | None, str]:
    """Retourne (nom canonique, quantité en unité de base, statut ok|check|unknown).
    Sans correspondance, crée un ingrédient « à vérifier » (verified=0)."""
    name, sure = catalog.match(parsed["name"])
    status = "ok" if sure else "check"
    if name is None:
        status = "unknown"
        name = parsed["name"].strip() or "ingrédient inconnu"
        kind = "g" if parsed["unit"] in MASS else "ml" if parsed["unit"] in VOL else "piece"
        conn.execute("INSERT OR IGNORE INTO ingredients(name,aliases,aisle,kind,verified) VALUES(?,?,?,?,0)",
                     (name, "[]", "Divers", kind))
        catalog.rows[name] = dict(conn.execute("SELECT * FROM ingredients WHERE name=?", (name,)).fetchone())
        catalog.phrases.append((frozenset(tokens(name)), name))
    return name, to_base(parsed["qty"], parsed["unit"], catalog.rows[name]), status


def find_or_create(conn, catalog: Catalog, label: str) -> str | None:
    """Article saisi à la main : l'ingrédient du catalogue s'il existe, sinon un nouvel ingrédient « à vérifier »."""
    label = re.sub(r"\s+", " ", label or "").strip()[:80]
    if not label:
        return None
    name = catalog.exact(label)
    if name:
        return name
    name = label.lower()
    conn.execute("INSERT OR IGNORE INTO ingredients(name,aliases,aisle,kind,verified) VALUES(?,?,?,?,0)",
                 (name, "[]", "Divers", "piece"))
    catalog.rows[name] = dict(conn.execute("SELECT * FROM ingredients WHERE name=?", (name,)).fetchone())
    catalog.phrases.append((frozenset(tokens(name)), name))
    return name