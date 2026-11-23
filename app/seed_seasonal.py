# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lot de 20 recettes de saison (4 personnes), rédigées pour cette application.
Même format que seed_recipes.SEED. Mois : « 12-2 » = décembre à février (la plage peut franchir le Nouvel An).
Chaque ingrédient doit exister dans catalog_seed.CATALOG (sinon il est créé « à vérifier » : voir tests/test_seed_seasonal.py)."""

SEED_SEASONAL = """
# Raclette et charcuterie | porc | pdt | d | 15/30 | 12-2 |
ing: 600 g de fromage à raclette; 1 kg de pommes de terre; 250 g de jambon cru; 100 g de cornichons; 1 salade verte; poivre
steps: Cuire les pommes de terre avec leur peau 25 minutes dans l'eau salée. ## Laver la salade et sortir le fromage du réfrigérateur. ## Allumer l'appareil à raclette et disposer le jambon et les cornichons sur la table. ## Chacun fait fondre des tranches de fromage dans son poêlon et les verse sur ses pommes de terre pelées. ## Servir avec la salade.

# Tartiflette | porc | pdt | d | 20/40 | 11-2 | four
ing: 1 kg de pommes de terre; 1 reblochon; 200 g de lardons; 2 oignons; 10 cl de crème fraîche; 1 salade verte; poivre
steps: Préchauffer le four à 200 °C. ## Cuire les pommes de terre épluchées et coupées en rondelles 15 minutes dans l'eau salée, puis égoutter. ## Faire revenir les lardons à sec, puis les oignons émincés 5 minutes. ## Mélanger avec les pommes de terre et la crème, verser dans un plat. ## Couper le reblochon en deux dans l'épaisseur et poser les moitiés sur le plat, croûte vers le haut. ## Cuire 25 minutes jusqu'à ce que le fromage soit doré, servir avec la salade.

# Soupe à l'oignon gratinée | veggie | pain | d | 15/45 | 11-2 |
ing: 6 oignons; 40 g de beurre; 1 c. à soupe de farine; 1 L de bouillon de légumes; 1/2 baguette; 100 g de gruyère râpé; sel; poivre
steps: Émincer finement les oignons. ## Les faire fondre 15 minutes dans le beurre à feu doux en remuant, jusqu'à ce qu'ils soient bien dorés. ## Saupoudrer de farine, mélanger, verser le bouillon chaud, saler, poivrer et laisser mijoter 20 minutes. ## Allumer le gril du four et répartir la soupe dans des bols qui vont au four. ## Poser du pain grillé et le fromage râpé sur chaque bol, gratiner 5 minutes.

# Potée de chou et saucisses | porc | pdt | d | 20/60 | 11-2 |
ing: 1 chou vert; 4 carottes; 800 g de pommes de terre; 6 saucisses; 150 g de lardons; 1 oignon; 2 feuilles de laurier; sel; poivre
steps: Couper le chou en lanières, les carottes en rondelles, les pommes de terre en gros cubes et émincer l'oignon. ## Dans une grande cocotte, faire revenir les lardons et l'oignon 5 minutes. ## Ajouter le chou, les carottes, le laurier, le sel et le poivre, couvrir d'eau à hauteur et cuire 25 minutes. ## Ajouter les pommes de terre et les saucisses piquées, cuire encore 30 minutes. ## Servir très chaud dans des assiettes creuses.

# Crêpes jambon fromage | porc | autre | d | 15/20 | 1-3 |
ing: 250 g de farine; 3 oeufs; 50 cl de lait; 30 g de beurre; 4 tranches de jambon blanc; 150 g de gruyère râpé; sel
steps: Mélanger la farine et une pincée de sel, ajouter les oeufs puis le lait peu à peu en fouettant, puis le beurre fondu. ## Laisser reposer la pâte 30 minutes si possible. ## Cuire les crêpes dans une poêle chaude légèrement beurrée, environ 1 minute par face. ## Garnir chaque crêpe de jambon et de fromage, la plier en carré. ## Réchauffer 2 minutes à la poêle pour faire fondre le fromage.

# Risotto aux asperges et petits pois | veggie | riz | d | 10/25 | 4-6 |
ing: 300 g de riz; 500 g d'asperges; 200 g de petits pois; 1 oignon; 1 L de bouillon de légumes; 50 g de parmesan; 30 g de beurre; sel; poivre
steps: Couper les asperges en tronçons de 3 cm en gardant les pointes à part. ## Faire revenir l'oignon émincé dans le beurre, ajouter le riz et remuer 2 minutes. ## Verser le bouillon chaud louche par louche en remuant, pendant 10 minutes. ## Ajouter les tronçons d'asperges et les petits pois, continuer 8 minutes, puis ajouter les pointes pour les 4 dernières minutes. ## Hors du feu, ajouter le parmesan, saler, poivrer.

