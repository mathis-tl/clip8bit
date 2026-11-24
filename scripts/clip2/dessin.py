"""Essais « dessin » : transforme un extrait en croquis / crayon / encre / peinture / aplats (aucun IA, aucun appel réseau).
python dessin.py <clip.mp4> <début_s> <durée_s> <dossier_sortie> [styles,séparés,par,virgules]
styles : croquis crayon encre peinture aplats. Sortie : <dossier>/dessin_<style>.mp4 (1280×720, 25 i/s, une image dessinée sur 2 = animation « sur les doubles »,
tracé qui tremble d'une image dessinée à l'autre). Pas d'audio (essai image)."""
import sys, os, subprocess, numpy as np, cv2
W, H, FPS = int(os.environ.get('DESSIN_W', 1920)), int(os.environ.get('DESSIN_H', 1080)), 25
S = W / 1280                                                   # tous les réglages (px) sont donnés pour 1280 de large
def lire(f, a, d):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(a), "-t", str(d), "-i", f, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
def champ(rng, amp, nx=10, ny=6):
    """déplacement lisse aléatoire (px) : fait trembler le trait comme un dessin refait à la main à chaque image"""
    d = rng.normal(0, amp, (ny, nx, 2)).astype(np.float32)
    d = cv2.resize(d, (W, H), interpolation=cv2.INTER_CUBIC)
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return gx + d[..., 0], gy + d[..., 1]
def trembler(img, rng, amp=1.6, fond=None):
    mx, my = champ(rng, amp * S)
    return cv2.remap(img, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
def xdog(g, s=1.1, k=1.6, p=22., eps=-.02, phi=14.):
    """contours « dessinés » (différence de gaussiennes seuillée en douceur) : 0 = trait, 1 = papier"""
    a = cv2.GaussianBlur(g, (0, 0), s * S); b = cv2.GaussianBlur(g, (0, 0), s * k * S)
    d = (1 + p) * a - p * b
    return np.where(d >= eps, 1., 1. + np.tanh(phi * (d - eps))).clip(0, 1)
def papier(rng, seed=7):
    r = np.random.RandomState(seed); t = r.normal(0, 1, (H, W)).astype(np.float32)
    t = cv2.GaussianBlur(t, (0, 0), 1.2 * S) * .5 + cv2.GaussianBlur(r.normal(0, 1, (H, W)).astype(np.float32), (0, 0), 6 * S) * 2.5
    return t
PAP = None
def hachures(g, niveaux, pas=7, ang=45, ep=1.2):
    """hachures croisées : plus la zone est sombre, plus il y a de directions de traits"""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); out = np.ones((H, W), np.float32)
    for (seuil, a) in niveaux:
        t = np.deg2rad(a); u = xx * np.cos(t) + yy * np.sin(t)
        ligne = (np.abs((u % (pas * S)) - pas * S / 2) > ep * S).astype(np.float32)           # 1 = papier, 0 = trait de hachure
        out = np.where(g < seuil, np.minimum(out, ligne), out)
    return out
def releve(f):
    """couleurs relevées (CLAHE sur la luminance) : visages et ombres lisibles avant de peindre / poser les aplats"""
    lab = cv2.cvtColor(f, cv2.COLOR_BGR2LAB); lab[..., 0] = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
def gris(f):
    """gris relevé (CLAHE + gamma) : les scènes de concert sont sombres, sans ça les traits se perdent dans le noir"""
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    g = cv2.createCLAHE(clipLimit=3., tileGridSize=(8, 8)).apply(g).astype(np.float32) / 255
    return g ** .8
def gris_local(f):
    """contraste local normalisé : un bord dans le noir (blouson, ciel) compte autant qu'un bord dans la lumière → traits réguliers partout"""
    g = gris(f); m = cv2.GaussianBlur(g, (0, 0), 18 * S); v = np.sqrt(cv2.GaussianBlur((g - m) ** 2, (0, 0), 18 * S))
    return np.clip(.5 + .22 * (g - m) / (v + .04), 0, 1)
