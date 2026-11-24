"""Clip fictif pour un titre sans clip : montage de plans pris dans d'autres clips (sources 1920×1080), coupes calées sur les mesures du titre.
Chaque plan est recadré en portrait 608×1080 centré sur la zone la plus riche en détails (estimation, sans détecteur de visage) puis posé à x=656 d'un cadre noir 1920×1080 :
le résultat se passe directement à stemmix.py (--crop_x 656, --decalage_clip = instant du titre au début de la fenêtre, affiché en fin d'exécution).
Plans rejetés : trop clairs, trop sombres ou sans contraste (cartons, titres, fondus), bandes noires, logos connus (france·tv : ne pas passer les sources `tiak_live`).
Usage : montage.py --audio titre.wav --debut_mesure 20 --mesures 35 --sortie clip.mp4 --sources a.mp4 b.mp4 ... [--coupe 2] [--graine 7]"""
import sys, os, argparse, random, subprocess, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchainer import grille, temps_fort
FPS = 30; CW = 608; CH = 1080; X0 = 656

def duree(f): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True).stdout)
def image(f, t):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", f, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).reshape(1080, 1920, 3) if len(b) == 1080 * 1920 * 3 else None
def valide(im):
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY); m, s = g.mean(), g.std()
    haut, bas = g[:10].mean(), g[-10:].mean()
    return 25 < m < 190 and s > 28 and haut > 14 and bas > 14                    # pas de bandes noires ni de carton
def centre(im):
    """Centre horizontal du sujet : colonne la plus riche en contours et en lumière (pas de détecteur de visage dans OpenCV 5), lissée sur la largeur du recadrage."""
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32); e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    prof = e.mean(axis=0) * (0.5 + g.mean(axis=0) / 255.); prof = np.convolve(prof, np.ones(CW // 2) / (CW // 2), mode="same")
    return int(np.argmax(prof[CW // 2:1920 - CW // 2]) + CW // 2)

def main(a):
    g = grille(a.audio); p = g["p"]; bar = 4 * p; t0 = temps_fort(g, a.debut_mesure)
    coupes = [a.coupe] * (a.mesures // a.coupe); reste = a.mesures - sum(coupes)
    if reste: coupes[-1] += reste
    rnd = random.Random(a.graine); sources = []
    for x in a.sources:   # chemin ou chemin@début-fin (secondes de la source utilisables)
        f, _, w = x.partition("@"); d = duree(f); lo, hi = (float(v) for v in w.split("-")) if w else (a.tmin, d - 6.0); sources.append((f, lo, hi))
    pris = {f: [] for f, _, _ in sources}; plan = []
    n = 0; k = 0
    while len(plan) < len(coupes):
        s, lo, hi = sources[k % len(sources)]; k += 1
        L = coupes[len(plan)] * bar
        if hi - L <= lo: continue
        if k > 1500: sys.exit("pas assez de plans valides")
        t = rnd.uniform(lo, hi - L)
        if any(abs(t - u) < L + 1.0 for u in pris[s]): continue
        mid = image(s, t + L / 2)
        if mid is None or not valide(mid): continue
        ims = [image(s, t + 0.05 * L), mid, image(s, t + 0.95 * L)]
        if any(i is None or not valide(i) for i in ims): continue
        pris[s].append(t); plan.append((s, t, centre(ims[1]), coupes[len(plan)]))
    tmp = a.sortie + ".parts"; os.makedirs(tmp, exist_ok=True); parts = []; cum = 0.0; f0 = 0
    for i, (s, t, cx, nb) in enumerate(plan):
        cum += nb * bar; f1 = round(cum * FPS); nf = f1 - f0; f0 = f1
        cx = int(np.clip(cx, CW / 2, 1920 - CW / 2)); out = f"{tmp}/{i:02d}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", s, "-ss", f"{t:.3f}", "-vf", f"crop={CW}:{CH}:{cx - CW // 2}:0,pad=1920:1080:{X0}:0:black,fps={FPS},setsar=1", "-frames:v", str(nf), "-an", "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", out], check=True)
        parts.append(out); print(f"{i:02d} {os.path.basename(os.path.dirname(s))} t={t:.1f}s cx={cx} {nb} mesures")
    lst = f"{tmp}/liste.txt"; open(lst, "w").write("".join(f"file '{os.path.abspath(x)}'\n" for x in parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", a.sortie], check=True)
    for x in parts + [lst]: os.remove(x)
    os.rmdir(tmp)
    print(f"{a.sortie} : {cum:.2f} s ; stemmix --decalage_clip {t0:.3f} --debut_mesure {a.debut_mesure} --crop_x {X0}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--audio", required=True); ap.add_argument("--debut_mesure", type=int, required=True); ap.add_argument("--mesures", type=int, default=35)
    ap.add_argument("--coupe", type=int, default=2, help="mesures par plan"); ap.add_argument("--sortie", required=True); ap.add_argument("--sources", nargs="+", required=True); ap.add_argument("--graine", type=int, default=7); ap.add_argument("--tmin", type=float, default=3.0, help="pas de plan avant cet instant de la source (génériques)"); main(ap.parse_args())
