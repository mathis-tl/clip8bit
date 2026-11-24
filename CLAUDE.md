# clip-8bit : contexte et règles (point d'entrée de tout agent)

Expérience à part, **autonome** : transformer des extraits de clips de rap en rendu rétro 8-bit pour TikTok. Droits et légalité : hors sujet de cette expérience. Réponses en français ; l'utilisateur aime les listes numérotées (« 1a / 1b ») pour choisir vite. Phase de développement : on teste plusieurs solutions, l'utilisateur choisit.

## Lire dans cet ordre
1. `docs/LECONS.md` : régressions déjà rencontrées, référence de rendu `ref-clip2-v3`, procédure de non-régression. **À relire avant de toucher au pipeline.**
2. `docs/RECETTE.md` : le pipeline complet (préparation, config, chaîne de commandes, contrôles, revue visuelle).
3. `docs/EFFETS.md` : catalogue des effets et des clés de config (viseur, combo, TARGET LOCKED, vertical…).
4. `docs/ANALYSE_RENDU.md` : grille de contrôle d'un rendu. `docs/PROMPT_NOUVEAU_CLIP.md` : modèle de demande pour un nouveau clip.

## Questions à poser à l'utilisateur AVANT de commencer un clip (ne jamais présumer)
Poser ces questions en une seule liste numérotée, attendre les réponses, puis les écrire dans la config.
1. **Gamma** (`gamma` dans la config) : 1a **1,3 fixe** (rendu de v3 et du clip 2, validé ; scènes sombres plus contrastées, parfois très noires) ; 1b **adaptatif** 1,3 à 1,9 par scène (pas de clé ; éclaircit les scènes sombres, rendu plus plat). Le clip 3 final est en 1,3. Dire ensuite en une ligne quel gamma est utilisé à chaque rendu.
2. **Couleur vif** (`gbc_mode`) : 2a avec (part visée ≈ 10 %), 2b sans (`off`). Les autres parts : brut ≈ 45 %, n&b ≈ 22 %, vert ≈ 13 %, cartes ≈ 8 % (à confirmer).
3. **Format et cadre** : vertical à bandes noires (`format: vertical`, `cadre_largeur` 480 par défaut ; 600–700 = moins de zoom ; 304 = plein cadre) ou 16:9.
4. **Cartes punchline** (`cards`) : choisies par l'utilisateur, jamais par l'agent.
5. **Couleur mono** (`mono`) et **sous-titres** (jaune par défaut).
6. Source : URL YouTube + minutes (`fetch.py`), paroles (`lyrics.py`, Genius, ou collées par l'utilisateur).
7. **Effets** : `glitch` (oui/non), `transition` (`entree` ou `mosaique`), `intro` (`titre` ou aucune), `carte_couleur`.
8. **Vitesse** (`speed.py`, facteur 1,03 à 1,05 ou 1) et export final 30 i/s 18 Mbit/s (`speed.py` le fait toujours).

## État validé (29/10/2026)
- Finals vertical : clip 2 `sorties/finaux/clip2_tiakola_mode-de-vie_v5_vertical.mp4` (config `exemples/config_clip2_v10_vertical.json`), clip 3 `sorties/finaux/clip3_vacra_fille-a-papa_v6_vertical.mp4` (config `exemples/config_clip3_v6_vertical.json`). v3 (clip 2) = référence de rendu 16:9.
- Clip 4 (Saki, 29/10) : violet, `transition: mosaique`, `intro: titre`, sans glitch, gamma adaptatif, sans couleur vif, sous-titres une ligne à la fois, combo sans contour, vitesse +3 %, config `exemples/config_saki.json`.
- Réglages communs : sous-titres jaunes Arial 40 sur 2 lignes (bas à 1480 px), combo `un_sur_deux` sans fond (contour fin), `viseur_texte` « TARGET LOCKED », habillage `muet` (3-2-1 START visuel sans son), `n3_every: 0` (tout N2), `effets_hors: ["gb","bw"]` (pas de flash/zoom/transition sur vert et n&b), `pulse_every: 45`, transitions `entree` et rythme `both` sur brut/couleur.
- Mesuré mais pas encore traité : brut jusqu'à 6 s sur le clip 3, phrases de sous-titres sur 3 lignes, `controls.py` ne lit pas le vertical.

## Zones TikTok (règle permanente, 04/11/2026)
Tout texte ou dessin posé par code sur une vidéo verticale reste dans la **zone sûre** de `scripts/clip2/zones.py` (x 60–910, y 240–1290) : l'interface TikTok recouvre le haut (île dynamique), la colonne d'icônes à droite et la description en bas. `doodle_clip.py` refuse le rendu sinon. Nouveau style ou nouvelle sortie = importer `zones.py` et contrôler par `zones.py planche` avant de livrer.

## Doodle : standard « boost TikTok » (05/11/2026)
Tout nouveau clip doodle part de `exemples/config_doodle_bottega_rouge_boost.json` (rouge `#FF1A00`, netteté et saturation renforcées pour compenser la compression TikTok) ; référence : clip 10 Bottega v4. Détail et limites : `docs/DOODLE.md`.

## Chevauchements (règle permanente, 04/11/2026)
Style doodle : **jamais de chevauchement** entre bulle, soulignement, éclair/flèche de vers, tampon, hook et doodle libre tant qu'ils sont à l'écran ensemble (`scripts/clip2/chevauche.py`, tolérance 5 % du plus petit, marge ≈ 8 px). `doodle_clip.py` place pour l'éviter et **refuse le rendu** sinon (`chevauchement_off` pour passer outre ; `evitement: false` = ancien placement). `doodle_clip.py mesurer` compte sans rendre. Détail et contrôle visuel : `docs/DOODLE.md`.

## Règles de travail
- Le visuel se juge sur des **images exportées** relues une à une, jamais « au jugé » ; dire ce qui n'a pas été contrôlé (mouvement, écoute, ton, rythme).
- Ne jamais modifier une config de référence : copier. Tout changement de défaut qui touche un clip validé se fait **par clé optionnelle**.
- Après tout changement de `quant.py`, `plan.py`, `compose.py`, `fx.py`, `styles.py` : procédure de non-régression de `docs/LECONS.md`.
- Cache : supprimer `work/<clip>/s*/L*/q_*` après un changement de palette, de `mono` ou de gamma avant `quant.py`.
- Mesurer les parts de style avec `plan.py` seul avant tout rendu de 35 s.
- Les MP4 de `sorties/` sont ignorés par git : prévenir l'utilisateur de les sauvegarder. Commits en français, explicites, avec la ligne `Co-Authored-By`.
- Automatisation : `scripts/clip2/fetch.py <url> <début> <fin> <work>` prépare le dossier de travail depuis une URL YouTube (yt-dlp déjà installé).

## À venir (demandé par l'utilisateur le 29/10)
Son pitché et très légèrement accéléré (esprit Skyrock), nouvelles animations pour varier les vidéos (liste à proposer, l'utilisateur choisit).

## Système mix (fusionné depuis l'ancien dépôt mix-lab, 07/11/2026)
Transitions façon DJ entre deux morceaux et vidéo « piste par piste » (stems demucs + blocs rouges + curseurs + titre doodle). Code `scripts/mix/`, docs `docs/mix/` (`STEMMIX.md` = recette validée du clip 11, `TRANSITIONS.md`, `PLAN_PUBLICATION.md`, `analyses/`), données `work/mix/` (titres Tiakola, stems), sorties `sorties/mix/`. Environnement : `.venv` à la racine (`requirements-mix.txt`), distinct de `work/.venv`. Toujours lancer depuis la racine de clip-8bit.
- Coût : 0 €, tout en local. Spotify : exploration à l'écran seulement, jamais d'enregistrement du flux. Mixes de référence : `yt-dlp`.
- L'oreille de l'utilisateur tranche : 🚦 après écoute des variantes audio, puis après la vidéo.
- Méthode validée du piste par piste : la voix ne coupe jamais, blocs tous rouges sans contour, curseurs à droite, seule écriture doodle = le titre, tout dans la zone TikTok, clip net (jamais pixélisé), 4e stem nommé « MÉLODIE ».

### Nouvelle vidéo « piste par piste » : procédure (validée sur les clips 11 à 14)
Départ : un lien YouTube de titre (ou une recherche) + éventuellement l'instant de départ et la durée. Tout depuis la racine de clip-8bit, `.venv/bin/python`. Détail : `docs/mix/STEMMIX.md`.
1. Choisir la source : le vrai clip en 1080p (pas la pochette fixe ni une reprise à légendes) ; `yt-dlp -F` pour vérifier la résolution ; audio extrait dans `work/mix/tiakola/<nom>.wav`.
2. Stems : `python -m demucs -n htdemucs -d mps -o work/mix/stems4 work/mix/tiakola/<nom>.wav` ; `scripts/mix/structure.py` pour repérer le début du refrain ; `mesure = (instant − t0) / durée d'une mesure` (via `enchainer.grille` / `temps_fort`).
3. Calage clip ↔ titre par corrélation audio (`--decalage_clip`). Pas de clip (pochette fixe) : `scripts/mix/montage.py` fabrique un clip fictif depuis les autres clips Tiakola.
4. Rendu : `scripts/mix/stemmix.py ... --ad doodle --curseurs [--plan "VDBO:4,V:6,..."] --sortie sorties/finaux --nom clipNN_...` (≈ 5-8 min, lancer en arrière-plan). Un seul exemplaire, dans `sorties/finaux/` ; supprimer le `.wav` intermédiaire.
5. Couverture : `scripts/clip2/doodle_cover.py work/<dossier> exemples/config_doodle_upa_cover.json <sortie> clipNN "TITRE" A:<t>,B:<t>` (titre en doodle, visage jamais masqué), à copier dans `sorties/finaux/couvertures/`.
6. Contrôles : décodage ffmpeg, `hors_zone_surete` vide, planche d'images relue. Non contrôlé par l'agent : l'écoute, le cadrage en lecture, les droits TikTok. Rappeler de sauvegarder les MP4.
Variante bass boost (clip 15, L2B « Chanel », validée à +12 dB le 11/11/2026) : `stemmix.py --boost_db 12 --plan "V:2,VB:2,VX:3,..."` (`X` = basse jouée et boostée ; mention « BOOST » doodle sous « BASSE » ; hook voix seule → basse → basse boostée).
Clip 16 (Tiakola « Sans toi », 45 s, 12/11/2026) : basse boostée partout où elle joue, a cappella mis en avant (5 + 4 mesures), `--fond_clair` pour clip à fond blanc (noms en rouge, rails gris).
Numérotation actuelle : dernier clip = 16 (Sans toi) ; 15 = Chanel (v1 normale + v2 bass boost 12 dB).
