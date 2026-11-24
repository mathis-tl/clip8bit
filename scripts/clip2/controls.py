"""Contrôles sur la vidéo exportée : python controls.py <work_dir> <vidéo.mp4>"""
import sys, json, subprocess, itertools, numpy as np
wd,vid=sys.argv[1],sys.argv[2]; FPS=25
log=json.load(open(f"{wd}/log.json")); P=json.load(open(f"{wd}/plan.json")); C=json.load(open(f"{wd}/cuts.json")); sc=C["scenes"]
subs=json.load(open(f"{wd}/subs.json"))
print("== 1. Rythme : chronologie des styles ==")
base=lambda t:t.split("+")[0]
seg=[(k,sum(1 for _ in g)) for k,g in itertools.groupby(base(t) for t in log)]
tot=len(log); cnt={}
for k,n in seg: cnt[k]=cnt.get(k,0)+n
print("part par style :",{k:f"{v/tot:.0%}" for k,v in sorted(cnt.items())})
print(f"{len(seg)} changements de style ; séquence la plus longue d'un même style : {max(n for _,n in seg)/FPS:.1f} s ({max(seg,key=lambda x:x[1])[0]})")
shares={k:v/tot for k,v in cnt.items() if k not in("raw","card")}; hi=[f"{k} {v:.0%}" for k,v in shares.items() if v>.25]
print("styles stylisés > 25 % :",hi or "aucun","; brut",f"{cnt.get('raw',0)/tot:.0%}","(cible 30–38 %)")
rawseq=[n for k,n in seg if k=="raw"]; print(f"séquences brutes : {len(rawseq)}, durée moyenne {np.mean(rawseq)/FPS:.2f} s, max {max(rawseq)/FPS:.2f} s")
CF=json.load(open(f"{wd}/config.json")); CIBLE=CF.get("cible","viseur")
ol=[(k,sum(1 for _ in g)) for k,g in itertools.groupby(any(x in t for x in ("contour","viseur")) for t in log)]; olc=[n for k,n in ol if k]
print(f"{CIBLE}s : {len(olc)} séquences, durée max {max(olc or [0])/FPS:.2f} s (limite 1 s), total {sum(olc)/FPS:.1f} s")
print("\n== 2. Immobilité (écart d'images sur la vidéo exportée) ==")
raw=subprocess.run(["ffmpeg","-v","error","-i",vid,"-vf","scale=96:54:flags=area,format=gray","-f","rawvideo","-"],capture_output=True,check=True).stdout
F=np.frombuffer(raw,np.uint8).reshape(-1,54,96).astype(np.float32); dd=np.r_[0,np.abs(F[1:]-F[:-1]).mean((1,2))]
still=[(k,sum(1 for _ in g)) for k,g in itertools.groupby(dd<.05)]; lng=max([n for k,n in still if k] or [0])
print(f"plus longue série d'images quasi identiques : {lng} images ({lng/FPS:.2f} s) ; écart moyen {dd.mean():.2f}")
print("\n== 3. Cibles (contours ou viseurs) : stabilité sur les images réellement affichées ==")
bad=0
for w in P["windows"]:
    s=sc[w["scene"]]; m=np.load(f"{wd}/s{w['scene']:02d}/mask.npy"); idx=sorted({min((f-s["s"])//2,s["n"]-1) for f in range(w["a"],w["a"]+w["n"])})
    ious=[(m[a]&m[b]).sum()/max(1,(m[a]|m[b]).sum()) for a,b in zip(idx[:-1],idx[1:])]
    cen=[np.array(np.nonzero(m[i])).mean(1) if m[i].any() else np.array([np.nan,np.nan]) for i in idx]; sh=[np.linalg.norm(a-b) for a,b in zip(cen[:-1],cen[1:])]
    flag=min(ious)<.8 or np.nanmax(sh)>5; bad+=flag
    print(f"  scène {w['scene']:2d} image {w['a']:4d} : IoU min {min(ious):.2f}, déplacement du centre max {np.nanmax(sh):.1f} px (grille 240×135) {'<< HORS SEUIL' if flag else 'ok'}")
print(f"{bad} fenêtre(s) hors seuil sur {len(P['windows'])}")
sys.path.insert(0,__file__.rsplit("/",1)[0]); from fx import FX
X=FX(wd,CF,P["frames"],sc[CF["first_scene"]]["s"],C["n"])
print("\n== 4. Lisibilité des sous-titres (contraste texte / fond) ==")
lum=lambda c:(lambda x:0.2126*x[0]+0.7152*x[1]+0.0722*x[2])(np.where(np.array(c)/255<=.03928,np.array(c)/255/12.92,((np.array(c)/255+.055)/1.055)**2.4))
from fx import SUBCOL; from overlays import geom; GEO=geom(CF); SUBC=SUBCOL[CF.get("sous_titres","ambre")]; LT=lum(SUBC); H,W=540,960
res=[]
for j,s in enumerate(subs):
    a=int(round(s["start"]*25)); b=int(round(s["end"]*25)); 
    if a<sc[json.load(open(f"{wd}/config.json"))["first_scene"]]["s"]: continue
    mid=min(range(a,b),key=lambda k:(k in X.eff or k in X.ramp or k<46,abs(k-(a+b)//2)))      # image du milieu la plus proche sans flash, zoom, transition ni décompte
    if P["frames"][mid]["m"] in("card","raw"): sty=P["frames"][mid]["m"]
    else: sty=log[mid].split("+")[0]
    f=subprocess.run(["ffmpeg","-v","error","-ss",f"{mid/25:.3f}","-i",vid,"-frames:v","1","-vf",f"crop=820:70:70:{int(540*GEO['suby'])-53}","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
    im=np.frombuffer(f,np.uint8).reshape(70,820,3).astype(int); txt=(np.abs(im-np.array(SUBC)).sum(2)<90)
    bg=im[~txt]; L=np.median([lum(x) for x in bg[::37]]) if len(bg) else 0
    r=(max(LT,L)+.05)/(min(LT,L)+.05); res.append((s["start"],sty,r))
low=[x for x in res if x[2]<3]
print(f"{len(res)} phrases ; contraste médian {np.median([x[2] for x in res]):.1f}:1 ; sous 3:1 : {len(low)}")
by={}
for t,sty,r in res: by.setdefault(sty,[]).append(r)
for sty,v in by.items(): print(f"  {sty:4s}: {len(v)} phrases, médiane {np.median(v):.1f}:1, sous 3:1 : {sum(x<3 for x in v)}")
print("  phrases sous 3:1 (début en s, style, contraste):",[(round(t,1),sty,round(r,1)) for t,sty,r in low])

print("\n== 5. Effets (config : cible, mono, transition, rythme, habillage, combo, viseur_texte) ==")
FIRST_SUB=sc[CF["first_scene"]]["s"]; cardf={k for k,f in enumerate(P["frames"]) if f["m"]=="card"}
print(f"couleur : {CF.get('mono','vert')} ; sous-titres : {CF.get('sous_titres','ambre')}")
from overlays import combo_schedule; _cb=combo_schedule(json.load(open(f"{wd}/subs.json")),C["n"],CF.get("combo",""))
print(f"combo ({CF.get('combo') or 'aucun'}) : {len(_cb)/25:.1f} s affichées, palier max x{max([c for c,_ in _cb.values()],default=0)} ; texte de viseur : {CF.get('viseur_texte') or 'aucun'}")
if CIBLE=="viseur":
    for w in P["windows"]:
        b=w["box"]; cx=(b[0]+b[2])/2/240; bh=(b[3]-b[1])/135
        print(f"  viseur scène {w['scene']:2d} image {w['a']:4d} : {w['n']} images, centre {cx:.0%}, hauteur {bh:.0%}, chevauche une carte : {'OUI' if any(f in cardf for f in range(w['a'],w['a']+w['n'])) else 'non'}")
if X.mode_t: print(f"transitions ({X.mode_t}) : {len(X.cuts)} aux images {X.cuts} ; sur une carte : {sum(1 for k in X.ramp if k in cardf)}")
if X.mode_r:
    gaps=np.diff(X.beats)/FPS if len(X.beats)>1 else [0]
    print(f"rythme ({X.mode_r}) : {len(X.beats)} effets, écart mini {min(gaps):.2f} s (≥ 0,8 s), sur une carte : {sum(1 for k in X.eff if k in cardf)}, avant le début stylisé : {sum(1 for k in X.eff if k<FIRST_SUB)}")
if X.hab: print(f"habillage ({X.hab}) : décompte images 0–45 ; piste son {'avec bips' if X.hab=='bips' else 'inchangée'}")
