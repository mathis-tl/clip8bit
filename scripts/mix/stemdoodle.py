"""Rendu « doodle » de la vidéo piste par piste : clip net et étalonné (standard « boost TikTok » de clip-8bit), légendes gribouillées au feutre rouge qui s'écrivent,
blocs de couleur centrés (seuls les blocs allumés sont dessinés ; le bloc du bas reste gris). Appelé par stemmix.py avec --ad doodle.
Réutilise en lecture seule scripts/clip2/doodle.py de clip-8bit (jamais modifié)."""
import sys, os, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw
CLIP8 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, f"{CLIP8}/scripts/clip2")
import doodle as DD
import doodle_clip as DC
POLICE = f"{CLIP8}/polices/SedgwickAveDisplay-Regular.ttf"
ROUGE_BGR = (0, 26, 255); BLANC_BGR = (245, 245, 245)                    # #FF1A00 (standard boost)
ETAL = {"expo": -.12, "sat": 1.34, "eclat": .26, "nettete": .5}; NETTETE = .42
PALETTES = {
    "rouge": {k: (255, 26, 0) for k in "VDBO"},                                                              # RGB ; la voix reprend le rouge des légendes
    "chaud": {"V": (255, 26, 0), "D": (255, 255, 255), "B": (255, 170, 0), "O": (0, 225, 255)},
    "neon": {"V": (255, 26, 0), "D": (255, 255, 255), "B": (255, 0, 170), "O": (0, 255, 120)},
}
CX = [225, 415, 605, 795]; CW, BASE, BH, PITCH, MAXB = 150, 1200, 22, 30, 16     # 4 colonnes de 150 px, pas de 190 : x 150 → 870, centre 510 (zone TikTok : x ≤ 910)
ZONE = (60, 240, 910, 1290)
def legendes(PLAN, deb, bar, hook, titre, no="INSTRU"):
    """seule écriture doodle : le titre, affiché pendant toute la vidéo (demande de l'auteur, 05/11)"""
    return [([titre], .05, deb[-1] * bar + 5., 170)]
def calque_legendes(PLAN, deb, bar, hook, titre, no="INSTRU"):
    L = DD.Calque(1080, 1920, ROUGE_BGR); zones = []
    for k, (mots, t0, t1, taille) in enumerate(legendes(PLAN, deb, bar, hook, titre, no)):
        tm = [t0 + q * .22 for q in range(len(mots))]; tl = taille
        while True:
            el = DD.texte(mots, tm, t1, tl, (-4 if k % 2 else 4), graine=30 + k, police=POLICE, trace="plein", ev=1.4, vit=1., larg_max=800, max_car=20)
            if el["th"] <= 380 or tl <= 70: break
            tl = int(tl * .9)
        cx, cy = 500., float(np.clip(400, 274 + el["th"] / 2, 640 - el["th"] / 2)); L.ajouter(el, cx, cy, nom=" ".join(mots))
        x0, y0 = int(cx - el["w"] / 2), int(cy - el["h"] / 2); ys, xs = np.nonzero(el["ink"] > .3)                  # boîte réelle de l'encre
        zones.append((" ".join(mots), (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()), t0, t1))
    return L, zones
def calque_noms(no="INSTRU", clair=False):
    L = DD.Calque(1080, 1920, ROUGE_BGR if clair else BLANC_BGR)   ; zones = []   # clair : fond d'image clair, noms en rouge (lisibles sur blanc comme sur noir)
    for j, (k, nom) in enumerate((("V", "VOIX"), ("D", "BATT"), ("B", "BASSE"), ("O", no))):
        el = DD.texte([nom], [.05], 1e5, 46, -2 if j % 2 else 2, graine=70 + j, police=POLICE, trace="plein", ev=1.3, larg_max=160, max_car=12); L.ajouter(el, CX[j], 1243, nom=nom)
        x0, y0 = int(CX[j] - el["w"] / 2), int(1243 - el["h"] / 2); ys, xs = np.nonzero(el["ink"] > .3); zones.append((nom, (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()), 0, 1e5))
    return L, zones
def calque_boost(fen):
    """mention « BOOST » (doodle rouge) sous « BASSE » pendant les fenêtres de basse boostée"""
    L = DD.Calque(1080, 1920, ROUGE_BGR); zones = []
    for q, (t0, t1) in enumerate(fen):
        el = DD.texte(["BOOST"], [t0], t1, 36, 2 if q % 2 else -2, graine=90 + q, police=POLICE, trace="plein", ev=1.3, larg_max=200, max_car=12); L.ajouter(el, CX[2], 1281, nom="BOOST")
        x0, y0 = int(CX[2] - el["w"] / 2), int(1281 - el["h"] / 2); ys, xs = np.nonzero(el["ink"] > .3); zones.append(("BOOST", (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()), t0, t1))
    return L, zones
