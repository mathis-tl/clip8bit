import json, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont
subs=json.load(open("subs.json")); W,H,FPS=960,540,25
F=ImageFont.truetype("/System/Library/Fonts/Supplemental/Impact.ttf",58)
def layer(words):
    lines=[]; cur=[]
    d=ImageDraw.Draw(Image.new("RGBA",(10,10)))
    for w in words:
        t=" ".join(cur+[w]).upper()
        if cur and d.textlength(t,font=F)>840: lines.append(cur); cur=[w]
        else: cur.append(w)
    lines.append(cur)
    lh=70; im=Image.new("RGBA",(W,lh*len(lines)+16),(0,0,0,0)); dd=ImageDraw.Draw(im)
    for k,l in enumerate(lines):
        t=" ".join(l).upper(); x=(W-dd.textlength(t,font=F))/2
        dd.text((x,8+k*lh),t,font=F,fill=(255,230,0,255),stroke_width=5,stroke_fill=(0,0,0,255))
    return im.resize((W,int(im.height*1.3)),Image.LANCZOS)
cache={}
dec=subprocess.Popen(["ffmpeg","-v","error","-i","clip.mp4","-vf",f"fps={FPS},scale={W}:{H}","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
enc=subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-framerate",str(FPS),"-i","-","-i","clip.mp4","-map","0:v","-map","1:a","-c:v","libx264","-crf","18","-pix_fmt","yuv420p","-c:a","aac","-shortest","preview_sous_titres.mp4"],stdin=subprocess.PIPE)
k=0
while True:
    b=dec.stdout.read(W*H*3)
    if len(b)<W*H*3: break
    t=k/FPS; k+=1
    fr=Image.frombytes("RGB",(W,H),b)
    for i,s in enumerate(subs):
        if s["start"]<=t<s["end"]:
            n=sum(1 for x in s["t"] if x<=t+0.02)
            if n:
                key=(i,n)
                if key not in cache: cache[key]=layer(s["words"][:n])
                full=layer(s["words"]) if (i,"f") not in cache else cache[(i,"f")]; cache[(i,"f")]=full
                L=cache[key]; fr.paste(L,(0,int(H*0.60)),L)       # ligne ancrée en haut pour ne pas bouger quand les mots arrivent
            break
    enc.stdin.write(fr.tobytes())
enc.stdin.close(); enc.wait(); print("images",k)
