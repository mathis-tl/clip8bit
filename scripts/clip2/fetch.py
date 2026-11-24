"""Télécharge un extrait YouTube et prépare le dossier de travail (RECETTE §1, étapes 1 à 3) :
python fetch.py <url> <début> <fin> <work_dir> [--60]   (--60 : garde aussi clip60.mp4, la source à 60 i/s ; début/fin en s, m:ss ou h:mm:ss ; ex. 1:50 2:50)
Écrit <work_dir>/source.json (url, titre, extrait), clip.mp4 (H.264 crf 14 + AAC, recadré au centre en 16:9 si besoin), raw/f%05d.jpg (960×540, 25 i/s) et audio16k.wav.
Ne télécharge que la section demandée (yt-dlp --download-sections), en 1080p maximum, sans la playlist de l'URL."""
import sys, os, re, json, subprocess, shutil
url, t0, t1, wd = sys.argv[1:5]
def sec(t):
    p = [float(x) for x in t.split(":")]; return sum(v * 60 ** i for i, v in enumerate(reversed(p)))
a, b = sec(t0), sec(t1); assert b > a, "fin avant début"
os.makedirs(f"{wd}/raw", exist_ok=True); tmp = f"{wd}/dl"; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
info = json.loads(subprocess.run(["yt-dlp", "--no-playlist", "--dump-json", "--skip-download", url], capture_output=True, text=True, check=True).stdout)
subprocess.run(["yt-dlp", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]", "--merge-output-format", "mp4", "--download-sections", f"*{a}-{b}", "--force-keyframes-at-cuts",
                "-o", f"{tmp}/section.%(ext)s", url], check=True)
src = next(f"{tmp}/{f}" for f in os.listdir(tmp) if f.startswith("section.") and f.endswith(".mp4"))
w, h = [int(x) for x in subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip().split(",")]
crop = "" if abs(w / h - 16 / 9) < .02 else (f"crop={w}:{int(round(w * 9 / 16 / 2) * 2)}:0:{(h - int(round(w * 9 / 16 / 2) * 2)) // 2}," if w / h < 16 / 9 else f"crop={int(round(h * 16 / 9 / 2) * 2)}:{h}:{(w - int(round(h * 16 / 9 / 2) * 2)) // 2}:0,")
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", crop + "scale=1920:1080", "-r", "25", "-c:v", "libx264", "-crf", "14", "-c:a", "aac", f"{wd}/clip.mp4"], check=True)
if "--60" in sys.argv:      # source à 60 i/s conservée telle quelle (1920×1080) pour le rendu en vrai 60 i/s ; clip.mp4 et raw/ restent à 25 i/s pour l'analyse
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", crop + "scale=1920:1080", "-r", "60", "-an", "-c:v", "libx264", "-crf", "12", "-preset", "fast", f"{wd}/clip60.mp4"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{wd}/clip.mp4", "-vf", "fps=25,scale=960:540", "-q:v", "2", f"{wd}/raw/f%05d.jpg"], check=True)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{wd}/clip.mp4", "-ar", "16000", "-ac", "1", f"{wd}/audio16k.wav"], check=True)
json.dump(dict(url=url, title=info.get("title"), uploader=info.get("uploader"), start_s=a, end_s=b, source_size=[w, h], crop=crop.rstrip(",")), open(f"{wd}/source.json", "w"), ensure_ascii=False, indent=1)
shutil.rmtree(tmp); n = len(os.listdir(f"{wd}/raw")); print(f"{info.get('title')} : {a:.0f}-{b:.0f} s, source {w}×{h}, crop '{crop.rstrip(',')}', {n} images, {n / 25:.1f} s")
