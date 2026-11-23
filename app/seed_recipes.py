# SPDX-License-Identifier: AGPL-3.0-or-later
"""Bibliothèque de départ : recettes familiales rédigées pour cette application (4 personnes).
Format : « # titre | protéine | féculent | repas (d/l) | préparation/cuisson en min | mois | tags »,
puis « ing: ... ; ... » et « steps: ... ## ... »."""
import re
from .seed_seasonal import SEED_SEASONAL

SEED = """
# Spaghetti bolognaise | boeuf | pates | dl | 15/30 | * |
ing: 400 g de spaghetti; 400 g de boeuf haché; 1 oignon; 1 carotte; 400 g de tomates concassées; 2 gousses d'ail; 2 c. à soupe d'huile d'olive; 60 g de gruyère râpé; sel; poivre
steps: Hacher finement l'oignon et la carotte, écraser l'ail. ## Faire revenir l'oignon et la carotte dans l'huile 5 minutes, ajouter la viande et l'émietter jusqu'à ce qu'elle soit dorée. ## Verser les tomates, saler, poivrer, laisser mijoter 20 minutes à feu doux. ## Cuire les spaghetti dans l'eau bouillante salée selon le paquet, puis égoutter. ## Servir la sauce sur les pâtes avec le fromage râpé.

# Gratin de coquillettes au jambon | porc | pates | d | 10/25 | * |
ing: 300 g de coquillettes; 4 tranches de jambon blanc; 20 cl de crème fraîche; 100 g de gruyère râpé; 20 g de beurre; noix de muscade; sel; poivre
steps: Préchauffer le four à 200 °C. ## Cuire les coquillettes 2 minutes de moins que sur le paquet, égoutter. ## Couper le jambon en morceaux et mélanger avec les pâtes, la crème, la moitié du fromage, le sel, le poivre et la muscade. ## Verser dans un plat beurré et couvrir du reste de fromage. ## Cuire 15 minutes, jusqu'à ce que le dessus soit doré.

# Poulet rôti et pommes de terre | volaille | pdt | dl | 15/50 | * | four
ing: 4 cuisses de poulet; 1 kg de pommes de terre; 1 oignon; 2 gousses d'ail; 3 c. à soupe d'huile d'olive; 1 branche de thym; sel; poivre
steps: Préchauffer le four à 200 °C. ## Éplucher les pommes de terre et les couper en gros morceaux, émincer l'oignon. ## Mettre le tout dans un plat avec le poulet, l'ail, le thym, l'huile, le sel et le poivre, bien mélanger. ## Enfourner 50 minutes en retournant à mi-cuisson, jusqu'à ce que la peau soit dorée.

# Riz cantonais | porc | riz | dl | 15/15 | * |
ing: 300 g de riz; 3 oeufs; 150 g de petits pois; 3 tranches de jambon blanc; 2 carottes; 2 c. à soupe de sauce soja; 2 c. à soupe d'huile
steps: Cuire le riz et l'étaler pour qu'il refroidisse un peu. ## Râper les carottes et couper le jambon en dés. ## Cuire les petits pois 3 minutes dans l'eau bouillante, égoutter. ## Battre les oeufs et les cuire en brouillade à la poêle, réserver. ## Faire sauter carottes, jambon et petits pois dans l'huile, ajouter le riz, les oeufs et la sauce soja, chauffer 3 minutes.

# Cabillaud, riz et brocoli | poisson | riz | d | 10/20 | * |
ing: 4 filets de cabillaud; 300 g de riz; 1 brocoli; 1 citron; 20 g de beurre; sel; poivre
steps: Cuire le riz dans l'eau salée. ## Détailler le brocoli en petits bouquets et les cuire 8 minutes. ## Faire fondre le beurre à la poêle, cuire les filets 4 minutes de chaque côté, saler, poivrer. ## Servir avec un filet de jus de citron.

# Saumon et purée | poisson | pdt | d | 15/25 | * |
ing: 4 pavés de saumon; 800 g de pommes de terre; 15 cl de lait; 30 g de beurre; 1 citron; sel; poivre
steps: Éplucher les pommes de terre et les cuire 20 minutes dans l'eau salée. ## Les écraser avec le lait chaud et le beurre, saler. ## Cuire les pavés de saumon à la poêle 4 minutes de chaque côté. ## Servir avec la purée et un peu de citron.

# Omelette et pommes de terre sautées | oeuf | pdt | dl | 10/25 | * | express
ing: 8 oeufs; 800 g de pommes de terre; 1 salade verte; 3 c. à soupe d'huile; sel; poivre
steps: Couper les pommes de terre épluchées en dés et les cuire à la poêle dans l'huile 20 minutes en remuant. ## Battre les oeufs avec sel et poivre. ## Cuire l'omelette à feu moyen et la plier en deux. ## Servir avec la salade lavée.

# Quiche lorraine | porc | autre | d | 15/35 | * |
ing: 1 pâte brisée; 200 g de lardons; 3 oeufs; 20 cl de crème fraîche; 10 cl de lait; 80 g de gruyère râpé; poivre
steps: Préchauffer le four à 180 °C et étaler la pâte dans un moule. ## Faire revenir les lardons à sec 3 minutes. ## Battre les oeufs avec la crème, le lait et le poivre, ajouter les lardons et le fromage. ## Verser sur la pâte et cuire 35 minutes.

# Tarte poireaux et chèvre | veggie | autre | d | 15/35 | 9-3 |
ing: 1 pâte feuilletée; 3 poireaux; 150 g de fromage de chèvre; 10 cl de crème fraîche; 2 oeufs; 1 c. à soupe d'huile; sel; poivre
steps: Préchauffer le four à 180 °C. ## Émincer les poireaux et les faire fondre 10 minutes à la poêle avec l'huile. ## Étaler la pâte, répartir les poireaux et le chèvre en rondelles. ## Battre les oeufs avec la crème, saler, poivrer, verser sur la tarte. ## Cuire 30 minutes.

# Spaghetti carbonara | porc | pates | d | 10/15 | * | express
ing: 400 g de spaghetti; 200 g de lardons; 3 oeufs; 50 g de parmesan; poivre
steps: Cuire les spaghetti dans l'eau salée et garder un verre d'eau de cuisson. ## Faire dorer les lardons à sec. ## Mélanger les oeufs, le parmesan râpé et du poivre. ## Hors du feu, mélanger les pâtes égouttées avec les lardons puis la sauce aux oeufs, ajouter un peu d'eau de cuisson pour napper.

# Lasagnes à la bolognaise | boeuf | pates | d | 30/45 | * | four
ing: 250 g de feuilles de lasagne; 500 g de boeuf haché; 500 g de tomates concassées; 1 oignon; 50 cl de lait; 40 g de beurre; 40 g de farine; 100 g de gruyère râpé; noix de muscade; sel; poivre
steps: Faire revenir l'oignon et la viande, ajouter les tomates, saler, poivrer, laisser mijoter 15 minutes. ## Préparer la béchamel : fondre le beurre, ajouter la farine, verser le lait peu à peu en fouettant jusqu'à épaississement, ajouter la muscade. ## Dans un plat, alterner sauce, feuilles de lasagne et béchamel, finir par la béchamel et le fromage. ## Cuire 40 minutes à 180 °C.

# Hachis parmentier | boeuf | pdt | d | 25/35 | * | four
ing: 500 g de boeuf haché; 1 kg de pommes de terre; 1 oignon; 15 cl de lait; 30 g de beurre; 50 g de gruyère râpé; sel; poivre
steps: Cuire les pommes de terre épluchées 20 minutes et les écraser avec le lait et le beurre. ## Faire revenir l'oignon et la viande 10 minutes, saler, poivrer. ## Mettre la viande au fond d'un plat, couvrir de purée puis de fromage. ## Gratiner 20 minutes à 200 °C.

# Dinde à la crème et riz | volaille | riz | d | 15/25 | * |
ing: 500 g d'escalope de dinde; 250 g de champignons; 20 cl de crème fraîche; 300 g de riz; 1 oignon; 2 c. à soupe d'huile; sel; poivre
steps: Cuire le riz. ## Couper la dinde en lanières et les champignons en lamelles. ## Dorer la dinde dans l'huile avec l'oignon émincé, ajouter les champignons 5 minutes. ## Verser la crème, saler, poivrer, laisser réduire 5 minutes. ## Servir sur le riz.

# Gratin dauphinois et jambon | porc | pdt | d | 20/60 | * | four
ing: 1 kg de pommes de terre; 30 cl de crème fraîche; 20 cl de lait; 1 gousse d'ail; 4 tranches de jambon blanc; noix de muscade; sel; poivre
steps: Préchauffer le four à 170 °C. Éplucher les pommes de terre et les couper en fines rondelles. ## Frotter un plat avec l'ail et y ranger les pommes de terre. ## Mélanger crème, lait, sel, poivre et muscade, verser dessus. ## Cuire 1 heure environ, jusqu'à ce que ce soit doré. ## Servir avec le jambon.

# Chili doux | boeuf | riz | d | 15/30 | * |
ing: 400 g de boeuf haché; 250 g de haricots rouges; 285 g de maïs; 400 g de tomates concassées; 1 oignon; 300 g de riz; 1 c. à café de paprika; sel
steps: Cuire le riz. ## Faire revenir l'oignon et la viande. ## Ajouter les tomates, les haricots rincés, le maïs égoutté, le paprika et le sel, laisser mijoter 20 minutes. ## Servir avec le riz.

# Croque-monsieur et soupe de légumes | porc | pain | d | 20/30 | 10-3 |
ing: 8 tranches de pain de mie; 4 tranches de jambon blanc; 100 g de gruyère râpé; 400 g de pommes de terre; 3 carottes; 2 poireaux; 20 g de beurre; sel; poivre
steps: Éplucher et couper pommes de terre, carottes et poireaux, les cuire 25 minutes dans de l'eau salée, puis mixer. ## Garnir quatre tranches de pain de jambon et de fromage, refermer avec le reste du pain. ## Beurrer légèrement l'extérieur et dorer à la poêle ou 10 minutes au four à 200 °C. ## Servir avec la soupe chaude.

# Curry doux de pois chiches | veggie | riz | d | 10/25 | * |
ing: 530 g de pois chiches; 40 cl de lait de coco; 400 g de tomates concassées; 1 oignon; 1 c. à soupe de curry; 300 g d'épinards; 300 g de riz; 2 c. à soupe d'huile
steps: Cuire le riz. ## Faire revenir l'oignon dans l'huile avec le curry. ## Ajouter les tomates, le lait de coco et les pois chiches égouttés, laisser mijoter 15 minutes. ## Ajouter les épinards et chauffer 5 minutes, servir sur le riz.

# Tortillas au poulet | volaille | autre | dl | 15/15 | * | express
ing: 8 tortillas; 400 g de blanc de poulet; 1 poivron; 285 g de maïs; 100 g de gruyère râpé; 10 cl de crème fraîche; 1 c. à soupe d'huile; sel
steps: Couper le poulet et le poivron en lanières. ## Les cuire à la poêle dans l'huile 10 minutes, saler. ## Réchauffer les tortillas. ## Garnir de poulet, poivron, maïs, crème et fromage, rouler et servir.

# Pizza jambon champignons | porc | autre | d | 15/20 | * | four
ing: 1 pâte à pizza; 150 g de tomates concassées; 2 mozzarella; 3 tranches de jambon blanc; 150 g de champignons; 1 c. à soupe d'huile d'olive; herbes de provence; sel
steps: Préchauffer le four à 220 °C. ## Étaler la pâte sur une plaque et la napper de tomates assaisonnées. ## Ajouter champignons émincés, jambon en morceaux, mozzarella en tranches et un filet d'huile. ## Cuire 15 à 20 minutes.

# Boulettes sauce tomate et semoule | boeuf | semoule | d | 20/25 | * |
ing: 500 g de boeuf haché; 1 oeuf; 3 c. à soupe de chapelure; 400 g de tomates concassées; 300 g de semoule; 1 oignon; 2 c. à soupe d'huile; sel; poivre
steps: Mélanger viande, oeuf, chapelure, sel et poivre, puis former des boulettes. ## Les dorer dans l'huile 5 minutes. ## Ajouter l'oignon émincé puis les tomates, laisser mijoter 15 minutes. ## Préparer la semoule avec de l'eau bouillante salée et servir.

# Saucisses, pommes de terre et haricots verts | porc | pdt | d | 10/30 | * |
ing: 6 saucisses; 800 g de pommes de terre; 400 g de haricots verts; 2 c. à soupe d'huile; sel; poivre
steps: Cuire les pommes de terre en cubes à la poêle ou au four 25 minutes. ## Cuire les haricots verts 8 minutes à l'eau bouillante. ## Dorer les saucisses 15 minutes. ## Servir ensemble.

# Poulet pané et purée | volaille | pdt | d | 20/25 | * |
ing: 500 g de blanc de poulet; 1 oeuf; 6 c. à soupe de chapelure; 800 g de pommes de terre; 15 cl de lait; 30 g de beurre; 2 c. à soupe d'huile; sel
steps: Couper le poulet en lanières. ## Les passer dans l'oeuf battu puis dans la chapelure. ## Les cuire à la poêle dans l'huile 4 minutes de chaque côté. ## Faire la purée avec les pommes de terre cuites, le lait et le beurre.

# Gratin de chou-fleur au jambon | porc | autre | d | 20/35 | 10-3 | four
ing: 1 chou-fleur; 4 tranches de jambon blanc; 40 cl de lait; 30 g de beurre; 30 g de farine; 100 g de gruyère râpé; noix de muscade; sel
steps: Cuire les bouquets de chou-fleur 10 minutes à l'eau bouillante, égoutter. ## Préparer la béchamel : fondre le beurre, ajouter la farine puis le lait en fouettant, saler, ajouter la muscade. ## Mettre le chou-fleur et le jambon en morceaux dans un plat, couvrir de béchamel et de fromage. ## Gratiner 25 minutes à 200 °C.

# Pâtes au thon et aux tomates | poisson | pates | dl | 10/15 | * | express
ing: 400 g de pâtes; 280 g de thon; 400 g de tomates concassées; 1 oignon; 1 c. à soupe d'huile d'olive; basilic; sel; poivre
steps: Cuire les pâtes. ## Faire revenir l'oignon, ajouter les tomates et laisser réduire 10 minutes. ## Ajouter le thon émietté, saler, poivrer. ## Mélanger avec les pâtes.

# Gnocchis crème et petits pois | veggie | pates | dl | 5/10 | * | express
ing: 500 g de gnocchi; 20 cl de crème fraîche; 250 g de petits pois; 50 g de parmesan; sel; poivre
steps: Cuire les gnocchis dans l'eau bouillante jusqu'à ce qu'ils remontent. ## Cuire les petits pois 3 minutes. ## Chauffer la crème avec sel et poivre, ajouter les gnocchis et les petits pois. ## Servir avec le parmesan.

# Couscous au poulet | volaille | semoule | d | 20/45 | * |
ing: 4 cuisses de poulet; 300 g de semoule; 3 carottes; 2 courgettes; 265 g de pois chiches; 1 oignon; 1 c. à soupe de ras el hanout; 2 c. à soupe d'huile; sel
steps: Dorer le poulet dans l'huile avec l'oignon émincé. ## Ajouter le ras el hanout, les carottes en rondelles et de l'eau à mi-hauteur, laisser mijoter 25 minutes. ## Ajouter les courgettes et les pois chiches, cuire 15 minutes. ## Préparer la semoule à l'eau bouillante et servir avec le bouillon.

# Merlu pané, riz et haricots verts | poisson | riz | d | 15/20 | * |
ing: 4 filets de merlu; 1 oeuf; 6 c. à soupe de chapelure; 300 g de riz; 400 g de haricots verts; 2 c. à soupe d'huile; sel
steps: Cuire le riz. ## Passer les filets dans l'oeuf battu puis dans la chapelure. ## Les dorer à la poêle 3 à 4 minutes de chaque côté. ## Cuire les haricots verts 8 minutes et servir.

# Pâtes aux légumes d'été | veggie | pates | d | 15/15 | 6-9 | express
ing: 400 g de pâtes; 2 courgettes; 4 tomates; 1 mozzarella; basilic; 2 c. à soupe d'huile d'olive; sel; poivre
steps: Cuire les pâtes. ## Couper les courgettes en dés et les poêler 8 minutes. ## Ajouter les tomates en dés pour 3 minutes. ## Mélanger avec les pâtes, la mozzarella en morceaux et le basilic.

# Salade de pâtes jambon mozzarella | porc | pates | dl | 15/10 | 5-9 | express
ing: 300 g de pâtes; 3 tomates; 285 g de maïs; 3 tranches de jambon blanc; 1 mozzarella; 2 c. à soupe d'huile d'olive; sel; poivre
steps: Cuire les pâtes et les rincer à l'eau froide. ## Couper tomates, jambon et mozzarella en dés. ## Mélanger avec le maïs, l'huile, le sel et le poivre. ## Servir frais.

# Burgers maison | boeuf | pdt | d | 20/30 | * |
ing: 4 pains à burger; 4 steaks hachés; 4 tranches de cheddar; 1 tomate; 1 salade verte; 800 g de pommes de terre; 2 c. à soupe d'huile; 2 c. à soupe de ketchup; sel
steps: Couper les pommes de terre en frites, les mélanger à l'huile et au sel, les cuire 30 minutes à 220 °C. ## Cuire les steaks à la poêle 3 minutes de chaque côté et poser le cheddar à la fin. ## Toaster les pains. ## Monter les burgers : pain, salade, tomate, steak, ketchup.

# Cordon bleu, petits pois et purée | volaille | pdt | d | 10/30 | * |
ing: 4 cordons bleus; 400 g de petits pois; 800 g de pommes de terre; 15 cl de lait; 30 g de beurre; sel
steps: Cuire les pommes de terre et les écraser avec le lait et le beurre. ## Cuire les cordons bleus au four 25 minutes à 200 °C, ou selon le paquet. ## Cuire les petits pois 4 minutes. ## Servir.

# Filet mignon à la moutarde | porc | pdt | d | 15/40 | * | four
ing: 600 g de filet mignon de porc; 2 c. à soupe de moutarde; 10 cl de crème fraîche; 1 kg de pommes de terre; 1 oignon; 2 c. à soupe d'huile; sel; poivre
steps: Préchauffer le four à 180 °C. Couper les pommes de terre épluchées en quartiers et les rôtir avec l'huile 40 minutes. ## Dorer le filet mignon dans une cocotte avec l'oignon 10 minutes. ## Ajouter la moutarde et la crème, couvrir et cuire 25 minutes à feu doux. ## Trancher et servir avec les pommes de terre.

# Risotto aux champignons | veggie | riz | d | 10/30 | * |
ing: 300 g de riz; 300 g de champignons; 1 oignon; 1 L de bouillon de légumes; 50 g de parmesan; 30 g de beurre; sel; poivre
steps: Faire revenir l'oignon émincé dans le beurre, ajouter les champignons 5 minutes. ## Ajouter le riz, remuer 2 minutes, puis verser le bouillon chaud louche par louche en remuant pendant 20 minutes. ## Ajouter le parmesan, saler, poivrer.

# Tarte tomate et moutarde | veggie | autre | d | 15/30 | 6-9 |
ing: 1 pâte brisée; 2 c. à soupe de moutarde; 5 tomates; 100 g de gruyère râpé; herbes de provence; sel
steps: Préchauffer le four à 200 °C et étaler la pâte. ## La badigeonner de moutarde. ## Couvrir de rondelles de tomates, de fromage et d'herbes, saler. ## Cuire 30 minutes.

# Velouté de potimarron | veggie | pain | d | 15/30 | 9-1 |
ing: 1 kg de potimarron; 1 pomme de terre; 1 oignon; 10 cl de crème fraîche; 1 L de bouillon de légumes; 1/2 baguette; 20 g de beurre; sel; poivre
steps: Éplucher et couper le potimarron, la pomme de terre et l'oignon. ## Les cuire 25 minutes dans le bouillon. ## Mixer avec la crème, saler, poivrer. ## Servir avec du pain grillé et beurré.

# Pâtes au saumon et aux épinards | poisson | pates | d | 10/20 | * |
ing: 400 g de pâtes; 2 pavés de saumon; 300 g d'épinards; 20 cl de crème fraîche; 1 c. à soupe d'huile; sel; poivre
steps: Cuire les pâtes. ## Cuire le saumon coupé en dés à la poêle 5 minutes. ## Ajouter les épinards décongelés et la crème, chauffer 5 minutes, assaisonner. ## Mélanger avec les pâtes.

# Poulet au curry doux et riz | volaille | riz | d | 15/25 | * |
ing: 500 g de blanc de poulet; 40 cl de lait de coco; 1 oignon; 1 c. à soupe de curry; 2 carottes; 300 g de riz; 2 c. à soupe d'huile; sel
steps: Cuire le riz. ## Dorer le poulet en dés avec l'oignon et les carottes coupées en petits morceaux. ## Ajouter le curry puis le lait de coco, cuire 15 minutes. ## Servir sur le riz.

# Gratin d'endives au jambon | porc | pdt | d | 20/40 | 11-3 | four
ing: 6 endives; 6 tranches de jambon blanc; 40 cl de lait; 30 g de beurre; 30 g de farine; 100 g de gruyère râpé; 600 g de pommes de terre; noix de muscade; sel
steps: Cuire les pommes de terre épluchées 20 minutes. ## Cuire les endives 15 minutes à la vapeur. ## Préparer la béchamel avec le beurre, la farine et le lait, saler, ajouter la muscade. ## Enrouler chaque endive dans une tranche de jambon, les ranger dans un plat, couvrir de béchamel et de fromage. ## Gratiner 25 minutes à 200 °C et servir avec les pommes de terre.

# Steak haché, purée et haricots verts | boeuf | pdt | d | 10/25 | * | express
ing: 4 steaks hachés; 800 g de pommes de terre; 400 g de haricots verts; 15 cl de lait; 30 g de beurre; 1 c. à soupe d'huile; sel; poivre
steps: Cuire les pommes de terre et les écraser avec le lait et le beurre. ## Cuire les haricots verts 8 minutes. ## Cuire les steaks 3 minutes de chaque côté.

# Oeufs au plat, jambon et salade | oeuf | pain | l | 5/10 | * | express
ing: 8 oeufs; 4 tranches de jambon blanc; 1 salade verte; 1 baguette; 2 c. à soupe d'huile; sel
steps: Cuire les oeufs au plat. ## Laver la salade. ## Servir avec le jambon et le pain.
"""


