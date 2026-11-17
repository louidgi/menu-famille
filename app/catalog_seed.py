# SPDX-License-Identifier: AGPL-3.0-or-later
"""Catalogue d'ingrédients de départ. Prix = estimations en € à corriger dans l'application.
Format : nom | alias;alias | rayon | unité de base (g/ml/piece) | poids d'une pièce (g) | densité |
         taille d'un paquet | libellé du paquet | prix du paquet (ou €/kg, €/L si pas de paquet) | drapeaux
Drapeaux : B = basique (jamais dans la liste sauf « bientôt fini »), R:n = récurrent, n par semaine."""

CATALOG = """
pomme de terre|pommes de terre;patate|Fruits et légumes|g|150|1|-|-|1.8|
oignon|oignons|Fruits et légumes|g|120|1|-|-|1.9|
ail|gousse d'ail;gousses d'ail;tête d'ail|Fruits et légumes|piece|4|1|10|tête d'ail|0.6|
carotte|carottes|Fruits et légumes|g|100|1|-|-|1.6|
poireau|poireaux|Fruits et légumes|g|150|1|-|-|2.5|
courgette|courgettes|Fruits et légumes|g|250|1|-|-|2.6|
tomate|tomates|Fruits et légumes|g|130|1|-|-|3.2|
poivron|poivrons|Fruits et légumes|g|180|1|-|-|3.5|
aubergine|aubergines|Fruits et légumes|g|300|1|-|-|3.0|
brocoli|brocolis|Fruits et légumes|g|400|1|-|-|3.2|
chou-fleur|chou fleur|Fruits et légumes|g|800|1|-|-|2.5|
champignon|champignons;champignons de paris|Fruits et légumes|g|20|1|250|barquette 250 g|1.9|
fenouil|fenouils|Fruits et légumes|g|250|1|-|-|3.5|
endive|endives|Fruits et légumes|g|110|1|-|-|3.5|
potimarron|potiron;courge butternut|Fruits et légumes|g|1200|1|-|-|2.5|
salade verte|salade;laitue|Fruits et légumes|piece|300|1|1|pièce|1.0|
citron|citrons;jus de citron|Fruits et légumes|piece|100|1|1|pièce|0.5|
orange|oranges|Fruits et légumes|piece|150|1|1|pièce|0.5|
haricots verts|haricot vert|Surgelés|g|-|1|750|sachet 750 g|2.2|
petits pois|petit pois|Surgelés|g|-|1|600|sachet 600 g|2.0|
épinards|épinard;épinards hachés|Surgelés|g|-|1|750|sachet 750 g|2.4|
maïs|maïs en boîte;maïs doux|Conserves|g|285|1|285|boîte 285 g|1.2|
pois chiches|pois chiche|Conserves|g|265|1|265|boîte 265 g|0.95|
haricots rouges|haricot rouge|Conserves|g|250|1|250|boîte 250 g|1.0|
thon|thon en boîte;thon au naturel|Conserves|g|140|1|140|boîte 140 g|1.7|
tomates concassées|tomate concassée;coulis de tomate;purée de tomate;passata;sauce tomate|Conserves|g|400|1|400|boîte 400 g|0.9|
boeuf haché|steak haché;steaks hachés;viande hachée;boeuf|Boucherie|g|125|1|500|barquette 500 g|6.0|
blanc de poulet|escalope de poulet;filet de poulet;poulet|Boucherie|g|150|1|500|barquette 500 g|7.0|
cuisse de poulet|cuisses de poulet;pilon de poulet|Boucherie|piece|-|1|4|lot de 4|4.5|
escalope de dinde|dinde;escalope de volaille|Boucherie|g|150|1|500|barquette 500 g|7.5|
filet mignon de porc|filet mignon;rôti de porc|Boucherie|g|-|1|500|pièce 500 g|7.0|
lardons|lardon|Boucherie|g|-|1|200|paquet 200 g|2.2|
jambon blanc|jambon|Boucherie|piece|45|1|4|paquet de 4 tranches|2.6|
saucisse|saucisses;saucisse de toulouse|Boucherie|piece|90|1|6|barquette de 6|4.5|
cordon bleu|cordons bleus|Boucherie|piece|120|1|4|boîte de 4|4.0|
cabillaud|filet de cabillaud;filets de cabillaud;merlu;colin;lieu;poisson blanc|Poissonnerie|g|125|1|125|filet|3.0|
saumon|pavé de saumon;pavés de saumon|Poissonnerie|piece|125|1|1|pavé|2.8|
oeuf|oeufs;œuf;œufs|Crèmerie|piece|60|1|6|boîte de 6|2.2|
lait|lait demi-écrémé;lait entier|Crèmerie|ml|-|1|1000|bouteille 1 L|1.1|R:5000
beurre|beurre doux|Crèmerie|g|-|0.95|250|plaquette 250 g|2.4|
crème fraîche|crème fraiche;crème liquide;crème|Crèmerie|ml|-|1|200|pot 20 cl|1.3|
gruyère râpé|gruyère;emmental;fromage râpé;fromage rapé;fromage|Crèmerie|g|-|1|200|sachet 200 g|2.0|
parmesan|parmigiano|Crèmerie|g|-|1|100|morceau 100 g|2.5|
mozzarella||Crèmerie|piece|125|1|1|boule|1.0|
fromage de chèvre|chèvre;bûche de chèvre|Crèmerie|g|-|1|150|bûche 150 g|2.5|
cheddar|tranche de cheddar|Crèmerie|piece|20|1|8|sachet de 8 tranches|2.0|
pâtes|spaghetti;spaghettis;coquillettes;penne;macaroni;torsades;tagliatelles;fusilli;pâtes alimentaires|Épicerie|g|-|1|500|paquet 500 g|1.2|
riz|riz long;riz basmati;riz arborio|Épicerie|g|-|1|500|paquet 500 g|1.6|
semoule|couscous;semoule de couscous|Épicerie|g|-|1|500|paquet 500 g|1.4|
gnocchi|gnocchis|Épicerie|g|-|1|500|paquet 500 g|2.0|
feuilles de lasagne|lasagnes;lasagne|Épicerie|g|20|1|500|paquet 500 g|1.6|
farine|farine de blé|Épicerie|g|-|0.55|1000|paquet 1 kg|1.1|B
chapelure||Épicerie|g|-|0.5|250|paquet 250 g|1.0|
sucre|sucre en poudre|Épicerie|g|-|0.85|1000|paquet 1 kg|1.3|B
huile d'olive|huile;huile de tournesol;huile végétale|Épicerie|ml|-|1|500|bouteille 50 cl|5.5|B
sel|sel fin;gros sel|Épicerie|g|-|1.2|1000|boîte 1 kg|0.5|B
poivre|poivre noir;poivre moulu|Épicerie|g|-|1|50|moulin|2.0|B
moutarde|moutarde de dijon|Épicerie|g|-|1|200|pot 200 g|1.8|B
curry|curry en poudre|Épicerie|g|-|1|40|pot|2.0|B
ras el hanout||Épicerie|g|-|1|40|pot|2.0|B
thym|thym frais;thym sec|Épicerie|g|-|1|20|pot|1.5|B
laurier|feuille de laurier|Épicerie|g|-|1|10|pot|1.5|B
basilic|basilic frais|Épicerie|g|-|1|20|pot|1.5|B
persil|persil frais|Épicerie|g|-|1|20|pot|1.5|B
coriandre|coriandre en grain;coriandre moulue|Épicerie|g|-|1|20|pot|1.5|B
herbes de provence|herbes|Épicerie|g|-|1|20|pot|1.5|B
paprika|piment doux;piment d'espelette;piment|Épicerie|g|-|1|40|pot|2.0|B
muscade|noix de muscade|Épicerie|g|-|1|20|pot|2.0|B
bouillon|bouillon de légumes;bouillon de volaille;cube de bouillon;fond de volaille|Épicerie|ml|-|1|1000|boîte de cubes|2.0|B
sauce soja|sauce de soja|Épicerie|ml|-|1|250|bouteille 25 cl|2.5|
ketchup||Épicerie|ml|-|1|500|flacon 500 g|2.0|
lait de coco||Épicerie|ml|-|1|400|boîte 40 cl|1.5|
céréales|céréales petit-déjeuner|Épicerie|g|-|0.4|500|boîte 500 g|3.0|R:500
café|café moulu|Épicerie|g|-|1|250|paquet 250 g|3.5|R:125
jus d'orange||Boissons|ml|100|1|1000|brique 1 L|1.6|
pâte brisée||Crèmerie|piece|-|1|1|rouleau|1.3|
pâte feuilletée||Crèmerie|piece|-|1|1|rouleau|1.4|
pâte à pizza||Crèmerie|piece|-|1|1|rouleau|1.5|
pain de mie|tranche de pain de mie;tranches de pain de mie|Boulangerie|piece|-|1|20|paquet de 20 tranches|1.8|
pain|baguette|Boulangerie|piece|250|1|1|baguette|1.1|
tortillas|galettes de blé;wraps|Boulangerie|piece|-|1|8|paquet de 8|2.2|
pain à burger|pains à burger|Boulangerie|piece|-|1|4|paquet de 4|1.9|
yaourt|yaourts;yogourt;yaourt nature|Crèmerie|piece|125|1|8|pack de 8|2.4|
compote|compotes;compote de pomme|Épicerie|piece|90|1|4|pack de 4|2.0|
confiture|confitures|Épicerie|piece|-|1|1|pot|2.5|
miel||Épicerie|g|-|1|250|pot 250 g|4.0|
biscuits|biscuit;gâteaux secs|Épicerie|piece|-|1|1|paquet|2.0|
thé|thé noir;thé vert;infusion;tisane|Boissons|piece|-|1|1|boîte|2.5|
jus de pomme||Boissons|ml|-|1|1000|brique 1 L|1.6|
pomme|pommes|Fruits et légumes|piece|150|1|-|-|0.4|
banane|bananes|Fruits et légumes|piece|120|1|-|-|0.3|
papier toilette||Hygiène et maison|piece|-|1|12|paquet de 12|4.5|
essuie-tout|sopalin;papier absorbant|Hygiène et maison|piece|-|1|1|rouleau|1.5|
sacs poubelle|sac poubelle|Hygiène et maison|piece|-|1|1|rouleau|2.5|
liquide vaisselle|produit vaisselle|Hygiène et maison|ml|-|1|500|flacon 50 cl|2.0|
lessive||Hygiène et maison|piece|-|1|1|bidon|8.0|
éponges|éponge|Hygiène et maison|piece|-|1|1|lot|2.0|
savon|savon liquide;gel douche|Hygiène et maison|piece|-|1|1|flacon|2.5|
dentifrice||Hygiène et maison|piece|-|1|1|tube|2.0|
mouchoirs|mouchoir;boîte de mouchoirs|Hygiène et maison|piece|-|1|1|boîte|2.0|
"""

DEFAULT_PRICE = {"g": 0.004, "ml": 0.002, "piece": 0.5}  # € par unité de base si aucun prix connu
DEFAULT_STEP = {"g": 50.0, "ml": 100.0, "piece": 1.0}     # pas d'achat pour les produits vendus en vrac
