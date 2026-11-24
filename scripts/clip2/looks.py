"""Moments « clip original + effet » : crt, bit1, fond (personnage net sur fond pixellisé). Entrées/sorties : images RGB uint8 960×540."""
import numpy as np, cv2
W, H = 960, 540
_yy, _xx = np.mgrid[0:H, 0:W]
_VIG = (1 - .38 * (((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) / 2)[..., None].astype(np.float32)
_SCAN = np.where(_yy % 3 == 2, .72, 1.0)[..., None].astype(np.float32)
def crt(a):
    """écran cathodique : lignes de balayage (1 sur 3 assombrie), aberration chromatique de 2 px, vignettage"""
    b = a.astype(np.float32); out = b.copy(); out[..., 0] = np.roll(b[..., 0], 2, axis=1); out[..., 2] = np.roll(b[..., 2], -2, axis=1)
    return np.clip(out * _SCAN * _VIG * 1.08, 0, 255).astype(np.uint8)
_B8 = (np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
                 [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25], [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]]) + .5) / 64
def bit1(a):
    """1 bit tramé (Bayer 8×8) sur une grille 480×270, niveaux recalés par percentiles : noir / crème"""
    g = cv2.cvtColor(cv2.resize(a, (W // 2, H // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY).astype(np.float32)
    lo, hi = np.percentile(g, 2), np.percentile(g, 98); g = np.clip((g - lo) / max(hi - lo, 1), 0, 1) ** 1.1
    th = np.tile(_B8, (g.shape[0] // 8 + 1, g.shape[1] // 8 + 1))[:g.shape[0], :g.shape[1]]
    m = (g > th); img = np.where(m[..., None], np.array([236, 236, 214], np.uint8), np.array([10, 10, 14], np.uint8)).astype(np.uint8)
    return cv2.resize(img, (W, H), interpolation=cv2.INTER_NEAREST)
def keep_big(mk):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mk)
    if n <= 2: return mk
    big = st[1:, 4].max(); return np.isin(lab, [i + 1 for i in range(n - 1) if st[i + 1, 4] >= .3 * big]).astype(np.uint8)
def fond(raw, bg, mask_grid):
    """personnage net (raw) sur fond pixellisé (bg) ; masque 240×135 → 960×540, bord adouci (≈ 2 px)"""
    m = keep_big(mask_grid.astype(np.uint8)).astype(np.float32); m = cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)
    m = cv2.GaussianBlur(m, (0, 0), 2.0); al = np.clip((m - .35) / .3, 0, 1)[..., None]
    return (raw * al + bg * (1 - al)).astype(np.uint8)