def croquis(f, rng):
    g = gris_local(f)
    for _ in range(2): g = cv2.bilateralFilter(g, 9, .1, 7 * S)
    L = xdog(g, s=1.5, p=25, eps=.015, phi=80)
    L = cv2.GaussianBlur(L, (0, 0), .8 * S); L = np.clip((L - .45) * 3 + .5, 0, 1)
    L = trembler(L, rng, 1.8)
    return cv2.cvtColor((L * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
def crayon(f, rng):
    global PAP
    if PAP is None: PAP = papier(rng)
    g = gris_local(f)
    for _ in range(2): g = cv2.bilateralFilter(g, 9, .1, 7 * S)
    L = xdog(g, s=1.3, p=22, eps=.015, phi=60); L = np.clip((cv2.GaussianBlur(L, (0, 0), .7 * S) - .45) * 3 + .5, 0, 1)
    H1 = hachures(g, [(.40, 45), (.26, 135), (.14, 0)], pas=6, ep=1.0)
    H1 = cv2.GaussianBlur(H1, (0, 0), .7 * S)
    ton = np.minimum(L, .25 + .75 * H1)                                          # trait + hachures
    ton = trembler(ton, rng, 2.0)
    grain = (PAP * .045).astype(np.float32)
    v = ((.96 + grain) * (1 - .88 * (1 - ton))).clip(0, 1)                      # graphite gris sur papier crème
    img = np.dstack([v * .93, v * .97, v * 1.0])
    return (img * 255).clip(0, 255).astype(np.uint8)
def encre(f, rng):
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    g = cv2.bilateralFilter(g, 9, .15, 7 * S)
    ad = cv2.adaptiveThreshold((cv2.GaussianBlur(g, (0, 0), 1.5 * S) * 255).astype(np.uint8), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, int(41 * S) | 1, 9).astype(np.float32) / 255
    noir = (cv2.GaussianBlur(g, (0, 0), 3 * S) < .17).astype(np.float32)            # aplats d'encre pleine dans les ombres
    L = xdog(g, s=1.4, p=40, eps=-.015, phi=25)
    t = np.minimum(np.minimum(L, ad), 1 - noir)
    t = cv2.GaussianBlur(t, (0, 0), 1.1 * S); t = np.clip((t - .5) * 4 + .5, 0, 1)   # bord d'encre légèrement irrégulier
    t = trembler(t, rng, 2.2)
    return cv2.cvtColor((t * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
def peinture(f, rng):
    global PAP
    if PAP is None: PAP = papier(rng)
    f = releve(f); x = cv2.pyrMeanShiftFiltering(cv2.resize(f, (W // 2, H // 2)), int(10 * S), 28); x = cv2.resize(x, (W, H))
    x = cv2.edgePreservingFilter(x, flags=1, sigma_s=40, sigma_r=.35)
    x = cv2.stylization(x, sigma_s=30, sigma_r=.35)
    hsv = cv2.cvtColor(x, cv2.COLOR_BGR2HSV).astype(np.float32); hsv[..., 1] = (hsv[..., 1] * 1.15).clip(0, 255); x = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    L = xdog(cv2.bilateralFilter(g, 7, .12, 5), s=1.6, p=12, eps=-.02, phi=6)
    x = x.astype(np.float32) / 255 * (.78 + .22 * L[..., None])                  # contours doux, comme du pinceau fin
    x = x * (1 + PAP[..., None] * .04)                                           # toile
    x = trembler(x.clip(0, 1), rng, 2.4)
    return (x * 255).astype(np.uint8)
def aplats(f, rng):
    global PAP
    if PAP is None: PAP = papier(rng)
    f = releve(f); s = cv2.bilateralFilter(cv2.resize(f, (W // 2, H // 2)), 9, 40, 9); s = cv2.resize(s, (W, H))
    z = s.reshape(-1, 3).astype(np.float32)
    if not hasattr(aplats, "c"):                                                 # palette fixée sur la 1re image (couleurs stables entre images)
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 12, 1.)
        _, _, c = cv2.kmeans(z[::37], 6, None, crit, 3, cv2.KMEANS_PP_CENTERS); aplats.c = c
    idx = np.argmin(((z[:, None, :] - aplats.c[None]) ** 2).sum(2), 1); q = aplats.c[idx].reshape(H, W, 3)
    hsv = cv2.cvtColor(q.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32); hsv[..., 1] = (hsv[..., 1] * 1.35).clip(0, 255); hsv[..., 2] = (hsv[..., 2] * 1.1).clip(0, 255)
    q = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32) / 255
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    L = xdog(cv2.bilateralFilter(g, 7, .12, 5), s=1.3, p=30, eps=-.012, phi=16)
    dx, dy = int(3 * S), int(2 * S)                                                                  # léger décalage couleur/trait (impression sérigraphie)
    q = np.roll(q, (dy, dx), (0, 1))
    img = q * (.1 + .9 * L[..., None]) * (1 + PAP[..., None] * .035)
    img = trembler(img.clip(0, 1), rng, 1.8)
    return (img * 255).astype(np.uint8)
STYLES = dict(croquis=croquis, crayon=crayon, encre=encre, peinture=peinture, aplats=aplats)
def rendre(clip, a, d, wd, noms):
    os.makedirs(wd, exist_ok=True)
    for n in noms:
        fn = STYLES[n]; rng = np.random.RandomState(3); last = None
        o = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", f"{wd}/dessin_{n}.mp4"], stdin=subprocess.PIPE)
        for i, fr in enumerate(lire(clip, a, d)):
            if i % 2 == 0: last = fn(fr, rng)                                      # une image dessinée sur 2
            o.stdin.write(last.tobytes())
        o.stdin.close(); o.wait(); print("ok", n, flush=True)
if __name__ == "__main__":
    rendre(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], (sys.argv[5] if len(sys.argv) > 5 else ",".join(STYLES)).split(","))
