"""Passage au format TikTok 1080×1920 (étape finale, après validation du rendu 960×540) : python vertical.py <entrée.mp4> <sortie.mp4> [noir|flou]
La vidéo est agrandie à 1080×608 (×1,125, plus proche voisin pour garder les pixels nets) et centrée verticalement : entièrement dans la zone sûre TikTok (marges haut/bas de 656 px).
noir : fond noir ; flou : la même vidéo en fond, remplie, floutée et assombrie. Le son est copié tel quel."""
import sys, subprocess
src, out = sys.argv[1], sys.argv[2]; fond = sys.argv[3] if len(sys.argv) > 3 else "noir"
if fond == "flou":
    fc = "[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:4,eq=brightness=-0.25[bg];[b]scale=1080:608:flags=neighbor[fg];[bg][fg]overlay=0:656,format=yuv420p[v]"
else:
    fc = "[0:v]scale=1080:608:flags=neighbor,pad=1080:1920:0:656:black,format=yuv420p[v]"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "17", "-c:a", "copy", out], check=True); print(out)
