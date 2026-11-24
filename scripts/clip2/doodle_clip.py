"""Clip « dessin + doodles rouges + écho » (RECETTE §7 quater). Autonome : ne passe pas par compose.py (qui travaille en 960×540 pixelisé).
python doodle_clip.py scan   <work_dir>                       → liste les coupes de plans (secondes) et écrit <work_dir>/coupes.png (planche) pour choisir les cadrages
python doodle_clip.py rendre <work_dir> <config.json> <sortie.mp4> [--max] [--de s --a s]
python doodle_clip.py mesurer <work_dir> <config.json> <prefixe>     → bulles, zones et chevauchements (chevauche.py), sans encoder ; écrit <prefixe>.rapport.json
config.json : {"rows":[y0,y1] bandes noires de la source à retirer, "crop_w":1080, "cx":[centre x (px source) par plan, dernier répété],
  "styles":["aplats","peinture"] (alternés d'un plan à l'autre), "subs":"chemin subs.json", "ancres":[[x,y,angle],…] (positions successives des sous-titres),
  "taille":150, "echo":[{"at":s,"dur_s":s}] + "echo_auto":seuil de mouvement (0 = désactivé), "doodles":[{"type":"eclair|fleche|trait","at":s,"dur_s":s,"pts":[[x,y],…]}]}
subs.json : liste de {"words","t","start","end", + facultatifs "souligne":indice, "fleche":[dx,dy], "eclair":true}. Sortie : 1080×1920, 25 i/s, audio de clip.mp4 (inchangé).
Une image dessinée sur deux (animation « sur les doubles »), le trait des doodles bout à chaque image dessinée."""
import sys, os, json, subprocess, numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
VW, VH, FPS = 1080, 1920, 25
import zones as ZN, chevauche as CH                                          # zones recouvertes par l'interface TikTok (haut, icônes à droite, description, promotion)
def source(wd, a=0., d=None):
    c = ["ffmpeg", "-v", "error", "-ss", str(a)] + (["-t", str(d)] if d else []) + ["-i", f"{wd}/clip.mp4", "-vf", f"fps={FPS},scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(c, stdout=subprocess.PIPE); n = 1920 * 1080 * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(1080, 1920, 3)
def coupes(wd, rows, seuil=26., mini=10):
    """indices d'images où le plan change (écart moyen en niveaux de gris sur vignettes) ; `mini` images au moins entre deux coupes"""
    out, prev, last = [0], None, 0
    for i, f in enumerate(source(wd)):
        g = cv2.resize(cv2.cvtColor(f[rows[0]:rows[1]], cv2.COLOR_BGR2GRAY), (96, 40)).astype(np.float32)
        if prev is not None and np.abs(g - prev).mean() > seuil * .55 and i - last >= mini: out.append(i); last = i
        prev = g
    return out, i + 1
def centres(wd, rows, cp, nfr, cw=1080):
    """cadrage auto : par plan, abscisse (px source) du pic d'énergie de contours (lissé) ≈ le sujet ; bornée pour que la fenêtre reste dans l'image"""
    prof = [np.zeros(1920, np.float32) for _ in cp]; k = 0
    for i, f in enumerate(source(wd)):
        while k + 1 < len(cp) and i >= cp[k + 1]: k += 1
        if i % 4: continue
        g = cv2.GaussianBlur(cv2.cvtColor(f[rows[0]:rows[1]], cv2.COLOR_BGR2GRAY), (0, 0), 2).astype(np.float32)
        e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)); prof[k] += e[int((rows[1] - rows[0]) * .1):int((rows[1] - rows[0]) * .75)].sum(0)
    out = []
    for p in prof:
        p = cv2.GaussianBlur(p.reshape(1, -1), (0, 0), 160).ravel(); p = p * (1 - .25 * np.abs(np.arange(1920) - 960) / 960)      # léger biais vers le centre
        out.append(int(np.clip(np.argmax(p), cw // 2, 1920 - cw // 2)))
    return out
def scan(wd, rows=(140, 940)):
    CF = dict(rows=list(rows)); cp, n = coupes(wd, CF["rows"]); print("coupes (s) :", [round(c / FPS, 2) for c in cp], "| images :", n)
    cxs = centres(wd, CF["rows"], cp, n); print("cx auto :", cxs); json.dump(cxs, open(f"{wd}/cx_auto.json", "w")); tuiles = []
    for k, c in enumerate(cp):
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", str((c + 3) / FPS), "-i", f"{wd}/clip.mp4", "-frames:v", "1", "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        if len(b) < 1920 * 1080 * 3: continue
        f = np.frombuffer(b, np.uint8).reshape(1080, 1920, 3)[CF["rows"][0]:CF["rows"][1]]; f = cv2.resize(f, (480, 200)); cv2.putText(f, f"{k}: {c / FPS:.1f}s", (6, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        xa, xb = int((cxs[k] - 540) / 4), int((cxs[k] + 540) / 4); cv2.rectangle(f, (xa, 1), (xb, 198), (255, 255, 0), 2); tuiles.append(f)       # cadre cyan = fenêtre 1080 px retenue
    while len(tuiles) % 4: tuiles.append(np.zeros_like(tuiles[0]))
    cv2.imwrite(f"{wd}/coupes.png", np.vstack([np.hstack(tuiles[i:i + 4]) for i in range(0, len(tuiles), 4)])); print(f"{wd}/coupes.png")
def decouper(subs, max_mots=4):
    """vers → bulles courtes de ≤ max_mots mots (coupes de préférence après une virgule) ; chaque bulle s'efface quand la suivante commence"""
    out = []
    for s in subs:
        w, t = s["words"], s["t"]; n = len(w); k = -(-n // max_mots); cuts = []
        for j in range(1, k):                                   # coupes équilibrées, ramenées à une virgule voisine (±1 mot) si possible
            c = round(j * n / k)
            for d in (0, -1, 1):
                if 0 < c + d < n and w[c + d - 1].rstrip().endswith((",", ";", ":", "?", "!")): c += d; break
            cuts.append(c)
        bornes = [0] + sorted(set(cuts)) + [n]
        for u in range(len(bornes) - 1):
            i0, i1 = bornes[u], bornes[u + 1]; last = u == len(bornes) - 2
            seg = dict(words=w[i0:i1], t=t[i0:i1], start=t[i0], end=(s["end"] if last else t[i1]), verset=s["start"])
            if s.get("souligne") is not None and i0 <= s["souligne"] < i1: seg["souligne"] = s["souligne"] - i0
            tp = [dict(type=q["type"], mot=q["mot"] - i0) for q in s.get("tampons", []) if i0 <= q["mot"] < i1]
            if tp: seg["tampons"] = tp
            if any(i0 <= q < i1 for q in s.get("kristi", [])): seg["kristi"] = True
            if last and s.get("eclair"): seg["eclair"] = True
            if last and s.get("fleche"): seg["fleche"] = s["fleche"]
            out.append(seg)
    return out
def analyse(wd, rows, cp, cx, cw, ch, r0, ph):
    """une passe sur la source : carte d'énergie de contours (54×96, repère sortie) par image + énergie de mouvement par image"""
    E, mv, prev = [], [], None; plan = 0
    for i, f in enumerate(source(wd)):
        while plan + 1 < len(cp) and i >= cp[plan + 1]: plan += 1
        x0 = int(np.clip(cx[min(plan, len(cx) - 1)] - cw / 2, 0, 1920 - cw)); pic = f[r0:r0 + ch, x0:x0 + cw]
        g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(pic, (108, 192)), cv2.COLOR_BGR2GRAY), (0, 0), 1.2).astype(np.float32)
        e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1)); E.append(cv2.resize(e, (54, 96), interpolation=cv2.INTER_AREA))
        gm = cv2.resize(cv2.cvtColor(f[rows[0]:rows[1]], cv2.COLOR_BGR2GRAY), (96, 40)).astype(np.float32); mv.append(0. if prev is None else float(np.abs(gm - prev).mean())); prev = gm
    return E, np.array(mv)
def echos(cp, nfr, mv, CF):
    """plages d'écho : une par plan au plus, jamais sur deux plans consécutifs, ≥ 3 s d'écart, entièrement dans le plan (durée réduite si le plan est court, ≥ 8 images), ≤ echo_pct des images ; choisies sur le mouvement le plus fort"""
    dur = int(CF.get("echo_dur_s", .5) * FPS); cand = []
    bornes = list(cp) + [nfr]
    for k in range(len(cp)):
        dk = min(dur, bornes[k + 1] - bornes[k] - 11)                  # début ≥ coupe + 8 images ; fin ≤ coupe suivante − 3 images
        if dk < 8: continue
        a, b = bornes[k] + 8, bornes[k + 1] - 3 - dk
        i = a + int(np.argmax(mv[a:b + 1])); cand.append((float(mv[i:i + dk].mean()), k, i, dk))
    cand.sort(reverse=True); pris = []; budget = int(CF.get("echo_pct", .12) * nfr)
    for sc, k, i, dk in cand:
        if sum(q[3] for q in pris) + dk > budget: continue
        if any(abs(k - k2) <= 1 or abs(i - i2) < 3 * FPS for _, k2, i2, _ in pris): continue
        pris.append((sc, k, i, dk))
    for e in CF.get("echo", []):                                      # plages manuelles : acceptées seulement si elles tiennent dans un plan
        i = int(e["at"] * FPS); k = max(j for j in range(len(cp)) if cp[j] <= i); j = i + int(e["dur_s"] * FPS)
        if j <= bornes[k + 1] - 3: pris.append((0., k, i, j - i))
    return sorted((i, i + dk, k) for _, k, i, dk in pris)
EXT_T = {"couronne": (-.62, .62, -.85, .12), "exclam": (-.1, .1, -.9, .6), "exclam2": (-.38, .38, -.9, .6), "etoile": (-.8, .8, -.8, .8)}     # étendue (xmin, xmax, ymin, ymax) du dessin, en unités de taille
TAILLE_T = {"couronne": 210, "exclam": 190, "exclam2": 190, "etoile": 150, "fleche": 170, "eclair": 300}
ORDRE_T = {"couronne": ["hc", "hg", "hd", "bc", "bg", "bd"], "exclam": ["hd", "hg", "bd", "bg", "hc"], "exclam2": ["hd", "hg", "bd", "bg", "hc"], "etoile": ["hg", "hd", "bg", "bd"], "fleche": ["hd", "bd", "hg", "bg"]}
_PROTO = {}
def proto_tampon(DD, ty, u, gr, t0, fin_min):
    """dessin au centre (0, 0) et son item de contrôle : il suffit de le décaler pour tester une position (même graine = même forme)"""
    cle = (ty, round(u, 1), gr, round(t0, 3), round(fin_min, 3))
    if cle not in _PROTO:
        e = tampon_el(DD, ty, 0, 0, u, t0, gr, fin_min); e["nom"] = "tampon " + ty; _PROTO[cle] = CH.items_element(e, *e["dec"])[0]
    return _PROTO[cle]
def tampon_el(DD, ty, cx, cy, u, t0, gr, fin_min):
    e = DD.tampon(ty, cx, cy, u, t0 - .1, dur=.4, graine=gr) if ty == "eclair" else DD.tampon(ty, cx, cy, u, t0, graine=gr, ang=0.) if ty not in ("couronne", "exclam", "exclam2", "etoile") else DD.tampon(ty, cx, cy, u, t0, graine=gr)
    e["fin"] = max(e["fin"], fin_min); return e
def tampons_bulle(seg, k, parts, yc, actifs, DD):
    """choisit la place de chaque dessin d'une bulle : positions candidates autour des mots (haut centre / gauche / droite, bas, côtés), puis taille réduite ×0,8 et ×0,62, sinon supprimé.
    Un dessin ne doit chevaucher ni les mots, ni l'éclair/flèche du vers, ni un élément à l'écran en même temps, et reste dans la zone sûre (sauf l'éclair, collé au bord gauche).
    Renvoie ([{ty, cx, cy, u, t0, gr, fin, nom, boite}], pénalité de score)."""
    res, pen = [], 0.; obst = list(actifs) + list(parts); W = parts[0].boite if parts else (0, 0, 0, 0)
    for q_, tp in enumerate(seg.get("tampons", [])):
        ty = tp["type"]; gr = 500 + k * 7 + q_; t0 = seg["t"][-1] + .1; fin_min = seg["end"] + .3; u0 = TAILLE_T.get(ty, 170); choisi = None
        for si, f in enumerate((1., .8, .62)):
            u = u0 * f; pr = proto_tampon(DD, ty, u, gr, t0, fin_min)
            if ty == "eclair": base = float(np.clip(yc - 80, ZN.HAUT + 165, ZN.BAS - 165)); sp = [(20, float(np.clip(base + d, ZN.HAUT + 165, ZN.BAS - 165))) for d in (0, -160, 160, -320, 320, -480, 480)]      # grand éclair à moitié hors cadre, toujours à GAUCHE
            else:
                xa, xb, ya, yb = EXT_T.get(ty, (-.95, .95, -.3, .4)); g = 20; wx0, wy0, wx1, wy1 = W
                cxs = {"c": (wx0 + wx1) / 2, "g": wx0 - xa * u, "d": wx1 - xb * u}; cys = {"h": wy0 - g - yb * u, "b": wy1 + g - ya * u}
                sp = [(cxs[c[1]], cys[c[0]]) for c in ORDRE_T.get(ty, ORDRE_T["fleche"])] + [(wx1 + g - xa * u, (wy0 + wy1) / 2), (wx0 - g - xb * u, (wy0 + wy1) / 2)]
            for r_, (cx, cy) in enumerate(sp):
                it = pr.decale(cx, cy)
                if ty != "eclair" and ZN.verifier(it.boite, ty): continue
                if CH.penalite([it], obst) > 0: continue
                choisi = dict(ty=ty, cx=float(cx), cy=float(cy), u=u, t0=t0, gr=gr, fin=fin_min, nom=f"tampon {ty} t={seg['start']:.2f}", boite=None if ty == "eclair" else tuple(it.boite)); pen += .04 * r_ + .25 * si; obst.append(it); break
            if choisi: break
        if choisi: res.append(choisi)
        else: pen += 2.
    return res, pen
def placer(seg, k, E, CF, hist_boites, tailles_prec, rng, DD, taille_max, occ=None):
    """choisit taille + emplacement d'une bulle : la plus grande taille qui trouve une zone calme (peu de contours), hors du visage, loin de la bulle précédente.
    occ (liste d'items de chevauche.py, None = ancien comportement) : la bulle, ses dessins et l'éclair/flèche du vers ne recouvrent aucun élément encore à l'écran (voir chevauche.py).
    Renvoie (el, x, y, taille, score, dessins choisis)."""
    a, b = int(seg["start"] * FPS), max(int(seg["end"] * FPS), int(seg["start"] * FPS) + 3)
    m = np.mean([E[j] for j in range(a, min(b, len(E)))] or [E[min(a, len(E) - 1)]], axis=0)
    ref = np.percentile(m, 60) + 1e-3; tailles = [t for t in CF.get("tailles", [taille_max, int(taille_max * .78), int(taille_max * .58)])]
    if seg["end"] - seg["start"] < .9: tailles = tailles[1:] or tailles                 # bulle courte : jamais la plus grande
    essais = []
    for ti, tl in enumerate(tailles):
        kr = bool(seg.get("kristi")) or (CF.get("police2") and rng.rand() < CF.get("p_kristi", .2)); pol = CF["police2"] if kr else CF.get("police", DD.POLICE); ev = CF.get("etire_v2", 1.6) if kr else CF.get("etire_v", 1.0)
        dispo = max(seg["end"] - seg["t"][-1], .1); vit = float(np.clip(.5 / dispo, 1., CF.get("vit_max", 2.6)))        # chanteur rapide : le dernier mot doit finir de s'écrire avant la bulle suivante
        ang = float(rng.choice([-1, 1]) * rng.uniform(3., CF.get("angle_max", 7.)))
        fin = max(seg["end"] + .05, seg["t"][-1] + .35 / vit + .3); gtx = int(rng.randint(1, 10 ** 6))
        mk = lambda cote: DD.texte(seg["words"], [t - .03 for t in seg["t"]], fin, tl if not kr else int(tl * .92), ang, police=pol, trace=CF.get("trace", "squelette"), ev=ev, vit=vit,
                      souligne=seg.get("souligne"), fleche=tuple(seg["fleche"]) if seg.get("fleche") else None, eclair=bool(seg.get("eclair")), graine=gtx, larg_max=CF.get("larg_max", ZN.DROITE - ZN.GAUCHE), eclair_cote=cote)
        variantes = [mk("d")] + ([mk("g")] if occ is not None and seg.get("eclair") else []); cand = []
        top = max([0] + [(0 if tp["type"] == "eclair" else {"couronne": 200, "etoile": 120}.get(tp["type"], 170)) for tp in seg.get("tampons", [])])      # place pour le dessin posé au-dessus du texte
        if occ is not None: top = 0                                                     # nouveau mode : la place des dessins est cherchée tampons_bulle (pénalité si aucune)
        for el in variantes:
            w, h = el["tw"], el["th"]
            if occ is not None:
                t0_, t1_ = el["debut"] - .02, el["fin"] + CH.EFFACER; actifs = [o for o in occ if min(o.t1, t1_) - max(o.t0, t0_) > CH.T_MIN]
                pit = [CH.item_encre(p["nom"], p["ink"], p["x"], p["y"], p["t0"] - .02, t1_) for p in el["parties"]]
            ys = np.arange(ZN.HAUT + top + h / 2, ZN.BAS - h / 2 + 1, 90 if occ is None else 45) if ZN.BAS - h / 2 >= ZN.HAUT + top + h / 2 else [(ZN.HAUT + ZN.BAS) / 2]
            for y in ys:
                xmx = ZN.x_max(y + h / 2)
                for x in sorted({ZN.GAUCHE + w / 2, min(max(540, ZN.GAUCHE + w / 2), xmx - w / 2), xmx - w / 2} | ({ZN.GAUCHE + w / 2 + f_ * max(xmx - ZN.GAUCHE - w, 0) for f_ in (.25, .75)} if occ is not None else set())):
                    bx = (x - w / 2, y - h / 2, x + w / 2, y + h / 2); r = m[int(bx[1] / 20):int(bx[3] / 20) + 1, int(bx[0] / 20):int(bx[2] / 20) + 1]
                    en = float(r.mean()) / ref if r.size else 9.
                    fz = (250, 300, 830, 1150); ov = max(0, min(bx[2], fz[2]) - max(bx[0], fz[0])) * max(0, min(bx[3], fz[3]) - max(bx[1], fz[1])) / (w * h + 1)
                    pv = sum(max(0, min(bx[2], q[2]) - max(bx[0], q[0])) * max(0, min(bx[3], q[3]) - max(bx[1], q[1])) / (w * h + 1) for q in hist_boites[-1:]) + sum(1. for q in hist_boites[-1:] if abs((q[0] + q[2]) / 2 - x) < 120 and abs((q[1] + q[3]) / 2 - y) < 160)
                    pen = 0.; parts = None; trims = []
                    if occ is not None:
                        ox_, oy_ = int(x - el["w"] / 2), int(y - el["h"] / 2); parts = [p.decale(ox_, oy_) for p in pit if p]
                        pen, trims = CH.penalite_ec(parts, actifs); pen += sum(3. for p in parts[1:] if ZN.verifier(p.boite))          # éclair / flèche du vers : hors des autres éléments ET dans la zone sûre
                    cand.append((en + CF.get('poids_visage', 1.0) * ov + 3. * pv + pen, x, y, el, tl, parts, trims))
        cand.sort(key=lambda c: c[0])
        if occ is not None and seg.get("tampons"):                                      # on teste les dessins sur les meilleures positions du texte
            tests = []
            for c in cand[:10]:
                tps, pt = tampons_bulle(seg, k, c[5], c[2], occ, DD); tests.append((c[0] + pt, c, tps))
            sc, c, tps = min(tests, key=lambda q: q[0]); _, x, y, el, tl, _p, trims = c
        else: sc, x, y, el, tl, _p, trims = cand[0]; tps = []
        seuil = CF.get("seuil_zone", 1.6) * (1.15 if ti == 0 else 1.5); essais.append((sc, (el, x, y, tl, sc, tps, trims)))
        if sc <= seuil or ti == len(tailles) - 1:
            if len(tailles_prec) >= 2 and all(t == tailles[-1] for t in tailles_prec[-2:]) and tl == tailles[-1] and ti > 0 and sc <= 1.6: continue    # pas plus de 2 petites de suite
            return min(essais, key=lambda q: q[0])[1] if occ is not None and sc > seuil else (el, x, y, tl, sc, tps, trims)      # nouveau mode, aucune taille satisfaisante : la meilleure des tailles essayées
    return essais[-1][1]
def actifs_de(occ, el):
    t0_, t1_ = el["debut"] - .02, el["fin"] + CH.EFFACER
    return [o for o in occ if min(o.t1, t1_) - max(o.t0, t0_) > CH.T_MIN]
def etalonner(img, g):
    """étalonnage global : expo (diaphragmes, négatif = plus sombre), sat (×), eclat (clarté locale + contraste des tons moyens), nettete (masque flou), pour compenser la compression TikTok"""
    f = img.astype(np.float32) / 255 * (2 ** g.get("expo", 0.))
    if g.get("eclat"): f = f + g["eclat"] * (f - cv2.GaussianBlur(f, (0, 0), 28)) + g["eclat"] * .5 * (f - f * f) * (f - .5) * 2        # clarté + S léger
    hsv = cv2.cvtColor(np.clip(f, 0, 1), cv2.COLOR_BGR2HSV); hsv[..., 1] = np.clip(hsv[..., 1] * g.get("sat", 1.), 0, 1); f = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
    if g.get("nettete"): f = cv2.addWeighted(f, 1 + g["nettete"], cv2.GaussianBlur(f, (0, 0), 1.6), -g["nettete"], 0)
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)
_BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + .5) / 16
def pixeliser(pic, mode, CF):
    """styles « pixel_nb » (noir et blanc, 4 niveaux, trame de Bayer) et « pixel_couleur » (5 niveaux par canal, couleurs relevées) : image réduite à `pixel_larg` px (120 par défaut) puis agrandie SANS lissage.
    Clés de config optionnelles : pixel_larg, pixel_gamma (<1 éclaircit, 0,7 par défaut : sources sombres), pixel_niv_nb (4), pixel_niv_couleur (5). Renvoie la petite image traitée (agrandie par l'appelant en plus proche voisin)."""
    h, w = pic.shape[:2]; W = int(CF.get("pixel_larg", 120)); H = int(round(W * h / w))
    sm = cv2.resize(pic, (W, H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255; g = CF.get("pixel_gamma", .7)
    tr = np.tile(_BAYER, (-(-H // 4), -(-W // 4)))[:H, :W]
    if mode == "pixel_nb":
        n = CF.get("pixel_niv_nb", 4) - 1; y = np.clip(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), 0, 1) ** g; y = np.clip((y - .04) / .62, 0, 1)
        q = np.clip(np.floor(y * n + tr), 0, n) / n; return (np.repeat(q[..., None], 3, axis=2) * 255).astype(np.uint8)
    n = CF.get("pixel_niv_couleur", 5) - 1; f = np.clip(sm, 0, 1) ** g; hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV); hsv[..., 1] = np.clip(hsv[..., 1] * 1.5, 0, 1); hsv[..., 2] = np.clip(hsv[..., 2] * 1.3, 0, 1)
    f = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR); q = np.clip(np.floor(f * n + tr[..., None]), 0, n) / n; return (q * 255).astype(np.uint8)
def hook(L, CF, DD, wd, rows, r0, cw, ch, cx, ph):
    """accroche des 1res secondes : 'mot' = mot-choc géant gribouillé au centre ; 'visage' = tour de visage + couronne + « !! » (visage détecté sur la 1re image)"""
    h = CF.get("hook")
    if not h: return []
    d = CF.get("hook_fin_s", 1.05)
    if h == "mot":
        el = DD.texte([CF.get("hook_mot", "TIAKOLA")], [.05], d, 330, -6, police=CF.get("police", DD.POLICE), trace=CF.get("trace", "squelette"), ev=CF.get("etire_v", 1.), vit=1.4, graine=77, larg_max=ZN.DROITE - ZN.GAUCHE, max_car=40)
        hx_ = min(540., ZN.DROITE - el["tw"] / 2); L.ajouter(el, hx_, 900, nom="hook mot"); L.ajouter(DD.tampon("exclam2", 880, 560, 150, .3, graine=78, reste=.3), 0, 0, nom="hook !!"); L.ajouter(DD.tampon("eclair", 20, 1130, 330, .15, dur=.35, graine=79, reste=.4), 0, 0, nom="hook éclair")
        return [("hook mot", (hx_ - el["tw"] / 2, 900 - el["th"] / 2, hx_ + el["tw"] / 2, 900 + el["th"] / 2)), ("hook !!", (805, 485, 955, 635))]
    else:
        fx, fy, rx, ry = CF.get("hook_visage", [540, 780, 300, 380])          # visage à entourer (px de la toile 1080×1920), relevé sur l'image 0-0,4 s
        rng = np.random.RandomState(9); a = np.linspace(-.4, 2 * np.pi * 1.15, 40); d = min(d, .9); pts = [(fx + rx * (1 + .04 * i / 40) * np.cos(t) + rng.normal(0, 5), fy + ry * (1 + .04 * i / 40) * np.sin(t) + rng.normal(0, 5)) for i, t in enumerate(a)]
        L.ajouter(DD.trait_multi([pts], .05, .3, d, ep=12, graine=80), 0, 0, nom="hook cercle")
        L.ajouter(DD.tampon("couronne", fx, fy - ry - 100, 230, .3, dur=.3, graine=81, reste=.3), 0, 0, nom="hook couronne"); L.ajouter(DD.tampon("exclam2", fx + rx + 90, fy - ry * .3, 190, .4, dur=.25, graine=82, reste=.2), 0, 0, nom="hook !!")
        return [("hook visage couronne", (fx - 115, fy - ry - 215, fx + 115, fy - ry + 15)), ("hook visage !!", (fx + rx - 5, fy - ry * .3 - 95, fx + rx + 185, fy - ry * .3 + 95))]
def rendre(wd, cfp, sortie, maxq=False, de=0., a=None, mesure=False):
    """mesure=True : construit les bulles et dessins, contrôle zones + chevauchements, écrit <sortie>.rapport.json, n'encode rien et n'échoue jamais"""
    CF = json.load(open(cfp)); rows = CF["rows"]; cw = CF.get("crop_w", 1080); ch = CF.get("crop_h", rows[1] - rows[0]); ph = round(ch * VW / cw); ph = VH if abs(ph - VH) <= 3 else ph    # fenêtre source cw×ch → image 1080×ph
    r0 = (rows[0] + rows[1] - ch) // 2                                                  # fenêtre centrée verticalement dans l'image utile
    os.environ["DESSIN_W"], os.environ["DESSIN_H"] = str(cw), str(ch)                  # dessin.py travaille sur la fenêtre découpée
    import dessin as DS, doodle as DD
    cp, nfr = coupes(wd, rows); cx = CF.get("cx", "auto"); cx = centres(wd, rows, cp, nfr, cw) if cx == "auto" else cx; styles = CF.get("styles", ["aplats", "peinture"])
    subs = json.load(open(CF["subs"])); taille = CF.get("taille", 150); rng = np.random.RandomState(CF.get("graine", 5))
    E, mv = analyse(wd, rows, cp, cx, cw, ch, r0, ph)
    segs = decouper(subs, CF.get("max_mots", 4)) if CF.get("max_mots") else subs
    hx = CF.get("couleur", "#FF2D0A").lstrip("#"); L = DD.Calque(VW, VH, (int(hx[4:6], 16), int(hx[2:4], 16), int(hx[0:2], 16))); boites = []; tprec = []; rap = []; occupe = []
    ev = CF.get("evitement", True)                                                      # False = ancien placement (clips validés avant le 04/11/2026) ; le contrôle de chevauchement reste actif
    occupe = hook(L, CF, DD, wd, rows, r0, cw, ch, cx, ph)                              # hook et doodles libres d'abord : les bulles les évitent
    for k, d in enumerate(CF.get("doodles", [])):
        L.ajouter(DD.trait_libre(d["pts"], d["at"], d["at"] + d.get("dur_s", .3), d["at"] + d.get("dur_s", .3) + d.get("reste_s", 1.2), ep=d.get("ep", 11), graine=100 + k), 0, 0, nom=f"doodle {k}")
    occ = CH.items_calque(L) if ev else None
    for k, s in enumerate(segs):                                                        # chaque bulle : texte qui s'écrit, taille et position choisies sur la place libre
        if CF.get("max_mots"):
            el, x, y, tl, sc, tps, trims = placer(s, k, E, CF, boites, tprec, rng, DD, taille, occ)
            L.ajouter(el, x, y, nom=f"texte t={s['start']:.2f}"); w_, h_ = el["tw"], el["th"]; its = CH.items_calque(L, len(L.els) - 1)
            occupe += [(it.nom, it.boite) for it in its[1:]]                           # éclair / flèche du vers : aussi dans la zone sûre
            if occ is not None:
                for src, t1n in trims:                                                  # éléments écourtés pour laisser la place (chevauche.penalite_ec)
                    src['fin'] = t1n - CH.EFFACER
                    for o in occ:
                        if o.src is src: o.t1 = t1n
                occ += its
                for T in tps:                                                           # dessins déjà placés par tampons_bulle (positions sans chevauchement)
                    e2 = tampon_el(DD, T["ty"], T["cx"], T["cy"], T["u"], T["t0"], T["gr"], T["fin"]); L.ajouter(e2, 0, 0, nom=T["nom"]); occ += CH.items_calque(L, len(L.els) - 1)
                    if T["boite"]: occupe.append((T["nom"], T["boite"]))
                for q_ in range(len(s.get("tampons", [])) - len(tps)): print(f"  dessin supprimé (pas de place sans chevauchement) : bulle t={s['start']:.2f}")
            else:
              for q_, tp in enumerate(s.get("tampons", [])):
                t0 = s["t"][-1] + .1; ty = tp["type"]; gr = 500 + k * 7 + q_; xm = ZN.x_max(y + h_ / 2); ex = min(x + w_ / 2 - 40, xm - 100); ey = y - h_ / 2 - 70       # dessin posé sur le coin haut du texte
                if ty == "couronne": e2 = DD.tampon(ty, x, y - h_ / 2 - 90, 210, t0, graine=gr); tb = (x, y - h_ / 2 - 90, 210)
                elif ty in ("exclam", "exclam2"): e2 = DD.tampon(ty, ex, ey, 190, t0, graine=gr); tb = (ex, ey, 190)
                elif ty == "etoile": e2 = DD.tampon(ty, max(x - w_ / 2 - 40, ZN.GAUCHE + 75), y - h_ / 2 - 20, 150, t0, graine=gr); tb = (max(x - w_ / 2 - 40, ZN.GAUCHE + 75), y - h_ / 2 - 20, 150)
                elif ty == "eclair": ey2 = float(np.clip(y - 80, ZN.HAUT + 165, ZN.BAS - 165)); e2 = DD.tampon(ty, 20, ey2, 300, t0 - .1, dur=.4, graine=gr); tb = None          # grand éclair à moitié hors cadre, toujours à GAUCHE (aucune icône de ce côté)
                else: e2 = DD.tampon(ty, ex, ey, 170, t0, graine=gr, ang=0.); tb = (ex, ey, 170)
                if tb: occupe.append((f"tampon {ty} t={s['start']:.1f}", (tb[0] - tb[2] / 2, tb[1] - tb[2] / 2, tb[0] + tb[2] / 2, tb[1] + tb[2] / 2)))
                e2["fin"] = max(e2["fin"], s["end"] + .3); L.ajouter(e2, 0, 0, nom=f"tampon {ty} t={s['start']:.2f}")
            occupe.append((f"texte t={s['start']:.1f}", (x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2)))
            boites.append((x - w_ / 2, y - h_ / 2, x + w_ / 2, y + h_ / 2)); tprec.append(tl); rap.append((round(s["start"], 2), tl, int(x), int(y), round(float(sc), 2)))
        else:
            anc = CF.get("ancres", [[540, 420, -3], [540, 1100, 2]]); x, y, ang = anc[k % len(anc)]; fl = s.get("fleche")
            el = DD.texte(s["words"], [t - .03 for t in s["t"]], s["end"] - .05, taille, ang, police=CF.get("police", DD.POLICE), trace=CF.get("trace", "squelette"), ev=CF.get("etire_v", 1.0), souligne=s.get("souligne"), fleche=tuple(fl) if fl else None, eclair=bool(s.get("eclair")), graine=k + 1)
            L.ajouter(el, x, y, nom=f"texte t={s['start']:.2f}")
    if CF.get("max_mots"): print("bulles :", len(segs), "| tailles", sorted(set(t for _, t, *_ in rap)), "| petites", sum(1 for _, t, *_ in rap if t == min(r[1] for r in rap)))
    pb = [m for n_, b_ in occupe for m in ZN.verifier(b_, n_)]
    if pb and not CF.get("zones_off") and not mesure: sys.exit("ZONES TIKTOK : " + str(len(pb)) + " débordement(s) : " + "; ".join(pb[:8]) + " (zones.py ; \"zones_off\": true pour passer outre)")
    print("zones TikTok : texte et dessins dans la zone sûre" if not pb else f"zones TikTok : {len(pb)} débordement(s) " + ("ignorés (zones_off)" if CF.get("zones_off") else "(mesure) : " + "; ".join(pb[:8])))
    items = CH.items_calque(L); cf = CH.conflits(items); rp = CH.rapport(items, cf); CH.afficher(rp)                # contrôle final : tous les couples simultanés
    if cf and not CF.get("chevauchement_off") and not mesure: sys.exit(f"CHEVAUCHEMENTS : {len(cf)} couple(s) de plus de {int(100 * CH.TOL)} % (chevauche.py ; \"chevauchement_off\": true pour passer outre)")
    if mesure: json.dump(dict(chevauchements=rp, bulles=rap, zones=pb), open(sortie + ".rapport.json", "w"), ensure_ascii=False, indent=1); print(sortie + ".rapport.json"); return rp
    pl = echos(cp, nfr, mv, CF); ech = set(j for a_, b_, _ in pl for j in range(a_, b_)); y0 = (VH - ph) // 2
    print("échos :", [(round(a_ / FPS, 2), round(b_ / FPS, 2), k) for a_, b_, k in pl], f"| {len(ech)} images sur {nfr} = {100 * len(ech) / nfr:.1f} %")
    json.dump(dict(echos=[(a_ / FPS, b_ / FPS, k) for a_, b_, k in pl], cp=[c / FPS for c in cp], bulles=rap, chevauchements=rp), open(sortie + ".rapport.json", "w"))
    enc = ["-c:v", "libx264", "-preset", "veryslow", "-crf", "14", "-profile:v", "high", "-maxrate", "35M", "-bufsize", "70M", "-c:a", "aac", "-b:a", "320k"] if maxq else ["-c:v", "libx264", "-preset", "fast", "-crf", "17", "-c:a", "aac", "-b:a", "192k"]
    o = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-", "-ss", str(de), "-i", f"{wd}/clip.mp4", "-map", "0:v", "-map", "1:a",
                          *(["-t", str(a - de)] if a else []), *enc, "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-shortest", sortie], stdin=subprocess.PIPE)
    plan = 0; last = None; hist = []; n_ech = 0
    for i, f in enumerate(source(wd, de, (a - de) if a else None)):
        i += int(de * FPS)
        while plan + 1 < len(cp) and i >= cp[plan + 1]: plan += 1; hist = []; DS.aplats.__dict__.pop("c", None)     # nouveau plan : l'historique d'écho repart de zéro (aucune copie ne vient du plan précédent)
        brut = styles[plan % len(styles)] == "brut"
        if brut or i % 2 == 0 or last is None:
            x0 = int(np.clip(cx[min(plan, len(cx) - 1)] - cw / 2, 0, 1920 - cw)); pic = np.ascontiguousarray(f[r0:r0 + ch, x0:x0 + cw])
            sty = styles[plan % len(styles)]
            if sty.startswith("pixel"): last = cv2.resize(pixeliser(pic, sty, CF), (VW, ph), interpolation=cv2.INTER_NEAREST)
            else:
                last = pic if brut else getattr(DS, sty)(pic, np.random.RandomState(plan * 7 + 1))
                last = cv2.resize(last, (VW, ph), interpolation=cv2.INTER_CUBIC)
            if not sty.startswith("pixel"):       # pas de netteté ni d'étalonnage sur les styles pixel (halos sur les gros pixels)
                if CF.get("nettete", 0): last = cv2.addWeighted(last, 1 + CF["nettete"], cv2.GaussianBlur(last, (0, 0), 2.2), -CF["nettete"], 0)       # renforcement après agrandissement
                if CF.get("etalonnage"): last = etalonner(last, CF["etalonnage"])
            hist = ([last] + hist)[:14]
        t = i / FPS; img = last
        if i in ech:
            # écho : l'image courante + copies de 3, 6, 9, 12 images plus tôt, chacune un peu plus grande (zoom +3,5 % par copie) → traînée visible même à l'arrêt
            acc = last.astype(np.float32); tot = 1.; h_, w_ = last.shape[:2]
            for k, wgt in ((3, .8), (6, .6), (9, .45), (12, .3)):
                if len(hist) > k:
                    z = 1 + CF.get("echo_zoom", .035) * (k // 3); M = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), 0, z)
                    acc += cv2.warpAffine(hist[k], M, (w_, h_), borderMode=cv2.BORDER_REPLICATE).astype(np.float32) * wgt; tot += wgt
            img = (acc / tot).astype(np.uint8); n_ech += 1
        can = np.zeros((VH, VW, 3), np.uint8); can[y0:y0 + ph, :] = img
        o.stdin.write(L.composer(can, t).tobytes())
    o.stdin.close(); o.wait(); print("ok", sortie, f"| plans {len(cp)} | images avec écho {n_ech}")
if __name__ == "__main__":
    a = sys.argv[1:]; opt = {a[i]: a[i + 1] for i in range(len(a) - 1) if a[i].startswith("--") and a[i] != "--max"}
    if a[0] == "scan": scan(a[1], json.loads(a[2]) if len(a) > 2 else (140, 940))
    elif a[0] == "mesurer": rendre(a[1], a[2], a[3], mesure=True)               # mesurer <work> <config> <prefixe> : zones + chevauchements sans encoder
    else: rendre(a[1], a[2], a[3], "--max" in a, float(opt.get("--de", 0)), float(opt["--a"]) if "--a" in opt else None)
