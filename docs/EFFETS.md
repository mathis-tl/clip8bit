# EFFETS : catalogue des effets d'originalité (validés par l'auteur le 28/10/2026)

> **Mise à jour du 29/10/2026** : les **défauts du code** restent ceux du 28/10 (ambre, `bips`…) pour ne pas changer les clips anciens ; les clips actuels utilisent **sous-titres jaunes, habillage `muet`, combo `un_sur_deux`, TARGET LOCKED, format vertical** (voir `exemples/config_modele_vertical.json` et `CLAUDE.md`). Les sections 7, 8, 9 sont corrigées ci-dessous ; ce qui est écrit en 1re section sur le clip 2/4 (parts, rendus) est historique.

Statut : les 5 effets ont été montrés en essai sur le clip 2 (viseur aussi sur le clip 3) ; l'auteur : « vraiment très bien, le seul truc à corriger : le viseur plus grand verticalement » (corrigé). **Variantes confirmées par l'auteur le 28/10** : couleur vert, `transition: entree`, `rythme: both`, `habillage: bips`, viseur activé ; ce sont les défauts du code.
Code : `scripts/clip2/fx.py` (appliqué image par image par `compose.py`) ; `plan.py` (choix des fenêtres de viseur) ; `quant.py` (couleur) . Contrôles : `controls.py` section 5.
Tout se règle dans `W/config.json` ; aucun effet ne change la durée, le son d'origine ni le calage des sous-titres.

| Clé | Valeurs | Défaut |
|---|---|---|
| `cible` | `"viseur"` / `"contour"` (ancien) | `"viseur"` |
| `mono` | `"vert"`, `"rouge"`, `"bleu"`, `"rose"`, `"jaune"` | `"vert"` |
| `sous_titres` | `"ambre"`, `"blanc"`, `"cyan"`, `"jaune"` (255,230,0) | `"ambre"` |
| `transition` | `""` (aucune), `"entree"`, `"sortie_entree"` | `"entree"` |
| `rythme` | `""`, `"flash"`, `"zoom"`, `"both"` | `"both"` |
| `habillage` | `""`, `"muet"`, `"bips"` | `"bips"` |
| `cycle` | `"classique"` (gbc, gb, raw, gbc, bw, raw… : gbc 40 %), `"equilibre"` (gb, bw, raw, gbc, crt, raw… chacun 9–22 %, brut 34 %), `"vert_nb_couleur"` (vert d'abord, n&b deuxième, couleur troisième, sans crt : clip 2 = gb 32 %, bw 17 %, gbc 14 %, brut 28 %, cartes 10 %), `"couleur"` (gbc, gbc, raw : pour comparer les variantes de gbc), ou une liste de styles | `"classique"` |
| `gbc_mode` | `"vif"` (palette fixe `gbcy`), `"doux"` (palette tirée de la scène, saturation × 0,7), `"mixte"` (doux + 25 % de l'image source), `"off"` (gbc remplacé par `crt`) | `"vif"` |
| `gbc_grille` | `""`, `"grosse"` (pixels de 3 px), `"tres_grosse"` (4 px) : pour les scènes gbc seulement | `""` |
| `gbc_couleurs` | nombre de couleurs de la palette douce (6 à 24) | `24` |
| `viseur_texte` | `""` ou un texte (ex. `"TARGET LOCKED"`) près du coin haut gauche du viseur | `""` |
| `combo` | `""`, `"chaque_vers"` (affiché à chaque palier), `"un_sur_deux"` (le compteur monte à chaque vers, affiché sur les paliers pairs) | `""` |
| `zone_sure` | `""` ou `"tiktok"` : sous-titres remontés (bas du texte à 80 % de la hauteur, 680 px de large au plus) et combo rentré en (100, 60) | `""` |
| `gamma` | un nombre (ex. `1.3`) : gamma fixe de la quantification ; absent = adaptatif 1,3 à 1,9 par scène. **À demander à l'auteur par clip** (`LECONS.md`) | adaptatif |
| `repli` | `"bw"`, `"gb"`, `"gbc"` : style des scènes qui devraient être brutes mais doivent rester stylisées (cible de viseur, bloc brut trop long) | couleur vif, ou vert si `gbc_mode: off` |
| `effets_hors` | liste de styles sans flash, zoom ni transition (ex. `["gb","bw"]`) | `[]` |
| `n3_every` | `0` : tout en N2 ; N : une scène stylisée sur N en N3 | `3` |
| `format` | `"vertical"` : rendu direct 1080×1920 | 16:9 960×540 |
| `cadre_largeur` | largeur (px, image 960) de la fenêtre qui suit le personnage : 304 plein cadre 9:16, 480 bandes noires de ≈ 350 px, 960 letterbox | `304` |
| `glitch` | `"beat"` : glitch RGB (rouge/bleu décalés + bandes déplacées, 3 images) à la place du flash/zoom un temps fort sur deux ; `"seul"` : sur tous les temps forts | `""` |
| `transition` = `"mosaique"` | pixellisation en blocs de 8→32 px avant et 32→2 px après **chaque changement de style** (même sur gb/bw) | |
| `intro` | `"titre"` : écran-titre plein cadre (titre qui descend, `intro_sous`, PRESS START clignotant, 1 PLAYER) puis mosaïque vers l'extrait en pixels, fondu vers le rendu ; 52 images, remplace le 3-2-1 START. `"gameboy"` : même idée dans une console (abandonnée par l'auteur le 29/10). Clés `intro_titre`, `intro_sous`, `intro_couleur` | `""` |
| `carte_couleur` | nom d'une couleur mono (ex. `violet`) pour le texte des cartes punchline | rouge |
| `crf` | qualité d'encodage de `compose.py` (6 = master pour l'export final) | `17` |
| `viseur_souple` | `true` : couverture ≤ 62 %, IoU .80/.70, centre du viseur 30–70 % (au lieu de 55 %, .85/.75, 35–65 %) | `false` |

