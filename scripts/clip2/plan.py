"""Planning image par image : styles, niveaux N2/N3, brut court, fenêtres de contour sur plans calmes, cartes punchline.
python plan.py <work_dir>  -> <work>/plan.json (réglages dans <work>/config.json)"""
import sys, json, numpy as np, cv2
wd=sys.argv[1]; CF=json.load(open(f"{wd}/config.json"))
C=json.load(open(f"{wd}/cuts.json")); sc=C["scenes"]; zones=set(C["zones"]); NF=C["n"]; D=np.array(C["d"])
subs=json.load(open(f"{wd}/subs.json"))
PL=CF.get('pulse_len',10)
FIRST=CF["first_scene"]; WIN=CF.get("win",18)                        # fenêtre de contour : 18 images = 0,72 s
TH_MOVE=CF["th_move"]     # mouvement moyen maximal (écart d'images 64×36)
sys.path.insert(0,__file__.rsplit("/",1)[0]); from styles import cycle_of, resolve, ORIG
CYCLE=cycle_of(CF)      # préréglage ou liste de styles (voir styles.py) ; bw = filtre noir et blanc sur la pixellisation de base
NOCONTOUR=set(CF["nocontour_scenes"]); BADWIN=[tuple(x) for x in CF["nocontour_windows"]]
CARD_AT=CF.get("card_at",[])                # lignes de paroles qui reçoivent une carte punchline (début approximatif)
iou=lambda a,b:(a&b).sum()/max(1,(a|b).sum())
SOUPLE=bool(CF.get("viseur_souple"))      # règles de viseur assouplies : couverture ≤ 62 %, IoU .80/.70, centre 30–70 %
CIBLE=CF.get("cible","viseur")        # "viseur" : coins de viseur sur la tête et le buste du personnage central ; "contour" : ancien contour (clips 2 et 3 d'origine)
def keep_big(mk):
    n,lab,st,_=cv2.connectedComponentsWithStats(mk)
    if n<=2: return mk
    big=st[1:,4].max(); return np.isin(lab,[i+1 for i in range(n-1) if st[i+1,4]>=.3*big]).astype(np.uint8)
def box_of(mk,body=.62):
    """boîte de la cible en coordonnées de la grille 240×135 : largeur du buste, hauteur ≥ 62 % du personnage et ≥ 1,5 fois la largeur de la tête ; la 5e valeur est la largeur de la tête"""
    mk=keep_big(mk.astype(np.uint8)); ys,xs=np.nonzero(mk)
    if not len(xs): return None
    y0,y1=ys.min(),ys.max()+1; hh=y1-y0; yh=y0+max(8,int(.40*hh)); xs2=np.nonzero(mk[y0:yh].any(0))[0]; hw=xs2.max()+1-xs2.min()
    yb=min(y1,y0+max(int(body*hh),int(1.5*hw))); xs3=np.nonzero(mk[y0:yb].any(0))[0]
    return (xs3.min(),y0,xs3.max()+1,yb,hw)