def _months(spec: str) -> list[int]:
    spec = spec.strip()
    if spec in ("*", ""):
        return []
    a, _, b = spec.partition("-")
    a, b = int(a), int(b or a)
    return [((m - 1) % 12) + 1 for m in range(a, (b if b >= a else b + 12) + 1)]


def parse_seed(text: str | None = None) -> list[dict]:
    out, cur = [], None
    for line in (SEED if text is None else text).strip().splitlines():
        line = line.strip()
        if line.startswith("# "):
            f = [x.strip() for x in line[2:].split("|")]
            prep, _, cook = f[4].partition("/")
            cur = {"title": f[0], "protein": f[1], "carb": f[2], "meals": f[3], "prep_min": int(prep),
                   "cook_min": int(cook), "months": _months(f[5]), "tags": [t for t in f[6].split(",") if t.strip()]
                   if len(f) > 6 else [], "servings": 4, "source_type": "seed"}
            out.append(cur)
        elif line.startswith("ing:"):
            cur["ingredients"] = [x.strip() for x in line[4:].split(";") if x.strip()]
        elif line.startswith("steps:"):
            cur["steps"] = [x.strip() for x in line[6:].split("##") if x.strip()]
    return out


def load_seed(conn, cat) -> int:
    """Bibliothèque de départ (base sans recette), puis lot saisonnier (une seule fois par base)."""
    from .recipes import save_recipe
    n = 0
    if not conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]:
        for d in parse_seed():
            save_recipe(conn, cat, d); n += 1
    if not conn.execute("SELECT 1 FROM meta WHERE key='seed_seasonal_v1'").fetchone():
        have = {r[0] for r in conn.execute("SELECT title FROM recipes")}
        for d in parse_seed(SEED_SEASONAL):
            if d["title"] not in have:
                save_recipe(conn, cat, d); n += 1
        conn.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('seed_seasonal_v1','1')")
        conn.commit()
    return n
