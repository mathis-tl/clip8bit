"""Couvertures « doodle » 1080×1920 : python doodle_cover.py <work_dir> <config.json> <sortie_dossier> <préfixe> "TITRE|sous-titre" A:17.5,B:21.5,C:40
Image = même cadrage et même étalonnage que la vidéo (fenêtre crop_w×crop_h, cx de la fenêtre = centre), à l'instant t de la source ; titre gribouillé dans la couleur de la config,
entièrement écrit (clé optionnelle `cover_titre_y`, 440 par défaut : à descendre vers 1050 si le visage est dans le haut), dans la zone sûre du profil TikTok (grille recadrée 3:4 : y 240 → 1680), + couronne, « !! » et éclair hors cadre."""
import sys, os, json, subprocess, numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import doodle as DD, doodle_clip as DC
wd, cfp, outd, pre, titre, cands = sys.argv[1:7]; CF = json.load(open(cfp)); os.makedirs(outd, exist_ok=True)
cw, ch = CF.get("crop_w", 1080), CF.get("crop_h", 1080); rows = CF["rows"]; r0 = (rows[0] + rows[1] - ch) // 2
hx = CF.get("couleur", "#FF2D0A").lstrip("#"); col = (int(hx[4:6], 16), int(hx[2:4], 16), int(hx[0:2], 16)); l1, l2 = (titre.split("|") + [""])[:2]
for c in cands.split(","):
    n, t = c.split(":"); b = subprocess.run(["ffmpeg", "-v", "error", "-ss", t, "-i", f"{wd}/clip.mp4", "-frames:v", "1", "-vf", "scale=1920:1080", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    f = np.frombuffer(b, np.uint8).reshape(1080, 1920, 3); x0 = int(np.clip(CF.get("cover_cx", 960) - cw / 2, 0, 1920 - cw)); pic = np.ascontiguousarray(f[r0:r0 + ch, x0:x0 + cw])
    im = cv2.resize(pic, (1080, round(ch * 1080 / cw)), interpolation=cv2.INTER_CUBIC)
    if CF.get("nettete"): im = cv2.addWeighted(im, 1 + CF["nettete"], cv2.GaussianBlur(im, (0, 0), 2.2), -CF["nettete"], 0)
    if CF.get("etalonnage"): im = DC.etalonner(im, CF["etalonnage"])
    if im.shape[0] > 1920: o = (im.shape[0] - 1920) // 2; im = im[o:o + 1920]      # fenêtre un peu plus haute que 9:16 (ex. 472×840 → 1922 px) : rognée au centre
    can = np.zeros((1920, 1080, 3), np.uint8); y0 = (1920 - im.shape[0]) // 2; can[y0:y0 + im.shape[0]] = im
    L = DD.Calque(1080, 1920, col); kw = dict(police=CF.get("police", DD.POLICE), trace=CF.get("trace", "squelette"), ev=CF.get("etire_v", 1.), vit=1., larg_max=980, max_car=40)
    e1 = DD.texte([l1], [0.], 9., 270, -5, graine=21, **kw); TY = CF.get("cover_titre_y", 440); L.ajouter(e1, 540, TY)
    L.ajouter(DD.tampon("couronne", 540, TY - e1["th"] / 2 - 40, 210, 0., graine=22, dur=.1, reste=20), 0, 0); L.ajouter(DD.tampon("exclam2", 900, TY - 250, 190, 0., graine=23, dur=.1, reste=20), 0, 0); L.ajouter(DD.tampon("eclair", 1060, 1450, 330, 0., graine=24, dur=.1, reste=20), 0, 0)
    if l2: L.ajouter(DD.texte([l2], [0.], 9., 150, 4, graine=25, **kw), 540, 1600)
    out = L.composer(can, 5.); p = f"{outd}/{pre}_{n}.png"; cv2.imwrite(p, out); print(p)
