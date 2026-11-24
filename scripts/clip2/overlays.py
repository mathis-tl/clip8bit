"""Incrustations de texte Press Start 2P validées le 28/10 : « TARGET LOCKED » près du viseur, compteur « COMBO xN » (config : `viseur_texte`, `combo`)."""
from PIL import ImageDraw, ImageFont, Image
FPS, SHOW = 25, 30                       # un palier de combo reste affiché 30 images (1,2 s)
_F = {s: ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", s) for s in (14, 16, 22)}
def combo_schedule(subs, nf, mode):
    """{image: (palier, rang)} ; `chaque_vers` : le palier monte à chaque fin de vers (dernier mot de subs.json), retombe à 1 si plus de 5 s séparent deux fins de vers ; affiché dès x2"""
    over = {}; cnt = 0; prev = None
    if mode not in ("chaque_vers", "un_sur_deux"): return over
    for s in subs:
        t = s["t"][-1]; cnt = cnt + 1 if (prev is not None and t - prev <= 5.0) else 1; prev = t
        if cnt >= 2 and (mode == "chaque_vers" or cnt % 2 == 0):      # un_sur_deux : le compteur monte à chaque vers mais ne s'affiche que sur les paliers pairs
            k = int(round(t * FPS))
            for i in range(SHOW):
                if k + i < nf: over[k + i] = (cnt, i)
    return over
def geom(CF):
    """zone d'incrustation : `zone_sure: \"tiktok\"` remonte les sous-titres (bas du texte à 80 % de la hauteur, 680 px de large au plus) et rentre le combo ; sinon valeurs d'origine"""
    if CF.get("zone_sure") == "tiktok": return dict(suby=.80, wrapw=680, combo=(100, 60))
    return dict(suby=.895, wrapw=800, combo=(24, 24))
def draw_combo(im, c, i, col=(255, 230, 0), xy=(24, 24)):
    ImageDraw.Draw(im).text(xy, f"COMBO x{c}", font=_F[22 if i < 3 else 16], fill=col)
def draw_target(im, box, text, col=(255, 230, 0), bg=None):
    """texte au-dessus du coin haut gauche du viseur (dedans s'il n'y a pas de place), couleur des coins"""
    x = max(6, box[0] * 4 - 10) + 4; y = max(6, box[1] * 4 - 10); y = y - 24 if y - 24 >= 6 else y + 12
    d = ImageDraw.Draw(im)
    if bg: w = d.textlength(text, font=_F[14]); d.rectangle((x - 4, y - 3, x + w + 3, y + 17), fill=bg)      # fond sombre pour les styles où le jaune se perd sur un plan clair
    d.text((x, y), text, font=_F[14], fill=col)

# ---- format vertical 1080×1920 (recadrage 9:16 qui suit le chanteur ; config `format: "vertical"`) ----
import cv2, numpy as np
from PIL import Image
VW, VH, CW = 1080, 1920, 304                  # CW : largeur du recadrage dans l'image 960×540 (9:16 de la hauteur)
SX, SY = VW / CW, VH / 540
_FV = {s: ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", s) for s in (28, 46, 64, 130, 300)}
_ARIAL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 40)
SUB_BOTTOM, SUB_WRAP, SUB_LH = 1480, 900, 50      # bas du texte à 1480 px (marge basse de 440 px pour l'interface TikTok)
def sub_layer_v(text, col):
    d0 = ImageDraw.Draw(Image.new("RGB", (4, 4))); lines = []; cur = ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if cur and d0.textlength(t, font=_ARIAL) > SUB_WRAP: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    if len(lines) == 2:          # deux lignes : coupure la plus équilibrée (évite un mot seul sur la 2e ligne)
        ws = text.split(); best = min(range(1, len(ws)), key=lambda i: max(d0.textlength(" ".join(ws[:i]), font=_ARIAL), d0.textlength(" ".join(ws[i:]), font=_ARIAL))); lines = [" ".join(ws[:best]), " ".join(ws[best:])]
    im = Image.new("RGBA", (VW, VH), (0, 0, 0, 0)); d = ImageDraw.Draw(im); y = SUB_BOTTOM - SUB_LH * len(lines)
    for l in lines: d.text(((VW - d.textlength(l, font=_ARIAL)) / 2, y), l, font=_ARIAL, fill=col + (255,)); y += SUB_LH
    return im
def cam_path(wd, sc, nf, masks_of, cw=CW):
    """abscisse (px, image 960) du centre du recadrage pour chaque image : centroïde du plus grand personnage du masque, médiane de la scène pour les trous, moyenne glissante de 15 images dans la scène"""
    cx = np.full(nf, 480.0)
    for si, s in enumerate(sc):
        if "n" not in s: continue
        m = masks_of(si); c = []
        for i in range(len(m)):
            mk = m[i].astype(np.uint8); n, lab, st, cen = cv2.connectedComponentsWithStats(mk)
            c.append(cen[1 + st[1:, 4].argmax()][0] * 4 if n > 1 else np.nan)
        c = np.array(c, float); good = c[~np.isnan(c)]
        if not len(good): continue
        c[np.isnan(c)] = np.median(good); a, b = s["s"], s["e"]; ks = np.arange(a, b); p = np.interp((ks - a) / 2.0, np.arange(len(c)), c)
        k = np.ones(15) / 15; pad = np.pad(p, 7, mode="edge"); cx[a:b] = np.convolve(pad, k, "valid")
    return np.clip(cx, cw / 2, 960 - cw / 2)
AIM_N, LOCK_N = 7, 12      # animation « on vise » (fenêtre de 12 images à 25 i/s) : 0–7 les coins se resserrent, 7–12 carré qui clignote (TARGET LOCKED)
def lock_on(n):
    """vrai si le carré (et le texte) est affiché à l'instant n (images 25 i/s, fractionnaires) : clignotement rapide (≈ 0,06 s) puis fixe sur la dernière image"""
    return n >= AIM_N and (n >= LOCK_N - 1 or int((n - AIM_N) * 2.5) % 2 == 0)
def brackets_v(img, box, local_n, col, x0, cw=CW, anim=None):
    """coins de viseur sur l'image 1080×1920 : boîte (grille 240×135) → pixels 960×540 → recadrage → 1080×1920, rognée à la fenêtre ; coins de 14 px d'épaisseur"""
    bx0, by0, bx1, by1 = [v * 4 for v in box]; sc_ = {0: 1.25, 1: 1.12}.get(local_n, 1.0) if anim != "vise" else 1.0 + .8 * (1 - min(1.0, local_n / AIM_N)) ** 2; s = VW / cw; hv = min(VH, int(round(540 * s))); yo = (VH - hv) // 2
    X0, X1 = (bx0 - x0) * s, (bx1 - x0) * s; Y0, Y1 = by0 * s + yo, by1 * s + yo; cx, cy = (X0 + X1) / 2, (Y0 + Y1) / 2
    hw, hh = (X1 - X0) / 2 * sc_ + 30, (Y1 - Y0) / 2 * sc_ + 30; X0, X1 = max(40, cx - hw), min(VW - 41, cx + hw); Y0, Y1 = max(yo + 40, cy - hh), min(yo + hv - 41, cy + hh)
    L = max(100, int(.22 * min(X1 - X0, Y1 - Y0))); t = 14; X0, X1, Y0, Y1 = int(X0), int(X1), int(Y0), int(Y1)
    if anim == "vise" and local_n >= AIM_N:      # verrouillé : les coins se rejoignent en carré complet qui clignote
        if lock_on(local_n): cv2.rectangle(img, (X0, Y0), (X1, Y1), col, t)
        return img, (X0, Y0)
    for (px, py, dx, dy) in ((X0, Y0, 1, 1), (X1, Y0, -1, 1), (X0, Y1, 1, -1), (X1, Y1, -1, -1)):
        cv2.rectangle(img, (px, py), (px + dx * L, py + dy * t), col, -1); cv2.rectangle(img, (px, py), (px + dx * t, py + dy * L), col, -1)
    return img, (X0, Y0)
def draw_target_v(im, corner, text, col, bg=None):
    x, y = corner; y = y - 56 if y - 56 >= 40 else y + 30; d = ImageDraw.Draw(im)
    if bg: w = d.textlength(text, font=_FV[28]); d.rectangle((x - 8, y - 6, x + w + 8, y + 36), fill=bg)
    d.text((x, y), text, font=_FV[28], fill=col)
def draw_combo_v(im, c, i, col, y=230):
    """dans l'image vidéo (y = haut de l'image + marge), sans fond ni contour (retiré le 29/10 sur demande)"""
    ImageDraw.Draw(im).text((90, y), f"COMBO x{c}", font=_FV[64 if i < 3 else 46], fill=col)
def habillage_v(a, k):
    for t, s0, s1, size in (("3", 0, 10, 300), ("2", 10, 20, 300), ("1", 20, 30, 300), ("START", 30, 46, 130)):
        if s0 <= k < s1:
            f = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", size); im = Image.fromarray(a).convert("RGBA"); lay = Image.new("RGBA", (VW, VH), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            tw = d.textlength(t, font=f); x, y = (VW - tw) / 2, VH / 2 - size / 2 - 40
            d.text((x + 10, y + 10), t, font=f, fill=(20, 12, 40, 255)); d.text((x, y), t, font=f, fill=(255, 236, 60, 255) if t == "START" else (255, 255, 255, 255))
            return np.array(Image.alpha_composite(im, lay).convert("RGB"))
    return a

# ---- sous-titres en gros texte (sous_titres: "carte") et tremblement de caméra sur les drops (tremblement) ----
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
BIG_SIZE, BIG_WRAP, BIG_STRETCH = 96, 960, 1.35      # défauts : Impact majuscule, ligne de 960 px au plus, étiré en hauteur comme les cartes
_BF = {}
def _bigfont(size):
    if size not in _BF: _BF[size] = ImageFont.truetype(IMPACT, size)
    return _BF[size]
def big_len(words, size=BIG_SIZE):
    return ImageDraw.Draw(Image.new("RGB", (4, 4))).textlength(" ".join(words).upper(), font=_bigfont(size))
def sub_layer_big(text, col, size=BIG_SIZE, stretch=BIG_STRETCH, yc=None, grad=None):
    """sous-titre en grand, sans fond : Impact majuscule étiré en hauteur ; bas du texte à SUB_BOTTOM (place habituelle), ou centré sur la hauteur `yc` (1 px = 1 px de la toile 1080×1920)"""
    f = _bigfont(size); t = text.upper(); tmp = Image.new("RGBA", (VW, size + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
    d.text(((VW - d.textlength(t, font=f)) / 2, 10), t, font=f, fill=col + (255,))
    if grad:      # dégradé vertical (liste de couleurs de haut en bas) sur la hauteur du texte, canal alpha du texte conservé
        import numpy as np
        ar = np.array(tmp); ys = np.nonzero(ar[..., 3].max(1))[0]; y0, y1 = (ys.min(), ys.max()) if len(ys) else (0, 1)
        G = np.array(grad, float); u = np.clip((np.arange(ar.shape[0]) - y0) / max(1, y1 - y0), 0, 1) * (len(G) - 1)
        rgb = np.stack([np.interp(u, np.arange(len(G)), G[:, c]) for c in range(3)], 1).astype(np.uint8); ar[..., :3] = rgb[:, None, :]; tmp = Image.fromarray(ar)
    h = int(tmp.height * stretch); tmp = tmp.resize((VW, h), Image.LANCZOS); im = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    y = SUB_BOTTOM - h if yc is None else int(yc - h / 2); im.paste(tmp, (0, y), tmp); return im
def detect_drops(wav, min_db=25, gap=1.2):
    """instants (s) des coups de basse qui repartent fort après un creux : montée du niveau 35–130 Hz d'au moins `min_db` dB en 0,25 s, au plus un par `gap` s"""
    import numpy as np
    from scipy.io import wavfile
    from scipy.signal import stft, find_peaks
    sr, x = wavfile.read(wav); x = x.astype(float) / 32768; x = x if x.ndim == 1 else x.mean(1)
    f, t, Z = stft(x, sr, nperseg=1024, noverlap=1024 - 160); A = np.abs(Z); hop = t[1] - t[0]
    lo = A[(f >= 35) & (f < 130)].sum(0); n = int(.04 / hop); e = np.convolve(lo, np.ones(n) / n, "same"); db = 20 * np.log10(e / e.max() + 1e-6); w = int(.25 / hop)
    r = np.array([db[i:i + int(.08 / hop)].max() - db[i - w:i].min() for i in range(w, len(db) - w)])
    pk, _ = find_peaks(r, height=min_db, distance=int(gap / hop)); return [round(float(t[p + w]), 2) for p in pk]
def shake_table(drops, n_out, fps, amp=9.0, dur=.3, seed=7):
    """{image de sortie: (dx, dy, rotation°)} : secousse qui s'amortit sur `dur` s après chaque drop, aléatoire à chaque image (calé sur la sortie, donc en vrai 60 i/s)"""
    import numpy as np
    rng = np.random.default_rng(seed); out = {}
    for d in drops:
        a = int(round(d * fps)); m = max(1, int(dur * fps))
        for i in range(m):
            if a + i >= n_out: break
            g = (1 - i / m) ** 2; out[a + i] = (rng.uniform(-1, 1) * amp * g, rng.uniform(-1, 1) * amp * g, rng.uniform(-1, 1) * .5 * g)
    return out
