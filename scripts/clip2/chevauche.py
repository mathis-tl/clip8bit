"""Chevauchements texte / dessins du style doodle : mesure, évitement au placement, contrôle bloquant (règle permanente, 04/11/2026).
RÈGLE : deux éléments (bulle de texte, soulignement, éclair ou flèche d'un vers, tampon, hook, doodle libre) ne se recouvrent jamais PENDANT QU'ILS SONT TOUS DEUX À L'ÉCRAN.
Mesure : chaque élément = masque d'encre (réduit ×4, dilaté de 2 px réduits ≈ 8 px de marge de chaque côté) + intervalle [début de tracé, fin + 0,18 s d'effacement].
Un couple est en conflit si les intervalles se recouvrent de plus de 0,02 s ET si la surface commune des masques dépasse TOL = 5 % du plus petit des deux (tolérance du rendu ;
le placement vise TOL_PLACEMENT = 2 %, pour absorber l'arrondi de la grille ×4). Les boîtes englobantes (px) sont listées dans le rapport à titre indicatif.
python chevauche.py <rapport.json>      # relit un rapport écrit par `doodle_clip.py mesurer` ou `rendre` et l'affiche
python chevauche.py planche <rapport.json> <video.mp4> <prefixe> [par_planche=10]   # images aux instants où plusieurs éléments sont à l'écran ensemble (contrôle visuel)"""
import sys, json, numpy as np, cv2
VW, VH = 1080, 1920
ECH, DIL, EFFACER, SEUIL = 4, 2, .18, .3
TOL, TOL_PLACEMENT, T_MIN = .05, .02, .02
_K = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * DIL + 1, 2 * DIL + 1))

class Item:
    """un élément visible : grille ×4 dilatée (m, décalée de ox, oy mailles), boîte englobante de l'encre en px, intervalle d'affichage [t0, t1] en s"""
    def __init__(s, nom, t0, t1, ox, oy, m, boite, n=None, src=None):
        s.nom, s.t0, s.t1, s.ox, s.oy, s.m, s.boite, s.src = nom, t0, t1, ox, oy, m, boite, src; s.n = int(m.sum()) if n is None else n
    def decale(s, dx, dy):
        b = s.boite; return Item(s.nom, s.t0, s.t1, s.ox + int(round(dx / ECH)), s.oy + int(round(dy / ECH)), s.m, (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy), s.n, s.src)

