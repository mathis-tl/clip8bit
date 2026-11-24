# RECETTE : reproduire le rendu rétro 8-bit d'un extrait de clip

Version **v5 (29/10/2026)**, format vertical. Validée sur deux clips : clip 2 (Tiakola, « Mode de vie », 1:50–2:50) et clip 3 (Vacra, « Fille à papa », 0:40–1:40, source 3:2 très sombre). Config de départ : `exemples/config_modele_vertical.json`. **Lire `CLAUDE.md` (questions à poser à l'auteur, dont le gamma) et `LECONS.md` avant de commencer.** Droits et légalité : hors sujet de cette expérience.

## 0. Entrées et dossiers
- Dépôt : `<racine du dépôt>`. Scripts : `scripts/clip2/` (`scripts/clip1/` est obsolète). Dossier de travail ignoré par git : `work/<clip>/` (`W` ci-dessous). Venv : `work/.venv/bin/python`.
- Il faut : une URL YouTube + minutes de début et de fin (ou un fichier vidéo), les **paroles** (texte brut, ad-libs entre parenthèses acceptés), ffmpeg, yt-dlp, `mlx_whisper`.
- Résolution de travail **960×540, 25 i/s** ; le vertical 1080×1920 est produit directement par `compose.py` (`format: vertical`).

## 1. Préparation (une fois par clip)
1. **Extrait** : `python scripts/clip2/fetch.py <url> <début> <fin> W` (ex. `1:50 2:50`) : télécharge seulement la section (1080p max, sans la playlist), recadre au centre en 16:9 si la source ne l'est pas (3:2 → crop, jamais d'étirement), écrit `W/clip.mp4`, `W/raw/f%05d.jpg` (numérotation à partir de 1), `W/audio16k.wav` et `W/source.json`. Depuis un fichier local : `ffmpeg -ss <début> -t <durée> -i source.mp4 -c:v libx264 -crf 14 -c:a aac W/clip.mp4`, puis les deux commandes d'images et d'audio de `fetch.py`.
2. **Sous-titres calés** : Whisper (`mlx-community/whisper-large-v3-turbo`, `word_timestamps`, langue `fr`) sur `W/audio16k.wav` → `W/whisper.json`, puis `python scripts/clip2/align2.py W <durée_s>` aligne `W/lyrics.txt` sur les mots Whisper → `W/subs.json` (liste de `{"start","end","words","t"}`). Les ad-libs `(…)` et titres `[Couplet…]` sont ignorés ; une ligne dont moins de 40 % des mots sont retrouvés est abandonnée.
   - **Contrôle obligatoire** : relancer Whisper en ciblé (`--clip-timestamps`) sur toute ligne douteuse ; avec un second modèle (`whisper-small-mlx`), corriger si **les deux** s'accordent et diffèrent de plus de 0,15 s. Pas de `--initial-prompt` (boucle sur les passages rapides).
3. `python scripts/clip2/cuts.py W` → `W/cuts.json` (scènes, mouvement `d`, `zones` = flashs forcés en brut).
4. `python scripts/clip2/prep.py W palettes <first_scene>` : masques de personnage `rembg u2net_human_seg` (240×135), bases par scène. `first_scene` : l'intro brute doit durer ~1,5–2,5 s (clip 2 : scène 2 ; clip 3 : 1,56 s). À choisir en regardant `cuts.json`.

   - **Rap rapide (clip 8 MMA)** : Whisper normal reconnaît mal le texte. Méthode qui a marché : (1) `ffmpeg -i audio16k.wav -af atempo=0.7 slow.wav`, Whisper large-v3 ET turbo sur `slow.wav`, temps × 0,7 ; ne garder que les mots qui correspondent aux paroles Genius ; (2) refrains répétés : mesurer le décalage constant entre deux occurrences d'une même ligne (MMA : 13,27 s) pour dater celles que Whisper rate ; (3) creux d'énergie 1,5–5 kHz (pas de 0,1 s) = frontières de phrases ; (4) `subs.json` écrit à la main (`words`, `t` proportionnel à la longueur des mots, `start`, `end`) ; (5) contrôle sur le MP4 exporté : début et fin de chaque ligne en images (crop de la bande sous-titres, temps de la vidéo × 1,03 = temps source) ; `verify_subs.py` ne gère pas le style `carte`. Cartes libres : `{"at": s, "dur_s": s, "text": …}` (indépendantes des numéros de ligne).

