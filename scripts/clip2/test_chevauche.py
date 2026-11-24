"""Tests de chevauche.py : python3 scripts/clip2/test_chevauche.py   (rapide, sans vidéo)"""
import os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chevauche as CH

def bloc(nom, x, y, w, h, t0, t1, src=None):
    ink = np.ones((h, w), np.float32); it = CH.item_encre(nom, ink, x, y, t0, t1); it.src = src; return it

def test_recouvrement():
    a = bloc("a", 100, 100, 200, 200, 0, 5); assert CH.recouvrement(a, bloc("b", 600, 600, 100, 100, 0, 5)) == 0
    assert CH.recouvrement(a, bloc("c", 100, 100, 200, 200, 0, 5)) > .99
    assert CH.recouvrement(a, bloc("p", 150, 150, 40, 40, 0, 5)) > .99                    # petit dessin entièrement dans le grand : 100 % du plus petit
    assert CH.recouvrement(a, a.decale(1000, 0)) == 0

def test_marge():
    a = bloc("a", 100, 100, 200, 200, 0, 5)
    assert CH.recouvrement(a, bloc("b", 300 + 40, 100, 100, 200, 0, 5)) == 0                # 40 px d'écart : libre
    assert CH.recouvrement(a, bloc("c", 300 + 2, 100, 100, 200, 0, 5)) > CH.TOL            # 2 px d'écart : dans la marge de 2×8 px

def test_temps():
    a, b = bloc("a", 100, 100, 200, 200, 0, 2), bloc("b", 100, 100, 200, 200, 2.0, 4)
    assert not CH.simultane(a, b) and CH.conflits([a, b]) == []                             # même place mais l'un après l'autre : pas de conflit
    c = bloc("c", 100, 100, 200, 200, 1.9, 4); assert CH.simultane(a, c) and len(CH.conflits([a, c])) == 1

def test_tolerance():
    a = bloc("a", 100, 100, 400, 100, 0, 5); b = bloc("b", 100 + 400 - 6, 100, 400, 100, 0, 5)                # ~8 px de recouvrement des marges sur 400 px
    r = CH.recouvrement(a, b); assert 0 < r < 1; assert (len(CH.conflits([a, b])) == 1) == (r > CH.TOL)

def test_ecourter():
    ordre = np.full((10, 10), np.inf, np.float32); ordre[2:5, 2:5] = 1.0                      # tracé fini à t = 1 → fin_min = 1,15
    src = dict(ordre=ordre, debut=0., fin=6.)
    vieux = bloc("vieux", 100, 100, 200, 200, 0, 4.3, src); nouveau = bloc("nouveau", 120, 120, 200, 200, 4.0, 8)
    pen, trims = CH.penalite_ec([nouveau], [vieux]); assert len(trims) == 1 and pen < 2 and trims[0][1] < 4.1     # écourté
    src2 = dict(ordre=np.full((10, 10), 3.9, np.float32), debut=0., fin=6.)                    # tracé fini à 3,9 : ne peut plus être écourté
    vieux2 = bloc("vieux2", 100, 100, 200, 200, 0, 4.3, src2); pen, trims = CH.penalite_ec([nouveau], [vieux2]); assert trims == [] and pen >= 2

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"): f(); print("ok", n)