def item_encre(nom, ink, x0, y0, t0, t1):
    """ink : tableau (float 0-1 ou bool) posé en (x0, y0) sur la toile. None si rien n'est dessiné"""
    b = ink > SEUIL; ys, xs = np.nonzero(b)
    if not len(ys): return None
    x0, y0 = int(x0), int(y0); h, w = b.shape; ax, ay = x0 // ECH, y0 // ECH; px, py = x0 - ax * ECH, y0 - ay * ECH
    H, W = -(-(h + py) // ECH) * ECH, -(-(w + px) // ECH) * ECH; a = np.zeros((H, W), np.uint8); a[py:py + h, px:px + w] = b
    m = a.reshape(H // ECH, ECH, W // ECH, ECH).max(axis=(1, 3)); m = cv2.dilate(cv2.copyMakeBorder(m, DIL, DIL, DIL, DIL, cv2.BORDER_CONSTANT, value=0), _K).astype(bool)
    return Item(nom, t0, t1, ax - DIL, ay - DIL, m, (x0 + int(xs.min()), y0 + int(ys.min()), x0 + int(xs.max()) + 1, y0 + int(ys.max()) + 1))

def items_element(el, x0, y0):
    """items d'un élément du Calque posé en (x0, y0) : une bulle donne mots / éclair vers / flèche vers, un dessin un seul item"""
    nom = el.get("nom", "?"); t1 = el["fin"] + EFFACER; out = []
    if el.get("parties"):
        for p in el["parties"]:
            it = item_encre(f"{nom} {p['nom']}" if p["nom"] != "mots" else nom, p["ink"], x0 + p["x"], y0 + p["y"], p["t0"] - .02, t1)
            if it: it.src = el; out.append(it)
    else:
        it = item_encre(nom, el["ink"], x0, y0, el["debut"] - .02, t1)
        if it: it.src = el; out.append(it)
    return out

def items_calque(L, depuis=0):
    return [it for el, x0, y0 in L.els[depuis:] for it in items_element(el, x0, y0)]

def simultane(a, b): return min(a.t1, b.t1) - max(a.t0, b.t0) > T_MIN

def recouvrement(a, b):
    """part de la surface commune des masques, rapportée au plus petit des deux (0 si pas de contact)"""
    x0, y0 = max(a.ox, b.ox), max(a.oy, b.oy); x1, y1 = min(a.ox + a.m.shape[1], b.ox + b.m.shape[1]), min(a.oy + a.m.shape[0], b.oy + b.m.shape[0])
    if x1 <= x0 or y1 <= y0: return 0.
    return float((a.m[y0 - a.oy:y1 - a.oy, x0 - a.ox:x1 - a.ox] & b.m[y0 - b.oy:y1 - b.oy, x0 - b.ox:x1 - b.ox]).sum()) / max(1, min(a.n, b.n))

def penalite(cands, actifs, tol=TOL_PLACEMENT):
    """pour le placement : somme des pénalités des items `cands` face aux items `actifs` à l'écran en même temps (0 = libre)"""
    pen = 0.
    for c in cands:
        for o in actifs:
            if simultane(c, o):
                r = recouvrement(c, o)
                if r > tol: pen += 2. + 10. * r
    return pen

def fin_min(el):
    """plus petite valeur de `fin` qui laisse l'élément entièrement tracé (+ 0,15 s de tenue)"""
    if "_fin_min" not in el: o = el["ordre"]; el["_fin_min"] = float(o[np.isfinite(o)].max()) + .15 if np.isfinite(o).any() else el["debut"]
    return el["_fin_min"]

def penalite_ec(cands, actifs, tol=TOL_PLACEMENT):
    """comme `penalite`, mais un élément déjà à l'écran peut être ÉCOURTÉ (sa fin avancée jusqu'à l'apparition du nouveau) s'il reste entièrement tracé :
    coût 0,3 (dessin, hook) ou 0,9 (bulle de texte) + 3 par seconde retirée. Renvoie (pénalité, [(élément, nouvelle fin d'affichage)])"""
    pen, trims = 0., {}
    for c in cands:
        for o in actifs:
            if not simultane(c, o): continue
            r = recouvrement(c, o)
            if r <= tol: continue
            t1n = c.t0 + T_MIN / 2
            if o.src is not None and o.t0 < c.t0 and t1n - EFFACER >= max(fin_min(o.src), o.src["debut"] + .5):
                k = id(o.src); dt = o.t1 - t1n
                if k not in trims or t1n < trims[k][1]: trims[k] = (o.src, t1n, dt)
            else: pen += 2. + 10. * r
    for src, t1n, dt in trims.values(): pen += (.9 if src.get("parties") else .3) + 3. * dt
    return pen, [(src, t1n) for src, t1n, _ in trims.values()]

def conflits(items, tol=TOL):
    """tous les couples simultanés dont le recouvrement dépasse `tol`, du pire au moins grave"""
    out = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if not simultane(a, b): continue
            r = recouvrement(a, b)
            if r > tol: out.append(dict(a=a.nom, b=b.nom, recouvrement=round(r, 3), du=round(max(a.t0, b.t0), 2), au=round(min(a.t1, b.t1), 2), boite_a=[int(v) for v in a.boite], boite_b=[int(v) for v in b.boite]))
    return sorted(out, key=lambda c: -c["recouvrement"])

def rapport(items, cf):
    return dict(tol=TOL, n_items=len(items), n_conflits=len(cf), conflits=cf, items=[dict(nom=i.nom, t0=round(i.t0, 2), t1=round(i.t1, 2), boite=[int(v) for v in i.boite]) for i in items])

def afficher(r, max_lignes=60):
    print(f"chevauchements : {r['n_conflits']} couple(s) en conflit (> {int(100 * r['tol'])} % du plus petit) sur {r['n_items']} éléments")
    for c in r["conflits"][:max_lignes]: print(f"  {c['recouvrement'] * 100:5.1f} %  {c['du']:6.2f}→{c['au']:6.2f} s  {c['a']}  ×  {c['b']}")
    if len(r["conflits"]) > max_lignes: print(f"  … {len(r['conflits']) - max_lignes} autres")

def charger(chemin):
    r = json.load(open(chemin)); return r.get("chevauchements", r)

def instants(r, pas=.3):
    """un instant par période où ≥ 2 éléments sont visibles ensemble : milieu de chaque intervalle commun, dédoublonné (< `pas` s)"""
    its = r["items"]; ts = []
    for i in range(len(its)):
        for j in range(i + 1, len(its)):
            a, b = max(its[i]["t0"], its[j]["t0"]), min(its[i]["t1"], its[j]["t1"])
            if b - a > T_MIN: ts.append((a + b) / 2)
    out = []
    for t in sorted(ts):
        if not out or t - out[-1] >= pas: out.append(t)
    return out

def planche(rapport_json, video, prefixe, par=10):
    import subprocess
    from PIL import Image, ImageDraw
    r = charger(rapport_json); ts = instants(r); tuiles = []
    for t in ts:
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={VW}:{VH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        if len(b) < VW * VH * 3: continue
        im = Image.fromarray(np.frombuffer(b, np.uint8).reshape(VH, VW, 3)).resize((324, 576)); ImageDraw.Draw(im).text((6, 6), f"{t:.2f}s", fill=(255, 255, 0)); tuiles.append(im)
    for k in range(0, len(tuiles), par):
        lot = tuiles[k:k + par]; col = 5; lig = (len(lot) + col - 1) // col; S = Image.new("RGB", (col * 330, lig * 582), "black")
        for i, t in enumerate(lot): S.paste(t, ((i % col) * 330, (i // col) * 582))
        S.save(f"{prefixe}_{k // par + 1}.png"); print(f"{prefixe}_{k // par + 1}.png")
    print(len(tuiles), "instants :", [round(t, 2) for t in ts])

if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "planche": planche(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 10)
    elif len(sys.argv) > 1: afficher(charger(sys.argv[1]))
    else: print(__doc__)
