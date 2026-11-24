"""Montage : python compose.py <work_dir> <sortie.mp4>   (plan.json vient de plan.py ; les images de quant.py)"""
import sys, json, subprocess, numpy as np, cv2
from fx import FX, brackets, MONO, SUBCOL
from PIL import Image, ImageDraw, ImageFont
wd,out=sys.argv[1],sys.argv[2]
C=json.load(open(f"{wd}/cuts.json")); sc=C["scenes"]; NF=C["n"]; FPS=25; FOUT=int(json.load(open(f"{wd}/config.json")).get("fps_sortie",25))      # FPS : grille d'analyse (plan, scènes) ; FOUT : cadence du rendu (60 = vrai 60 i/s, source clip60.mp4)
P=json.load(open(f"{wd}/plan.json")); fr=P["frames"]
subs=json.load(open(f"{wd}/subs.json")); W,H=960,540; CF=json.load(open(f"{wd}/config.json")); FIRST_SUB=sc[CF["first_scene"]]["s"]; CIBLE=CF.get("cible","viseur"); BIGSUB=CF.get("sous_titres")=="carte"; BSZ=int(CF.get("sous_titres_taille",96)); BST=float(CF.get("sous_titres_etire",1.35)); BYC=CF.get("sous_titres_y"); SUBC=SUBCOL.get(CF.get("sous_titres","ambre"),(235,30,40))      # "carte" : gros texte rouge sans fond, une ligne à la fois
GRID={0:(240,135),1:(320,180),2:(480,270),3:(640,360)}
PAL={"gbc":"gbcy","gb":"gb","bw":"gbcy"}      # le N&B est un filtre sur le rendu couleur
COL={"gbc":[(255,255,255),(255,230,0)],"gb":[MONO[CF.get("mono","vert")][3]],"bw":[(255,230,0)]}
from overlays import geom
GEO=geom(CF)
FORMAT=CF.get("format")=="vertical"; VW,VH=(1080,1920) if FORMAT else (W,H)
FONT=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf",21)
def wrap(text):
    d=ImageDraw.Draw(Image.new("RGB",(4,4))); lines=[]; cur=""
    for w in text.split():
        t=(cur+" "+w).strip()
        if cur and d.textlength(t,font=FONT)>GEO["wrapw"]: lines.append(cur); cur=w
        else: cur=t
    return lines+[cur]
def sub_layer(text):
    lines=wrap(text); lh=26; im=Image.new("RGBA",(W,H),(0,0,0,0)); d=ImageDraw.Draw(im); y=int(H*GEO["suby"])-lh*(len(lines)-1)-12
    for l in lines:
        x=(W-d.textlength(l,font=FONT))/2; d.text((x,y),l,font=FONT,fill=SUBC+(255,)); y+=lh
    return im
SUBL=[sub_layer(" ".join(s["words"])) for s in subs]
def bw(q):
    """filtre noir et blanc : luminance du rendu couleur, contraste légèrement relevé"""
    g=(q[...,0]*.299+q[...,1]*.587+q[...,2]*.114); g=np.clip((g-18)*1.35,0,255).astype(np.uint8); return np.dstack([g,g,g])
def keep_big(mk):
    """ne garde que les composantes du masque d'au moins 30 % de la plus grande (supprime les îlots parasites)"""
    n,lab,st,_=cv2.connectedComponentsWithStats(mk); 
    if n<=2: return mk
    big=st[1:,4].max(); keep=[i+1 for i in range(n-1) if st[i+1,4]>=.3*big]
    return np.isin(lab,keep).astype(np.uint8)
