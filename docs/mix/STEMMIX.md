# Vidéo « piste par piste » : recette validée (clip11 Tiakola « Mode de vie », 5 nov. 2026)

Méthode validée par l'auteur le 05/11/2026 (v3 doodle = final). À reprendre pour les prochains titres.

## Ce qu'on obtient
Un extrait de clip plein cadre vertical, **son recomposé par pistes** (demucs 4 stems) : on part du tout, la voix reste seule (a cappella 4 mesures), puis on ajoute une piste à la fois, puis des mélanges, puis le tout (boucle). La **voix ne coupe jamais**. Chaque entrée/sortie se fait sur un temps (fondu d'un temps, courbe lisse). 4 piles de blocs rouges (une par piste) + un curseur par pile : bloc allumé et poignée en haut = piste jouée, poignée en bas = coupée.

## Choix validés
- Image : clip net, étalonnage « boost TikTok » de clip-8bit (netteté, saturation, éclat), **aucune pixélisation, aucun assombrissement**.
- Écriture : **doodle** (Sedgwick Ave Display, rouge `#FF1A00`), **seulement le titre** (« MODE DE VIE ») affiché toute la vidéo, y ≈ 400. Petits noms des pistes sous les piles (VOIX, BATT, BASSE, MÉLODIE), en doodle blanc.
- Blocs : tous rouges, **sans contour noir ni cases vides** (seul le bloc du bas est grisé quand la piste est coupée), plus étroits (96 px), curseur à droite (rail 8 px, poignée blanche + trait rouge). Groupe **centré** (x 141 → 873).
- Zone TikTok respectée (x 60–910, y 240–1290), contrôle automatique sur l'encre réelle (`hors_zone_surete` vide).
- Pistes demucs : voix, batterie, basse, « autre » (tout le reste : synthés, nappes, samples). Le 6 pistes (guitare, piano) n'apporte rien sur ce titre (piano vide, guitare −38 dB). Nom du 4e stem : `--nom_o` (provisoire « MÉLODIE », non vérifié à l'oreille).

## Commandes (`.venv` à la racine de clip-8bit, requirements-mix.txt)
1. Stems 4 pistes : `.venv/bin/python -m demucs -n htdemucs -d mps -o work/mix/stems4 work/mix/tiakola/<titre>.wav`.
2. Calage clip ↔ titre : corrélation audio (clip → `work/mix/tiakola/<titre>.wav`) pour trouver `--decalage_clip` (instant du titre moins instant du clip) ; choisir `--debut_mesure` (refrain, voir `work/mix/stems6/<titre>.json`).
3. Rendu final : `.venv/bin/python scripts/mix/stemmix.py --stems work/mix/stems4/htdemucs/<titre> --audio work/mix/tiakola/<titre>.wav --video <clip.mp4> --decalage_clip <s> --debut_mesure <n> --sortie sorties/mix/stemmix --nom <nom> --titre "<TITRE>" --ad doodle --curseurs [--nom_o MÉLODIE] [--crop_x 656]`.
   Plan par blocs : `PLAN` dans `scripts/mix/stemmix.py`. Autres styles d'animation (aperçus, `--style`) : blocs, fines, cercles, ondes, faders, spectre, capsules, colonnes, points.
4. Contrôles : `ffmpeg -v error -xerror -i f.mp4 -f null -`, planche d'images, `hors_zone_surete` du rapport JSON.
5. Livraison : `sorties/finaux/clipN_<artiste>_<titre>_v1_piste-par-piste_doodle.mp4`.

## Limites connues
- Non contrôlé par moi : écoute (entrées, voix isolée, résidus demucs), mouvement en lecture, premier temps de mesure (estimé, peu de contraste).
- Recadrage centré (`--crop_x`) : l'artiste peut être coupé sur les plans larges.
- Droits : un a cappella ou une recomposition peut être signalé par TikTok (non testé).
- Dépend de `scripts/clip2/doodle.py` et `doodle_clip.py` (lus seulement, jamais modifiés) et de `opencv-python-headless` + `scikit-image` dans `.venv`.

## Titre sans clip : clip fictif (clip 14, 10/11/2026)
`scripts/mix/montage.py` assemble des plans d'autres clips (coupes de 2 mesures, plans sans bandes noires ni carton, fenêtre `source@début-fin` pour éviter génériques et légendes) dans un portrait posé à x=656 ; il affiche ensuite le `--decalage_clip` à passer à `stemmix.py`. Durée plus longue : `stemmix.py --plan "VDBO:4,V:6,VD:3,VB:3,VO:3,VDB:3,VBO:3,VDO:3,VDBO:7"` (35 mesures ≈ 60 s). Le recadrage du sujet est une estimation (OpenCV 5 n'a pas de détecteur de visage) : relire la planche des plans avant le rendu.
