"""Sections d'un morceau et meilleurs extraits (repli d'allin1). Grille de mesures (enchainer.grille) + similarité entre mesures (chroma + timbre)
+ voix (demucs) + niveau. Sorties : blocs de 8 mesures avec niveau, voix, répétition ; frontières de sections (nouveauté en damier sur les mesures) ;
top-3 extraits de N mesures (alignés sur 4 mesures) classés par : répétition (le passage revient ailleurs dans le titre : refrain), niveau, présence de voix, attaque propre.
LIMITES : la « répétition » favorise un passage qui revient (refrain, mais aussi un couplet répété) ; pas d'étiquettes nommées ; le temps fort de mesure est estimé.
Usage : structure.py <audio.wav> <voix.wav> <sortie.json> [--mesures 8]"""
import sys, os, json, argparse, numpy as np, librosa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchainer import grille, temps_fort
SR = 22050
def db(x): return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
def main(audio, voix, sortie, N=8):
    g = grille(audio); p = g["p"]; bar = 4 * p
    y, _ = librosa.load(audio, sr=SR, mono=True); v, _ = librosa.load(voix, sr=SR, mono=True)
    nb = int((g["duree"] - temps_fort(g, 0)) // bar); t0 = temps_fort(g, 0)
    ch = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=512); mf = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=512); fps = SR / 512
    F, lev, voc = [], [], []
    for k in range(nb):
        a, b = t0 + k * bar, t0 + (k + 1) * bar; fa, fb = int(a * fps), max(int(b * fps), int(a * fps) + 1)
        F.append(np.concatenate([ch[:, fa:fb].mean(axis=1) / (ch[:, fa:fb].mean(axis=1).max() + 1e-9), mf[1:, fa:fb].mean(axis=1) / 40]))
        lev.append(db(y[int(a * SR):int(b * SR)])); voc.append(db(v[int(a * SR):int(b * SR)]))
    F = np.array(F); F = (F - F.mean(axis=0)) / (F.std(axis=0) + 1e-6); lev = np.array(lev); voc = np.array(voc)
    # similarité de blocs de 4 mesures glissants (pas de 1 mesure)
    W = 4; B = np.array([F[i:i + W].ravel() for i in range(nb - W + 1)]); B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-9; S = B @ B.T
    # frontières de sections : noyau en damier sur S
    L = 8; nov = np.zeros(len(S)); k = np.ones((2 * L, 2 * L)); k[:L, L:] = -1; k[L:, :L] = -1; Sp = np.pad(S, L, mode="edge")
    for i in range(len(S)): nov[i] = (Sp[i:i + 2 * L, i:i + 2 * L] * k).sum()
    from scipy.signal import find_peaks
    pk, _ = find_peaks(nov, distance=6, prominence=nov.std() * .5); front = [int(i + L) for i in pk if 4 <= i + L < nb - 2]
    # fenêtres candidates
    cands = []
    corps = np.percentile(lev, 70)
    for s in range(0, nb - N + 1, 4):
        i0 = min(s, len(S) - 1); rep = []
        for kk in range(s, s + N - W + 1, 2):
            j = np.arange(len(S)); mask = np.abs(j - kk) >= N; rep.append(S[min(kk, len(S) - 1)][mask].max() if mask.any() else 0)
        rep = float(np.mean(rep)); nivw = float(np.median(lev[s:s + N])); vw = float(np.median(voc[s:s + N]))
        attaque = float(lev[s] - lev[s - 1]) if s > 0 else 0.0; fin_ok = float(lev[s + N - 1] - nivw)
        score = 2.0 * rep + 0.15 * (nivw - corps) + 0.05 * (vw - np.percentile(voc, 50)) + 0.03 * np.clip(attaque, -3, 6)
        cands.append({"mesure": s, "t_s": round(t0 + s * bar, 1), "duree_s": round(N * bar, 1), "repetition": round(rep, 2), "niveau_db": round(nivw, 1), "voix_db": round(vw, 1), "attaque_db": round(attaque, 1), "score": round(float(score), 2)})
    top = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if all(abs(c["mesure"] - t["mesure"]) >= N for t in top): top.append(c)
        if len(top) == 3: break
    blocs = [{"mesure": s, "t_s": round(t0 + s * bar, 1), "niveau_db": round(float(np.median(lev[s:s + 8])), 1), "voix_db": round(float(np.median(voc[s:s + 8])), 1)} for s in range(0, nb, 8)]
    out = {"audio": audio, "bpm": g["bpm"], "cle": g["cle"], "duree_s": round(g["duree"], 1), "mesures": nb, "sections_frontieres_mesures": front, "sections_frontieres_s": [round(t0 + f * bar, 1) for f in front], "blocs_8_mesures": blocs, "top_extraits": top}
    json.dump(out, open(sortie, "w"), indent=1, default=float); return out
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("voix"); ap.add_argument("sortie"); ap.add_argument("--mesures", type=int, default=8); a = ap.parse_args()
    o = main(a.audio, a.voix, a.sortie, a.mesures); print(o["audio"], o["bpm"], o["cle"], "sections à", o["sections_frontieres_s"]); [print(" ", c) for c in o["top_extraits"]]
