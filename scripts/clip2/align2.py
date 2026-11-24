import sys, json, re, unicodedata, difflib
wd=sys.argv[1]   # dossier de travail : lit lyrics.txt et whisper.json, écrit subs.json
def nw(s):
    s=unicodedata.normalize("NFD",s.lower().replace("’","'")); s="".join(c for c in s if unicodedata.category(c)!="Mn")
    return re.sub(r"[^a-z0-9]","",s)
lines=[]
for raw in open(f"{wd}/lyrics.txt",encoding="utf-8"):
    main=re.sub(r"\[.*?\]","",re.sub(r"\(.*?\)","",raw)).strip()
    ws=[w for w in re.split(r"\s+",main) if nw(w)]
    if ws: lines.append(ws)
CUT=float(sys.argv[2]) if len(sys.argv)>2 else 60.0   # durée de l'extrait (s)
A=[(li,w) for li,ws in enumerate(lines) for w in ws]
W=json.load(open(f"{wd}/whisper.json"))
B=[w for s in W["segments"] if s["start"]<CUT-0.5 for w in s["words"] if nw(w["word"]) and w["start"]<CUT-0.1]
# mots à plusieurs sous-mots (« ce-vi », « te-tê ») : on les compare sans trait d'union
def sc(a,b):
    x,y=nw(a),nw(b)
    if x==y: return 2.0
    r=difflib.SequenceMatcher(None,x,y).ratio()
    return 1.0 if r>=.75 else (-1.0 if r<.4 else -0.3)
n,m=len(A),len(B); GAP=-0.6
F=[[0.0]*(m+1) for _ in range(n+1)]; P=[[0]*(m+1) for _ in range(n+1)]
for i in range(1,n+1):
    for j in range(1,m+1):
        d=F[i-1][j-1]+sc(A[i-1][1],B[j-1]["word"]); u=F[i-1][j]+GAP; l=F[i][j-1]+GAP
        F[i][j],P[i][j]=max((d,1),(u,2),(l,3))
# semi-global : fin libre (le morceau continue après l'extrait, et l'intro n'est pas dans les paroles)
bi,bj=max(((i,j) for i in range(n+1) for j in (m,) ),key=lambda x:F[x[0]][x[1]])
cand=[(F[n][j],n,j) for j in range(m+1)]+[(F[i][m],i,m) for i in range(n+1)]
_,i,j=max(cand)
tm=[None]*n; ex=[False]*n
while i>0 and j>0:
    p=P[i][j]
    if p==1:
        s=sc(A[i-1][1],B[j-1]["word"])
        if s>0: tm[i-1]=(B[j-1]["start"],B[j-1]["end"]); ex[i-1]=s>=2
        i-=1; j-=1
    elif p==2: i-=1
    else: j-=1
known=[k for k in range(n) if tm[k]]
for a,b in zip(known[:-1],known[1:]):
    for k in range(a+1,b):
        f=(k-a)/(b-a); s=tm[a][1]+(tm[b][0]-tm[a][1])*f if tm[b][0]>tm[a][1] else tm[a][1]
        tm[k]=(s,min(tm[b][0],s+0.25))
last=known[-1]
out=[]; k=0
for li,ws in enumerate(lines):
    idx=[x for x in range(n) if A[x][0]==li]
    if idx[0]>last: break
    ids=[x for x in idx if tm[x]]
    if len(ids)<0.4*len(idx): continue      # ligne coupée par la fin de l'extrait ou non reconnue
    out.append(dict(words=[A[x][1] for x in ids],t=[tm[x][0] for x in ids],start=tm[ids[0]][0],end=tm[ids[-1]][1],exact=round(sum(ex[x] for x in ids)/len(ids),2),total=len(idx)))
for o,nx in zip(out,out[1:]+[None]):
    o["end"]=min(o["end"]+0.3,nx["start"]-0.02) if nx else o["end"]+0.3
json.dump(out,open(f"{wd}/subs.json","w"),ensure_ascii=False)
print("mots calés exactement:",sum(ex),"/",n,"; calés au total:",len([1 for x in tm if x]),"; lignes:",len(out),"sur",len(lines))
for o in out: print(f"{o['start']:5.2f}-{o['end']:5.2f} exact={o['exact']:.2f} mots={len(o['words'])}/{o['total']}")
