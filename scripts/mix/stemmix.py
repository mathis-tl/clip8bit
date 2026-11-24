"""Vidéo « piste par piste » : l'audio d'un titre recomposé par pistes (demucs 4 stems) + clip en fond (net, non pixélisé) + 4 barres verticales (voix, batterie, basse, instru).
Une barre active oscille avec le niveau réel de sa piste ; une piste coupée fait retomber sa barre. Format 1080×1920, 30 i/s, texte et barres dans la zone sûre TikTok.
Usage : stemmix.py --stems <dossier 4 stems> --audio <titre.wav> --video <clip.mp4> --debut_mesure N --sortie <dossier> --nom <nom> [--titre "COEUR DE PIRATE"]"""
import sys, os, json, argparse, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchainer import grille, temps_fort, charger, lisse, SR
HAUT, BAS, GAUCHE, DROITE = 240, 1290, 60, 910
FPS, W, H = 30, 1080, 1920
# planning par blocs de 2 mesures : V voix, D batterie, B basse, O instru
# planning (stems, nombre de mesures) : la voix ne coupe jamais ; on part du tout, on isole la voix, on rajoute une piste à la fois, on mélange, on finit sur le tout (boucle)
PLAN = [("VDBO", 2), ("V", 4), ("VD", 2), ("VB", 2), ("VO", 2), ("VDB", 2), ("VBO", 2), ("VDO", 2), ("VDBO", 4)]
NOMS = {"V": "VOIX", "D": "BATT.", "B": "BASSE", "O": "INSTRU"}; ORDRE = ["V", "D", "B", "O"]
COUL = {"V": (255, 214, 10), "D": (255, 70, 60), "B": (60, 140, 255), "O": (60, 220, 130)}
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "fonts", "PressStart2P-Regular.ttf")


CX = [170, 360, 550, 740]; BASE, TOP, MAXB = 1200, 720, 16
LABEL_Y = {n: 1222 for n in ["blocs", "fines", "spectre", "faders", "capsules", "colonnes", "points"]}; LABEL_Y.update({"cercles": 1110, "ondes": 1222})

def rr(d, box, r, fill=None, outline=None, width=1): d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def st_blocs(d, c, bx):
    bh, pitch = 22, 30
    for j, k in enumerate(ORDRE):
        x0 = CX[j] - 70; nl = int(round(c["lit"][k])); col = COUL[k]
        for b in range(MAXB):
            y1 = BASE - b * pitch; y0 = y1 - bh
            if b < nl: d.rectangle((x0, y0, x0 + 140, y1), fill=col + (235,))
            elif b == 0: d.rectangle((x0, y0, x0 + 140, y1), fill=(255, 255, 255, 70))
            else: d.rectangle((x0, y0, x0 + 140, y1), outline=(255, 255, 255, 60), width=2)
        if bx is not None: bx.append((k, (x0, BASE - MAXB * pitch, x0 + 140, BASE)))

def st_fines(d, c, bx):
    for j, k in enumerate(ORDRE):
        sm = c["lit"][k] / MAXB; col = COUL[k]; x0 = CX[j] - 70; on = c["on"][k]
        for b in range(9):
            env = .55 + .45 * np.cos((b - 4) / 4 * np.pi / 2); wob = .65 + .35 * abs(np.sin(c["t"] * 6.5 + j * 1.7 + b * .9)); h = max(8, 470 * sm * env * wob) if on or sm > .02 else 8
            xx = x0 + b * 16; rr(d, (xx, BASE - h, xx + 11, BASE), 5, fill=col + (235,) if h > 9 else (255, 255, 255, 80))
        if bx is not None: bx.append((k, (x0, BASE - 470, x0 + 140, BASE)))

def st_cercles(d, c, bx):
    cy = 940
    for j, k in enumerate(ORDRE):
        sm = c["lit"][k] / MAXB; col = COUL[k]; cx = CX[j]; r = 26 + 60 * sm
        if sm > .02:
            for q, al in ((1.5, 40), (1.25, 80)): d.ellipse((cx - r * q, cy - r * q, cx + r * q, cy + r * q), fill=col + (al,))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col + (240,))
        else: d.ellipse((cx - 26, cy - 26, cx + 26, cy + 26), outline=(255, 255, 255, 110), width=4)
        if bx is not None: bx.append((k, (cx - 90, cy - 90, cx + 90, cy + 90)))

