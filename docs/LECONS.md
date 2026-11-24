# Leçons : régressions de rendu déjà rencontrées (à relire avant de toucher au pipeline)

> Avant tout nouveau clip, `CLAUDE.md` impose de **demander à l'auteur le gamma** (1,3 fixe ou adaptatif) et les autres choix de départ.

Écrit le 28/10/2026 après l'enquête « le rendu de v3 était meilleur que v6/v8 » (clip 2, Tiakola).

## Référence
- `sorties/finaux/clip2_tiakola_mode-de-vie_v3.mp4` est la référence de rendu (n&b, vert, couleur). Les réglages et le code qui l'ont produite : tag git **`ref-clip2-v3`** (commit 097884b).
- Plan réel de v3 : **brut 36 %, couleur vif 26 %, n&b 17,8 %, vert 10,5 %, cartes 9,6 %** (541 images brutes, 10 impulsions, 5 fenêtres de contour). Pas 28 % : c'est le plan recalculé avec le code d'aujourd'hui (voir erreur 2).
- Reproduction exacte : `git show ref-clip2-v3:scripts/clip2/plan.py` + config sans `cible` + `gamma: 1.3`. Mesuré : écart moyen 0,04 (n&b), 0,3 (vert), 0,4 (couleur) sur 255 ; rejeu complet des 1500 images après correction du `compose.py` (cartes d'anciens plans repérées par n° de ligne, `cible: contour` dans la config) : écart moyen 1,15 sur 255 (n&b 0,59 ; vert 0,54 ; couleur 0,75 ; brut 1,58 ; cartes 2,3). Les plans écrits désormais portent `cards_by: index`.

## Les causes (par ordre d'effet)
1. **Gamma adaptatif (27/10, 19h42, commit 8987d6e, fait pour le clip 3).** `quant.py` relevait le gamma jusqu'à 1,9 sur les scènes sombres. Le clip 2 est nocturne : tout son n&b, son vert et sa couleur sont devenus plus gris et plus plats. v3 avait un gamma fixe de 1,3.
   - Correctif : clé `gamma` dans la config (`"gamma": 1.3` pour le clip 2). Sans la clé, le gamma reste adaptatif (clip 3).
   - Règle : tout changement d'un défaut de `quant.py`, `plan.py` ou `compose.py` se vérifie par **le rejeu du clip de référence** (config de référence, comparaison image par image avec le MP4 de référence, écart par style) avant de passer à autre chose.
2. **La config de référence a été modifiée après coup.** `exemples/config_clip2_v3.json` a reçu `cible: viseur` (alignement des défauts, 28/10) et `plan.py` a changé (viseur à la place du contour, repli des scènes brutes, impulsions « une par tranche de 45 images »). Le plan recalculé n'était plus celui de v3 (1307 images sur 1500 identiques). Mes comparaisons ont d'abord porté sur ce mauvais plan.
   - Règle : **ne jamais retoucher une config de référence ; tagger le commit** (fait : `ref-clip2-v3`). Avant de conclure « ce style est moins bon », vérifier que le plan comparé est bien celui du fichier de référence (part de chaque style, nombre d'images brutes).
3. **Effets ajoutés sur le vert et le n&b (28/10, 17h).** Flash blanc 50 %/22 %, zoom 107→101 % au plus proche voisin et pixellisation de transition 32→1 s'appliquaient à tous les plans stylisés. v3 n'avait aucun de ces effets. Le vert devenait flou et en gros blocs aux temps forts.
   - Correctif : clé `effets_hors` (`["gb","bw"]` : pas de flash, de zoom ni de transition sur ces styles).
4. **N3 réparti par rang de scène.** `n3_every: 3` donne une scène N3 (640×360, effet pixel plus faible) sur trois scènes stylisées. En retirant la couleur du cycle, 64 % du vert est tombé en N3 (30 % dans v3).
   - Correctif : `n3_every: 0` = tout en N2. Règle : après un changement de cycle, **relire la part de chaque style par niveau** (script d'analyse : `plan.json`, champ `lvl`).
5. **Moments stylisés plus courts.** `pulse_every` à 20 au lieu de 45 coupait les plans n&b et verts par du brut toutes les 0,8 s. Le brut ne doit pas augmenter par ce moyen.
6. **Ce qui n'était PAS en cause** : le filtre n&b (`bw()` identique), les palettes, le dither, le mode vif (la palette `gbcy` n'a pas changé). L'écart de 12 sur la couleur vif venait des plans différents (cause 2), pas du rendu.

## Pièges du processus
- **Cache de quantification** : `quant.py ... resume` saute les dossiers déjà complets. Après un changement de palette, de `mono` ou de **gamma**, supprimer `work/<clip>/s*/L*/q_*` avant de relancer (sinon l'ancien rendu est réutilisé sans erreur).
- **Comparer des vidéos entières, pas deux images** : part de chaque style, durée moyenne et maximale des moments, niveaux de pixellisation, écart image par image par style contre la référence. Deux images bien choisies peuvent faire croire que rien n'a changé (ou l'inverse).
- **Mesurer avant de rendre** : les parts de style dépendent de l'ordre et de la longueur des scènes ; tester les cycles avec `plan.py` seul (quelques secondes) avant tout rendu de 35 s.
- **Vertical à bandes noires** : une surimpression posée dans la bande se perd (le vert le plus sombre sur le noir) ; le combo se place dans l'image vidéo, avec un fond sombre. Le vertical ne passe pas par `controls.py` (non adapté) : ne pas dire « contrôlé » pour le contraste ou le rythme.
- **Dire ce qui n'est pas vérifié** : aucun rendu n'a été regardé en mouvement ni écouté par l'agent.

## Procédure de non-régression (à lancer après toute modification de `quant.py`, `plan.py`, `compose.py`, `fx.py`, `styles.py`)
1. Rejouer la référence (plan de `ref-clip2-v3`, `gamma 1.3`, sans transition ni rythme) et comparer image par image au MP4 de référence : écart moyen par style < 1 sur 255 pour n&b, vert, couleur.
2. Si l'écart monte : le dernier changement est la cause, le corriger avant de continuer.
3. Rendre ensuite le clip voulu, comparer les parts de styles, les niveaux N2/N3 et les moments les plus longs à la référence.

## Clip 3 (Vacra) au format vertical (29/10/2026)
- Config : `exemples/config_clip3_v3_vertical.json` (gamma adaptatif conservé : c'est celui du clip 3, pas de clé `gamma`). Nouvelle clé `repli` : style de remplacement quand une scène « brut » doit rester stylisée (cible de viseur possible, bloc brut trop long) ; sans elle, le repli est la couleur vif et gonfle sa part (clip 3 : 32 % au lieu de 16 %).
- Vertical : sur les plans verts, les coins de viseur prennent le ton le plus clair et « TARGET LOCKED » a toujours son fond sombre (vert foncé sur vert clair illisible). Le rejeu du clip 2 v10 vertical après ce changement est identique au final (écart 0,000).
- **Clip 3 v4 (sans couleur vif)** : `exemples/config_clip3_v4_vertical.json` (`gbc_mode: off`, `repli: bw`, cycle bw/raw/gb) : brut 51 %, n&b ≈ 35 %, vert 6 %, cartes 8 %. Piège : `repli: bw` gonfle le n&b dès qu'une scène brute doit rester stylisée (le plus long brut monte à 6,3 s car le repli et les impulsions se compensent mal) ; à surveiller avant de publier.
- Sous-titres verticaux : l'équilibrage ne traite que 2 lignes ; une phrase longue passe sur 3 lignes (ex. image 888 du clip 3).
- **Combo sans fond (29/10)** : demandé par l'auteur. Sans rectangle sombre, le texte jaune ou vert clair se perd sur le vert clair ; un contour sombre de 4 px (pas un fond) garde le texte lisible. Sous-titres verticaux : Arial 40 px (au lieu de 46), interligne 50. Ces changements sont dans le code (`overlays.py`) : ils valent pour tous les rendus verticaux.
- **Gamma du clip 3** : le clip 3 n'a pas de clé `gamma` (il garde le gamma adaptatif 1,3 à 1,9 de sa validation) ; seul le clip 2 est à 1,3. À trancher avec l'auteur clip par clip.

## Histoire du gamma (à ne pas refaire) — noté le 29/10/2026
- **Dire clairement quel gamma chaque clip utilise** : clip 2 = 1,3 fixe (clé `gamma`, comme v3, validé) ; clip 3 = gamma adaptatif 1,3 à 1,9 par scène (pas de clé `gamma`). J'avais gardé l'adaptatif sur le clip 3 sans le dire, alors que le gamma 1,3 « dont on avait parlé » était celui du clip 2.
- Cause d'origine : le gamma adaptatif (commit 8987d6e, pour le clip 3) a aplati le clip 2 nocturne ; le correctif a été la clé `gamma`. Un défaut qui change le rendu d'un clip validé doit être **optionnel par clé**, jamais un changement de défaut silencieux.
- **Comparaison clip 3, adaptatif (v5) contre 1,3 fixe (v6)** : n&b plus sombre en 1,3 (luminance 58 contre 77 sur 255, contraste 54 contre 57), vert idem (49 contre 57) ; brut et cartes inchangés (écart 0,2 et 0,0). Les scènes sombres du clip 3 deviennent presque noires en 1,3 (ex. image 592) : l'adaptatif les éclaircit exprès. Choix à faire par l'auteur à l'image, clip par clip.
- Règle de livraison : à chaque rendu, écrire en une ligne le gamma utilisé (fixe 1,3 / adaptatif) dans le message au lieu de le laisser implicite.
- **Décision (29/10)** : clip 3 final = v6 (gamma 1,3 fixe), `exemples/config_clip3_v6_vertical.json`. Le v5 (adaptatif) reste dans `sorties/finaux/` pour comparaison.
