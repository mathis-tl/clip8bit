# Grille d'analyse d'un rendu (pour Claude, à la réception d'un MP4)

Entrées : le MP4, `W/config.json`, les images de contrôle. Verdict : **prêt / à corriger (liste) / refusé**, avec ce qui n'a pas été vérifié. Ne pas se fier au rapport d'une autre conversation : refaire les mesures.
1. `ffprobe` : 1080×1920 (vertical) ou 960×540, 25 i/s, ≈ 60 s, piste audio de même durée ; le son d'origine n'est pas modifié (sauf pitch/vitesse si demandés).
2. **Config** : mêmes clés que `exemples/config_modele_vertical.json` ; `gamma` renseigné et conforme au choix de l'auteur (le dire dans le verdict) ; `cards` choisies par l'auteur ; `sous_titres: jaune` avec `mono: jaune` interdit.
3. **Parts de style** (`plan.json`) : brut ≈ 40–50 %, n&b ≈ 20 %, vif ≤ 13 %, vert ≈ 6–13 %, cartes ≈ 8 % ; moment brut > 3 s à signaler ; viseurs ≤ 0,48 s, pas sur une carte.
4. `verify_subs.py` : écarts hors ±1 expliqués (carte, effet).
5. Images : 3-2-1-START, début et fin de chaque viseur, chaque carte, combo sur chaque style (lisible, dans l'image), sous-titres sur 2 lignes (3 lignes = défaut), texte des cartes = paroles, texte coupé.
6. `controls.py` ne lit que le 16:9 : ne rien dire du contraste ni du rythme en vertical.
7. Dire ce qui reste à l'auteur : écoute, fluidité, lisibilité sur téléphone, choix des cartes, choix de la couverture.
