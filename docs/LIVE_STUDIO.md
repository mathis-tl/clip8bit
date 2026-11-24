# LIVE_STUDIO : montage « version live puis version studio » (clip 7 Tiakola, « Cœur de pirate »)

Recette reproductible d'un clip de 30–45 s où la version live (Taratata, 576×324) enchaîne sur le clip studio (4K) par un **fondu enchaîné sonore** et une **coupe nette** de l'image, sur une même phrase. Final : `sorties/finaux/clip7_tiakola_coeur-de-pirate_v1_vertical_live-studio.mp4` (1080×1920, 30 i/s, 40,0 s, ~17 Mbit/s). Config : `exemples/config_tiakola_coeur_de_pirate.json`, sous-titres : `exemples/subs_tiakola_coeur_de_pirate.json`.

## Règles de l'auteur pour ce format
- Live : fenêtre 16:9 entière, bandes noires (pas de flou), **jamais pixellisé**, toujours n&b à gamma adaptatif. Studio : plein cadre, effets normaux, pixel total ≤ 20 % des images (n&b + rose).
- Pas de viseur, pas de flashs, pas de tremblement, pas d'intro ni d'affiche, pas de cartes. Vitesse +3 % et basses +10 dB comme les autres clips (`speed.py … 1.03 10 30`).
- Sous-titres comme Bedry (rouge Impact étiré, sans fond, une ligne au milieu).
- Transition : le studio démarre exactement sur l'attaque de la phrase, **sans attaque ni coupure sonore** : les deux sons se superposent en fondu (le studio entre en douceur avant la coupe, le live s'éteint), l'image fait une coupe nette sur la phrase.
- **Sous-titres = les voix qu'on entend réellement** : les ad-libs entre parenthèses de Genius (« Je veux que tu m'aimes encore », « Je veux l'entendre plus fort »), pas la ligne principale du refrain (voix de fond, inaudible).

