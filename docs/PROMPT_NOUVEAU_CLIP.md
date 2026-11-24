# Modèle de demande pour un nouveau clip (à remplir par l'auteur ; l'agent suit `CLAUDE.md`)

L'agent commence par poser la liste de questions de `CLAUDE.md` (gamma, couleur vif, cadre, cartes, couleur mono, sous-titres) et **attend les réponses**.

```
Source : <URL YouTube>  de <début> à <fin>
Paroles : <coller les paroles>
Gamma : 1,3 fixe | adaptatif
Couleur vif : oui (≈ 10 %) | non
Cadre : vertical 480 | autre
Couleur mono : vert | …
Cartes : <phrases choisies par l'auteur, ou « à proposer »>
Couverture : titre « … »
```

Consignes à l'agent : suivre `RECETTE.md` §1 à §6 (`fetch.py` pour l'extrait), partir de `exemples/config_modele_vertical.json`, mesurer les parts de style avec `plan.py` avant le rendu, relire les images une à une, appliquer la procédure de non-régression de `LECONS.md` si le pipeline a changé, rendre dans `sorties/essais/`, dire ce qui n'a pas pu être contrôlé (mouvement, écoute, lisibilité sur téléphone) et ne jamais signaler un contrôle non exécuté. Les finals vont dans `sorties/finaux/` seulement sur ordre de l'auteur.
