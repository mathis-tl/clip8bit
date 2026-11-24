"""3b : grammaire d'un mix de DJ. Détecte les changements de morceau (nouveauté sur chroma + timbre + basses),
puis mesure, à chaque frontière : tempo avant/après, clé avant/après, durée du chevauchement, moment de l'échange de basses.
Usage : python scripts/mix_grammaire.py <mix.wav> <sortie.json>
"""
import sys, json, numpy as np, librosa
from scipy.signal import butter, sosfiltfilt, find_peaks
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from analyse import tonalite

SR, HOP = 22050, 512
FPS_ = SR / HOP

def caracteristiques(y):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    chroma = librosa.feature.chroma_stft(S=S, sr=SR)
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=S**2, sr=SR)), n_mfcc=13)
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    bas = S[(freqs >= 40) & (freqs <= 150)].sum(axis=0)
    return chroma, mfcc, bas

def lisser(x, n):
    k = np.ones(n) / n
    return np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, x)

def nouveaute(chroma, mfcc, noyau_s=12):
    """courbe de nouveauté (noyau en damier) sur des blocs de 1 s"""
    n = int(FPS_)                                   # 1 s
    def blocs(x): return np.stack([x[:, i:i + n].mean(axis=1) for i in range(0, x.shape[1] - n, n)], axis=1)
    F = np.vstack([blocs(chroma) / (chroma.max() + 1e-9), blocs(mfcc) / (np.abs(mfcc).max() + 1e-9) * 2])
    F = (F - F.mean(axis=1, keepdims=True)) / (F.std(axis=1, keepdims=True) + 1e-6)
    D = np.linalg.norm(F[:, :, None] - F[:, None, :], axis=0); Ssim = np.exp(-D / D.mean())
    L = noyau_s; g = np.hanning(2 * L)[:, None] * np.hanning(2 * L)[None, :]
    k = np.ones((2 * L, 2 * L)); k[:L, L:] = -1; k[L:, :L] = -1; k = k * g
    Sp = np.pad(Ssim, L, mode="edge"); nov = np.zeros(Ssim.shape[0])
    for i in range(Ssim.shape[0]): nov[i] = (Sp[i:i + 2 * L, i:i + 2 * L] * k).sum()
    return nov / (nov.max() + 1e-9)

def tempo_fenetre(y_seg):
    yp = librosa.effects.percussive(y_seg)
    oenv = librosa.onset.onset_strength(y=yp, sr=SR, hop_length=HOP)
    t = float(np.atleast_1d(librosa.beat.beat_track(onset_envelope=oenv, sr=SR, hop_length=HOP, start_bpm=120)[0])[0])
    while t < 70: t *= 2
    while t > 180: t /= 2
    return float(t)

def main(mix, sortie):
    y, _ = librosa.load(mix, sr=SR, mono=True)
    print("chargé", len(y) / SR, "s")
    chroma, mfcc, bas = caracteristiques(y)
    nov = nouveaute(chroma, mfcc)
    pics, props = find_peaks(nov, height=0.25, distance=40, prominence=0.12)
    out = {"duree_s": len(y) / SR, "nouveaute_s": [round(float(p), 1) for p in pics], "hauteurs": [round(float(nov[p]), 2) for p in pics], "frontieres": []}
    bas_s = lisser(bas[None, :], int(FPS_ * 2))[0]
    for p in pics:
        t0 = float(p)
        def seg(a, b): return y[int(max(a, 0) * SR):int(min(b, len(y) / SR) * SR)]
        av, ap = seg(t0 - 40, t0 - 10), seg(t0 + 10, t0 + 40)
        if len(av) < SR * 15 or len(ap) < SR * 15: continue
        ta, tb = tempo_fenetre(av), tempo_fenetre(ap)
        ka, kb = tonalite(av, SR), tonalite(ap, SR)
        out["frontieres"].append({"t_s": round(t0, 1), "nouveaute": round(float(nov[p]), 2), "bpm_avant": round(ta, 1), "bpm_apres": round(tb, 1), "cle_avant": ka["camelot"], "cle_apres": kb["camelot"]})
    json.dump(out, open(sortie, "w"), indent=1)
    print(len(out["frontieres"]), "frontières")
    for f in out["frontieres"]: print(f)

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
