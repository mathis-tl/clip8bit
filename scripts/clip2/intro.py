"""Ouverture « console » (format vertical) : écran-titre sur une console dessinée par code, appui sur A, l'extrait apparaît en pixels dans l'écran
(palette mono ou n&b), zoom jusqu'à ce que l'écran remplisse la zone vidéo, puis fondu vers le rendu normal. Remplace le « 3, 2, 1, START » (même durée, le son ne change pas).
Config : "intro": "gameboy", "intro_titre": "SAKI KOUDOU", "intro_sous": "SAKI225", "intro_couleur": "vert"|"rouge"|"bleu"|"rose"|"jaune"|"nb" (défaut : "mono" de la config).
Essai seul : python intro.py <work_dir> <sortie_dir>   (écrit des images et intro.mp4)"""
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
FONT = "assets/fonts/PressStart2P-Regular.ttf"
NB = [(10, 10, 10), (85, 85, 85), (170, 170, 170), (240, 240, 240)]
T_PRESS, T_CLIP, Z0, Z1, FADE = 14, 18, 28, 44, 8
BAY = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + .5) / 16
def ease(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
class Intro:
    def __init__(self, CF, mono, VW, VH, HV, YO, titre, sous):
        self.mode = CF.get("intro"); self.n = Z1 + FADE; self.VW, self.VH, self.HV, self.YO = VW, VH, HV, YO
        self.tones = NB if CF.get("intro_couleur") == "nb" else mono[CF.get("intro_couleur")] if CF.get("intro_couleur") in mono else mono[CF.get("mono", "vert")]
        self.gw = 216; self.gh = int(round(self.gw * HV / VW))                    # grille de pixels de l'écran, agrandie ×3 dans la console puis ×5 plein cadre
        self.sw, self.sh = self.gw * 3, self.gh * 3; self.titre, self.sous = titre.upper(), (sous or "").upper()
        self.sx, self.sy = (VW - self.sw) // 2, 300; self.bg = (14, 14, 26)
        self.logo = CF.get("intro_logo")                                          # "batman" : emblème dessiné par code, au-dessus du titre
        self.base = {p: self._console(p) for p in (False, True)}
    def _console(self, pressed):
        W, H = self.VW, self.VH; im = Image.new("RGB", (W, H), self.bg); d = ImageDraw.Draw(im); sx, sy, sw, sh = self.sx, self.sy, self.sw, self.sh
        bx0, bx1, by0, by1 = sx - 100, sx + sw + 100, sy - 110, sy + sh + 640
        d.rounded_rectangle((bx0 + 14, by0 + 14, bx1 + 14, by1 + 14), 70, fill=(6, 6, 12)); d.rounded_rectangle((bx0, by0, bx1, by1), 70, fill=(196, 192, 184)); d.rounded_rectangle((bx0, by0, bx1, by1), 70, outline=(150, 146, 140), width=6)
        d.rounded_rectangle((sx - 52, sy - 52, sx + sw + 52, sy + sh + 52), 34, fill=(70, 66, 92)); d.rectangle((sx - 6, sy - 6, sx + sw + 6, sy + sh + 6), fill=(20, 20, 30))
        f = ImageFont.truetype(FONT, 20); d.text((sx - 36, sy - 40), "DOT MATRIX WITH STEREO SOUND", font=ImageFont.truetype(FONT, 11), fill=(190, 190, 205))
        f2 = ImageFont.truetype(FONT, 44); d.text((sx + 6, sy + sh + 74), "PIXEL BOY", font=f2, fill=(48, 52, 140))
        cx, cy = sx + 150, sy + sh + 330                                       # croix directionnelle
        d.rounded_rectangle((cx - 24, cy - 90, cx + 24, cy + 90), 8, fill=(40, 40, 48)); d.rounded_rectangle((cx - 90, cy - 24, cx + 90, cy + 24), 8, fill=(40, 40, 48))
        for (bxc, byc, t) in ((sx + sw - 70, sy + sh + 290, "A"), (sx + sw - 200, sy + sh + 350, "B")):     # boutons A et B
            o = 8 if (pressed and t == "A") else 0
            d.ellipse((bxc - 56 + 4, byc - 56 + 8, bxc + 56 + 4, byc + 56 + 8), fill=(88, 22, 52)); d.ellipse((bxc - 56, byc - 56 + o, bxc + 56, byc + 56 + o), fill=(150, 30, 80 if not (pressed and t == "A") else 60))
            d.text((bxc - 12, byc + 76), t, font=f, fill=(48, 52, 140))
        for xx in (sx + 230, sx + 400):                                        # select / start
            d.rounded_rectangle((xx, sy + sh + 520, xx + 120, sy + sh + 548), 14, fill=(120, 118, 124))
        for i in range(5): d.line((bx1 - 120 + i * 18, by1 - 150 + i * 4, bx1 - 40 + i * 18 - 60, by1 - 40 + i * 4 - 60), fill=(120, 116, 112), width=7)
        return np.array(im)
    def _title(self, k):
        t = self.tones; sw, sh = self.sw, self.sh; im = Image.new("RGB", (sw, sh), t[3]); d = ImageDraw.Draw(im)
        if k < 3: return np.array(im)                                         # écran qui s'allume
        d.rectangle((10, 10, sw - 11, sh - 11), outline=t[1], width=6)
        words = self.titre.split(); size = 60
        while True:
            f = ImageFont.truetype(FONT, size); lines = []; cur = ""
            for w in words:
                s = (cur + " " + w).strip()
                if cur and d.textlength(s, font=f) > sw - 70: lines.append(cur); cur = w
                else: cur = s
            lines.append(cur)
            if max(d.textlength(l, font=f) for l in lines) <= sw - 70 or size <= 18: break
            size -= 2
        drop = int((1 - ease((k - 3) / 8)) * -260) // 8 * 8                   # le titre descend par paliers de 8 px
        y = sh * .27 - size * len(lines) * .75 + drop
        for l in lines: d.text(((sw - d.textlength(l, font=f)) / 2 + 4, y + 4), l, font=f, fill=t[1]); d.text(((sw - d.textlength(l, font=f)) / 2, y), l, font=f, fill=t[0]); y += size * 1.5
        if self.sous and k >= 11: fs = ImageFont.truetype(FONT, 22); d.text(((sw - d.textlength(self.sous, font=fs)) / 2, sh * .52), self.sous, font=fs, fill=t[1])
        if k >= 12 and (k // 3) % 2 == 0: fp = ImageFont.truetype(FONT, 28); d.text(((sw - d.textlength("PRESS START", font=fp)) / 2, sh * .72), "PRESS START", font=fp, fill=t[0])
        if k >= 12: fp = ImageFont.truetype(FONT, 14); d.text(((sw - d.textlength("1 PLAYER", font=fp)) / 2, sh * .83), "1 PLAYER", font=fp, fill=t[1])
        return np.array(im)
    BAT = [(0, 5), (2, 5), (3, 0), (5, 4), (8, 2), (14, 1), (21, 2), (27, 5), (31, 10), (28, 10), (26, 14), (23, 9), (19, 13), (15, 9), (11, 13), (8, 9), (5, 12), (3, 10), (2, 13), (0, 16)]
    def _bat(self, col, scale=5):
        """emblème en pixels : demi-contour mis en miroir, tracé sur une petite grille puis agrandi au plus proche voisin"""
        pts = [(31 + x, 1 + y) for x, y in self.BAT] + [(31 - x, 1 + y) for x, y in reversed(self.BAT)]
        m = Image.new("L", (64, 19), 0); ImageDraw.Draw(m).polygon(pts, fill=255); m = m.resize((64 * scale, 19 * scale), Image.NEAREST)
        return m, Image.new("RGB", m.size, col)
    def _title_full(self, k):
        """écran-titre plein cadre (sans console) : dessiné en 540×960 puis agrandi ×2 au plus proche voisin ; le titre descend par paliers, PRESS START clignote"""
        t = self.tones; w, h = self.VW // 2, self.VH // 2; im = Image.new("RGB", (w, h), t[3]); d = ImageDraw.Draw(im)
        if k >= 2:
            d.rectangle((16, 16, w - 17, h - 17), outline=t[1], width=8); d.rectangle((34, 34, w - 35, h - 35), outline=t[0], width=4)
            size = 64
            while True:
                f = ImageFont.truetype(FONT, size); lines = []; cur = ""
                for wd_ in self.titre.split():
                    s_ = (cur + " " + wd_).strip()
                    if cur and d.textlength(s_, font=f) > w - 110: lines.append(cur); cur = wd_
                    else: cur = s_
                lines.append(cur)
                if max(d.textlength(l, font=f) for l in lines) <= w - 110 or size <= 24: break
                size -= 8
            drop = int((1 - ease((k - 2) / 8)) * -420) // 8 * 8; y = h * .30 - size * len(lines) * .75 + drop
            if self.logo == "batman":
                m, c = self._bat(t[0], 6); lx, ly = (w - m.width) // 2, int(h * .07) + drop; im.paste(c, (lx, ly), m)
            for l in lines: x = (w - d.textlength(l, font=f)) / 2; d.text((x + 6, y + 6), l, font=f, fill=t[1]); d.text((x, y), l, font=f, fill=t[0]); y += size * 1.5
            if self.sous and k >= 10: fs = ImageFont.truetype(FONT, 24); d.text(((w - d.textlength(self.sous, font=fs)) / 2, h * .52), self.sous, font=fs, fill=t[1])
            if k >= 12:
                fp = ImageFont.truetype(FONT, 32)
                if (k // 3) % 2 == 0: d.text(((w - d.textlength("PRESS START", font=fp)) / 2, h * .70), "PRESS START", font=fp, fill=t[0])
                fq = ImageFont.truetype(FONT, 16); d.text(((w - d.textlength("1 PLAYER", font=fq)) / 2, h * .78), "1 PLAYER", font=fq, fill=t[1])
        return cv2.resize(np.array(im), (self.VW, self.VH), interpolation=cv2.INTER_NEAREST)
    def _pixels(self, crop):
        """extrait → grille gw×gh en 4 tons (gamma 1,3, tramage Bayer), à l'échelle de la grille"""
        small = cv2.resize(crop, (self.gw, self.gh), interpolation=cv2.INTER_AREA).astype(float)
        g = (small[..., 0] * .299 + small[..., 1] * .587 + small[..., 2] * .114); lo, hi = np.percentile(g, 2), np.percentile(g, 98); g = np.clip((g - lo) / max(hi - lo, 1), 0, 1) ** 1.3
        th = np.tile(BAY, (self.gh // 4 + 1, self.gw // 4 + 1))[:self.gh, :self.gw]; idx = np.clip(np.floor(g * 3 + th - .5 + .5), 0, 3).astype(int)
        return np.array(self.tones, np.uint8)[idx]
    def frame(self, k, v, crop):
        """v : l'image normale de ce k (1080×1920) ; crop : image 960×540 d'origine recadrée sur la fenêtre de la caméra"""
        VW, VH, HV, YO = self.VW, self.VH, self.HV, self.YO; px = self._pixels(crop)
        full = np.zeros((VH, VW, 3), np.uint8); full[YO:YO + HV] = cv2.resize(px, (VW, HV), interpolation=cv2.INTER_NEAREST)
        if k >= Z1: a = (k - Z1 + 1) / FADE; return (full * (1 - a) + v * a).astype(np.uint8)
        if self.mode == "titre":      # titre plein cadre, puis mosaïque vers l'extrait en pixels, puis fondu vers le rendu normal
            T = 26
            if k < T: return self._title_full(k)
            b = [32, 16, 8, 4, 2][k - T] if k - T < 5 else 1
            if k - T < 5:
                tt = self._title_full(T - 1); return cv2.resize(cv2.resize(full if k - T >= 2 else tt, (self.VW // b, self.VH // b), interpolation=cv2.INTER_AREA), (self.VW, self.VH), interpolation=cv2.INTER_NEAREST)
            return full
        pressed = T_PRESS <= k < T_CLIP + 2; cv = self.base[pressed].copy()
        cv[self.sy:self.sy + self.sh, self.sx:self.sx + self.sw] = self._title(k) if k < T_CLIP else cv2.resize(px, (self.sw, self.sh), interpolation=cv2.INTER_NEAREST)
        e = ease((k - Z0 + 1) / (Z1 - Z0)) if k >= Z0 else 0.0
        if e == 0: return cv
        c0 = np.array([self.sx + self.sw / 2, self.sy + self.sh / 2]); ct = np.array([VW / 2, YO + HV / 2]); s = 1 + (VW / self.sw - 1) * e; c1 = c0 + (ct - c0) * e
        M = np.array([[s, 0, c1[0] - s * c0[0]], [0, s, c1[1] - s * c0[1]]]); return cv2.warpAffine(cv, M, (VW, VH), flags=cv2.INTER_LINEAR, borderValue=self.bg)
if __name__ == "__main__":
    import sys, os, json, subprocess
    from fx import MONO
    from overlays import cam_path
    wd, outd = sys.argv[1], sys.argv[2]; os.makedirs(outd, exist_ok=True); CF = json.load(open(f"{wd}/config.json")); C = json.load(open(f"{wd}/cuts.json")); sc, NF = C["scenes"], C["n"]
    VW, VH = 1080, 1920; CW = int(CF.get("cadre_largeur", 480)); HV = min(VH, int(round(540 * VW / CW))); YO = (VH - HV) // 2
    _m = {}
    def masks_of(si):
        if si not in _m: _m[si] = np.load(f"{wd}/s{si:02d}/mask.npy")
        return _m[si]
    CAMX = cam_path(wd, sc, NF, masks_of, CW); I = Intro(CF, MONO, VW, VH, HV, YO, CF.get("intro_titre", "TITRE DU CLIP"), CF.get("intro_sous", ""))
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-framerate", "25", "-i", "-", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", f"{outd}/intro.mp4"], stdin=subprocess.PIPE)
    for k in range(I.n + 8):
        raw = np.array(Image.open(f"{wd}/raw/f{k + 1:05d}.jpg").convert("RGB")); x0 = int(round(CAMX[k] - CW / 2)); crop = raw[:, x0:x0 + CW]
        v = np.zeros((VH, VW, 3), np.uint8); v[YO:YO + HV] = cv2.resize(crop, (VW, HV), interpolation=cv2.INTER_CUBIC)
        f = I.frame(k, v, crop) if k < I.n else v; enc.stdin.write(f.tobytes())
        if k in (4, 10, 15, 22, 32, 38, 43, 47, 51): Image.fromarray(f).resize((540, 960)).save(f"{outd}/i{k:02d}.png")
    enc.stdin.close(); enc.wait(); print(outd)
