"""Effets validés (EFFETS.md) appliqués image par image par compose.py : viseur, transitions par pixellisation, rythme, habillage de jeu.
Réglages dans <work>/config.json : "cible", "mono", "sous_titres", "transition" (""|"entree"|"sortie_entree", défaut entree), "rythme" (""|"flash"|"zoom"|"both", défaut both), "habillage" (""|"muet"|"bips", défaut bips) ; "" = effet désactivé."""
import json, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
from scipy.io import wavfile
from scipy.signal import stft, find_peaks
ORIG = ("raw", "crt")      # styles « clip original » (voir styles.py)
W, H, FPS = 960, 540, 25
MONO = {"vert": [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)], "rouge": [(44, 0, 14), (122, 12, 32), (214, 44, 54), (255, 150, 140)],
        "bleu": [(8, 16, 60), (24, 64, 160), (60, 140, 230), (170, 215, 255)], "rose": [(58, 8, 50), (150, 30, 122), (240, 92, 192), (255, 202, 236)],
        "jaune": [(52, 38, 0), (130, 100, 0), (225, 180, 10), (255, 236, 122)], "violet": [(24, 6, 48), (70, 24, 128), (150, 70, 220), (214, 170, 255)],
        "rdc": [(0, 34, 110), (206, 16, 33), (247, 214, 24), (255, 244, 170)],        # drapeau de la RDC : bleu → rouge → jaune
        "ciel": [(2, 12, 52), (0, 72, 168), (0, 127, 255), (176, 220, 255)],        # bleu ciel du drapeau de la RDC (#007FFF)
        "rdc_bleu": [(6, 18, 70), (0, 104, 222), (247, 214, 24), (255, 244, 170)]}