## 2. Réglages : `W/config.json` (copie de `exemples/config_modele_vertical.json`)
Toutes les clés d'effets sont décrites dans `EFFETS.md` (tableau des clés). Essentielles :
- **À demander à l'auteur avant de commencer** : `gamma` (1,3 fixe, ou aucune clé = adaptatif), `gbc_mode` (`vif` ou `off`), `cycle` (voir `styles.py`), `cadre_largeur`, `mono`.
- `first_scene`, `th_move` (7 = plans calmes seulement), `max_jump` (5), `win` (12 images de viseur), `nocontour_scenes` / `nocontour_windows` (exclusions décidées à l'œil, §6).
- `cards` : `[{"line": n° de ligne de subs.json, "from": 1er mot, "to": dernier mot+1, "min_s": durée mini}]`, **choisies par l'auteur** ; la carte dure jusqu'au dernier mot (maxi 2 s).
- `pulse_len` (10) / `pulse_every` (45) : impulsions brutes dans les scènes stylisées ; `max_raw_frames` (60) : une scène plus longue qui devrait être brute reste stylisée, avec pour style de repli `repli` (si absent : couleur vif ou vert). `n3_every: 0` = tout en N2.
- `effets_hors: ["gb","bw"]` : pas de flash, zoom ni transition sur le vert et le n&b.
- Défauts du code (clips anciens) : sous-titres `ambre`, habillage `bips` ; les clips actuels les remplacent par `jaune` et `muet` (déjà dans le modèle).

## 3. Règles de rendu
Cycle de styles par scène à partir de `first_scene` (`plan.py` + `styles.py`) :
- **raw** : image d'origine. Cible ≈ 45 % (séquences de 0,3 à 1 s ; un brut de plus de 3 s est à signaler). S'y ajoutent les impulsions brutes et les flashs.
- **gbc** (couleur vif, palette fixe `gbcy`, Bayer) : cible ≈ 10 à 13 % ; peut être retiré (`gbc_mode: off`). Variantes `doux`/`mixte` : `EFFETS.md` §6.
- **gb** : vert Game Boy (`palettes/gb.png`). **bw** : **filtre n&b posé sur le rendu `gbcy`** (luminance `0,299 R + 0,587 G + 0,114 B`, `clip((g-18)*1,35)`), il hérite de la pixellisation de base.
- **Niveaux** : N2 (480×270, blocs de 2 px, `bayer_scale` 4) ; N3 (640×360) seulement si `n3_every` > 0. **Gamma** : voir `CLAUDE.md` et `LECONS.md` (le gamma adaptatif aplatit les clips nocturnes).
- **Viseur + TARGET LOCKED** : 4 coins autour d'une cible calme et centrée (12 images), texte avec fond sombre ; sur le vert, coins en ton clair (vertical).
- **Combo** `un_sur_deux` : « COMBO xN » dans l'image (jamais dans les bandes noires), sans fond, contour fin ; pas pendant un viseur.
- **Cartes punchline** : fond noir, texte rouge (235,30,40), Impact majuscule étiré ×1,45, tout d'un coup, sans sous-titres pendant la carte.
- **Sous-titres** : Arial 40, jaune (255,230,0), phrase entière d'un coup, 2 lignes équilibrées, bas à 1480 px, masqués pendant l'intro et les cartes.
- **Habillage** `muet` : 3-2-1-START visuel sans son. **Transitions** `entree` et **rythme** `both` sur brut/couleur.
- **Vertical** : fenêtre de `cadre_largeur` px (480) dans l'image 960×540 qui suit le personnage, agrandie à 1080 px de large, centrée sur 1920 (bandes noires) ; effets appliqués avant le recadrage.
- **Audio** : celui de `clip.mp4` tel quel. Cadence : stylisé à 12,5 i/s, brut à 25 i/s.

## 4. Chaîne de commandes
```
python scripts/clip2/plan.py    W                    # → W/plan.json ; LIRE les parts de style avant d'aller plus loin
rm -rf W/s*/L*/q_*                                   # si palette, mono ou gamma ont changé
python scripts/clip2/quant.py   W palettes 2,3       # (~2 min, parallèle)
python scripts/clip2/compose.py W sorties/essais/<nom>.mp4
python scripts/clip2/verify_subs.py sorties/essais/<nom>.mp4 W/subs.json <1re image sous-titrée>
python scripts/clip2/cover.py   W sorties/finaux/couvertures <préfixe> "LIGNE 1|LIGNE 2" "A_vif:<image>:gbcy:0,B_nb:<image>:gbcy:1,C_vert:<image>:gb:0"   # palette "raw" = sans pixellisation
python scripts/clip2/controls.py W <mp4>             # 16:9 seulement (ne lit pas le vertical)
```
Après tout changement de config : `plan.py`, puis `quant.py`, puis `compose.py`.

## 5. Contrôles avant de montrer (faits sur le MP4 exporté)
1. Parts de style (`plan.json`) et durées des moments (brut le plus long : signaler s'il dépasse 3 s).
2. `ffprobe` : 1080×1920 (ou 960×540), 25 i/s, ≈ 60 s, piste audio de même durée.
3. `verify_subs.py` : changement mesuré à ±1 image ; les écarts attendus tombent sur une carte ou un effet (l'expliquer).
4. Planches d'images relues une à une : 3-2-1-START, début et fin de chaque viseur, chaque carte, combo sur chaque style, sous-titres (3 lignes ?), texte coupé.
5. **Non faisable par l'agent** : écoute, ton, fluidité en lecture, lisibilité sur téléphone. `controls.py` ne lit pas le vertical : ne pas écrire « contrôlé » pour le contraste ou le rythme.

## 6. Revue visuelle des viseurs (obligatoire, les métriques ne suffisent pas)
Pour chaque fenêtre de `plan.json["windows"]` : 4–5 images de la fenêtre dans le MP4 final, en planche. Rejeter (→ `nocontour_windows`, puis §4) si le cadre flotte à côté du visage, la cible n'est pas le chanteur, un bras est mal pris, le personnage bouge nettement, ou la fenêtre chevauche une carte. Un viseur manquant vaut mieux qu'un faux.

## 7. Décisions de l'auteur (ne pas les rediscuter)
- Pixellisation N2 ; vert conservé ; n&b = filtre sur la pixellisation de base ; plus de brut (≈ 45 %) en séquences courtes ; n&b avant le vert ; couleur vif ≈ 10 % (ou aucune sur le clip 3).
- Pas de style `fond` (abandonné). Combo + TARGET LOCKED gardés ; console Game Boy non retenue.
- Sous-titres jaunes, plus petits (Arial 40). Combo sans fond. Habillage 3-2-1 sans son.
- Cartes : choisies par l'auteur. Gamma : demandé par clip (clip 2 et clip 3 en 1,3).
- Couverture TikTok : image plein cadre + titre rouge Impact dans la zone sûre 3:4.

## 7 bis. Format « live puis studio »
Voir `LIVE_STUDIO.md` (transition sonore en fondu enchaîné, mesures de tempo, vérifications) et `scripts/clip2/livestudio.py`.

## 7 ter. Format « sous-titres et cartes seulement » (clip 9 Indochine)
Config : `exemples/config_indochine_sans_effets.json` : `cycle:["raw"]`, `bandes_noires:true` (toute la vidéo en fenêtre 16:9 sur fond noir, couleurs conservées, compose.py), `sans_viseur`, `rythme:""`, `transition:""`, pas d'intro. Cartes libres `{"at","dur_s","text"}`. `cover_rows:[y0,y1]` : recadre la couverture sur l'image utile quand la source a des bandes noires incrustées. `live_cadre_largeur` (720 = image agrandie de 33 %, recadrée au centre, bords perdus) et `sous_titres_degrade` (liste de couleurs RGB de haut en bas, ex. palette jaune color-hex 1008813) en option. `source_hd:true` : mode brut lu en 1920×1080 depuis `clip.mp4` (pas les jpg 960×540), à utiliser avec `live_cadre_largeur` (540 = image 1080×816 en 1:1 sur une source 1080p, rognée au centre sur 56 % de la largeur). Export qualité maximale : `speed.py in out 1.03 10 30 max` (crf 14, veryslow, plafond 35 Mbit/s, AAC 320 k) et `crf` de la config à 4 pour le master. Piège : avec `first_scene:0` les images de la 1re scène (courte) restent sans mode dans `plan.json` ; les passer à `"raw"` avant `compose.py`. Source déjà en noir et blanc : vérifier la saturation des `raw/` avant de parler de filtre.

## 8. Reste à faire
- Son pitché et très légèrement accéléré (esprit Skyrock) ; nouvelles animations pour varier ; `controls.py` pour le vertical ; limiter le brut long et les phrases à 3 lignes ; généraliser les chemins en dur de `align2.py` et `prep.py`.

## 7 quater. Style « dessin + doodles rouges + écho » (essai Lacrim/Booba, 3 nov.)
Autonome (ne passe pas par compose.py) : `scripts/clip2/doodle_clip.py`, calque `doodle.py`, styles `dessin.py` (aplats, peinture alternés d'un plan à l'autre, palette d'aplats recalculée à chaque plan).
1. `fetch.py <url> <début> <fin> work/<slug>` → Whisper large (mlx) → `lyrics.py <url genius>` → `subs.json` à la main (mots, `t` proportionnels à la longueur, `start`, `end`, + `souligne` indice, `fleche` [dx,dy], `eclair` true).
2. `python doodle_clip.py scan work/<slug>` : coupes + `coupes.png` (cadre cyan = fenêtre retenue ; `cx` auto = pic d'énergie de contours par plan, à relire : 1-2 plans coupent le visage). Source avec bandes noires intégrées : `rows` (cropdetect).
3. `python doodle_clip.py rendre work/<slug> exemples/config_doodle_<slug>.json sortie.mp4 [--max] [--de s --a s]`. Clés : `crop_w/crop_h` (fenêtre source, redimensionnée en 1080 de large), `styles`, `ancres` [x,y,angle] (position des sous-titres, qui change à chaque ligne ; le texte est ramené dans l'écran), `taille`, `echo_auto` (seuil de mouvement, 16 ≈ 13 % des images), `echo_s`, `echo` (plages manuelles), `doodles` (traits libres).
4. Vérification : détection des pixels rouges dans la zone de l'ancre de chaque ligne (début visible = prévu à 0,04 s près, effacement +0,1 s). Cela vérifie le rendu contre `subs.json`, PAS `subs.json` contre l'audio (temps issus de Whisper large + paroles Genius).
Pièges : police manuscrite `Bradley Hand Bold` (macOS), tracé = squelette (skimage) épaissi ; peinture = visages sombres très flous ; écho discret sur images fixes (jugé sur le mouvement) ; une image dessinée sur deux, ~2 min de rendu pour 30 s.

Mise à jour v2 (3 nov.) : style `brut` (vidéo d'origine, aucune transformation) en plein écran 1080×1920 : `crop_w 450, crop_h 800` pris dans les lignes utiles de la source (agrandi 2,4×, `nettete` 0,5 compense), `police` + `trace` (`plein` = glyphe entier, `squelette` = fil épaissi) + `etire_v` (lettres étirées en hauteur, 1,4–1,6). Polices testées (OFL / Apache, usage commercial OK, dossier `polices/`) : Sedgwick Ave Display (gras, lisible), Kristi (fine, haute, plus proche du gribouillis de la référence mais moins lisible), Permanent Marker, Reenie Beanie, Gochi Hand, Just Me Again Down Here ; Rock Salt et Beth Ellen inutilisables en `squelette`. Écho : images −3/−6/−9/−12 zoomées de +3,5 % par copie, 0,6 s, plages `echo` garanties + auto sur mouvement. Texte borné à l'écran en largeur et en hauteur. Planches : `sorties/essais/polices_doodle*.png`.

Mise à jour v3 (3 nov.) : `max_mots` (4) découpe chaque vers en bulles courtes (une à la fois, effacée quand la suivante commence). Taille (`tailles`, 190/148/110) et emplacement choisis par bulle sur la zone la plus calme (énergie de contours moyennée sur sa durée), hors zone du visage, loin de la bulle précédente ; bulle < 0,9 s jamais en grande. Écho : au plus un par plan, jamais deux plans consécutifs, ≥ 3 s d'écart, entièrement dans le plan, ≤ `echo_pct` (12 %) des images, 0,5 s, choisi sur le mouvement le plus fort ; l'historique est vidé à chaque coupe. `scan <dossier> "[y0,y1]"` accepte les lignes utiles. Rapport écrit à côté du MP4 (`.rapport.json`). Source en couleur 16:9 sans bandes épaisses (SCH) : rows [60,1020], fenêtre 540×960 (agrandie 2×).

Mise à jour v4 (3 nov., Tiakola « Bottega ») : `doodle.tampon(type, x, y, taille, t0)` dessine couronne / exclam / exclam2 / etoile / eclair (grand, à moitié hors cadre) / fleche, attachés à un mot via `tampons:[{type, mot}]` dans `subs.json` ; `kristi:[mots]` met la bulle en police 2 (`police2`, `p_kristi` pour du hasard) ; angle ±3 à ±7° (`angle_max`) ; vitesse d'écriture `vit` calculée pour que le dernier mot finisse avant la bulle suivante (`vit_max`) ; accroche `hook:"mot"` (mot-choc géant, `hook_mot`) ou `"visage"` (tour de visage + couronne + « !! », `hook_visage:[x,y,rx,ry]` relevé à la main, la détection de visage OpenCV n'est pas disponible dans le venv). Une seule couleur (rouge) : pas encore de couleur par artiste. Écho : durée réduite dans les plans courts (≥ 8 images). Source 16:9 sans bandes : rows [0,1080], fenêtre 608×1080.

**Recette complète du style doodle : voir `DOODLE.md`** (chaîne de fabrication pas à pas, règles de mise en page, pièges). Référence finale : `sorties/finaux/clip10_tiakola_bottega_v1_vertical_doodle-rouge.mp4`.
