"""Détecte les cuts et les images flash/noires d'un extrait : python cuts.py <work_dir>  -> <work>/cuts.json"""
import sys, json, subprocess, numpy as np
wd=sys.argv[1]; FPS=25; w,h=64,36
raw=subprocess.run(["ffmpeg","-v","error","-i",f"{wd}/clip.mp4","-vf",f"fps={FPS},scale={w}:{h}:flags=area,format=gray","-f","rawvideo","-"],capture_output=True,check=True).stdout
F=np.frombuffer(raw,np.uint8).reshape(-1,h,w).astype(np.float32); n=len(F)
d=np.zeros(n); d[1:]=np.abs(F[1:]-F[:-1]).mean((1,2))
# histogramme : un cut change la répartition des tons, un mouvement de caméra beaucoup moins
H=np.stack([np.histogram(f,bins=32,range=(0,256))[0] for f in F]).astype(np.float32)/(w*h)
hd=np.zeros(n); hd[1:]=np.abs(H[1:]-H[:-1]).sum(1)
br=F.mean((1,2))
cuts=[]
for k in range(1,n):
    loc=np.r_[d[max(1,k-4):k],d[k+1:k+5]]; ref=max(np.median(loc) if len(loc) else 0,2.0)
    if d[k]>14 and d[k]>3.2*ref and (hd[k]>.18 or d[k]>35): cuts.append(k)
flash=[k for k in range(n) if br[k]>190 or br[k]<3]
json.dump(dict(n=n,fps=FPS,cuts=cuts,flash=flash,d=d.round(1).tolist(),hd=hd.round(2).tolist()),open(f"{wd}/cuts.json","w"))
print(n,"images ;",len(cuts),"cuts :",cuts); print("flash/noir :",flash)

# --- scènes : un flash isolé (paire de cuts) est une zone brute ; c'est un vrai cut seulement si l'avant et l'après diffèrent
g=[]
for k in cuts:
    if g and k==g[-1][-1]+1: g[-1].append(k)
    else: g.append([k])
bounds=[0]; zones=set(flash)
for gr in g:
    if len(gr)==1: bounds.append(gr[0]); continue
    a,last=gr[0],gr[-1]
    zones.update(range(a,last))
    dd=np.abs(F[a-1]-F[last]).mean(); hh=np.abs(H[a-1]-H[last]).sum()
    real=dd>25 or hh>.35
    print(f"flash {a}-{last-1}: avant/après diff={dd:.1f} hist={hh:.2f} -> {'CUT' if real else 'même scène'}")
    if real: bounds.append(last)
bounds=sorted(set(bounds))+[n]
scenes=[dict(s=a,e=b) for a,b in zip(bounds[:-1],bounds[1:])]
c=json.load(open(f"{wd}/cuts.json")); c.update(scenes=scenes,zones=sorted(zones)); json.dump(c,open(f"{wd}/cuts.json","w"))
print(len(scenes),"scènes :",[(s["s"],s["e"]-s["s"]) for s in scenes])
