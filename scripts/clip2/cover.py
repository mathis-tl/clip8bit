"""Couverture TikTok 1080×1920 : python cover.py <work_dir> <sortie_dossier> [préfixe] [ligne1|ligne2] [A:image:palette:n&b,B:...]
Trois candidates : image pixellisée (palette du plan) recadrée 9:16 sur le personnage, plein cadre, + titre rouge Impact dans la zone sûre
(la grille du profil TikTok recadre au centre en 3:4 : le titre reste entre y=240 et y=1680)."""
import sys, json, os, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
wd, outd = sys.argv[1], sys.argv[2]; os.makedirs(outd, exist_ok=True); PRE = sys.argv[3] if len(sys.argv) > 3 else "couverture"
C = json.load(open(f"{wd}/cuts.json"))["scenes"]; IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"; LINES = (sys.argv[4] if len(sys.argv) > 4 else "C'EST UN|MODE DE VIE").split("|")
CAND = {"A_vif": (322, "gbcy", False), "B_nb": (441, "gbcy", True), "C_vert": (1354, "gb", False)}
if len(sys.argv) > 5: CAND = {n: (int(k), p, g == "1") for n, k, p, g in (c.split(":") for c in sys.argv[5].split(","))}
def bw(q):
    g = (q[..., 0] * .299 + q[..., 1] * .587 + q[..., 2] * .114); g = np.clip((g - 18) * 1.35, 0, 255).astype(np.uint8); return np.dstack([g, g, g])
def title(im, y0):
    f = ImageFont.truetype(IMPACT, 190); lines = LINES; lay = Image.new("RGB", (1080, 400), (0, 0, 0)); d = ImageDraw.Draw(lay); y = 10
    for l in lines: d.text(((1080 - d.textlength(l, font=f)) / 2, y), l, font=f, fill=(235, 30, 40)); y += 190
    lay = lay.resize((1080, 520), Image.LANCZOS); base = im.copy(); mask = Image.fromarray((np.array(lay).sum(2) > 60).astype(np.uint8) * 255)
    band = Image.new("RGB", (1080, 560), (0, 0, 0)); base.paste(band, (0, y0 - 20), Image.fromarray(np.full((560, 1080), 150, np.uint8)))
    base.paste(lay, (0, y0), mask); return base
for name, (k, pal, gray) in CAND.items():
    si = next(i for i, s in enumerate(C) if s["s"] <= k < s["e"]); s = C[si]; i = min((k - s["s"]) // 2, s["n"] - 1)
    q = np.array(Image.open(f"{wd}/raw/f{k + 1:05d}.jpg").convert("RGB")) if pal == "raw" else np.array(Image.open(f"{wd}/s{si:02d}/L2/q_{pal}1/f{i + 1:04d}.png").convert("RGB")); q = bw(q) if gray else q      # pal "raw" : image d'origine (couverture sans pixellisation)
    _r = json.load(open(f"{wd}/config.json")).get("cover_rows")      # [y0, y1] : source avec bandes noires incrustées, on recadre sur l'image utile
    if _r: q = q[_r[0]:_r[1]]
    m = np.load(f"{wd}/s{si:02d}/mask.npy")[i].astype(np.uint8); ys, xs = np.nonzero(m); cx = (xs.mean() / m.shape[1] * q.shape[1]) if len(xs) else q.shape[1] / 2
    cw = int(round(q.shape[0] * 9 / 16)); x0 = int(np.clip(cx - cw / 2, 0, q.shape[1] - cw)); crop = q[:, x0:x0 + cw]
    im = Image.fromarray(cv2.resize(crop, (1080, 1920), interpolation=cv2.INTER_CUBIC if pal == "raw" else cv2.INTER_NEAREST)); im = title(im, 1130); im.save(f"{outd}/{PRE}_{name}.png"); print(name, k, "scène", si)