def cands(k,s):
    """fenêtres de contour possibles dans la scène k (indépendamment du style) : plan calme, masque stable"""
    if k<FIRST or k in NOCONTOUR or not s.get("stable") or s.get("cover",1)>(.62 if SOUPLE else .55): return []
    ln=s["e"]-s["s"]; m=np.load(f"{wd}/s{k:02d}/mask.npy"); out=[]
    for a in range(s["s"]+4,s["e"]-WIN+1,2):
        if any(f in zones for f in range(a,a+WIN)): continue
        mv=float(D[a:a+WIN].mean()); i0=(a-s["s"])//2; i1=min((a+WIN-s["s"])//2,len(m))
        io=[iou(m[i],m[i-1]) for i in range(i0+1,i1)] or [1]
        cen=[np.array(np.nonzero(m[i])).mean(1) if m[i].any() else np.array([np.nan,np.nan]) for i in range(i0,i1)]
        sh=[np.linalg.norm(x-y) for x,y in zip(cen[:-1],cen[1:])] or [0]      # un saut du centre du masque bien au-dessus du mouvement normal = contour qui saute
        if np.isnan(sh).any() or max(sh)>CF.get("max_jump",5): continue
        if not(mv<=TH_MOVE and np.mean(io)>=(.80 if SOUPLE else .85) and min(io)>=(.70 if SOUPLE else .75)): continue
        box=None
        if CIBLE=="viseur":                    # cible grande et centrée : centre de la boîte entre 35 et 65 % de la largeur, tête de 8 à 50 % de la largeur, boîte ≥ 15 % de la hauteur
            bx=[box_of(m[i]) for i in range(i0,i1)]
            if any(b is None for b in bx): continue
            b=np.median(np.array(bx),axis=0); cx=(b[0]+b[2])/2/240; bh=(b[3]-b[1])/135
            if not((.30 if SOUPLE else .35)<=cx<=(.70 if SOUPLE else .65) and bh>=.15 and .08<=b[4]/240<=.5): continue
            box=[float(x) for x in b[:4]]
        out.append((mv,a,float(np.mean(io)),float(min(io)),box))
    out.sort(); ch=[]
    for c in out:
        if any(k==bk and abs(c[1]-ba)<WIN for bk,ba in BADWIN): continue
        if all(abs(c[1]-b[1])>=WIN+12 for b in ch) and len(ch)<(2 if ln>=75 else 1): ch.append(c)
    return ch
CH=[cands(k,s) for k,s in enumerate(sc)]
MV=CF.get("max_viseurs")      # nombre maximal de viseurs sur le clip : candidats répartis régulièrement
if MV:
    allc=[(k,i) for k in range(len(sc)) for i in range(len(CH[k]))]
    if len(allc)>MV:
        keep={allc[int(round(j*(len(allc)-1)/max(1,MV-1)))] for j in range(MV)}; CH=[[c for i,c in enumerate(CH[k]) if (k,i) in keep] for k in range(len(sc))]
if CF.get("sans_viseur"): CH=[[] for _ in sc]      # aucun viseur (clip 7 Tiakola)
style=[None]*len(sc); ci=0; ngb=0
for k,s in enumerate(sc):
    ln=s["e"]-s["s"]
    if k<FIRST or s["s"]<int(CF.get("live_nb_s",0)*25): style[k]="raw"; continue      # partie live : toujours brut (n&b appliqué par compose), jamais pixel
    if ln<8: style[k]=style[k-1]; continue
    st=resolve(CYCLE[ci%len(CYCLE)],CF); ci+=1
    if st.startswith("fond") and not (s.get("stable") and s.get("cover",1)<=.55): st="gb"      # le fond pixellisé exige un masque fiable (scène stable, personnage ≤ 55 % de l'image)
    if st=="raw" and CH[k]: st=(resolve("gbc",CF) if CF.get("gbc_mode","vif")!="off" else "gb") if not CF.get("repli") else CF["repli"]            # un plan calme avec cible possible reste stylisé : le brut va ailleurs
    if st=="raw" and ln>=CF.get("max_raw_frames",60): st=(resolve("gbc",CF) if CF.get("gbc_mode","vif")!="off" else "gb") if not CF.get("repli") else CF["repli"]   # pas de bloc brut long : la scène reste stylisée, le brut vient des impulsions
    style[k]=st
fr=[dict(m="raw",ol=0,card=None) for _ in range(NF)]
pulses=0; windows=[]
for k,s in enumerate(sc):
    for f in range(s["s"],s["e"]): fr[f]["m"]=style[k]