def st_ondes(d, c, bx):
    ys = [790, 915, 1040, 1165]
    for j, k in enumerate(ORDRE):
        w = c["wave"][k]; yc = ys[j]; col = COUL[k]; amp = 58
        pts = [(100 + q * (770 / 63), yc - float(w[q]) * amp) for q in range(64)]
        if np.abs(w).max() > .01: d.line(pts, fill=col + (255,), width=7, joint="curve")
        else: d.line([(100, yc), (870, yc)], fill=(255, 255, 255, 110), width=4)
        if bx is not None: bx.append((k, (100, yc - amp, 870, yc + amp)))

def st_faders(d, c, bx):
    for j, k in enumerate(ORDRE):
        cx = CX[j]; col = COUL[k]; pos = min(1.0, c["mk"][k]); sm = c["lit"][k] / MAXB
        d.rounded_rectangle((cx - 7, TOP, cx + 7, BASE), radius=7, fill=(255, 255, 255, 60))
        ky = BASE - 44 - (BASE - TOP - 44) * (.12 + .88 * pos) + 22 * (1 - pos) * 0
        d.rounded_rectangle((cx - 7, ky + 22, cx + 7, BASE), radius=7, fill=col + (200,))
        rr(d, (cx - 52, ky, cx + 52, ky + 44), 10, fill=(240, 240, 240, 255), outline=col + (255,), width=5); d.rectangle((cx - 40, ky + 19, cx + 40, ky + 25), fill=col + (255,))
        nl = int(round(sm * 14))
        for b in range(14):
            yy = BASE - b * 33; d.rectangle((cx + 64, yy - 24, cx + 76, yy), fill=col + (235,) if b < nl else (255, 255, 255, 50))
        if bx is not None: bx.append((k, (cx - 52, TOP, cx + 76, BASE)))

def st_spectre(d, c, bx):
    for j, k in enumerate(ORDRE):
        x0 = CX[j] - 70; col = COUL[k]; sp = c["spec"][k]
        for b in range(8):
            v = float(sp[b + 1]); h = max(8, 470 * v ** 1.2); xx = x0 + b * 18
            rr(d, (xx, BASE - h, xx + 13, BASE), 4, fill=col + (235,) if v > .03 else (255, 255, 255, 80))
        if bx is not None: bx.append((k, (x0, BASE - 470, x0 + 140, BASE)))

def st_capsules(d, c, bx):
    for j, k in enumerate(ORDRE):
        cx = CX[j]; col = COUL[k]; sm = c["lit"][k] / MAXB; x0, x1 = cx - 62, cx + 62; h = BASE - TOP
        mk = Image.new("L", (124, h), 0); ImageDraw.Draw(mk).rounded_rectangle((0, 0, 123, h - 1), radius=62, fill=255)
        lq = Image.new("L", (124, h), 0); level = h * (.06 + .94 * sm) if sm > .02 else 0; ty = h - level
        pts = [(q, ty + 7 * np.sin(c["t"] * 5 + q / 18 + j)) for q in range(0, 125, 4)] + [(124, h), (0, h)]
        if level > 0: ImageDraw.Draw(lq).polygon(pts, fill=255)
        fill = Image.new("RGBA", (124, h), col + (225,)); a_ = Image.fromarray((np.array(lq, np.float32) * np.array(mk, np.float32) / 255).astype(np.uint8)); fill.putalpha(a_)
        c["ov"].alpha_composite(fill, (x0, TOP)); rr(d, (x0, TOP, x1, BASE), 62, outline=(255, 255, 255, 150) if sm > .02 else (255, 255, 255, 90), width=4)
        if bx is not None: bx.append((k, (x0, TOP, x1, BASE)))

def st_colonnes(d, c, bx):
    for j, k in enumerate(ORDRE):
        cx = CX[j]; col = COUL[k]; sm = c["lit"][k] / MAXB; h = 20 + 740 * sm if sm > .02 else 6; x0 = cx - 80
        for q, al in ((18, 35), (9, 60)): d.rectangle((x0 - q, BASE - h - q, x0 + 160 + q, BASE), fill=col + (al,))
        d.rectangle((x0, BASE - h, x0 + 160, BASE), fill=col + (150,)); d.rectangle((x0, BASE - h, x0 + 160, BASE - h + 10), fill=col + (255,))
        if bx is not None: bx.append((k, (x0 - 18, BASE - 760 - 18, x0 + 178, BASE)))