IMPACT="/System/Library/Fonts/Supplemental/Impact.ttf"
CARDC=tuple(MONO[CF["carte_couleur"]][2]) if CF.get("carte_couleur") else (235,30,40)      # carte_couleur : nom d'une couleur mono (ex. violet) ; défaut rouge
def card(text):
    """fond noir, texte rouge, Impact majuscule étiré verticalement, tout d'un coup (vertical : toile 1080×1920, texte jusqu'à 940 px de large, 5 lignes)"""
    W_,H_,WR,ML,S0=(VW,VH,940,5,150) if FORMAT else (W,H,820,3,84)
    d0=ImageDraw.Draw(Image.new("RGB",(4,4))); text=text.upper(); size=S0
    while True:
        f=ImageFont.truetype(IMPACT,size); lines=[]; cur=""
        for w in text.split():
            t=(cur+" "+w).strip()
            if cur and d0.textlength(t,font=f)>WR: lines.append(cur); cur=w
            else: cur=t
        lines.append(cur)
        if len(lines)<=ML or size<40: break
        size-=4
    lh=int(size*1.0); tot=lh*len(lines)
    txt=Image.new("RGB",(W_,tot+40),(0,0,0)); td=ImageDraw.Draw(txt); y=20
    for l in lines: td.text(((W_-td.textlength(l,font=f))/2,y),l,font=f,fill=CARDC); y+=lh
    txt=txt.resize((W_,int(txt.height*1.45)),Image.LANCZOS)
    lay=Image.new("RGB",(W_,H_),(0,0,0)); lay.paste(txt,(0,(H_-txt.height)//2)); return np.array(lay)
CARDS={(i if P.get("cards_by")=="index" else c["line"]):card(c["text"]) for i,c in enumerate(P["cards"])}      # anciens plans (v3) : carte repérée par le n° de ligne de paroles
def sub_at(k,t=None):
    t=k/FPS if t is None else t
    for i,s in enumerate(subs):
        if s["start"]<=t<s["end"]: return i
# l'objet FX est créé avant l'encodeur (les bips de l'habillage sont écrits dans <work>/bips.wav)
WINBOX={}
for w in P["windows"]:
    for n in range(w["n"]): WINBOX[w["a"]+n]=(w.get("box"),n)
FXE=FX(wd,CF,fr,FIRST_SUB,NF)
BIPS=CF.get("habillage","bips")=="bips"
AUD=["-filter_complex","[1:a][2:a]amix=inputs=2:duration=first:normalize=0[a]","-map","0:v","-map","[a]"] if BIPS else ["-map","0:v","-map","1:a"]
enc=subprocess.Popen(["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{VW}x{VH}","-framerate",str(FOUT),"-i","-","-i",f"{wd}/clip.mp4"]+(["-i",f"{wd}/bips.wav"] if BIPS else [])+AUD+["-c:v","libx264","-crf",str(CF.get("crf",17)),"-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest",out],stdin=subprocess.PIPE)
log=[]; masks={}
from overlays import combo_schedule, draw_combo, draw_target
if FORMAT:
    from overlays import lock_on, sub_layer_v, cam_path, brackets_v, draw_target_v, draw_combo_v, habillage_v
    CW=int(CF.get("cadre_largeur",304)); HV=min(VH,int(round(540*VW/CW))); YO=(VH-HV)//2      # CW : largeur de la fenêtre dans l'image 960×540 (304 = plein cadre 9:16, 960 = bandes noires de 656 px)
    from overlays import _ARIAL, SUB_WRAP, BIG_WRAP, big_len, sub_layer_big, detect_drops, shake_table
    def split_subs(subs):
        """une seule ligne à l'écran : une phrase trop large pour SUB_WRAP est coupée en morceaux de largeur voisine, chacun affiché de son 1er mot jusqu'au 1er mot du suivant"""
        d0=ImageDraw.Draw(Image.new("RGB",(4,4))); tl=(lambda ws: big_len(ws,BSZ)) if BIGSUB else (lambda ws: d0.textlength(" ".join(ws),font=_ARIAL)); LIM=BIG_WRAP if BIGSUB else SUB_WRAP; out=[]
        for s_ in subs:
            ws=s_["words"]; n=-(-int(tl(ws))//LIM)
            if n<=1: out.append(s_); continue
            best=None
            while best is None and n<=len(ws):      # si n morceaux ne tiennent pas dans la largeur, on essaie n+1 (un morceau trop large serait rogné)
                for cuts in __import__("itertools").combinations(range(1,len(ws)),n-1):
                    parts=[ws[a:b] for a,b in zip((0,)+cuts,cuts+(len(ws),))]; m=max(tl(p) for p in parts)
                    if m<=LIM and (best is None or m<best[0]): best=(m,cuts)
                n+=1
            if best is None: out.append(s_); continue
            idx=(0,)+best[1]+(len(ws),)
            for a,b in zip(idx,idx[1:]):
                st=s_["t"][a]; en=s_["t"][b] if b<len(ws) else s_["end"]; out.append(dict(words=ws[a:b],t=s_["t"][a:b],start=st,end=min(en,s_["end"]) if b==len(ws) else en))
        return out
    SUBFULL=subs; subs=split_subs(subs)
    SUBLV=[sub_layer_big(" ".join(s_["words"]),SUBC,BSZ,BST,BYC,CF.get("sous_titres_degrade")) if BIGSUB else sub_layer_v(" ".join(s_["words"]),SUBC) for s_ in subs]; _mk={}
    def _masks(si):
        if si not in _mk: _mk[si]=np.load(f"{wd}/s{si:02d}/mask.npy")
        return _mk[si]
    CAMX=cam_path(wd,sc,NF,_masks,CW)
    INTRO=None
    if CF.get("intro") in ("gameboy","titre"):
        from intro import Intro; _t=json.load(open(f"{wd}/source.json")).get("title","") if __import__("os").path.exists(f"{wd}/source.json") else ""
        INTRO=Intro(CF,MONO,VW,VH,HV,YO,CF.get("intro_titre",_t or "PRESS START"),CF.get("intro_sous",""))
COMBO=combo_schedule(SUBFULL if FORMAT else subs,NF,CF.get("combo","")); VTXT=CF.get("viseur_texte","")
sys.path.insert(0,__import__("os").path.dirname(__import__("os").path.abspath(__file__))); from styles import pal_of; from looks import crt, bit1, fond
VCOL={"gbc":[(255,255,255),(255,230,0)],"gb":[MONO[CF.get("mono","vert")][3 if FORMAT else 0]],"fond_vert":[MONO[CF.get("mono","vert")][3]]}      # couleur des coins de viseur par style (défaut : jaune)
NOUT=int(NF*FOUT/FPS); CUR=[None]; RAWNB=CF.get("raw_nb",False)
if FOUT==60:      # source à 60 i/s lue en continu (960×540), une image par image de sortie
    _dec=subprocess.Popen(["ffmpeg","-v","error","-i",f"{wd}/clip60.mp4","-vf","scale=960:540","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
HD=bool(CF.get("source_hd")); _hd=[None,-1]      # source_hd : image brute lue à pleine définition (1920×1080 de clip.mp4) au lieu des jpg 960×540, pour le mode brut sans effet (bandes_noires)
if HD: _hdp=subprocess.Popen(["ffmpeg","-v","error","-i",f"{wd}/clip.mp4","-vf","fps=25,scale=1920:1080","-f","rawvideo","-pix_fmt","rgb24","-"],stdout=subprocess.PIPE)
def hdimg(k):
    while _hd[1]<k:
        r=_hdp.stdout.read(1920*1080*3)
        if len(r)<1920*1080*3: break
        _hd[0]=np.frombuffer(r,np.uint8).reshape(1080,1920,3); _hd[1]+=1
    return _hd[0]
_T=np.array(MONO["rouge"],float); LUT_R=np.stack([np.interp(np.arange(256),np.linspace(0,255,4),_T[:,c]) for c in range(3)],1).astype(np.uint8)
def _gray(a): g=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY); return np.dstack([g,g,g])
LIVE_END=int(CF.get("live_nb_s",0)*FPS); _GAM={}; LCW=int(CF.get("live_cadre_largeur",960)); LHV=min(1920,int(round(540*1080/LCW)))
def _gam_live(si):      # gamma adaptatif de la scène (même formule que quant.py) : scène sombre = gamma relevé de 1,3 à 1,9
    if si not in _GAM:
        s=sc[si]; ks=range(s["s"],s["e"],max(1,(s["e"]-s["s"])//4)); lum=np.mean([cv2.imread(f"{wd}/raw/f{k+1:05d}.jpg",cv2.IMREAD_GRAYSCALE).mean() for k in ks])
        g=1.3+max(0.0,(70-lum)/70)*0.6; _GAM[si]=(255*(np.arange(256)/255)**(1/g)).astype(np.uint8)
    return _GAM[si]
def rawimg(k):
    a=CUR[0] if FOUT==60 else np.array(Image.open(f"{wd}/raw/f{k+1:05d}.jpg").convert("RGB"))
    if k<LIVE_END: return _gam_live(next(i for i,s in enumerate(sc) if s["s"]<=k<s["e"]))[_gray(a)]      # partie live : toujours n&b, gamma adaptatif, jamais l'image d'origine
    return _gray(a) if RAWNB else a
DROPS=detect_drops(f"{wd}/audio16k.wav",**CF["tremblement"].get("detect",{})) if CF.get("tremblement") else []
SHAKE=shake_table(DROPS,NOUT,FOUT,CF["tremblement"].get("amp",9.0),CF["tremblement"].get("dur_s",.3)) if DROPS else {}
if DROPS: print("drops (tremblement) :",DROPS)
def quantimg(si,lvl,pal,i,mode,kind="1"):
    q=np.array(Image.open(f"{wd}/s{si:02d}/L{lvl}/q_{pal}{kind}/f{i+1:04d}.png").convert("RGB"))
    return bw(q) if mode in ("bw","fond_bw") else q
for jo in range(NOUT):
    k=min(NF-1,int(jo*FPS/FOUT))
    if FOUT==60:
        _r=_dec.stdout.read(960*540*3)
        if len(_r)==960*540*3: CUR[0]=np.frombuffer(_r,np.uint8).reshape(540,960,3)
    si=next(i for i,s in enumerate(sc) if s["s"]<=k<s["e"]); s=sc[si]; p=fr[k]; local=k-s["s"]; mode=p["m"]; lvl=P["lvl"][si]; GW,GH=GRID[lvl]; i=min(local//2,s["n"]-1) if "n" in s else 0
    tag=mode
    if mode=="card": a=CARDS[p["card"]]
    elif mode=="raw": a=rawimg(k)
    elif mode=="rouge_plat": g=rawimg(k)[...,0]; a=LUT_R[g]      # le brut passe d'abord au rouge sans pixel (puis pixel rouge)
    elif mode=="crt": a=crt(rawimg(k))
    elif mode=="bit1": a=bit1(rawimg(k))
    elif mode.startswith("fond"):
        if si not in masks: masks[si]=np.load(f"{wd}/s{si:02d}/mask.npy")
        bg=cv2.resize(quantimg(si,lvl,pal_of(mode,CF),i,mode),(W,H),interpolation=cv2.INTER_NEAREST); a=fond(rawimg(k),bg,masks[si][i])
    elif p["ol"] and CIBLE=="contour":
        q=quantimg(si,lvl,pal_of(mode,CF),i,mode,"2")
        if si not in masks: masks[si]=np.load(f"{wd}/s{si:02d}/mask.npy")
        mk=keep_big((cv2.resize(masks[si][i].astype(np.float32),(GW,GH),interpolation=cv2.INTER_LINEAR)>.5).astype(np.uint8))
        col=COL[mode][si%len(COL[mode])]; q[(cv2.dilate(mk,np.ones((3,3),np.uint8))>mk)]=col; tag=mode+"+contour"; a=cv2.resize(q,(W,H),interpolation=cv2.INTER_NEAREST)
    else: a=cv2.resize(quantimg(si,lvl,pal_of(mode,CF),i,mode),(W,H),interpolation=cv2.INTER_NEAREST)
    if p["ol"] and CIBLE=="viseur" and mode!="card" and mode!="raw":
        bx,ln_=WINBOX[k]; cl=VCOL.get(mode,[(255,230,0)]); vcol=tuple(CF["viseur_couleur"]) if CF.get("viseur_couleur") else cl[si%len(cl)]; a=a if FORMAT else brackets(a.copy(),bx,ln_,vcol); tag=mode+"+viseur"
    if FORMAT:
        j=sub_at(k,jo/FOUT)
        if mode=="card": v=a
        else:
            LV=k<LIVE_END or bool(CF.get("bandes_noires"))      # bandes_noires : toute la vidéo en 16:9 sur fond noir, couleurs conservées ; partie live : fenêtre 16:9 (live_cadre_largeur), bandes noires, jamais de flou ni de pixel
            cw_,hv_=(LCW,LHV) if LV else (CW,HV); yo_=(VH-hv_)//2 if LV else YO
            fxa=FXE.frame(k,a,hab=False); x0=0 if LV and LCW>=960 else (960-cw_)//2 if (LV and CF.get("bandes_noires")) else int(round(CAMX[k]-cw_/2)); x0=max(0,min(960-cw_,x0)); crop=fxa[:,x0:x0+cw_]
            if HD and mode=="raw" and LV: crop=hdimg(k)[:,2*x0:2*(x0+cw_)]      # pleine définition : 2 px source par px de travail
            v=cv2.resize(crop,(VW,hv_),interpolation=(cv2.INTER_AREA if crop.shape[1]>VW else cv2.INTER_CUBIC) if mode in ("raw","crt") else cv2.INTER_NEAREST); corner=None
            if jo in SHAKE and k>=FIRST_SUB: dx,dy,rot=SHAKE[jo]; v=cv2.warpAffine(v,cv2.getRotationMatrix2D((VW/2,hv_/2),rot,1.0)+np.array([[0,0,dx],[0,0,dy]]),(VW,hv_),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)      # tremblement léger sur les drops (l'image bouge, pas le texte)
            if hv_<VH:
                canvas=np.zeros((VH,VW,3),np.uint8)
                if CF.get("bandes")=="flou" and not LV:      # bandes remplies par la même image agrandie à couvrir 1080×1920, très floutée et assombrie
                    sc_=VH/540; bg=cv2.resize(crop,(int(CW*sc_),VH),interpolation=cv2.INTER_LINEAR); bx=(bg.shape[1]-VW)//2; bg=cv2.GaussianBlur(bg[:,max(0,bx):max(0,bx)+VW],(0,0),38); canvas=(bg*.4).astype(np.uint8)
                    if canvas.shape[1]!=VW: canvas=cv2.resize(canvas,(VW,VH))
                canvas[yo_:yo_+hv_]=v; v=canvas
            if tag.endswith("+viseur"):
                nf_=WINBOX[k][1]+(jo*FPS/FOUT-k); v,corner=brackets_v(v.copy(),WINBOX[k][0],nf_ if CF.get("viseur_anim")=="vise" else WINBOX[k][1],vcol,x0,CW,CF.get("viseur_anim"))
                if CF.get("viseur_anim")=="vise" and not lock_on(nf_): corner=None      # texte TARGET LOCKED seulement pendant le verrouillage
            im=Image.fromarray(v)
            if j is not None and k>=FIRST_SUB: im.paste(SUBLV[j],(0,0),SUBLV[j])
            if k>=FIRST_SUB:
                if k in COMBO and corner is None: draw_combo_v(im,*COMBO[k],MONO[CF.get("mono","vert")][3] if mode in ("gb","fond_vert") else (255,230,0),YO+40 if HV<VH else 230)      # dans l'image vidéo, jamais dans les bandes noires
                if VTXT and corner is not None: draw_target_v(im,corner,VTXT,vcol,(10,10,14))
            v=np.array(im.convert("RGB"))
            if INTRO and not CF.get("intro_fin") and k<INTRO.n: x0_=int(round(CAMX[k]-CW/2)); v=INTRO.frame(k,v,rawimg(k)[:,x0_:x0_+CW])
            elif INTRO and CF.get("intro_fin") and k>=NF-INTRO.n: x0_=int(round(CAMX[k]-CW/2)); v=INTRO.frame(NF-1-k,v,rawimg(k)[:,x0_:x0_+CW])      # l'affiche à la fin : l'animation d'ouverture jouée à l'envers
            elif CF.get("habillage","bips") and k<46 and not INTRO: v=habillage_v(v,k)
        enc.stdin.write(v.tobytes()); log.append(tag); continue
    im=Image.fromarray(a); j=sub_at(k)
    if mode!="card" and j is not None and k>=FIRST_SUB: im.paste(SUBL[j],(0,0),SUBL[j])
    if mode!="card" and k>=FIRST_SUB:
        if k in COMBO and not tag.endswith("+viseur"): draw_combo(im,*COMBO[k],MONO[CF.get("mono","vert")][0] if mode in ("gb","fond_vert") else (255,230,0),GEO["combo"])
        if VTXT and tag.endswith("+viseur"): draw_target(im,WINBOX[k][0],VTXT,vcol,None if mode=="gb" else (10,10,14))
    enc.stdin.write(FXE.frame(k,np.array(im.convert("RGB"))).tobytes()); log.append(tag)
enc.stdin.close(); enc.wait(); json.dump(log,open(f"{wd}/log.json","w")); print(out,NOUT,"images à",FOUT,"i/s")
