"""Pour chaque transition d'un mix : niveau (RMS dB, 1 s) au début du chevauchement, à son milieu, à sa fin, comparé à la médiane locale (±60 s).
Dit si le DJ transite sur du fort (≈ médiane) ou sur des creux (outro/intro), et si le niveau creuse pendant la transition.
Usage : mix_energie.py mix.mp3 largeurs.json"""
import sys, json, numpy as np, librosa
y, sr = librosa.load(sys.argv[1], sr=22050, mono=True); n = sr
rms = 20 * np.log10(np.sqrt((y[:len(y) // n * n].reshape(-1, n) ** 2).mean(axis=1)) + 1e-9)
res = []
for r in json.load(open(sys.argv[2])):
    if "largeur_s" not in r: continue
    m, w = r["milieu_s"], r["largeur_s"]; c = int(round(r["t_s"])); loc = np.median(rms[max(c - 60, 0):c + 60])
    a, b = int(m - w / 2), int(m + w / 2); db = lambda i: float(np.median(rms[max(i - 2, 0):i + 3]) - loc)
    dip = float(rms[max(a, 0):b + 1].min() - loc) if b > a else 0.0
    res.append({"t_s": r["t_s"], "largeur_s": w, "debut_vs_med_db": round(db(a), 1), "milieu_vs_med_db": round(db(int(m)), 1), "fin_vs_med_db": round(db(b), 1), "creux_min_db": round(dip, 1)})
for r in res: print(r)
f = lambda k: np.round(np.median([r[k] for r in res]), 1)
print(len(res), "transitions ; médianes : largeur", np.median([r["largeur_s"] for r in res]), "début", f("debut_vs_med_db"), "milieu", f("milieu_vs_med_db"), "fin", f("fin_vs_med_db"), "creux", f("creux_min_db"))
print("part de transitions longues (>=11 s) :", round(np.mean([r["largeur_s"] >= 11 for r in res]), 2), "; courtes (<=6 s) :", round(np.mean([r["largeur_s"] <= 6 for r in res]), 2))
json.dump(res, open(sys.argv[2].replace("largeurs", "energie"), "w"), indent=1)