def st_points(d, c, bx):
    pitch, r = 28, 10; env = [.7, .9, 1., .9, .7]
    for j, k in enumerate(ORDRE):
        x0 = CX[j] - 2 * pitch; col = COUL[k]; sm = c["lit"][k] / MAXB; on = c["on"][k]
        for q in range(5):
            nl = int(round(sm * 17 * env[q] * (.85 + .15 * np.sin(c["t"] * 9 + q * 1.3 + j)))) if sm > .02 else 0
            for b in range(17):
                cxq, cyq = x0 + q * pitch, BASE - b * pitch
                if b < nl: d.ellipse((cxq - r, cyq - r, cxq + r, cyq + r), fill=col + (240,))
                else: d.ellipse((cxq - 3, cyq - 3, cxq + 3, cyq + 3), fill=(255, 255, 255, 70))
        if bx is not None: bx.append((k, (x0 - r, BASE - 16 * pitch - r, x0 + 4 * pitch + r, BASE + r)))

STYLES = {"blocs": st_blocs, "fines": st_fines, "cercles": st_cercles, "ondes": st_ondes, "faders": st_faders, "spectre": st_spectre, "capsules": st_capsules, "colonnes": st_colonnes, "points": st_points}

def lisse3(x): return x * x * (3 - 2 * x)

