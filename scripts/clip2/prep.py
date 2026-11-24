"""Pour chaque scène : images 25 i/s réduites, masques de personnage stabilisés, bases L1/L2, quantification par palette.
python prep.py <work_dir> <palettes_dir> <première_scène_stylisée>"""
import os, sys, json, subprocess, numpy as np, cv2
from PIL import Image
from rembg import remove, new_session
wd,pal_dir,first=sys.argv[1],sys.argv[2],int(sys.argv[3])
W,H=240,135; STEP=2                       # rendu stylisé à 12,5 i/s (une image source sur deux)
C=json.load(open(f"{wd}/cuts.json")); sc=C["scenes"]
sess=new_session("u2net_human_seg")
def run(*c): subprocess.run(c,check=True)
def iou(a,b): return (a&b).sum()/max(1,(a|b).sum())
def clean(mk):
    mk=cv2.morphologyEx(mk,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    for inv in (0,1):
        x=(1-mk) if inv else mk
        nl,lab,st,_=cv2.connectedComponentsWithStats(x,connectivity=4)
        for c in range(1,nl):
            if st[c,cv2.CC_STAT_AREA]<60: x[lab==c]=0
        mk=(1-x) if inv else x
    return mk
for k,s in enumerate(sc):
    if k<first: continue
    d=f"{wd}/s{k:02d}"; os.makedirs(f"{d}/fr",exist_ok=True)
    idx=list(range(s["s"],s["e"],STEP)); n=len(idx); s["n"]=n
    for i,f in enumerate(idx): 
        a=Image.open(f"{wd}/raw/f{f+1:05d}.jpg").convert("RGB").resize((480,270),Image.AREA if hasattr(Image,"AREA") else Image.BILINEAR); a.save(f"{d}/fr/f{i+1:04d}.png")
    ms=np.stack([cv2.resize(np.asarray(remove(Image.open(f"{d}/fr/f{i+1:04d}.png"),session=sess,only_mask=True)).astype(np.float32)/255,(W,H),interpolation=cv2.INTER_AREA) for i in range(n)])
    m=np.stack([clean((np.median(ms[max(0,i-1):i+2],0)>.5).astype(np.uint8)) for i in range(n)])
    first_stats=[iou(m[i],m[i-1]) for i in range(1,n)] or [1]
    o=m.copy()                             # rejet des images aberrantes, puis vote sur 5 images
    for i in range(n):
        p=o[i-1] if i>0 else None; q=o[i+1] if i<n-1 else None
        if p is not None and q is not None and iou(o[i],p)<.5 and iou(o[i],q)<.5 and iou(p,q)>.6: o[i]=p
    v=np.stack([(o[max(0,i-2):i+3].sum(0)*2>=len(o[max(0,i-2):i+3])).astype(np.uint8) for i in range(n)])
    st=[iou(v[i],v[i-1]) for i in range(1,n)] or [1]
    s["iou_min"]=float(min(st)); s["iou_moy"]=float(np.mean(st)); s["cover"]=float(v.mean())
    # contour fiable : masque stable ET un personnage assez grand (sinon on segmente un objet ou le décor)
    s["stable"]=bool(n>=4 and s["iou_moy"]>=.78 and s["iou_min"]>=.5 and .04<=s["cover"]<=.8)
    np.save(f"{d}/mask.npy",v)
    for kind in ("1","2"):
        os.makedirs(f"{d}/b{kind}",exist_ok=True)
        for i in range(n):
            a=np.asarray(Image.open(f"{d}/fr/f{i+1:04d}.png").convert("RGB")); fg=cv2.resize(a,(W,H),interpolation=cv2.INTER_AREA)
            if kind=="2":
                bg=cv2.resize(cv2.resize(a,(W//4,H//4),interpolation=cv2.INTER_AREA),(W,H),interpolation=cv2.INTER_NEAREST)
                fg=np.where(v[i][...,None]>0,fg,(bg*.55+20).astype(np.uint8))
            Image.fromarray(fg).save(f"{d}/b{kind}/f{i+1:04d}.png")
        for pal in ("gbcy","gb","bw"):
            o_=f"{d}/q_{pal}{kind}"; os.makedirs(o_,exist_ok=True)
            run("ffmpeg","-y","-v","error","-framerate","12.5","-i",f"{d}/b{kind}/f%04d.png","-i",f"{pal_dir}/{pal}.png","-filter_complex","[0:v]normalize=smoothing=12,eq=gamma=1.3[a];[a][1:v]paletteuse=dither=bayer:bayer_scale=3",f"{o_}/f%04d.png")
    print(f"s{k:02d} s={s['s']} n={n} IoU min/moy {s['iou_min']:.2f}/{s['iou_moy']:.2f} couv {s['cover']:.2f} {'contour OK' if s['stable'] else 'PAS de contour'}",flush=True)
C["scenes"]=sc; json.dump(C,open(f"{wd}/cuts.json","w"))
