"""Photo de profil : image nette du clip carrée + texte rouge style carte, sans fond ni contour.
python pfp.py <frame.png> <cx 0-1> <cy 0-1> <zoom 0-1> <out.png> [texte]"""
import sys
from PIL import Image, ImageDraw, ImageFont
src, cx, cy, zoom, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5]
text = (sys.argv[6] if len(sys.argv) > 6 else "RAP.EXE").upper()
S = 1080; TW = 560                      # largeur du texte : tient dans le cercle d'affichage de TikTok
im = Image.open(src).convert("RGB"); w, h = im.size; side = zoom*h
x0 = min(max(cx*w-side/2, 0), w-side); y0 = min(max(cy*h-side/2, 0), h-side)
can = im.crop((int(x0), int(y0), int(x0+side), int(y0+side))).resize((S, S), Image.LANCZOS).convert("RGBA")
f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf", 200)
tw = ImageDraw.Draw(Image.new("RGB", (4, 4))).textlength(text, font=f)
t = Image.new("RGBA", (int(tw)+20, 260), (0, 0, 0, 0)); ImageDraw.Draw(t).text((10, 10), text, font=f, fill=(235, 30, 40, 255))
t = t.crop(t.getbbox()); t = t.resize((TW, int(t.height*(TW/t.width)*1.45)), Image.LANCZOS)
can.alpha_composite(t, ((S-TW)//2, 850-t.height//2)); can.convert("RGB").save(out)
