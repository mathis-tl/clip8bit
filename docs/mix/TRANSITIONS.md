# TRANSITIONS : recette et règles mesurées

(À remplir : grammaire mesurée sur les mixes, recettes d'enchaînement, vérifications.)

## 3a. Analyse d'un morceau (`scripts/mix/analyse.py`)
Tempo (librosa puis affinage par peigne sur l'enveloppe des basses 40–200 Hz, ±3 %), premier temps, tonalité (profils de Krumhansl, code Camelot), temps détectés. Tempo ramené dans [70 ; 180] (60 BPM détecté = 120).

**Test de non-régression sur « Cœur de pirate »** (fenêtre 5–85 s de l'audio de clip-8bit, références de `LIVE_STUDIO.md`) :
| | référence (peigne, fenêtres 60–80 s) | analyse.py | écart |
|---|---|---|---|
| live | 141,5 BPM (0,4240 s) | 140,79 BPM (0,4262 s) | −0,5 % |
| studio | 144,1 BPM (0,4165 s) | 143,71 BPM (0,4175 s) | −0,3 % |
| rapport studio/live | 1,018 | 1,021 | +0,3 point |
Tolérance retenue : 0,5 % sur le BPM. Limites connues : les deux fenêtres ne sont pas identiques à celles de la référence ; sur le live, la tonalité (11B) et le tempo peuvent varier selon la fenêtre ; `ecart_librosa_ms` compare au suivi de librosa, ce n'est pas une mesure de justesse.

## Règles provisoires issues de Spotify (04/11/2026, 4 paires observées : `analyses/spotify-mix.md`)
- Geste constant : échange de basses au milieu de la fenêtre (une basse sort, l'autre entre).
- Durée : 2 bars si les titres sont très compatibles (même clé, BPM ≤ 2 d'écart), 4 bars sinon.
- Titres peu compatibles en tonalité : passe-haut sur les deux titres (ouverture et fermeture) pour ôter les basses pendant le chevauchement.
- Placement : fenêtre vers la fin de A, sur l'intro de B ; à confronter à ce que font les DJ (mix Bouss).
Ce sont des observations sur 4 paires, pas des règles de Spotify.

## 3b — Mix DJ MEDDAY (04/11/2026) : ce qui est mesuré, et ce qui ne l'est pas
Scripts : `scripts/mix/mix_grammaire.py` (frontières), `scripts/mix/mix_largeur.py` (largeur). Sorties : `work/mix/medday/frontieres.json`, `largeurs.json`.
- 21 frontières détectées sur 25 min 30 (nouveauté timbre + harmonie). Pas toutes vérifiées à l'oreille : certaines peuvent être des changements de section d'un même titre.
- Largeur du chevauchement : 18 sur 21 sortent à **11 s ou plus**, 3 entre 5 et 6 s, une seule ≤ 2 s. Les valeurs ≥ 30 s touchent le plafond de ma fenêtre (±20 s) : à lire comme « long », pas comme un chiffre. La première version de cette mesure était fausse (15 « coupes » artificielles, normalisation saturée) et a été refaite.
- Les BPM par frontière viennent de `beat_track` seul (valeurs quantifiées 117,5 / 123 / 129,2 / 136…) : **non fiables** pour mesurer l'écart de tempo entre deux titres.
- Non mesuré : où DJ MEDDAY sort de A (début, milieu, fin) et quelle partie de B est jouée avant l'entrée ; échange de basses. À faire avec des repères placés à la main sur quelques paires, ou avec d'autres mixes.

## 3c — Moteur `scripts/mix/enchainer.py` (première version)
Appel : `python scripts/mix/enchainer.py A.wav B.wav <stems> sorties/mix/variantes --nom <paire>`. Six variantes : 1 fondu 8 mesures + échange de basses, 2 fondu 4 mesures (style Spotify), 3 coupe sèche, 4 filtre + écho en fin de A, 5 voix de A sur l'instru de B (demucs), 6 sortie en milieu de A (60 %) + écho, B entre après son intro.
Contrôles : creux de niveau ≤ 3 dB, décalage des attaques à la grille < 20 ms (ajusté avant le chevauchement, vérifié sur le chevauchement), décodage ffmpeg, normalisation anti-écrêtage.
Leçons : (1) l'intercorrélation des attaques de deux morceaux différents est trop bruitée pour caler (a empiré le décalage) ; on mesure l'écart de chaque titre à la grille. (2) Le temps fort de mesure est une estimation (contraste 1,03 pour A) : les temps sont calés, pas forcément les mesures. (3) L'intro de B est ~10 dB sous A : sans gain progressif, creux de 7 dB.

## 3b suite — trois mixes, 134 transitions (DJ MEDDAY 21, Rastine 33, DOV'X 80), 04/11/2026
`scripts/mix/mix_energie.py` : niveau du mix (RMS 1 s) au début, milieu et fin de chaque chevauchement, comparé à la médiane locale ±60 s.
- Niveau au début / milieu / fin : écart médian à la médiane locale entre −0,6 et +0,9 dB dans les trois mixes. **Les DJ transitent au niveau normal du mix, pas sur un outro qui s'éteint.** (Mes variantes 1 à 4 sortaient à 92 % de A, dans son outro : probable cause du résultat « pas satisfaisant ».)
- Largeur médiane du chevauchement : 24 s, 20 s, 22 s ; part ≥ 11 s : 81 %, 70 %, 85 % ; part ≤ 6 s : 19 %, 24 %, 9 %. (Mesure grossière, plafonnée par la fenêtre ±20 s.)
- Non mesuré : en quel point de A sort le DJ, quelle partie de B entre ; il faudrait les titres séparés ou une liste horodatée.
## Moteur v2 (`scripts/mix/enchainer2.py`)
Sortie de A sur une phrase de 8 mesures dans un passage dense (niveau ≥ corps − 3,5 dB sur tout le chevauchement) ; B entre pour que son premier passage fort tombe au milieu du chevauchement (échange de basses) ; alignement des attaques de B sur la grille de A mesuré et corrigé sur la fenêtre du chevauchement (2 passes) ; compensation de niveau (+6 dB max) ; voix de A choisie sur une reprise vocale. Leçon : la même fenêtre doit servir à corriger et à contrôler, sinon la dérive de tempo du titre fait mentir le contrôle.

## Détection de sections : essai d'allin1 (04/11/2026) — échec, repli
`allin1` 1.1.0 s'installe mais exige `madmom` (compilé depuis GitHub avec `SDKROOT=$(xcrun --show-sdk-path)` : OK) et `natten` dont l'API `natten1dav` a disparu des versions récentes ; 0.17.x et 0.15.x ne se compilent pas avec torch 2.15 sur ce Mac. Une réécriture de `natten` en PyTorch pur est possible mais non vérifiable (les poids dépendent de la sémantique exacte des bords) : écartée. Repli : `scripts/mix/structure.py` (répétition sur grille de mesures + voix demucs + niveau).

## Capsule audio v1 (04/11/2026) : `scripts/mix/capsule.py`
AF1 Nouvo (refrain 14,4 s) → Mélo Décalé (48,6 s) → Cœur de pirate (130,3 s). Tous ramenés à 139,7 BPM (rubberband : +4,5 % / 0 / −2,8 %). 32 mesures = 55,0 s. Deux fondus de 8 mesures avec échange de basses au milieu ; le refrain de B (puis C) tombe au milieu du fondu. Contrôles : creux par mesure 1,6 et 1,0 dB ; écart d'attaques à la grille 2, −2, 4 ms après correction (mesuré avant : −68, 292, 76 ms ; Mélo = presque une demi-croche de décalage, grille globale approximative) ; décodage ffmpeg ok. Non vérifié : que le premier temps de mesure soit le bon (le contraste de phase est faible), que les débuts de refrain tombent pile (Cœur de pirate : calé à 130,0 s au lieu de 130,3 s), le ressenti.

## Sources des mixes de référence (audio supprimé le 07/11/2026, mesures JSON gardées dans `work/mix/{medday,dovx,rastine}`)
- Rastine : https://soundcloud.com/deejayrastine/we-re-mix-2025-rip-werenoi-by-rastine-beat
- DOV'X : https://soundcloud.com/djdovx/ninho-session-by-dovx-hors-serie/s-Fa3IItcoe83
- DJ MEDDAY « MIX PROMO 100% BOUSS » : lien non conservé.
- `capsule.py` (capsule 3 titres) supprimé le 07/11 ; récupérable dans l'historique git de clip-8bit avant ce commit.
