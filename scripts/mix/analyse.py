"""Analyse d'un morceau : tempo, grille de temps, premiers temps de mesure, tonalité (Camelot), phrases.
Usage : python scripts/analyse.py <audio> [--debut s] [--fin s] [--sortie analyse.json]
Le tempo est affiné par régression linéaire sur les temps détectés (pas par la durée des mots) ;
un tempo dans [70, 180] est ramené dans cette plage (60 BPM détecté = 120 BPM).
"""
import argparse, json
import numpy as np, librosa

CAMELOT_MAJ = ["8B","3B","10B","5B","12B","7B","2B","9B","4B","11B","6B","1B"]  # C, C#, D...
CAMELOT_MIN = ["5A","12A","7A","2A","9A","4A","11A","6A","1A","8A","3A","10A"]
MAJ = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
MIN = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])

def tonalite(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = (-2, None)
    for k in range(12):
        for nom, prof, tab in (("maj", MAJ, CAMELOT_MAJ), ("min", MIN, CAMELOT_MIN)):
            c = np.corrcoef(chroma, np.roll(prof, k))[0, 1]
            if c > best[0]:
                best = (c, tab[k], nom, k)
    return {"camelot": best[1], "mode": best[2], "score": round(float(best[0]), 3)}

def peigne(y, sr, p0, a0):
    """Cherche (période, phase) qui maximisent l'énergie des basses sur une grille régulière, période à ±3 % de p0."""
    from scipy.signal import butter, sosfiltfilt
    sos = butter(4, [40, 200], btype="band", fs=sr, output="sos")
    b = np.abs(sosfiltfilt(sos, y))
    hop = int(sr * 0.005)                       # 5 ms
    env = b[: len(b) // hop * hop].reshape(-1, hop).mean(axis=1)
    env = env - np.convolve(env, np.ones(40) / 40, mode="same")   # retire la tendance lente
    n = len(env)
    best = (-1e9, p0, a0)
    for p in np.arange(p0 * 0.97, p0 * 1.03, 0.0002):
        k = np.arange(0, int(n * 0.005 / p))
        for ph in np.arange(0, p, 0.005):
            idx = ((ph + k * p) / 0.005).astype(int)
            idx = idx[idx < n]
            sc = env[idx].mean()
            if sc > best[0]: best = (sc, p, ph)
    return best[1], best[2]

def analyser(path, debut=0.0, fin=None):
    dur = None if fin is None else fin - debut
    y, sr = librosa.load(path, sr=22050, mono=True, offset=debut, duration=dur)
    # séparer la percussion pour des temps plus nets
    yp = librosa.effects.percussive(y)
    oenv = librosa.onset.onset_strength(y=yp, sr=sr, hop_length=512)
    tempo0, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=512, start_bpm=120, tightness=200)
    t = librosa.frames_to_time(beats, sr=sr, hop_length=512)
    tempo0 = float(np.atleast_1d(tempo0)[0])
    # régression : t_i = a + i * p  (période p moyenne exacte)
    i = np.arange(len(t))
    p, a = np.polyfit(i, t, 1)
    bpm = 60.0 / p
    while bpm < 70: bpm *= 2
    while bpm > 180: bpm /= 2
    # affinage par peigne sur l'enveloppe des basses (40-200 Hz), comme livestudio.py
    p, a = peigne(y, sr, p, a)
    bpm = 60.0 / p
    while bpm < 70: bpm *= 2
    while bpm > 180: bpm /= 2
    ecart = np.abs(t - (a + np.round((t - a) / p) * p))
    return {
        "fichier": str(path), "debut_s": debut, "duree_s": round(len(y) / sr, 3),
        "bpm_librosa": round(tempo0, 2), "bpm_affine": round(bpm, 2),
        "periode_temps_s": round(float(p), 5),
        "premier_temps_s": round(float(a) + debut, 3),
        "ecart_librosa_ms_median": round(float(np.median(ecart)) * 1000, 1),
        "ecart_librosa_ms_p90": round(float(np.percentile(ecart, 90)) * 1000, 1),
        "tonalite": tonalite(y, sr),
        "temps_s": [round(float(x) + debut, 3) for x in t[:400]],
    }

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("audio"); ap.add_argument("--debut", type=float, default=0.0)
    ap.add_argument("--fin", type=float); ap.add_argument("--sortie")
    a = ap.parse_args()
    r = analyser(a.audio, a.debut, a.fin)
    if a.sortie: json.dump(r, open(a.sortie, "w"), indent=1)
    print({k: v for k, v in r.items() if k != "temps_s"})