def blocs(d, lit, pal, curseurs=False, clair=False):
    """blocs de couleur sans contour ; curseurs=True : blocs plus étroits + un curseur (rail et poignée) à droite de chaque pile, haut = piste jouée, bas = piste coupée"""
    cw = 96 if curseurs else CW
    for j, k in enumerate("VDBO"):
        x0 = CX[j] - (84 if curseurs else CW // 2); nl = int(round(lit[k])); col = pal[k]
        for b in range(max(nl, 1)):
            y1 = BASE - b * PITCH; y0 = y1 - BH
            if b < nl: d.rectangle((x0, y0, x0 + cw, y1), fill=col + (255,))
            else: d.rectangle((x0, y0, x0 + cw, y1), fill=(128, 128, 128, 200) if clair else (200, 200, 200, 130))          # bloc du bas, grisé, quand la piste est coupée
        if curseurs:
            rx = CX[j] + 52; top, bot = BASE - MAXB * PITCH + BH + 14, BASE - 14; pos = float(lit.get("m" + k, 0.))
            d.rounded_rectangle((rx - 4, top - 14, rx + 4, bot + 14), radius=4, fill=(128, 128, 128, 170) if clair else (255, 255, 255, 90))      # rail
            ky = bot - pos * (bot - top)
            d.rounded_rectangle((rx - 4, ky, rx + 4, bot + 14), radius=4, fill=col + (255,))                     # partie du rail « montée »
            d.rounded_rectangle((rx - 27, ky - 16, rx + 27, ky + 16), radius=8, fill=(250, 250, 250, 255), outline=col + (255,) if clair else None, width=4 if clair else 0); d.rectangle((rx - 19, ky - 3, rx + 19, ky + 3), fill=col + (255,))   # poignée
def rendre(a, PLAN, deb, bar, t0, nf, FPS, W, H, wav, lit_step, boxes_out, out):
    pal = PALETTES[a.palette]; L1, z1 = calque_legendes(PLAN, deb, bar, a.hook, a.titre, a.nom_o); L2, z2 = calque_noms(a.nom_o, getattr(a, "fond_clair", False)); L3, z3 = calque_boost(getattr(a, "boost_fen", []))
    cmd = ["ffmpeg", "-v", "error", "-i", a.video, "-ss", f"{t0 - a.decalage_clip:.3f}", "-t", f"{nf / FPS:.3f}", "-vf", f"fps={FPS},crop=608:1080:{a.crop_x}:0,scale={W}:{H}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    bg = subprocess.Popen(cmd, stdout=subprocess.PIPE); fsz = W * H * 3
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
    for i in range(nf):
        raw = bg.stdout.read(fsz)
        if len(raw) < fsz: raw = (raw + b"\x00" * fsz)[:fsz]
        im = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
        im = cv2.addWeighted(im, 1 + NETTETE, cv2.GaussianBlur(im, (0, 0), 2.2), -NETTETE, 0); im = DC.etalonner(im, ETAL)           # même traitement que les doodles (netteté, saturation, éclat)
        t = (i + .5) / FPS; im = L1.composer(im, t); im = L2.composer(im, t); im = L3.composer(im, t)
        img = Image.fromarray(np.ascontiguousarray(im[..., ::-1])).convert("RGBA"); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        blocs(d, lit_step(i), pal, getattr(a, "curseurs", False), getattr(a, "fond_clair", False)); enc.stdin.write(Image.alpha_composite(img, ov).convert("RGB").tobytes())
    enc.stdin.close(); enc.wait(); bg.stdout.close(); bg.wait()
    bx = [(n, b) for n, b, _, _ in z1 + z2 + z3] + [("blocs", (CX[0] - (84 if getattr(a, "curseurs", False) else CW // 2), BASE - MAXB * PITCH, CX[3] + (79 if getattr(a, "curseurs", False) else CW // 2), BASE))]
    hors = [f"{n}: {tuple(int(v) for v in b)}" for n, b in bx if b[0] < ZONE[0] or b[1] < ZONE[1] or b[2] > ZONE[2] or b[3] > ZONE[3]]
    return bx, hors