Config par défaut (validée) : `"cible":"viseur","mono":"vert","sous_titres":"ambre","transition":"entree","rythme":"both","habillage":"bips"`.

## 1. Coins de viseur (remplacent les contours)
- **Rendu** : 4 coins en L (épaisseur 4 px, longueur ≈ 22 % du plus petit côté de la boîte, min 28 px) autour de la cible, peints sur l'image quantifiée. Couleur : blanc/jaune en gbc, ton clair de la palette en gb, jaune en n&b. Plus d'assombrissement du fond. Animation : les coins démarrent 25 % plus larges et se resserrent en 3 images, puis restent.
- **Boîte** (grille 240×135, médiane des boîtes de la fenêtre, donc figée) : largeur = celle du buste ; hauteur = max(62 % de la hauteur du personnage, 1,5 × largeur de la tête), du haut du masque vers le bas. *Correction du 28/10* : la 1re version ne prenait que la tête et le cou.
- **Cible admise** : plan calme (mêmes règles que les contours : `th_move`, `max_jump`, IoU masque, fenêtre `win` = 12 images = 0,48 s, pas de chevauchement avec une carte, `nocontour_*`) **et** centre de la boîte entre 35 et 65 % de la largeur, hauteur ≥ 15 % de l'image, largeur de la tête de 8 à 50 % de la largeur. Une seule cible (composantes ≥ 30 % de la plus grande).
- **Limite connue** : la machine ne sait pas *qui* est le chanteur ; « grand et central » est un indicateur. **Revue visuelle obligatoire** (RECETTE §6) : cadre qui flotte à côté du visage, plan à deux personnages dont un seul est cadré, nom incrusté sous la cible.
- Résultat : clip 2 : 2 viseurs ; clip 3 : 8 viseurs.