def main(a):
    global PLAN
    if a.plan: PLAN = [(b.split(":")[0], int(b.split(":")[1])) for b in a.plan.split(",")]
    boostblk = ["X" in blk for blk, _ in PLAN]; PLAN = [(blk.replace("X", "B"), nb) for blk, nb in PLAN]   # « X » = basse jouée ET boostée (--boost_db)
    g = grille(a.audio); p = g["p"]; bar = 4 * p; t0 = temps_fort(g, a.debut_mesure); nbar = sum(b for _, b in PLAN); dur = nbar * bar
    names = {"V": "vocals", "D": "drums", "B": "bass", "O": "other"}; st = {k: charger(f"{a.stems}/{v}.wav") for k, v in names.items()}
    i0, n = int(t0 * SR), int(dur * SR); seg = {k: x[:, i0:i0 + n] for k, x in st.items()}; n = min(s.shape[1] for s in seg.values()); t = np.arange(n) / SR
    # blocs : début en mesures de chaque bloc ; masque par piste avec fondus d'un temps (entrée : finie sur le temps fort ; sortie : commence sur le temps fort)
    deb = np.cumsum([0] + [b for _, b in PLAN]); mask = {k: np.zeros(n) for k in ORDRE}; rampe = a.fondu * p
    for k in ORDRE:
        etat = [k in blk for blk, _ in PLAN]
        for j, (blk, nb) in enumerate(PLAN):
            a0, a1 = deb[j] * bar, deb[j + 1] * bar; m_ = (t >= a0) & (t < a1)
            if etat[j]: mask[k][m_] = 1
        for j in range(1, len(PLAN)):
            tb = deb[j] * bar; prev, cur = etat[j - 1], etat[j]
            if cur and not prev: w = (t >= tb - rampe) & (t < tb); mask[k][w] = lisse3((t[w] - (tb - rampe)) / rampe)       # entrée : monte pendant le temps qui précède
            if prev and not cur: w = (t >= tb) & (t < tb + rampe); mask[k][w] = 1 - lisse3((t[w] - tb) / rampe)            # sortie : descend pendant le temps qui suit
    segm = dict(seg); a.boost_fen = []
    if a.boost_db > 0 and any(boostblk):
        from scipy.signal import butter, sosfiltfilt
        bc = np.zeros(n)
        for j in range(len(PLAN)):
            if boostblk[j]: bc[(t >= deb[j] * bar) & (t < deb[j + 1] * bar)] = 1; a.boost_fen.append((float(deb[j] * bar), float(deb[j + 1] * bar)))
        for j in range(1, len(PLAN)):
            tb = deb[j] * bar
            if boostblk[j] and not boostblk[j - 1]: w = (t >= tb - rampe) & (t < tb); bc[w] = lisse3((t[w] - (tb - rampe)) / rampe)
            if boostblk[j - 1] and not boostblk[j]: w = (t >= tb) & (t < tb + rampe); bc[w] = 1 - lisse3((t[w] - tb) / rampe)
        g = 10 ** (a.boost_db / 20); lp = sosfiltfilt(butter(4, 140, btype="low", fs=SR, output="sos"), seg["B"], axis=1)
        bb = seg["B"] + bc[None, :] * (g - 1) * lp; bs = np.tanh(1.6 * bb) / 1.6; segm["B"] = bc[None, :] * bs + (1 - bc[None, :]) * bb
    mix = sum(segm[k] * mask[k][None, :] for k in ORDRE); full = sum(segm[k] for k in ORDRE)
    # compensation de moitié de la chute de niveau, 4 dB max, lissée
    blk_n = int(.1 * SR); m = n // blk_n * blk_n
    rm = lambda x: 20 * np.log10(np.sqrt((x[:, :m].mean(axis=0).reshape(-1, blk_n) ** 2).mean(axis=1)) + 1e-9)
    drop = np.clip(rm(full) - rm(mix), 0, 12); gdb = np.convolve(np.clip(.5 * drop, 0, 4), np.ones(9) / 9, mode="same")
    gain = np.interp(np.arange(n) / SR, (np.arange(len(gdb)) + .5) * .1, gdb); mix = mix * (10 ** (gain / 20))[None, :]
    if a.boost_db > 0:                                     # limiteur à fenêtre de 50 ms (crête visée 0,85), gain lissé, pour que le boost ne sature pas
        bl = int(.05 * SR); mm = n // bl * bl; pk = np.abs(mix[:, :mm]).max(axis=0).reshape(-1, bl).max(axis=1); gl = np.minimum(1, .85 / (pk + 1e-9))
        from scipy.ndimage import minimum_filter1d, uniform_filter1d
        gl = uniform_filter1d(minimum_filter1d(gl, 9), 5); mix[:, :mm] *= np.repeat(gl, bl)[None, :]
    cr = float(np.abs(mix).max()); mix = np.tanh(mix / .85) * .85 if cr > .9 else mix; mix *= 10 ** (-1.5 / 20)
    mix[:, :int(.01 * SR)] *= np.linspace(0, 1, int(.01 * SR)); mix[:, -int(.03 * SR):] *= np.linspace(1, 0, int(.03 * SR))
    os.makedirs(a.sortie, exist_ok=True); wav = f"{a.sortie}/{a.nom}.wav"
    import soundfile as sf; sf.write(wav, mix.T, SR, subtype="PCM_16")
    # niveaux par image pour les barres
    nf = int((min(n / SR, a.max_s) if a.max_s else n / SR) * FPS); lv = {}; NB = 14
    ws = int(SR / FPS); win = np.hanning(2048); edges = np.unique(np.geomspace(2, 1000, NB + 1).astype(int)); wave = {}; spec = {}
    for k in ORDRE:
        x = (seg[k] * mask[k][None, :]).mean(axis=0); fr = np.array([np.sqrt((x[int(i / FPS * SR):int((i + 1) / FPS * SR)] ** 2).mean()) for i in range(nf)]); d = 20 * np.log10(fr + 1e-9)
        xm = seg[k].mean(axis=0); ref = np.percentile(20 * np.log10(np.array([np.sqrt((xm[int(i / FPS * SR):int((i + 1) / FPS * SR)] ** 2).mean()) for i in range(nf)]) + 1e-9), 90)
        lv[k] = np.clip((d - (ref - 22)) / 22, 0, 1)
    for k in ORDRE:
        xm = seg[k].mean(axis=0); xk = xm * mask[k]; ww = np.zeros((nf, 64)); sp = np.zeros((nf, NB)); spr = np.zeros((nf, NB))
        for i in range(nf):
            c = int((i + .5) / FPS * SR); a0 = max(0, min(c - ws // 2, n - ws)); chunk = xk[a0:a0 + ws]; ww[i] = np.interp(np.linspace(0, ws - 1, 64), np.arange(ws), chunk)
            b0 = max(0, min(c - 1024, n - 2048)); mg = np.abs(np.fft.rfft(xk[b0:b0 + 2048] * win)); mu = np.abs(np.fft.rfft(xm[b0:b0 + 2048] * win))
            sp[i] = [mg[edges[q]:max(edges[q] + 1, edges[q + 1])].mean() for q in range(len(edges) - 1)] + [0] * (NB - len(edges) + 1); spr[i] = [mu[edges[q]:max(edges[q] + 1, edges[q + 1])].mean() for q in range(len(edges) - 1)] + [0] * (NB - len(edges) + 1)
        refw = np.percentile(np.abs(xm), 99) + 1e-9; refs = np.percentile(spr, 90, axis=0) + 1e-9
        wave[k] = np.clip(ww / refw, -1, 1); spec[k] = np.clip((20 * np.log10(sp / refs + 1e-6) + 30) / 30, 0, 1)
    if a.ad == "doodle":
        import stemdoodle as SD
        lit = {k: 0.0 for k in ORDRE}; etat = []
        for i in range(nf):                                  # animation des blocs, même logique que le style « blocs »
            for k in ORDRE:
                mk = mask[k][min(int((i + .5) / FPS * SR), n - 1)]
                if mk > .05: target = max(2.0, lv[k][i] * MAXB * min(1.0, mk * 1.5)); lit[k] = min(target, lit[k] + 3.0) if target > lit[k] else max(target, lit[k] - 1.0)
                else: lit[k] = max(0.0, lit[k] - 1.0)
            etat.append({**lit, **{"m" + k: float(min(1.0, mask[k][min(int((i + .5) / FPS * SR), n - 1)])) for k in ORDRE}})
        out = f"{a.sortie}/{a.nom}.mp4"
        bx, hors = SD.rendre(a, PLAN, deb, bar, t0, nf, FPS, W, H, wav, lambda i: etat[i], None, out)
        rap = {"fichier": out, "duree_s": round(nf / FPS, 2), "debut_s_source": round(t0, 2), "plan": PLAN, "palette": a.palette, "boites": {n_: [int(v) for v in b] for n_, b in bx}, "hors_zone_surete": hors}
        json.dump(rap, open(f"{a.sortie}/{a.nom}_rapport.json", "w"), indent=1); print(json.dumps({k: rap[k] for k in ("fichier", "duree_s", "hors_zone_surete")}, indent=1)); return
    # fond : clip recadré plein cadre vertical, net (aucune pixélisation), légèrement assombri pour la lisibilité
    cmd = ["ffmpeg", "-v", "error", "-i", a.video, "-ss", f"{t0 - a.decalage_clip:.3f}", "-t", f"{nf / FPS:.3f}", "-vf", f"fps={FPS},crop=608:1080:{a.crop_x}:0,scale={W}:{H}:flags=lanczos,lutrgb=r=val*{a.assombrir}:g=val*{a.assombrir}:b=val*{a.assombrir}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    bg = subprocess.Popen(cmd, stdout=subprocess.PIPE); fsz = W * H * 3
    out = f"{a.sortie}/{a.nom}.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
    fT, fS, fL = ImageFont.truetype(FONT, 36), ImageFont.truetype(FONT, 20), ImageFont.truetype(FONT, 16)
    maxb = MAXB; boxes = []
    lit = {k: 0.0 for k in ORDRE}
    # fenêtres « a cappella » : voix seule pendant au moins 4 mesures
    cap = [(deb[j] * bar, deb[j + 1] * bar) for j, (blk, nb) in enumerate(PLAN) if blk == "V" and nb >= 4]
    def txt(d, xy, s_, font, fill):
        d.text((xy[0] + 3, xy[1] + 3), s_, font=font, fill=(0, 0, 0, 190)); d.text(xy, s_, font=font, fill=fill)
    for i in range(nf):
        raw = bg.stdout.read(fsz)
        if len(raw) < fsz: raw = (raw + b"\x00" * fsz)[:fsz]
        img = Image.frombuffer("RGB", (W, H), raw, "raw", "RGB", 0, 1).convert("RGBA"); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        txt(d, (GAUCHE + 20, 262), a.titre, fT, (255, 255, 255, 255)); txt(d, (GAUCHE + 20, 322), "PISTE PAR PISTE", fS, (255, 214, 10, 255))
        if i == 0: boxes += [("titre", (GAUCHE + 20, 262, GAUCHE + 20 + 36 * len(a.titre), 298)), ("sous", (GAUCHE + 20, 322, GAUCHE + 20 + 20 * 15, 342))]
        ctx = {"i": i, "t": i / FPS, "lit": lit, "on": {}, "mk": {}, "wave": {k: wave[k][i] for k in ORDRE}, "spec": {k: spec[k][i] for k in ORDRE}, "ov": ov}
        for j, k in enumerate(ORDRE):
            mk = mask[k][min(int((i + .5) / FPS * SR), n - 1)]; on = mk > .05; ctx["on"][k] = on; ctx["mk"][k] = mk
            if on: target = max(2.0, lv[k][i] * maxb * min(1.0, mk * 1.5)); lit[k] = min(target, lit[k] + 3.0) if target > lit[k] else max(target, lit[k] - 1.0)   # attaque rapide mais progressive, retombée lente
            else: lit[k] = max(0.0, lit[k] - 1.0)                                                                                                              # piste coupée : la barre redescend d'un cran par image
        STYLES[a.style](d, ctx, boxes if i == 0 else None)
        for j, k in enumerate(ORDRE):
            cx = CX[j]; ly = LABEL_Y[a.style]; txt(d, (cx - 8 * len(NOMS[k]), ly), NOMS[k], fL, COUL[k] + (255,) if ctx["on"][k] else (200, 200, 200, 255))
            if i == 0: boxes.append(("nom_" + k, (cx - 8 * len(NOMS[k]), ly, cx + 8 * len(NOMS[k]), ly + 16)))
        tt = (i + .5) / FPS
        if any(a0 <= tt < a1 for a0, a1 in cap):
            txt(d, (GAUCHE + 20, 400), "A CAPPELLA", fS, (255, 214, 10, 255))
            if "cap" not in [b[0] for b in boxes]: boxes.append(("cap", (GAUCHE + 20, 400, GAUCHE + 20 + 20 * 10, 420)))
        enc.stdin.write(Image.alpha_composite(img, ov).convert("RGB").tobytes())
    enc.stdin.close(); enc.wait(); bg.stdout.close(); bg.wait()
    pb = [f"{n_}: {b}" for n_, b in boxes if b[0] < GAUCHE or b[1] < HAUT or b[2] > DROITE or b[3] > BAS]
    rap = {"fichier": out, "duree_s": round(nf / FPS, 2), "debut_s_source": round(t0, 2), "mesures": int(nbar), "plan": PLAN, "boites": {n_: b for n_, b in boxes}, "hors_zone_surete": pb, "compensation_max_db": round(float(gdb.max()), 1), "crete_avant_limiteur": round(cr, 2)}
    json.dump(rap, open(f"{a.sortie}/{a.nom}_rapport.json", "w"), indent=1); print(json.dumps(rap, indent=1))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stems", required=True); ap.add_argument("--audio", required=True); ap.add_argument("--video", required=True)
    ap.add_argument("--debut_mesure", type=int, required=True); ap.add_argument("--sortie", required=True); ap.add_argument("--nom", required=True); ap.add_argument("--titre", default="COEUR DE PIRATE"); ap.add_argument("--crop_x", type=int, default=656); ap.add_argument("--decalage_clip", type=float, default=0.0, help="instant du titre = instant du clip + ce décalage"); ap.add_argument("--assombrir", type=float, default=.8); ap.add_argument("--fondu", type=float, default=1.0, help="durée des fondus en temps"); ap.add_argument("--style", default="blocs", choices=list(STYLES)); ap.add_argument("--ad", default="pixel", choices=["pixel", "doodle"]); ap.add_argument("--palette", default="rouge"); ap.add_argument("--curseurs", action="store_true"); ap.add_argument("--hook", default="TIAKOLA"); ap.add_argument("--nom_o", default="MÉLODIE", help="nom affiché du 4e stem (autre)"); ap.add_argument("--plan", default="", help="plan par blocs, ex. VDBO:4,V:6,VD:3 (défaut : PLAN)"); ap.add_argument("--boost_db", type=float, default=0.0, help="gain de la basse dans les blocs « X » du plan"); ap.add_argument("--fond_clair", action="store_true", help="clip à fond clair : noms, rails et poignées en sombre"); ap.add_argument("--max_s", type=float, default=0.0, help="n'écrire que les N premières secondes de vidéo (aperçus)"); main(ap.parse_args())
