"""Calque « doodle » rouge fait main (inspiré de Tiakola « AF1 Nouvo ») : texte gribouillé qui s'écrit, soulignements, flèches, éclairs. Sans IA, sans réseau.
Un élément = un patch d'encre (float 0-1) + une carte d'ordre (instant d'apparition de chaque pixel) → le tracé se révèle mot par mot, ou le long d'un chemin.
À chaque image dessinée (12,5 par seconde) le patch est déformé par un champ lisse aléatoire : le trait « bout » comme un dessin refait à la main.
    el = texte(mots, temps_des_mots, fin, taille, angle, souligne=i, fleche=(dx,dy), eclair=True)   # patch prêt
    layer = Calque(W, H); layer.ajouter(el, x, y); out = layer.composer(img_bgr, t)                 # t = seconde dans l'extrait"""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from skimage.morphology import skeletonize
ROUGE = (10, 45, 255)                                    # BGR : rouge-orangé vif (255, 45, 10)
POLICE = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
MARGE = 190                                              # marge du patch autour du texte (place pour flèche / éclair)
def _champ(rng, h, w, amp, pas=60):
    ny, nx = max(2, h // pas + 2), max(2, w // pas + 2)
    d = cv2.resize(rng.normal(0, amp, (ny, nx, 2)).astype(np.float32), (w, h), interpolation=cv2.INTER_CUBIC)
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)); return gx + d[..., 0], gy + d[..., 1]
def _trait(ink, ordre, pts, t0, t1, ep, rng):
    """trace une polyligne d'épaisseur irrégulière ; ordre = t0 → t1 le long du chemin"""
    pts = np.asarray(pts, np.float32); seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); cum = np.concatenate([[0], np.cumsum(seg)]); L = max(cum[-1], 1)
    for i in range(len(pts) - 1):
        m = np.zeros(ink.shape, np.uint8); cv2.line(m, tuple(int(v) for v in pts[i]), tuple(int(v) for v in pts[i + 1]), 255, int(max(2, ep * rng.uniform(.75, 1.25))), cv2.LINE_AA)
        a = m > 0; ink[a] = np.maximum(ink[a], m[a] / 255.); ordre[a] = np.minimum(ordre[a], t0 + (t1 - t0) * (cum[i] + seg[i] * .5) / L)
def _ondule(p0, p1, rng, n=14, amp=7):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); u = (p1 - p0); L = np.linalg.norm(u) + 1e-6; nrm = np.array([-u[1], u[0]]) / L
    return [p0 + u * k / n + nrm * rng.normal(0, amp * .5) + nrm * amp * .6 * np.sin(k * 1.7) for k in range(n + 1)]
def _eclair(x, y, taille, ang, rng):
    pts = [(0, 0), (.35, .25), (.12, .38), (.55, .7), (.3, .78), (.75, 1.15)]
    c, s = np.cos(ang), np.sin(ang); return [(x + taille * (px * c - py * s), y + taille * (px * s + py * c)) for px, py in pts]
