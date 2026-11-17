# Menus de la famille

Application auto-hébergée (Docker) : menus sur plusieurs jours, recettes simplifiées, liste de courses
qui suit le planning, stock à la maison. PWA utilisable hors ligne au supermarché.

## Démarrage

```bash
cp .env.example .env        # puis éditez APP_PASSWORD
docker compose up -d --build
```

Au premier lancement, 40 recettes familiales sont chargées (bibliothèque de départ, écrite pour cette application).
Les données sont dans le volume `menu-data` (`/data/menu.db`), avec une sauvegarde par jour dans `/data/backups`
(7 conservées) et un téléchargement manuel dans **Réglages → Télécharger une sauvegarde**.

## Reverse proxy (c'est vous qui le gérez)

- **HTTPS obligatoire** pour l'installation en PWA et le mode hors ligne (les service workers exigent un contexte sécurisé,
  sauf sur `localhost`). Le cookie de session est marqué `Secure` : sans HTTPS, la connexion « réussit » mais le navigateur
  jette le cookie. Pour un essai en HTTP, mettez `COOKIE_SECURE=false`.
- Ne **publiez pas** le port 8000 : rattachez le service au réseau de votre proxy (voir le `docker-compose.yml`).
  Faites suivre `X-Forwarded-For` (la plupart des proxys le font par défaut) : la limite de tentatives de connexion
  (5 échecs / 15 min) s'applique par adresse IP, et sans cet en-tête tout le monde partagerait l'IP du proxy.
- `FORWARDED_ALLOW_IPS` : par défaut `*`, acceptable uniquement si seul le proxy peut joindre le conteneur.
  Sinon, mettez l'adresse du proxy.

## Utilisation

- **Menus** : repas des prochains jours. `⋯` → *Changer ce repas* (ingrédient refusé / trop cher / autre envie),
  *Absent*, *Verrouiller*. Après un changement ou une absence, les repas **suivants non verrouillés** sont régénérés.
  Un ingrédient refusé est mémorisé (Réglages) ; « trop cher » ne vaut que pour le remplacement.
- **Recettes** : touchez un repas pour la recette, quantités calculées pour la famille. *Ajouter* : coller une URL
  (Marmiton, 750g, CuisineAZ… ou tout site publiant des données de recette), puis **relire** les ingrédients avant
  d'enregistrer. Si le site bloque ou a changé : coller le code source de la page, ou saisie à la main.
- **Courses** : ✓ = acheté (quantité proposée, arrondie au paquet) ; `⋯` = autre quantité (le surplus va en stock et
  sert aux repas suivants), déjà à la maison, retirer. Les basiques (sel, huile, farine…) n'apparaissent jamais,
  sauf via *Ajouter un article*. Le stock baisse automatiquement quand les repas passent.
- **Petit-déjeuner** : produits récurrents (lait, céréales, café) avec une consommation par semaine, réglable.

## Ce qui peut casser avec le temps

| Quoi | Symptôme | Que faire |
|---|---|---|
| Un site de recettes change son HTML ou ajoute une protection anti-robot | L'import d'URL échoue pour ce site ; **les recettes déjà en base ne sont pas touchées** | Mettre à jour `recipe-scrapers` (voir ci-dessous), coller le code source, ou saisir à la main |
| `recipe-scrapers` change d'API | Erreur au démarrage ou à l'import après une mise à jour | Les versions sont **figées** dans `requirements.txt` ; ne mettre à jour qu'en relançant les tests. L'API a déjà changé entre les versions 13 et 15 |
| Session expirée | Retour à l'écran de connexion | 30 jours glissants (`SESSION_DAYS`). Changer `APP_PASSWORD` révoque toutes les sessions |
| Prix | Budget faux | Les prix du catalogue sont des **estimations** à corriger ; aucun prix de supermarché n'est récupéré |
| Stock dérivé | Stock qui ne reflète plus la réalité | Il est calculé (achats − repas passés − récurrents) : corrigez-le dans Réglages → Stock si vous cuisinez autre chose |
| Ingrédient mal reconnu | Ligne de courses bizarre | Les ingrédients « à vérifier » sont signalés ; corrigez-les à l'import ou dans Réglages |
| Cache hors ligne | Écran légèrement ancien sans réseau | Normal ; se resynchronise au retour du réseau |

Mettre à jour la bibliothèque : changez la version dans `requirements.txt`, lancez `pip install -r requirements-dev.txt && pytest`,
puis reconstruisez l'image. Mettre à jour la base : les migrations sont versionnées (`app/db.py`), appliquées au démarrage.

## Restaurer une sauvegarde

Arrêtez le service, remplacez `menu.db` dans le volume par une copie de `/data/backups/menu-AAAA-MM-JJ.db`, relancez.

## Tests

```bash
python -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest
```

Couverts : analyse des ingrédients français (formats observés sur Marmiton et 750g : « 500g », « c.à.s », fractions,
quantités vagues…), règles du planificateur (vérifiées par mutation), régénération, courses, stock, opérations hors ligne
rejouées ou concurrentes, authentification, API, protection contre l'import d'adresses privées.

Les tests d'import utilisent une **page synthétique** (`tests/fixtures/recette-exemple.html`) qui reproduit ces particularités.
Si vous placez de vraies pages Marmiton/750g dans `tests/local_fixtures/` (dossier ignoré par git : ce sont des contenus de tiers,
ne les publiez pas), deux tests supplémentaires les utilisent ; sinon ils sont ignorés.

**Non couverts** : téléchargement réel depuis Marmiton/750g (anti-robot), service worker et mode hors ligne dans un vrai
navigateur, rendu sur téléphone. La construction de l'image Docker et un démarrage réel sont vérifiés par la CI GitHub
(`.github/workflows/ci.yml`) ; ils n'avaient pas pu être exécutés lors de l'écriture initiale.

## Limites connues

- Les conversions d'unités (cuillères, pièces ↔ grammes) sont des approximations par ingrédient (poids de pièce, densité).
- Compte unique, pas de gestion de plusieurs familles. Pas de restes réutilisés ni de saisonnalité fine (mois par recette).
- L'import refuse les adresses privées (SSRF) ; un nom de domaine changeant de réponse entre le contrôle et la requête
  n'est pas couvert. Placez l'application derrière votre authentification de proxy si elle est exposée.

## Usage des sites de recettes

L'import récupère **une page à la fois, à votre demande**, pour un usage personnel. Il n'est pas conçu pour un import en masse.
Les conditions d'utilisation de chaque site peuvent restreindre l'accès automatisé : c'est à vous de les respecter.
Les recettes importées restent dans votre base ; ne les redistribuez pas. La bibliothèque de départ (`app/seed_recipes.py`)
a été rédigée pour ce projet et suit la licence du code.

## Licence

Copyright © les contributeurs du projet. Distribué sous licence **GNU AGPL-3.0 ou ultérieure** (voir `LICENSE`).
Si vous modifiez l'application et la rendez accessible à d'autres personnes via un réseau, l'article 13 de l'AGPL vous
oblige à proposer à ces utilisateurs le code source de votre version modifiée (un lien vers votre dépôt suffit).
Les dépendances (FastAPI, recipe-scrapers, requests…) sont sous licences permissives (MIT, BSD, Apache-2.0, PSF, MPL-2.0).

