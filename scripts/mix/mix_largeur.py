"""Largeur de chaque transition d'un mix. Pour chaque frontière t : profil de A = moyenne sur [t-35, t-15], profil de B = [t+15, t+35].
s(u) = (dA-dB)/(dA+dB) sur u in [t-20, t+20] (pas 1 s, lissé 3 s) : -1 = comme A, +1 = comme B. s est normalisé sur sa plage (5e–95e percentile) ; largeur = temps entre s>0,2 et s>0,8.
Écart de séparation A/B affiché : si trop faible (< 0.5), la mesure n'est pas fiable (« incertain »).
"""
import sys, json, numpy as np, librosa
SR, HOP = 22050, 512
def main(mix, fr, sortie):
    y, _ = librosa.load(mix, sr=SR, mono=True)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    mel = librosa.power_to_db(librosa.feature.melspectrogram(S=S**2, sr=SR, n_mels=48)); chroma = librosa.feature.chroma_stft(S=S, sr=SR)
    F = np.vstack([mel / 15, chroma * 2]); n = int(SR / HOP); T = F.shape[1] // n
    B = np.stack([F[:, i * n:(i + 1) * n].mean(axis=1) for i in range(T)], axis=1)   # 1 s
    res = []
    for f in json.load(open(fr))["frontieres"]:
        c = int(round(f["t_s"]))
        if c - 35 < 0 or c + 35 >= T: continue
        A, Bm = B[:, c - 35:c - 15].mean(axis=1), B[:, c + 15:c + 35].mean(axis=1)
        sep = np.linalg.norm(A - Bm) / (np.std(B[:, c - 35:c - 15], axis=1).mean() * np.sqrt(B.shape[0]) + 1e-9)
        u = np.arange(c - 20, c + 21); dA = np.linalg.norm(B[:, u] - A[:, None], axis=0); dB = np.linalg.norm(B[:, u] - Bm[:, None], axis=0)
        s = np.convolve((dA - dB) / (dA + dB + 1e-9), np.ones(3) / 3, mode="same")
        lo, hi = np.percentile(s, 5), np.percentile(s, 95); s = (s - lo) / (hi - lo + 1e-9)   # plage normalisée 0..1
        i0 = np.argmax(s > .2) if (s > .2).any() else None; i1 = np.argmax(s > .8) if (s > .8).any() else None
        if i0 is None or i1 is None or sep < 0.5: res.append({"t_s": f["t_s"], "type": "incertain", "sep": round(float(sep), 2)}); continue
        larg = float(max(i1 - i0, 0)); mid = float(u[0] + (i0 + i1) / 2)
        res.append({"t_s": f["t_s"], "largeur_s": larg, "milieu_s": mid, "decalage_s": round(mid - f["t_s"], 1), "type": "coupe" if larg <= 2 else "court" if larg <= 8 else "long",
                    "sep": round(float(sep), 2), "bpm": f"{f['bpm_avant']}→{f['bpm_apres']}", "cle": f"{f['cle_avant']}→{f['cle_apres']}"})
    json.dump(res, open(sortie, "w"), indent=1)
    for r in res: print(r)
    from collections import Counter; ok = [r for r in res if "largeur_s" in r]
    print(Counter(r["type"] for r in res), "largeur médiane", np.median([r["largeur_s"] for r in ok]) if ok else None)
main(*sys.argv[1:4])