def texte(mots, tm, fin, taille=130, angle=0., souligne=None, fleche=None, eclair=False, graine=1, max_car=16, police=POLICE, larg_max=960, trace="squelette", ev=1.0, vit=1.0, eclair_cote="d"):
    """mots : liste de str ; tm : instant (s) d'apparition de chaque mot ; fin : instant où tout s'efface.
    souligne : indice du mot à souligner ; fleche : (dx, dy) en px depuis le bord du texte ; eclair : petit éclair près du mot clé.
    eclair_cote : "d" (à droite du dernier mot de la 1re ligne) ou "g" (à gauche du 1er mot) ; sert à éviter un chevauchement.
    Retourne dict(ink, ordre, fin, cx, cy, w, h, parties) : patch tourné de `angle` degrés (sens horaire à l'écran) ;
    `parties` = [{nom, t0, x, y, ink}] (mots+soulignement / éclair / flèche, masques recadrés dans le repère du patch) pour le contrôle des chevauchements."""
    rng = np.random.RandomState(graine); mots_u = [m.upper() for m in mots]
    while True:                                           # la plus grande taille ≤ `taille` dont le texte tient dans larg_max px
        F = ImageFont.truetype(police, taille); lignes, cur = [], []
        for i, m in enumerate(mots_u):                    # retour à la ligne
            if cur and sum(len(mots_u[j]) + 1 for j in cur) + len(m) > max_car: lignes.append(cur); cur = []
            cur.append(i)
        lignes.append(cur); boite = {}; y = MARGE; larg = 0
        haut = int(taille * 1.12 * ev); gap = int(taille * .28)
        for ln in lignes:                                 # mise en page : positions x de chaque mot
            x = MARGE
            for i in ln:
                w = int(F.getlength(mots_u[i])); boite[i] = (x, y, w, haut); x += w + gap
            larg = max(larg, x - gap - MARGE); y += haut
        if larg <= larg_max or taille <= 60: break
        taille = int(taille * .92)
    Wp, Hp = larg + 2 * MARGE, y - 0 + MARGE
    ink = np.zeros((Hp, Wp), np.float32); ordre = np.full((Hp, Wp), np.inf, np.float32)
    ep = max(7, int(taille * .085))
    for i, m in enumerate(mots_u):
        x, y0, w, h = boite[i]; im = Image.new("L", (w + 20, int(taille * 1.12) + 20), 0); ImageDraw.Draw(im).text((10, 0), m, font=F, fill=255)
        if ev != 1.0: im = im.resize((w + 20, h + 20), Image.BICUBIC)            # lettres étirées en hauteur (feutre « haut et étroit » de la référence)
        if trace == "plein": sk = (np.array(im) > 90).astype(np.uint8)             # glyphe entier (polices déjà épaisses : feutre gras)
        else:
            sk = skeletonize(np.array(im) > 90).astype(np.uint8)                   # fil de 1 px : écriture au feutre, une seule ligne
            sk = cv2.dilate(sk, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ep, ep)))
        pm = cv2.GaussianBlur(sk.astype(np.float32), (0, 0), .9)
        xs = np.arange(sk.shape[1], dtype=np.float32)[None, :] / max(w, 1)         # 0 → 1 le long du mot (gauche → droite)
        d = (tm[i + 1] if i + 1 < len(tm) else tm[i] + .5) - tm[i]; d = float(np.clip(d * .9, .18, .6)) / vit              # vit > 1 : le mot s'écrit plus vite (chanteur rapide)
        o = tm[i] + d * np.clip(xs, 0, 1) + rng.normal(0, .015, sk.shape).astype(np.float32)
        ys, xs0 = max(y0 - 10, 0), x - 10; hh, ww = sk.shape; sl = (slice(ys, ys + hh), slice(xs0, xs0 + ww))
        a = pm > ink[sl][:hh, :ww] if False else pm > 0.25
        sub_ink = ink[sl]; sub_o = ordre[sl]; hh2, ww2 = sub_ink.shape; a = a[:hh2, :ww2]
        sub_ink[a] = np.maximum(sub_ink[a], pm[:hh2, :ww2][a]); sub_o[a] = o[:hh2, :ww2][a]
    if souligne is not None:                              # double trait ondulé sous le mot clé
        x, y0, w, h = boite[souligne]; t0 = tm[souligne] + .3; yb = y0 + int(haut * .98)
        for k, dy in enumerate((0, int(taille * .1))):
            _trait(ink, ordre, _ondule((x - 8, yb + dy), (x + w + 14, yb + dy + rng.randint(-5, 6)), rng), t0 + k * .12, t0 + .3 + k * .12, ep, rng)
    ink_mots = ink.copy(); decos = []                    # masques séparés : mots+soulignement / éclair / flèche (contrôle des chevauchements)
    def _deco(nom, t0, f):
        ie = np.zeros_like(ink); oe = np.full_like(ordre, np.inf); f(ie, oe); a = ie > 0
        ink[a] = np.maximum(ink[a], ie[a]); ordre[a] = np.minimum(ordre[a], oe[a]); decos.append((nom, t0, ie))
    if eclair:                                            # petit éclair rouge près du mot clé (à droite du dernier mot de la 1re ligne, ou à gauche du 1er)
        ig = lignes[0][-1] if eclair_cote == "d" else lignes[0][0]; x, y0, w, h = boite[ig]
        ex = x + w + 25 if eclair_cote == "d" else x - 25 - taille * 1.1 * .8
        _deco("éclair vers", float(tm[ig]) + .2, lambda ie, oe: _trait(ie, oe, _eclair(ex, max(y0 - 60, 10), taille * 1.1, -.15, rng), tm[ig] + .2, tm[ig] + .38, ep, rng))
    if fleche:                                            # flèche courbe qui part du bord du texte
        dx, dy = fleche; xa = MARGE + larg * (1 if dx > 0 else 0); ya = MARGE + haut * .5
        p0 = np.array([xa, ya]); p1 = p0 + np.array([dx, dy], float); mid = (p0 + p1) / 2 + np.array([-dy, dx], float) * .25
        t = np.linspace(0, 1, 18)[:, None]; courbe = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1
        tf = tm[-1] + .25
        def _fl(ie, oe):
            _trait(ie, oe, courbe, tf, tf + .3, ep, rng)
            u = (p1 - courbe[-4]); u /= np.linalg.norm(u) + 1e-6
            for sg in (-1, 1):
                r = np.array([[np.cos(sg * 2.6), -np.sin(sg * 2.6)], [np.sin(sg * 2.6), np.cos(sg * 2.6)]]); _trait(ie, oe, [p1, p1 + (r @ u) * taille * .3], tf + .3, tf + .4, ep, rng)
        _deco("flèche vers", float(tf), _fl)
    cy_, cx_ = Hp / 2, Wp / 2                             # rotation du patch (encre + ordre)
    M = cv2.getRotationMatrix2D((cx_, cy_), -angle, 1.); ink = cv2.warpAffine(ink, M, (Wp, Hp)); ordre = cv2.warpAffine(ordre, M, (Wp, Hp), flags=cv2.INTER_NEAREST, borderValue=np.inf)
    parties = []
    for nom, t0, m in [("mots", float(tm[0]), ink_mots)] + decos:
        b = cv2.warpAffine(m, M, (Wp, Hp)) > .3; ys, xs = np.nonzero(b)
        if len(ys): parties.append(dict(nom=nom, t0=t0, x=int(xs.min()), y=int(ys.min()), ink=b[ys.min():ys.max() + 1, xs.min():xs.max() + 1]))
    return dict(ink=ink, ordre=ordre, fin=fin, w=Wp, h=Hp, debut=float(tm[0]), graine=graine, tw=larg, th=y - MARGE, parties=parties)