SUBCOL = {"ambre": (232, 168, 40), "blanc": (255, 255, 255), "cyan": (110, 230, 240), "jaune": (255, 230, 0)}
def brackets(img, box, local_n, col):
    """4 coins en L autour de la boîte (grille 240×135 → 960×540) ; les coins partent 25 % plus larges et se resserrent en 3 images"""
    x0, y0, x1, y1 = [v * 4 for v in box]; sc_ = {0: 1.25, 1: 1.12}.get(local_n, 1.0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2 * sc_ + 10, (y1 - y0) / 2 * sc_ + 10; x0, x1 = max(6, cx - hw), min(W - 7, cx + hw); y0, y1 = max(6, cy - hh), min(H - 7, cy + hh)
    L = max(28, int(.22 * min(x1 - x0, y1 - y0))); t = 4; x0, x1, y0, y1 = int(x0), int(x1), int(y0), int(y1)
    for (px, py, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        cv2.rectangle(img, (px, py), (px + dx * L, py + dy * t), col, -1); cv2.rectangle(img, (px, py), (px + dx * t, py + dy * L), col, -1)
    return img
def pix(a, b):
    if b <= 1: return a
    return cv2.resize(cv2.resize(a, (W // b, H // b), interpolation=cv2.INTER_AREA), (W, H), interpolation=cv2.INTER_NEAREST)
def glitch(a, k, amp):
    """glitch RGB : rouge et bleu décalés en sens contraires + 2 ou 3 bandes horizontales déplacées (graine = n° d'image, donc reproductible)"""
    rng = np.random.default_rng(k); dx = int((6 + rng.integers(0, 6)) * amp); o = a.copy()
    o[..., 0] = np.roll(a[..., 0], dx, axis=1); o[..., 2] = np.roll(a[..., 2], -dx, axis=1)
    for _ in range(2 + int(rng.integers(0, 2))):
        y = int(rng.integers(0, H - 40)); h = int(rng.integers(8, 40)); o[y:y + h] = np.roll(o[y:y + h], int(rng.integers(-60, 60) * amp), axis=1)
    return o
class FX:
    def __init__(self, wd, CF, fr, first_start, nf):
        self.CF, self.fr, self.nf = CF, fr, nf; self.mode_t = CF.get("transition", "entree"); self.mode_r = CF.get("rythme", "both"); self.hab = CF.get("habillage", "bips"); self.start = first_start; self.glitch = CF.get("glitch", ""); self.intro_n = 52 if CF.get("intro") else 0; self.nofx = set(CF.get("effets_hors", []))      # styles sans flash/zoom ni pixellisation de transition (ex. ["gb","bw"])
        self.ramp = {}; self.eff = {}; self.beats = []
        if self.mode_t: self._transitions()
        if CF.get("pixel_drops"):      # flash fort sur chaque drop (appliqué même sur les styles de `effets_hors`, voir frame())
            from overlays import detect_drops
            for t in detect_drops(f"{wd}/audio16k.wav", **CF["pixel_drops"].get("detect", {})):
                k = int(round(t * FPS))
                for i, v in enumerate((.7, .35)): self.eff.setdefault(k + i, {})["dflash"] = v
        if self.mode_r: self._rythme(wd)
        if self.hab == "bips": self._bips(wd)
    def _transitions(self):
        m = [f["m"] for f in self.fr]; seg = []; s0 = 0
        for k in range(1, self.nf + 1):
            if k == self.nf or m[k] != m[s0]: seg.append((s0, k, m[s0])); s0 = k
        cuts = []
        for (a0, a1, ma), (b0, b1, mb) in zip(seg, seg[1:]):
            if "card" in (ma, mb) or (ma == mb if self.mode_t == "mosaique" else (ma in ORIG) == (mb in ORIG)): continue      # mosaïque : tout changement de style ; sinon seulement brut ↔ stylisé
            if b0 < self.start + 10 or b0 < self.intro_n + 4 or a1 - a0 < 12 or b1 - b0 < 12 or (cuts and b0 - cuts[-1] < 40): continue
            cuts.append(b0)
        IN = [32, 16, 8, 4, 2, 1, 1, 1]; OUT = [4, 8, 16, 32]; self.cuts = cuts
        if self.mode_t == "mosaique": IN = [32, 16, 8, 4, 2]; OUT = [8, 16, 32]
        for c in cuts:
            for i, b in enumerate(IN):
                if c + i < self.nf: self.ramp[c + i] = b
            if self.mode_t in ("sortie_entree", "mosaique"):
                for i, b in enumerate(OUT): self.ramp[c - len(OUT) + i] = b
    def _rythme(self, wd):
        sr, x = wavfile.read(f"{wd}/audio16k.wav"); x = x.astype(float) / 32768; x = x if x.ndim == 1 else x.mean(1)
        f, t, Z = stft(x, sr, nperseg=512, noverlap=512 - 128); S = np.log1p(np.abs(Z) * 30)
        def flux(lo, hi):
            b = S[(f >= lo) & (f < hi)].mean(0); d = np.maximum(np.diff(b, prepend=b[0]), 0); return np.convolve(d, np.ones(5) / 5, "same")
        F = flux(40, 160) + flux(160, 4000) * .6; hop = t[1] - t[0]; pk, _ = find_peaks(F, height=np.percentile(F, 93), distance=int(.38 / hop)); last = -99
        for p in pk:
            k = int(round(float(t[p]) * FPS))
            if k >= self.nf or k < max(self.start, self.intro_n) or self.fr[k]["m"] == "card" or k - last < int(self.CF.get("rythme_ecart_s", .8) * FPS): continue
            last = k; self.beats.append(k)
            if self.glitch and (self.glitch == "seul" or len(self.beats) % 2 == 0):      # glitch RGB : tous les temps forts (« seul ») ou un sur deux, à la place du flash/zoom
                for i in range(3): self.eff.setdefault(k + i, {})["glitch"] = (1.0, .7, .4)[i]
                continue
            for i in range(4):
                e = self.eff.setdefault(k + i, {})
                if self.mode_r in ("flash", "both") and i < 2: e["flash"] = [.50, .22][i]
                if self.mode_r in ("zoom", "both"): e["zoom"] = [1.07, 1.05, 1.03, 1.01][i]
    def _bips(self, wd):
        SR = 48000; au = np.zeros(int(3.0 * SR))
        def bip(t, fr, ln):
            n = int(ln * SR); w = np.sign(np.sin(2 * np.pi * fr * np.arange(n) / SR)) * np.linspace(1, .3, n) * .22; a = int(t * SR); au[a:a + n] += w[:max(0, len(au) - a)][:n]
        for a in (0, 10, 20): bip(a / FPS, 440, .09)
        bip(30 / FPS, 880, .09); bip(30 / FPS + .12, 1320, .18)
        wavfile.write(f"{wd}/bips.wav", SR, (np.clip(np.stack([au, au], 1), -1, 1) * 32767).astype(np.int16))
    def frame(self, k, a, hab=True):
        """a : image RGB 960×540 déjà composée (sous-titres inclus) ; renvoie l'image avec rythme, transition puis habillage"""
        if self.fr[k]["m"] != "card" and k >= self.start:
            e = self.eff.get(k)
            if e and "dflash" in e: a = (a * (1 - e["dflash"]) + 255 * e["dflash"]).astype(np.uint8)
            if e and self.fr[k]["m"] not in self.nofx:
                if "zoom" in e: z = e["zoom"]; w, h = int(W / z), int(H / z); x0, y0 = (W - w) // 2, (H - h) // 2; a = cv2.resize(a[y0:y0 + h, x0:x0 + w], (W, H), interpolation=cv2.INTER_NEAREST)
                if "flash" in e: a = (a * (1 - e["flash"]) + 255 * e["flash"]).astype(np.uint8)
            if k in self.ramp and (self.fr[k]["m"] not in self.nofx or self.mode_t == "mosaique"): a = pix(a, self.ramp[k])
            if e and "glitch" in e: a = glitch(a, k, e["glitch"])
        if hab and self.hab and k < 46: a = self._hab(k, a)
        return a
    def _hab(self, k, a):
        steps = [("3", 0, 10, 220), ("2", 10, 20, 220), ("1", 20, 30, 220), ("START", 30, 46, 96)]
        for t, s0, s1, size in steps:
            if s0 <= k < s1:
                f = ImageFont.truetype("assets/fonts/PressStart2P-Regular.ttf", size); im = Image.fromarray(a).convert("RGBA"); lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
                tw = d.textlength(t, font=f); x, y = (W - tw) / 2, H / 2 - size / 2 - 20
                d.text((x + 6, y + 6), t, font=f, fill=(20, 12, 40, 255)); d.text((x, y), t, font=f, fill=(255, 236, 60, 255) if t == "START" else (255, 255, 255, 255))
                return np.array(Image.alpha_composite(im, lay).convert("RGB"))
        return a
