"""Export final TikTok + effet « Skyrock » : accélère l'image ET le son ensemble (hauteur qui monte avec la vitesse, comme une bande accélérée).
python speed.py <entrée.mp4> <sortie.mp4> [facteur=1.03] [basses_dB=0] [i/s=30]      (facteur 1 = sans accélération ; basses_dB > 0 : renfort des basses autour de 100 Hz, limiteur contre l'écrêtage)
Étape finale sur le rendu (master crf 6) : sous-titres, effets et calage restent synchrones puisque tout est accéléré pareil. Durée / facteur.
Export : 30 i/s, H.264 High yuv420p, 18 Mbit/s (plafond 27), AAC 256 k, faststart (choix de l'auteur le 29/10). Hauteur : +12·log2(facteur) demi-tons (1,03 → +0,51)."""
import sys, subprocess
src, out = sys.argv[1], sys.argv[2]; f = float(sys.argv[3]) if len(sys.argv) > 3 else 1.03; bass = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0; fps = sys.argv[5] if len(sys.argv) > 5 else "30"; MAXQ = len(sys.argv) > 6 and sys.argv[6] == "max"      # 6e argument « max » : qualité maximale (crf 14, preset veryslow, plafond 35 Mbit/s, AAC 320 k)
sr = int(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout)
af = f"asetrate={sr * f:.0f},aresample={sr}" if f != 1 else "anull"
if bass > 0: af += f",volume=-{bass * .35:.1f}dB,bass=g={bass}:f=100:w=0.7,alimiter=limit=0.85:attack=5:release=60:level=disabled"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", f"setpts=PTS/{f},fps={fps}", "-af", af, "-c:v", "libx264", *(["-preset", "veryslow", "-profile:v", "high", "-crf", "14", "-maxrate", "35M", "-bufsize", "70M"] if MAXQ else ["-preset", "slow", "-profile:v", "high", "-b:v", "18M", "-maxrate", "27M", "-bufsize", "36M"]),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k" if MAXQ else "256k", "-movflags", "+faststart", out], check=True)
print(out)
