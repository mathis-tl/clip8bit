"""Zones recouvertes par l'interface TikTok sur une vidéo 1080×1920 (calibrage du 21/10/2026, vérifié en lecture réelle ; copié ici, dépôt indépendant).
Rouge (toujours recouvert) : haut (île dynamique, onglets, recherche) y < 230 ; colonne d'icônes (j'aime, commentaires, partage…) x ≥ 920 pour 800 ≤ y ≤ 1640 ;
rognage latéral x < 45 ou x > 1035 ; description, hashtags, nom du son : y > 1630. Orange : promotion suggérée possible dès y = 1300.
ZONE SÛRE DU TEXTE (marges comprises) : x 60 → 910 (jusqu'à 1020 si la boîte est entièrement au-dessus de y = 780), y 240 → 1290.
Tout texte ou dessin posé par code doit y tenir : `verifier` est appelé par doodle_clip.py (échec du rendu sinon). `planche` superpose les zones sur des images du rendu.
python zones.py planche <video.mp4> <sortie.png> [n_images=12]    # contrôle visuel : rouge = recouvert, orange = promotion possible
"""
import sys, subprocess, numpy as np
VW, VH = 1080, 1920
HAUT, BAS, GAUCHE, DROITE, DROITE_HAUT, COL_Y0 = 240, 1290, 60, 910, 1020, 780
ROUGE = [(0, 0, 1080, 230), (920, 800, 1080, 1640), (0, 0, 45, 1920), (1035, 0, 1080, 1920), (0, 1630, 1080, 1920)]
ORANGE = [(0, 1300, 1080, 1630)]

def x_max(y_bas):
    """limite droite de la zone sûre pour une boîte dont le bas est à y_bas"""
    return DROITE_HAUT if y_bas < COL_Y0 else DROITE

def verifier(boite, nom="", tol=2):
    """(x0, y0, x1, y1) → liste de problèmes (vide = dans la zone sûre)"""
    x0, y0, x1, y1 = boite; pb = []
    if y0 < HAUT - tol: pb.append("haut")
    if y1 > BAS + tol: pb.append("bas")
    if x0 < GAUCHE - tol: pb.append("gauche")
    if x1 > x_max(y1) + tol: pb.append("droite")
    return [f"{nom} {p}" for p in pb]

def planche(video, sortie, n=12):
    from PIL import Image, ImageDraw
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True).stdout)
    tuiles = []
    for k in range(n):
        t = (k + .5) * d / n
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={VW}:{VH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        im = Image.fromarray(np.frombuffer(b, np.uint8).reshape(VH, VW, 3)).convert("RGBA"); ly = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(ly)
        for bx in ROUGE: dr.rectangle(bx, fill=(255, 0, 0, 90))
        for bx in ORANGE: dr.rectangle(bx, fill=(255, 150, 0, 60))
        dr.rectangle((GAUCHE, HAUT, DROITE, BAS), outline=(0, 255, 0, 200), width=4)
        tuiles.append(Image.alpha_composite(im, ly).convert("RGB").resize((270, 480)))
    col = 6; lig = (n + col - 1) // col; S = Image.new("RGB", (col * 275, lig * 485), "black")
    for i, t in enumerate(tuiles): S.paste(t, ((i % col) * 275, (i // col) * 485))
    S.save(sortie); print(sortie)

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "planche": planche(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 12)
    else: print(__doc__)
