"""Mesure, sur la vidéo exportée, l'image où chaque sous-titre apparaît/disparaît, et la compare à subs.json : python verify_subs.py <video> <subs.json> <1ère_image_sous-titrée>"""
import sys, json, subprocess, numpy as np
v,sj,first=sys.argv[1],sys.argv[2],int(sys.argv[3]); W,H=960,540
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from fx import SUBCOL
cfp=os.path.join(os.path.dirname(os.path.abspath(sj)),"config.json"); from overlays import geom; _c=json.load(open(cfp)) if os.path.exists(cfp) else {}; GEO=geom(_c)
raw=subprocess.run(["ffmpeg","-v","error","-i",v,"-vf",("crop=900:200:90:1280" if _c.get("format")=="vertical" else f"crop=700:90:130:{int(540*GEO['suby'])-78}"),"-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True).stdout
F=np.frombuffer(raw,np.uint8).reshape(-1,*((200,900) if _c.get('format')=='vertical' else (90,700)),3).astype(int)
tgt=np.array(SUBCOL[json.load(open(cfp)).get("sous_titres","ambre")]) if os.path.exists(cfp) else np.array([232,168,40]); M=(np.abs(F-tgt).sum(3)<60)
xor=(M[1:]^M[:-1]).sum((1,2)); xor=np.r_[0,xor]            # pixels de texte qui changent d'une image à l'autre
subs=json.load(open(sj)); res=[]
for s in subs:
    a=max(int(round(s["start"]*25)),first)
    if a<=first: continue
    w=range(max(1,a-5),min(len(xor),a+6)); k=max(w,key=lambda x:xor[x]); res.append((s["start"],k,a,int(xor[k])))
d=[r[1]-r[2] for r in res]
print(f"{len(res)} changements de sous-titre ; image du changement mesurée - prévue : moy {np.mean(d):+.2f} min {min(d)} max {max(d)} ; hors ±1 : {sum(abs(x)>1 for x in d)}")
for r in res:
    if abs(r[1]-r[2])>1: print("  écart :",r)