def trait_libre(pts, t0, t1, fin, ep=9, graine=1):
    """chemin libre (éclair, flèche, gribouillis) en coordonnées px ; renvoie un élément à poser avec ajouter(el, x, y)"""
    rng = np.random.RandomState(graine); p = np.asarray(pts, np.float32); mn = p.min(0) - 20; p = p - mn; Wp, Hp = (p.max(0) + 20).astype(int)
    ink = np.zeros((Hp, Wp), np.float32); ordre = np.full((Hp, Wp), np.inf, np.float32); _trait(ink, ordre, p, t0, t1, ep, rng)
    return dict(ink=ink, ordre=ordre, fin=fin, w=Wp, h=Hp, debut=t0, graine=graine, dec=(int(mn[0]), int(mn[1])))
def trait_multi(chemins, t0, dur, fin, ep=9, graine=1):
    """plusieurs chemins tracés l'un après l'autre (couronne, « ! », étoile…) en coordonnées px de la toile ; peut dépasser du cadre (coordonnées négatives ou > largeur)"""
    rng = np.random.RandomState(graine); allp = np.vstack([np.asarray(c, np.float32) for c in chemins]); mn = allp.min(0) - 20; Wp, Hp = (allp.max(0) - mn + 20).astype(int)
    ink = np.zeros((Hp, Wp), np.float32); ordre = np.full((Hp, Wp), np.inf, np.float32); n = len(chemins)
    for k, c in enumerate(chemins): _trait(ink, ordre, np.asarray(c, np.float32) - mn, t0 + dur * k / n, t0 + dur * (k + 1) / n, ep, rng)
    return dict(ink=ink, ordre=ordre, fin=fin, w=Wp, h=Hp, debut=t0, graine=graine, dec=(int(mn[0]), int(mn[1])))