# Poulet printanier aux petits pois | volaille | pdt | d | 15/45 | 4-6 |
ing: 4 cuisses de poulet; 400 g de petits pois; 4 carottes; 1 oignon; 800 g de pommes de terre; 2 c. à soupe d'huile; 1 branche de thym; sel; poivre
steps: Dorer les cuisses de poulet dans l'huile 5 minutes de chaque côté avec l'oignon émincé. ## Ajouter les carottes en rondelles, les pommes de terre en morceaux, le thym, le sel et le poivre, couvrir à moitié d'eau. ## Cuire à couvert 30 minutes à feu doux. ## Ajouter les petits pois et cuire encore 10 minutes.

# Salade de pommes de terre, oeufs et radis | oeuf | pdt | dl | 15/20 | 4-6 |
ing: 800 g de pommes de terre; 6 oeufs; 2 bottes de radis; 1 salade verte; 2 c. à soupe de moutarde; 4 c. à soupe d'huile d'olive; persil; sel; poivre
steps: Cuire les pommes de terre avec leur peau 20 minutes, les peler et les couper en rondelles. ## Pendant ce temps, cuire les oeufs 10 minutes dans l'eau bouillante, les refroidir et les écaler. ## Préparer la vinaigrette avec la moutarde, l'huile, le sel et le poivre, et la verser sur les pommes de terre tièdes. ## Ajouter les radis en rondelles, les oeufs en quartiers et le persil, servir sur la salade.

# Tarte aux épinards et au chèvre | veggie | autre | d | 15/35 | 3-6 |
ing: 1 pâte brisée; 300 g d'épinards; 150 g de fromage de chèvre; 3 oeufs; 20 cl de crème fraîche; noix de muscade; sel; poivre
steps: Préchauffer le four à 180 °C et étaler la pâte dans un moule. ## Cuire les épinards décongelés à la poêle 5 minutes pour évaporer l'eau, bien les égoutter. ## Battre les oeufs avec la crème, la muscade, le sel et le poivre. ## Répartir les épinards sur la pâte, ajouter le chèvre en morceaux et verser le mélange. ## Cuire 35 minutes.

# Saumon aux asperges et riz | poisson | riz | d | 10/25 | 4-6 |
ing: 4 pavés de saumon; 600 g d'asperges; 300 g de riz; 1 citron; 30 g de beurre; sel; poivre
steps: Cuire le riz dans l'eau salée. ## Éplucher le bas des asperges et les cuire 10 minutes à l'eau bouillante ou à la vapeur. ## Faire fondre le beurre dans une poêle et cuire les pavés de saumon 4 minutes de chaque côté, saler, poivrer. ## Servir avec le riz, les asperges et un filet de jus de citron.

# Salade niçoise | poisson | pdt | dl | 20/15 | 6-9 |
ing: 600 g de pommes de terre; 300 g de haricots verts; 4 oeufs; 4 tomates; 280 g de thon; 1 poivron; 3 c. à soupe d'huile d'olive; 1 c. à soupe de moutarde; basilic; sel; poivre
steps: Cuire les pommes de terre épluchées 15 minutes dans l'eau salée, puis les couper en rondelles. ## Cuire les haricots verts 8 minutes et les oeufs 10 minutes dans l'eau bouillante. ## Couper les tomates et le poivron en morceaux, les oeufs en quartiers. ## Préparer la vinaigrette avec l'huile, la moutarde, le sel et le poivre. ## Disposer les légumes dans un grand plat, ajouter le thon émietté, le basilic et la vinaigrette.

# Melon, jambon cru et mozzarella | porc | pain | dl | 10/0 | 6-9 | express
ing: 1 melon; 150 g de jambon cru; 2 mozzarella; 1/2 baguette; basilic; 2 c. à soupe d'huile d'olive; poivre
steps: Couper le melon en deux, retirer les graines et le détailler en tranches. ## Égoutter la mozzarella et la couper en tranches. ## Dresser le melon, le jambon et la mozzarella sur un plat, ajouter le basilic, un filet d'huile d'olive et du poivre. ## Servir avec le pain.

# Gaspacho et tartines de chèvre | veggie | pain | d | 20/5 | 6-9 |
ing: 1 kg de tomates; 1 concombre; 1 poivron; 1 oignon; 1 gousse d'ail; 4 c. à soupe d'huile d'olive; 1/2 baguette; 150 g de fromage de chèvre; sel; poivre
steps: Couper grossièrement les tomates, le concombre épluché, le poivron épépiné et l'oignon. ## Mixer les légumes avec l'ail, l'huile, le sel et le poivre jusqu'à obtenir une soupe lisse. ## Mettre au réfrigérateur au moins 1 heure. ## Au moment de servir, couper le pain en tranches, y poser des rondelles de chèvre et les passer 5 minutes sous le gril. ## Servir le gaspacho bien frais avec les tartines.