## Chaîne de commandes (depuis `<racine du dépôt>`, `PY=work/.venv/bin/python`)
1. **Sources** : `fetch.py <url_live> 0 <fin> work/<x>_live` et `fetch.py <url_studio> 0 <fin> work/<x>_studio` (X/Twitter marche avec yt-dlp ; seule la vidéo, pas la playlist). Whisper turbo sur chaque `audio16k.wav` (`--condition-on-previous-text False`), paroles : `lyrics.py`.
2. **Mesures** : `$PY scripts/clip2/livestudio.py mesure work/<x>_live work/<x>_studio <t_coupe_live> <t_coupe_studio>` → tempo des deux versions, rapport r, fin de live conseillée (voir « Vérifications »).
3. **Repère de la phrase dans le studio** (`S_coupe`) : Whisper ciblé (`--clip-timestamps a,b`, modèles turbo ET small) + enveloppe sonore fine + repères donnés par l'auteur. Whisper « small » donne les bons débuts de mots ; les durées de mots de « turbo » sont fausses sur les voix de fond.
4. **Montage** : `$PY scripts/clip2/livestudio.py monter work/<x>_live work/<x>_studio work/<x>_mix <L0> <L1> <S_coupe> <S_fin> --fondu 2.0 --r <r>` → `clip.mp4`, `raw/`, `audio16k.wav`, `source.json` et **tableau des niveaux à relire avant de rendre**.
5. **Sous-titres** `work/<x>_mix/subs.json` : liste de `{"words","t","start","end","exact","total"}` ; live : `(t_source − L0)/r`, studio : `t_source − S_coupe + O` (O = `(L1−L0)/r`, affiché par `monter`). Mots répartis uniformément (`t`).
6. **Config** : copier `exemples/config_tiakola_coeur_de_pirate.json` dans `work/<x>_mix/config.json` et régler `live_nb_s` = `gamma_adaptatif_avant_s` = O (voir clés).
7. `cuts.py W` → `prep.py W palettes 0` → `plan.py W` (contrôler la part de pixel ≤ 20 %, ajuster `cycle`) → `quant.py W palettes 2,3` (supprimer d'abord les dossiers `q_*`) → `compose.py W master.mp4` → `speed.py master.mp4 final.mp4 1.03 10 30`. Ne jamais lancer deux processus qui écrivent le même fichier.

## Clés de config propres à ce format
| Clé | Rôle |
|---|---|
| `live_nb_s` | durée (s, temps du montage) de la partie live : images brutes en n&b à gamma adaptatif par scène, jamais pixel (`plan.py` force « brut » sur ces scènes) |
| `gamma_adaptatif_avant_s` | avant cet instant `quant.py` garde le gamma adaptatif, après il applique `gamma` fixe (1,3) |
| `live_cadre_largeur` | largeur (px de l'image 960) de la fenêtre live : 960 = vrai 16:9 bandes noires ; 480 = cadrage plus serré |
| `sans_viseur` | aucun viseur (`plan.py`) ; avec `rythme:""` (pas de flash), pas de `tremblement`, `intro:""`, `habillage:""` |
| `intro_fin` | affiche d'ouverture jouée à l'envers en fin de clip (non utilisée dans le final, retirée à la demande) |

## Vérifications faites sur ce clip (à refaire à chaque fois)
1. **Repère de la phrase du studio** : trois sources concordantes (Whisper small 140,52 s ; repères de l'auteur dans deux versions = 140,3 et 140,65 s ; Whisper turbo `l'entend` à 141,3 s). Mon premier repère (139,27 s) était faux d'environ 1 s : l'image studio démarrait trop tôt et l'écho studio passait à plein volume.
2. **Tempo mesuré sur les battements de basse** (peigne 40–200 Hz, fenêtres de 60–80 s) : live 0,4240 s/temps (141,5 BPM), studio 0,4165 s (144,1 BPM) → r = 1,018, live accéléré de **1,8 %** (`atempo` + `setpts`). **Piège évité** : les durées de lignes données par Whisper avaient fait croire à 10–13 %, valeur fausse. Les corrélations d'enveloppe sonore directes live/studio sont inutilisables (≤ 0,5, arrangements différents).
3. **Calage de la coupe sur la grille de battements** : la fin du live tombe à 0,13 temps après un temps, celle du studio à 0,15 : les deux grilles coïncident (L1 conseillé 53,509 s, retenu 53,5 s). Confiance moyenne (score de peigne live 0,68 contre 0,65 pour le suivant).
4. **Niveaux du fondu** (`monter` imprime le tableau, fenêtres de 0,25 s) : somme de 72,0 dB avant le fondu à 69,5 dB au plus bas, 71,3 dB puis 67,5 dB à la coupe, soit un creux maximal de ~2,5 dB. Studio de 48 dB à 68 dB sur 1,5 s, live de 72 dB à 46 dB. Fondus `afade curve=qsin` (puissance égale), `amix normalize=0`, `loudnorm -16 LUFS` avant les fondus.
5. **Signal** : pic 0,66 de la pleine échelle, 0 échantillon écrêté, saut d'échantillon max à la coupe 2772 (médian 485 : normal pour de la musique). Rendu final : −15,8 dB moyen, pic −1,4 dB, décodage `ffmpeg -f null` sans erreur.
6. **Image** : la coupe image tombe pile à l'image 282 (différence de 43,9 contre < 1 entre images voisines), vérifiée sur les images 276–289 ; le live est tronqué à `int(O×25)` images pour qu'aucune image studio ne soit rendue en style live.
7. **Revue d'images** (planche de 12 à 16 images) : fenêtre live 16:9 n&b sans pixel, studio plein cadre, sous-titres rouges au milieu.

## Non vérifié par la machine (reste à l'oreille et à l'œil de l'auteur)
Ressenti du fondu, tempo « naturel » du live accéléré, mouvement en lecture. Les temps des sous-titres du studio sont **estimés** (Whisper ne comprend pas ce refrain) : structure mesurée = début du refrain 130,3 s (Whisper small), lignes de 6,66 s (4 mesures), post-refrain à 157,0 s, « Cœur de pirate » toutes les 1,67 s ; ad-libs : écho 1 à +0,4…+3,0 s de la ligne, écho 2 à +3,5…+6,3 s. l'auteur a validé ces temps au rendu v6, sauf les deux lignes principales (« Il m'aime encore… ») qu'il a fait remplacer par les ad-libs entre parenthèses.

## Pièges rencontrés
- zsh : `$D:curve` dans une chaîne de filtres est lu comme un modificateur → toujours `${D}:curve`.
- Whisper large sur du live sort « Sous-titres par … » : utiliser turbo + `--condition-on-previous-text False` et vérifier avec small.
- X/Twitter : 576×324, logo france•tv incrusté en haut à droite (laissé tel quel à la demande de l'auteur).