def tampon(type_, x, y, taille, t0, dur=.45, reste=1.3, ep=9, graine=1, ang=0.):
    """petits dessins : couronne, exclam (« ! »), exclam2 (« !! »), etoile, eclair (grand), fleche (vers (dx,dy) = ang en degrés). (x, y) = centre ; taille en px"""
    rng = np.random.RandomState(graine); u = taille
    if type_ == "couronne":
        c = [[(-.55, 0), (-.62, -.62), (-.28, -.28), (0, -.85), (.28, -.28), (.62, -.62), (.55, 0), (-.55, 0)], [(-.5, .12), (.5, .12)]]
    elif type_ in ("exclam", "exclam2"):
        un = lambda dx: [[(dx, -.9), (dx + .05, -.35), (dx + .02, .15)], [(dx - .05, .5), (dx + .07, .45), (dx + .06, .58), (dx - .06, .6), (dx - .05, .5)]]
        c = un(0) if type_ == "exclam" else un(-.28) + un(.28)
    elif type_ == "etoile":
        c = [[(np.sin(a) * .8, -np.cos(a) * .8) for a in np.deg2rad(np.arange(0, 721, 144))]]
    elif type_ == "eclair":
        c = [_eclair(-.4 * taille, -.6 * taille, taille * 1.3, -.2, rng)]; c = [[(px / u, py / u) for px, py in c[0]]]
    else:                                                   # flèche courbe + pointe
        a = np.deg2rad(ang); d = np.array([np.cos(a), np.sin(a)]); n = np.array([-d[1], d[0]]); t = np.linspace(0, 1, 16)[:, None]
        p0, p1 = -d * .9, d * .9; mid = n * .45; cb = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1; tg = p1 - cb[-3]; tg /= np.linalg.norm(tg) + 1e-6
        c = [list(map(tuple, cb)), [tuple(p1 + np.array([[np.cos(s_ * 2.6), -np.sin(s_ * 2.6)], [np.sin(s_ * 2.6), np.cos(s_ * 2.6)]]) @ tg * .35 * -1 * -1) for s_ in (-1,)] and [tuple(p1), tuple(p1 + (np.array([[np.cos(2.6), -np.sin(2.6)], [np.sin(2.6), np.cos(2.6)]]) @ tg) * .38)], [tuple(p1), tuple(p1 + (np.array([[np.cos(-2.6), -np.sin(-2.6)], [np.sin(-2.6), np.cos(-2.6)]]) @ tg) * .38)]]
    ch = [[(x + (px + rng.normal(0, .02)) * u, y + (py + rng.normal(0, .02)) * u) for px, py in p] for p in c]
    return trait_multi(ch, t0, dur, t0 + dur + reste, ep, graine)
class Calque:
    def __init__(s, W, H, couleur=None): s.W, s.H, s.els, s.couleur = W, H, [], (couleur or ROUGE)
    def ajouter(s, el, x, y, nom=None):
        """nom : étiquette pour le rapport de chevauchements. x, y : centre du patch sur la toile (px). Pour trait_libre, x, y = 0, 0 (le décalage est déjà dans el['dec'])"""
        if nom: el["nom"] = nom
        if "dec" in el: s.els.append((el, el["dec"][0], el["dec"][1]))
        else:
            if "tw" in el: x = float(np.clip(x, 50 + el["tw"] / 2, s.W - 50 - el["tw"] / 2))              # le texte reste entièrement dans l'écran
            if "th" in el: y = float(np.clip(y, 60 + el["th"] / 2, s.H - 60 - el["th"] / 2))      # et le texte reste entièrement dans la hauteur
            s.els.append((el, int(x - el["w"] / 2), int(y - el["h"] / 2)))
    def composer(s, img, t, effacer=.18):
        """pose l'encre visible à l'instant t sur img (BGR uint8, copie). Chaque élément bout toutes les 0,08 s."""
        a_tot = np.zeros((s.H, s.W), np.float32)
        for el, x0, y0 in s.els:
            if t < el["debut"] - .02 or t > el["fin"] + effacer: continue
            vis = (el["ordre"] <= t).astype(np.float32); a = el["ink"] * vis
            if t > el["fin"]: a = a * max(0., 1 - (t - el["fin"]) / effacer)               # l'encre s'efface vite à la fin
            h, w = a.shape; rng = np.random.RandomState(el["graine"] * 1000 + int(t * 12.5))
            mx, my = _champ(rng, h, w, 2.4); a = cv2.remap(a, mx, my, cv2.INTER_LINEAR, borderValue=0)
            xa, ya = max(x0, 0), max(y0, 0); xb, yb = min(x0 + w, s.W), min(y0 + h, s.H)
            if xb <= xa or yb <= ya: continue
            a_tot[ya:yb, xa:xb] = np.maximum(a_tot[ya:yb, xa:xb], a[ya - y0:yb - y0, xa - x0:xb - x0])
        if not a_tot.any(): return img
        al = np.clip(a_tot * 1.4, 0, 1)[..., None]; out = img.astype(np.float32) * (1 - al) + np.array(s.couleur, np.float32) * al
        return out.astype(np.uint8)