# Ratatouille et saucisses | porc | riz | d | 20/40 | 6-9 |
ing: 1 aubergine; 2 courgettes; 2 poivrons; 4 tomates; 2 oignons; 2 gousses d'ail; 6 saucisses; 300 g de riz; 3 c. à soupe d'huile d'olive; herbes de provence; sel; poivre
steps: Couper tous les légumes en dés. ## Faire revenir les oignons et l'ail dans l'huile, ajouter l'aubergine puis les poivrons et les courgettes, cuire 10 minutes. ## Ajouter les tomates, les herbes, le sel et le poivre, couvrir et laisser mijoter 30 minutes. ## Dorer les saucisses 15 minutes à la poêle. ## Cuire le riz et servir avec la ratatouille et les saucisses.

# Brochettes de poulet et légumes grillés | volaille | riz | d | 20/20 | 6-9 |
ing: 500 g de blanc de poulet; 2 courgettes; 2 poivrons; 1 oignon; 3 c. à soupe d'huile d'olive; 1 c. à café de paprika; 1 citron; 300 g de riz; sel
steps: Couper le poulet, les courgettes, les poivrons et l'oignon en gros cubes. ## Les mélanger avec l'huile, le paprika, le jus de citron et le sel. ## Enfiler en alternant viande et légumes sur des piques. ## Cuire 15 à 20 minutes au barbecue, sous le gril du four ou à la poêle, en les retournant. ## Cuire le riz et servir avec les brochettes.

# Risotto au potimarron | veggie | riz | d | 15/30 | 9-12 |
ing: 300 g de riz; 800 g de potimarron; 1 oignon; 1 L de bouillon de légumes; 50 g de parmesan; 30 g de beurre; sel; poivre
steps: Laver le potimarron (la peau se mange) et le couper en petits dés. ## Faire revenir l'oignon émincé dans le beurre, ajouter le potimarron et cuire 5 minutes. ## Ajouter le riz, remuer 2 minutes, puis verser le bouillon chaud louche par louche en remuant pendant 20 minutes. ## Écraser légèrement une partie du potimarron, ajouter le parmesan, saler, poivrer.

# Filet mignon aux pommes et purée | porc | pdt | d | 15/40 | 9-12 |
ing: 600 g de filet mignon de porc; 3 pommes; 1 oignon; 15 cl de crème fraîche; 30 g de beurre; 800 g de pommes de terre; 15 cl de lait; 1 branche de thym; sel; poivre
steps: Éplucher les pommes de terre et les cuire 20 minutes dans l'eau salée, puis les écraser avec le lait et la moitié du beurre. ## Dorer le filet mignon entier dans une cocotte avec le reste du beurre, l'oignon émincé et le thym, 10 minutes. ## Ajouter les pommes coupées en quartiers et la crème, saler, poivrer, couvrir et cuire 25 minutes à feu doux. ## Trancher le filet mignon et servir avec les pommes, la sauce et la purée.

# Tagliatelles crémeuses aux champignons et lardons | porc | pates | d | 10/20 | 9-11 |
ing: 400 g de tagliatelles; 300 g de champignons; 150 g de lardons; 20 cl de crème fraîche; 1 gousse d'ail; 40 g de parmesan; persil; sel; poivre
steps: Cuire les tagliatelles dans l'eau bouillante salée. ## Faire dorer les lardons à sec, ajouter les champignons en lamelles et l'ail écrasé, cuire 8 minutes. ## Verser la crème, saler, poivrer et laisser épaissir 3 minutes. ## Mélanger avec les pâtes égouttées, le persil et le parmesan.

# Gratin de pâtes, brocoli et poulet | volaille | pates | d | 20/30 | 10-3 | four
ing: 300 g de pâtes; 1 brocoli; 400 g de blanc de poulet; 40 cl de lait; 30 g de beurre; 30 g de farine; 100 g de gruyère râpé; noix de muscade; sel; poivre
steps: Préchauffer le four à 200 °C. ## Cuire les pâtes 2 minutes de moins que sur le paquet, en ajoutant les petits bouquets de brocoli pour les 5 dernières minutes, puis égoutter. ## Couper le poulet en dés et le dorer à la poêle 8 minutes, saler, poivrer. ## Préparer la béchamel : fondre le beurre, ajouter la farine puis le lait en fouettant, ajouter la muscade et saler. ## Mélanger pâtes, brocoli, poulet et béchamel dans un plat, couvrir de fromage. ## Gratiner 20 minutes.

# Cabillaud, fondue de poireaux et riz | poisson | riz | d | 15/25 | 10-3 |
ing: 4 filets de cabillaud; 4 poireaux; 300 g de riz; 20 cl de crème fraîche; 20 g de beurre; sel; poivre
steps: Couper les poireaux en rondelles et les faire fondre 15 minutes dans le beurre à feu doux, à couvert. ## Cuire le riz dans l'eau salée. ## Ajouter la crème aux poireaux, saler, poivrer et laisser réduire 5 minutes. ## Cuire les filets de cabillaud 4 minutes de chaque côté à la poêle. ## Servir le poisson sur la fondue de poireaux, avec le riz.
"""