for k,s in enumerate(sc):
    if k<FIRST: continue
    ln=s["e"]-s["s"]
    if style[k]!="raw":
        for mv,a,im,imn,bx in CH[k]:
            for f in range(a,a+WIN): fr[f]["ol"]=1
            windows.append(dict(scene=k,a=a,n=WIN,move=round(mv,2),iou_moy=round(im,2),iou_min=round(imn,2),box=bx))
    # impulsions brutes de 10 images (0,4 s) dans chaque scène stylisée de plus de 1,6 s, loin des contours ;
    # une de plus par tranche de 45 images (les longues scènes ne restent pas 3 s sans respiration brute)
    if style[k]!="raw" and ln>=40:
        want=max(1,ln//CF.get("pulse_every",45)); done=[]
        for a in sorted(range(s["s"]+8,s["e"]-PL-4,3),key=lambda a:abs(a-(s["s"]+ln//2-5))):
            if len(done)>=want: break
            if all(abs(a-b)>=PL+22 for b in done) and not any(fr[f]["ol"] for f in range(a-2,a+PL+2)):
                for f in range(a,a+PL): fr[f]["m"]="raw"
                done.append(a); pulses+=1
for f in zones: fr[f]["m"]="raw"; fr[f]["ol"]=0
MPX=CF.get("max_pixel_s")      # durée maximale d'un passage en pixel n&b par scène : au début de la scène, ou plus le viseur s'il y en a un (±5 images) ; le reste reste en n&b normal
if MPX:
    for k,s_ in enumerate(sc):
        if k<FIRST or style[k]!="bw": continue
        keep=set(range(s_["s"],min(s_["e"],s_["s"]+int(MPX*25))))
        ws=[w for w in windows if w["scene"]==k]
        if ws: keep|=set(f for w in ws for f in range(max(s_["s"],w["a"]-5),min(s_["e"],w["a"]+w["n"]+5)))
        for f in range(s_["s"],s_["e"]):
            if fr[f]["m"]=="bw" and f not in keep and not fr[f]["ol"]: fr[f]["m"]="raw"
RP=CF.get("rouge_pixel")      # {"n": nombre d'inserts, "len_s": durée max} : pixel rouge entre deux flashs (temps forts), le reste du clip n'est pas touché
if RP:
    from scipy.io import wavfile; from scipy.signal import stft, find_peaks
    sr_,x_=wavfile.read(f"{wd}/audio16k.wav"); x_=x_.astype(float)/32768; x_=x_ if x_.ndim==1 else x_.mean(1)
    f_,t_,Z_=stft(x_,sr_,nperseg=512,noverlap=512-128); S_=np.log1p(np.abs(Z_)*30)
    fl=lambda lo,hi: np.convolve(np.maximum(np.diff(S_[(f_>=lo)&(f_<hi)].mean(0),prepend=S_[(f_>=lo)&(f_<hi)].mean(0)[0]),0),np.ones(5)/5,"same")
    F_=fl(40,160)+fl(160,4000)*.6; pk_,_=find_peaks(F_,height=np.percentile(F_,93),distance=int(.38/(t_[1]-t_[0]))); beats=[]; last=-99     # mêmes temps forts que fx.py (_rythme)
    for p_ in pk_:
        k=int(round(float(t_[p_])*25))
        if k>=NF or k<max(sc[FIRST]["s"],52) or fr[k]["m"]=="card" or k-last<int(CF.get("rythme_ecart_s",.8)*25): continue
        last=k; beats.append(k)
    spans=[]
    for b0,b1 in zip(beats,beats[1:]):
        a0=b0+5; a1=min(b1-2,a0+int(RP.get("len_s",.7)*25))
        if a1-a0>=10 and all(fr[f]["m"]!="card" and not fr[f]["ol"] for f in range(a0,a1)) and all(sc_ for sc_ in [1]): spans.append((a0,a1))
    n=RP.get("n",4); pick=[spans[int(round(i*(len(spans)-1)/max(1,n-1)))] for i in range(min(n,len(spans)))] if spans else []
    PL_=RP.get("plat_images",6)      # d'abord PL_ images de brut passé au rouge (sans pixel), puis le pixel rouge
    for a0,a1 in pick:
        for f in range(a0,a1): fr[f]["m"]="rouge_plat" if f<a0+PL_ else "rouge"
    print("pixel rouge :",[(a0,a1) for a0,a1 in pick],"sur",len(beats),"temps forts")
cards=[]
# cartes : CF["cards"] = [{"line": n° de ligne, "from": 1er mot, "to": dernier mot + 1, "min_s": durée mini}] (extrait de la ligne)
# ou, à défaut, CF["card_at"] = instants approximatifs de lignes entières
specs=CF.get("cards") or [dict(line=min(range(len(subs)),key=lambda i:abs(subs[i]["start"]-t))) for t in CARD_AT]
for sp in specs:
    if "at" in sp:      # carte libre {"at": instant en s, "dur_s": durée, "text": texte} : ad-libs courts calés sur le rythme
        j=-1; a=int(round(sp["at"]*25)); n=min(int(round(sp.get("dur_s",.45)*25)),50); text=sp["text"]
    else:               # "end_s" (facultatif) : fin de la carte en secondes, à la place du mot suivant
        j=sp["line"]; s=subs[j]; w0=sp.get("from",0); w1=sp.get("to",len(s["words"]))
        t0=s["t"][w0]; t1=sp["end_s"] if "end_s" in sp else (s["t"][w1] if w1<len(s["t"]) else s["end"])
        a=int(round(t0*25)); n=min(max(int(round((t1-t0)*25)),int(sp.get("min_s",0)*25)),50); text=" ".join(s["words"][w0:w1]).rstrip(",;. ")
    for f in range(a,a+n): fr[f]["m"]="card"; fr[f]["card"]=len(cards); fr[f]["ol"]=0
    cards.append(dict(line=j,a=a,n=n,text=text))
PD=CF.get("pixel_drops")      # {"len_s": durée du pixel, "detect": {...}} : sur chaque gros coup de basse (drop), flash puis passage en pixel n&b ; fx.py ajoute le flash
if PD:
    from overlays import detect_drops
    DR=[int(round(t*25)) for t in detect_drops(f"{wd}/audio16k.wav",**PD.get("detect",{}))]; nd=0
    for k in DR:
        if k<max(sc[FIRST]["s"],52): continue
        for f in range(k,min(NF,k+int(PD.get("len_s",.6)*25))):
            if fr[f]["m"]=="raw" and not fr[f]["ol"]: fr[f]["m"]="bw"
        nd+=1
    print("pixel sur drops :",nd,"drops",DR)
cardf={f for f in range(NF) if fr[f]["m"]=="card"}
for w in list(windows):                          # un contour qui chevauche une carte est supprimé en entier
    if any(f in cardf for f in range(w["a"],w["a"]+w["n"])):
        for f in range(w["a"],w["a"]+w["n"]): fr[f]["ol"]=0
        windows.remove(w)
lvl=[]; n3=0
for k,s in enumerate(sc):                       # N2 par défaut, N3 une scène stylisée sur n3_every
    if style[k] not in ORIG and k>=FIRST and (s["e"]-s["s"])>=8:
        n3+=1; lvl.append(3 if CF["n3_every"] and n3%CF["n3_every"]==0 else 2)      # n3_every 0 : tout en N2
    else: lvl.append(2)
DG={"grosse":1,"tres_grosse":2}.get(CF.get("gbc_grille"),0)        # pixels plus gros sur les scènes gbc : grosse = un niveau de moins (N2→N1 320×180), tres_grosse = deux (N2→N0 240×135)
if DG: lvl=[l-DG if style[k]=="gbc" else l for k,l in enumerate(lvl)]
json.dump(dict(frames=fr,windows=windows,cards=cards,cards_by="index",style=style,lvl=lvl),open(f"{wd}/plan.json","w"))
raw=sum(x["m"]=="raw" for x in fr); card=sum(x["m"]=="card" for x in fr); ol=sum(x["ol"] for x in fr)
print(f"brut {raw/NF:.0%} ({raw} im.) ; cartes {card} im. ; {CIBLE} {len(windows)} fenêtres ({ol} im.) ; impulsions brutes {pulses}")
for w in windows: print("  ",CIBLE,w)
for c in cards: print("  carte",c["a"],c["n"],c["text"][:40])
