"""Quantifie les scènes stylisées : python quant.py <work_dir> <palettes_dir> <niveaux ex. 2,3> [resume]
N0 240×135 · N1 320×180 · N2 480×270 · N3 640×360 (la sortie reste 960×540) ; seul le niveau prévu par plan.json pour chaque scène est calculé.
Palettes : gbcy (couleurs vives), gb (vert ou `mono`), gbcd (« doux » : palette adaptative de la scène, saturation × 0,7), gbcm (« mixte » : gbcd + 25 % de l'image source).
`resume` : saute les scènes dont le dossier de sortie est déjà complet (utile pour comparer des variantes sans tout refaire ; ne pas l'utiliser après un changement de palette ou de `mono`)."""
import os, sys, json, subprocess, numpy as np, cv2
from multiprocessing import Pool
from PIL import Image
wd,pal_dir,levels=sys.argv[1],sys.argv[2],[int(x) for x in sys.argv[3].split(",")]; RESUME=len(sys.argv)>4 and sys.argv[4]=="resume"
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); from styles import pal_of
GRID={0:(240,135),1:(320,180),2:(480,270),3:(640,360)}; BAYER={0:3,1:3,2:4,3:5}
C=json.load(open(f"{wd}/cuts.json")); sc=C["scenes"]; CF=json.load(open(f"{wd}/config.json")); MONO=CF.get("mono","vert"); CIBLE=CF.get("cible","viseur")
P=json.load(open(f"{wd}/plan.json")); need={}; kind2=set()
for k,s in enumerate(sc):
    if k<CF["first_scene"]: continue      # scènes d'intro brutes : rien à quantifier
    pals={pal_of(P["frames"][f]["m"],CF) for f in range(s["s"],s["e"])}-{None}
    if pals: need[k]=pals
    if CIBLE=="contour" and any(P["frames"][f]["ol"] for f in range(s["s"],s["e"])): kind2.add(k)   # fond assombri seulement pour les contours
def desat(png,out,f=.7):
    """palette adaptative : saturation × f (en HSV), enregistrée comme palette 16×16"""
    im=np.array(Image.open(png).convert("RGB")); hsv=cv2.cvtColor(im,cv2.COLOR_RGB2HSV).astype(np.float32); hsv[...,1]*=f
    Image.fromarray(cv2.cvtColor(np.clip(hsv,0,255).astype(np.uint8),cv2.COLOR_HSV2RGB)).save(out)
def job(a):
    lvl,k=a; s=sc[k]; W,H=GRID[lvl]; d=f"{wd}/s{k:02d}/L{lvl}"; n=s["n"]
    m=np.load(f"{wd}/s{k:02d}/mask.npy"); kinds=["1"]+(["2"] if k in kind2 else [])
    for kind in kinds:
        os.makedirs(f"{d}/b{kind}",exist_ok=True)
        for i in range(n):
            a_=np.asarray(Image.open(f"{wd}/raw/f{s['s']+2*i+1:05d}.jpg").convert("RGB")); fg=cv2.resize(a_,(W,H),interpolation=cv2.INTER_AREA)
            if kind=="2":
                mk=(cv2.resize(m[i].astype(np.float32),(W,H),interpolation=cv2.INTER_LINEAR)>.5)
                bg=cv2.resize(cv2.resize(a_,(W//4,H//4),interpolation=cv2.INTER_AREA),(W,H),interpolation=cv2.INTER_NEAREST)
                fg=np.where(mk[...,None],fg,(bg*.55+20).astype(np.uint8))
            Image.fromarray(fg).save(f"{d}/b{kind}/f{i+1:04d}.png")
        lum=np.mean([np.asarray(Image.open(f"{d}/b{kind}/f{i+1:04d}.png").convert("L")).mean() for i in range(0,n,max(1,n//4))])
        gam=CF["gamma"] if "gamma" in CF and s["s"]/25>=CF.get("gamma_adaptatif_avant_s",0) else 1.3+max(0.0,(70-lum)/70)*0.6      # clé `gamma` : valeur fixe (clip 2 : 1.3, comme v3)         # scène sombre : gamma relevé (1,3 à 1,9) pour que la palette respire
        pre=f"normalize=smoothing=12,eq=gamma={gam:.2f}"
        for pal in sorted(need[k]):
            o=f"{d}/q_{pal}{kind}"
            if RESUME and os.path.isdir(o) and len(os.listdir(o))>=n: continue
            os.makedirs(o,exist_ok=True)
            def run(pf):
                subprocess.run(["ffmpeg","-y","-v","error","-framerate","12.5","-i",f"{d}/b{kind}/f%04d.png","-i",pf,"-filter_complex",f"[0:v]{pre}[a];[a][1:v]paletteuse=dither=bayer:bayer_scale={BAYER[lvl]}",f"{o}/f%04d.png"],check=True)
            if pal in ("gbcd","gbcm"):
                pp=f"{d}/pal_{pal}{kind}.png"; raw_pp=f"{d}/pal_raw{kind}.png"
                subprocess.run(["ffmpeg","-y","-v","error","-framerate","12.5","-i",f"{d}/b{kind}/f%04d.png","-vf",f"{pre},palettegen=max_colors={CF.get('gbc_couleurs',24)}:stats_mode=diff",raw_pp],check=True)
                desat(raw_pp,pp); run(pp)
                if pal=="gbcm":           # + 25 % de l'image source (même grille), pour reconnaître le clip
                    for i in range(n):
                        q=np.asarray(Image.open(f"{o}/f{i+1:04d}.png").convert("RGB")).astype(np.float32); b=np.asarray(Image.open(f"{d}/b{kind}/f{i+1:04d}.png").convert("RGB")).astype(np.float32)
                        Image.fromarray((q*.75+b*.25).astype(np.uint8)).save(f"{o}/f{i+1:04d}.png")
            else: run(f"{pal_dir}/{'mono_rouge' if pal=='gbr' else 'mono_'+MONO if pal=='gb' and MONO!='vert' else pal}.png")
    return lvl,k
if __name__=="__main__":
    jobs=[(P["lvl"][k],k) for k in sorted(need) if P["lvl"][k] in levels]
    with Pool(6) as p:
        for i,(l,k) in enumerate(p.imap_unordered(job,jobs)): print(f"{i+1}/{len(jobs)} N{l} s{k:02d}",flush=True)