## 2. Couleurs
- Palettes monochromes à 4 tons (sombre → clair), fichiers `palettes/mono_<nom>.png` : rouge `(44,0,14)(122,12,32)(214,44,54)(255,150,140)` ; bleu `(8,16,60)(24,64,160)(60,140,230)(170,215,255)` ; rose `(58,8,50)(150,30,122)(240,92,192)(255,202,236)` ; jaune `(52,38,0)(130,100,0)(225,180,10)(255,236,122)` ; vert (d'origine) `(15,56,15)(48,98,48)(139,172,15)(155,188,15)`.
- **Une seule couleur par clip** : elle remplace le vert (style `gb`) ; gbc et n&b ne changent pas.
- **Contraste des sous-titres ambrés** mesuré sur un extrait du clip 2 (médiane) : vert 3,5:1, rouge 5,3, bleu 4,4, rose 3,6, **jaune 2,7 (< 3:1 → mettre `"sous_titres":"blanc"`)** ; le blanc passe partout (5,6 à 11:1). Dans un clip entièrement rouge, les cartes rouges perdent leur contraste (à juger à l'œil).

## 3. Transitions par pixellisation
- Aux changements **brut ↔ stylisé** seulement, jamais autour d'une carte, avec ≥ 12 images de chaque côté, ≥ 40 images entre deux transitions, jamais dans l'intro.
- `entree` (défaut) : l'image entrante se précise, blocs 32→16→8→4→2→1 px sur 8 images (0,32 s). `sortie_entree` : en plus, l'image sortante se pixellise sur 4 images (4→8→16→32) avant le cut.
- Les sous-titres, dans l'image, se pixellisent aussi pendant ces 0,32 s.

## 4. Effets calés sur le rythme
- Détection des temps forts par scipy (STFT 512/128, flux spectral grosse caisse 40–160 Hz + 0,6 × bande 160–4000 Hz, pics au-dessus du 93e centile, ≥ 0,38 s entre pics ; `librosa` non utilisé). Clip 2 : ≈ 136 bpm.
- Au plus **un effet par 0,8 s**, aucun sur une carte, aucun avant le début stylisé. `flash` : 50 % puis 22 % de blanc sur 2 images ; `zoom` : 107 %→105→103→101 % sur 4 images, centré, au plus proche voisin ; `both` (défaut) : les deux ensemble.
- **Non vérifié à l'oreille par l'agent** : pour juger la détection, générer la version à clics (`scripts/lab/rythme.py`, bip de 1 kHz aux temps retenus).

## 5. Habillage de jeu « 3, 2, 1, START »
- Police `assets/fonts/PressStart2P-Regular.ttf` (OFL). Chiffres blancs 220 px (images 0–9, 10–19, 20–29), START jaune `(255,236,60)` 96 px (images 30–45), ombre portée de 6 px `(20,12,40)`, centré, apparition instantanée, **superposé à l'intro brute** : la musique démarre, la durée ne change pas.
- `bips` (défaut) : 3 bips carrés 440 Hz (90 ms) sur les chiffres, puis 880 Hz et 1320 Hz sur START, mixés à bas niveau sur la piste d'origine (`W/bips.wav`) ; `muet` : aucune modification du son.
- Les bips n'ont pas été écoutés par l'agent.

## 6. Rééquilibrage des styles et pixellisation couleur douce (28/10, clip 4)
- **Problème** : sur le clip 4, `classique` donnait 40 % d'images en gbc vif (cyan, orange, violet saturés), peu reconnaissable ; sur le clip 2 (Tiakola) il rendait très bien. **C'est donc un réglage par clip** (`gbc_mode`), pas une généralité.
- `equilibre` : aucun style pixellisé au-dessus de 25 % (clip 4 : gb 22 %, gbc 18 %, bw 11 %, crt 9 %, brut 34 %, cartes 7 %). `controls.py` §1 signale tout style > 25 % et le brut hors 30–38 %.
- **`doux` à 12 couleurs, pixels de 4 px** (`gbc_mode: doux`, `gbc_grille: tres_grosse`, `gbc_couleurs: 12`) : choix de l'auteur. Le doux seul (24 couleurs, grille N2/N3) paraissait trop faible : ce qui fait l'effet pixel est le nombre de couleurs et la taille des blocs, pas le niveau de grille seul. Moins de couleurs = plus d'effet mais image plus grise (8 et 6 couleurs essayés, écartés). Palette tirée du clip : une scène sans couleur reste grise.
- **`crt`** (style « clip original + effet ») : lignes de balayage (1 sur 3 assombrie), décalage rouge/bleu de 2 px, vignettage. Code : `scripts/clip2/looks.py`. `bit1` (noir et blanc 1 bit tramé) est écrit mais n'est dans aucun cycle ni essayé.
- **Abandonné par l'auteur** : style `fond` (personnage net, fond pixellisé) ; le code reste dans `looks.py`, non utilisé.
- **Sous-titres jaunes** (`jaune`, même jaune que START) : contraste médian 10:1 sur le clip 4, aucune phrase sous 3:1 sur l'image mesurée (une image par phrase).

## 7. « TARGET LOCKED » près du viseur (validé le 28/10)
- Petit texte Press Start 2P 14 px, apparition instantanée à la 1re image du viseur et disparition avec lui (12 images), au-dessus du coin haut gauche (dedans s'il n'y a pas de place), même couleur que les coins. Code : `scripts/clip2/overlays.py`.
- Sur une scène verte (`gb`) en **16:9** les coins et le texte prennent le ton le plus sombre de la palette ; **en vertical** ils prennent le ton le plus clair et le texte a toujours son fond sombre (corrigé le 29/10).

## 8. Compteur de combo (validé le 28/10)
- « COMBO x2 »… en haut à gauche, Press Start 2P 22 px sur 3 images puis 16 px, 1,2 s par palier, jaune (ton le plus sombre sur gb). `chaque_vers` : le palier monte à chaque fin de vers (dernier mot de `subs.json`) et retombe si plus de 5 s séparent deux fins de vers ; jamais sur une carte ni dans l'intro.
- Clip 4 : 16,6 s affichées en tout, jusqu'à x11 (plus que la sobriété visée de 8 s : à rediscuter). La version « par rimes » a été abandonnée : détecter les rimes par l'orthographe ne marche pas (une seule série sur le refrain « way »).
- Limite : jaune peu lisible sur un plan très clair. **Vertical (29/10)** : combo **dans l'image vidéo**, jamais dans les bandes noires, **sans fond** mais avec un contour sombre de 4 px (jaune ou ton clair du vert) ; 64 px sur 3 images puis 46 px.
- **Clip 2 (28 vers rapprochés)** : `chaque_vers` affichait 31 s jusqu'à x28 → mode `un_sur_deux` (16,5 s). **Le combo n'est plus dessiné pendant un viseur** (il chevauchait « TARGET LOCKED »). « TARGET LOCKED » a un fond sombre hors style vert (illisible en jaune sur un n&b clair).

## 9. Format TikTok 1080×1920 (étape finale)
- `scripts/clip2/vertical.py <entrée> <sortie> [noir|flou]` : le rendu 960×540 validé est agrandi à 1080×608 (plus proche voisin) et centré (marges de 656 px en haut et en bas, donc tout dans la zone sûre) ; fond noir ou même vidéo floutée et assombrie. Son copié tel quel.
- Limite : les sous-titres (≈ 24 px sur 1080 de large) et le combo sont petits à l'écran d'un téléphone ; la vidéo n'occupe que 32 % de la hauteur. Les agrandir demanderait de les sortir de l'image 960×540 (non fait). `zone_sure: "tiktok"` n'a plus d'utilité dans ce format.
- **Recadrage 9:16 qui suit le chanteur** (`"format": "vertical"` dans la config, rendu direct par `compose.py` en 1080×1920) : fenêtre de 304 px de large dans l'image 960×540, centrée sur le centroïde du plus grand personnage du masque (`cam_path` : médiane de la scène pour les trous, moyenne glissante de 15 images, jamais à cheval sur un cut), agrandie ×3,55 (bicubique pour raw/crt, plus proche voisin sinon). Les effets (flash, zoom, pixellisation de transition) sont appliqués avant le recadrage ; viseur, « TARGET LOCKED », combo, sous-titres (**Arial 40 px**, interligne 50, 2 lignes équilibrées, bas à 1480 px ; 3 lignes possibles sur une phrase longue) et 3-2-1 START sont redessinés sur la toile 1080×1920 ; les cartes sont refaites en vertical. `verify_subs.py` lit la zone verticale ; `controls.py` ne sait pas encore lire ce format.
- **Limites constatées** : les noms incrustés dans le clip d'origine (« SALOMÉ GOMIS-TREZISE ») sont coupés par le recadrage ; le viseur, calculé pour l'image large, est souvent plus large que la fenêtre et ses coins collent aux bords ; plans de groupe : un seul personnage est suivi.
- **`cadre_largeur`** (29/10) : 304 = plein cadre ×3,55 (visages coupés, pixels très gros) ; **480 = cadre retenu** (×2,25, vidéo de 1215 px de haut, bandes noires de ≈ 350 px) ; 960 = letterbox. Le viseur et « TARGET LOCKED » sont recalculés pour le cadre.
- Clip 2 v7 (historique) : config `exemples/config_clip2_v6_B.json` (cycle `brut_plus`, `pulse_every` 25, vif, vert, sous-titres jaunes, habillage muet, combo `un_sur_deux`, `viseur_texte`, 3 cartes).

## 10. Couverture TikTok (29/10)
- `scripts/clip2/cover.py` : image plein cadre 1080×1920 (recadrage 9:16 sur le personnage, pixellisée avec la palette du plan ou **d'origine** avec la palette `raw`) + titre rouge Impact sur un bandeau sombre, dans la zone sûre de la grille 3:4 du profil (y de 240 à 1680). Trois candidates numérotées, l'auteur choisit. Limites : le nom incrusté du clip d'origine peut passer sous le bandeau ; le centroïde du masque peut cadrer un bras si la scène est un gros plan (choisir l'image à la main).

## 11. Téléchargement YouTube (29/10)
- `scripts/clip2/fetch.py <url> <début> <fin> <work>` : yt-dlp (1080p max, section seulement, sans playlist) puis préparation du dossier de travail. Testé sur 6 s (clip 1920×1080 → `clip.mp4`, 150 images, `audio16k.wav`, `source.json`).

## 12. Sous-titres, export (29/10)
- **Vertical : une seule ligne à l'écran.** Une phrase plus large que 900 px (Arial 40) est coupée en morceaux de largeur voisine, chacun affiché de son 1er mot au 1er mot du suivant (`split_subs` dans `compose.py`). Le combo continue de compter les fins de vers de la phrase entière. `verify_subs.py` lit encore `subs.json` (phrases entières).
- Couleur mono **violet** `(24,6,48)(70,24,128)(150,70,220)(214,170,255)` (`palettes/mono_violet.png`). Le combo n'a plus de contour (demande de l'auteur).
- **Export final** : `scripts/clip2/speed.py <master> <final> [facteur]` : 30 i/s, 18 Mbit/s (plafond 27), AAC 256 k, + accélération image/son de `facteur` (1,03 pour Saki ; 1 = sans). Master rendu avec `crf: 6`.
- **Paroles** : `scripts/clip2/lyrics.py "titre artiste" <sortie>` (Genius, cookie `cf_clearance` dans `~/.config/clip-8bit/genius_cookies.txt`, hors dépôt). Relire : les `[?]` sont des passages non transcrits.

## Pas retenus pour l'instant
Ralentis d'image sans toucher au son (possible seulement en image seule, lipsync faux 0,3–0,5 s) ; console Game Boy autour de la vidéo ; glitch RGB sur les temps forts ; sprite 8-bit de l'artiste (sprite-lab, payant).
