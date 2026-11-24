"""Basse boostée sur un extrait entier (même traitement que `stemmix.py --boost_db`) : stems demucs (bass, drums, other, vocals) → basse + gain sur la partie < 140 Hz, tanh, limiteur 50 ms, crête ≤ 0,85.
python scripts/mix/boost_basse.py <dossier_stems> <sortie.wav> [gain_db=12]   (dossier_stems = work/.../stems/htdemucs/<nom>)"""
import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
from scipy.ndimage import minimum_filter1d, uniform_filter1d
d, out = sys.argv[1], sys.argv[2]; db = float(sys.argv[3]) if len(sys.argv) > 3 else 12.
S = {k: sf.read(f"{d}/{k}.wav", always_2d=True)[0].T for k in ("bass", "drums", "other", "vocals")}; SR = sf.info(f"{d}/bass.wav").samplerate
n = min(v.shape[1] for v in S.values()); S = {k: v[:, :n] for k, v in S.items()}
orig = sum(S.values()); g = 10 ** (db / 20)
lp = sosfiltfilt(butter(4, 140, btype="low", fs=SR, output="sos"), S["bass"], axis=1)
bb = S["bass"] + (g - 1) * lp; bb = np.tanh(1.6 * bb) / 1.6
mix = bb + S["drums"] + S["other"] + S["vocals"]
bl = int(.05 * SR); mm = n // bl * bl; pk = np.abs(mix[:, :mm]).max(axis=0).reshape(-1, bl).max(axis=1); gl = np.minimum(1, .85 / (pk + 1e-9)); gl = uniform_filter1d(minimum_filter1d(gl, 9), 5); mix[:, :mm] *= np.repeat(gl, bl)[None, :]
cr = float(np.abs(mix).max()); mix = np.tanh(mix / .85) * .85 if cr > .9 else mix; mix *= 10 ** (-1.5 / 20)
mix[:, :int(.01 * SR)] *= np.linspace(0, 1, int(.01 * SR)); mix[:, -int(.03 * SR):] *= np.linspace(1, 0, int(.03 * SR))
sf.write(out, mix.T, SR, subtype="PCM_16")
r = lambda x: 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9)
print(f"{out} : RMS avant {r(orig):.1f} dB, après {r(mix):.1f} dB, crête {np.abs(mix).max():.2f}, basse (<140 Hz) +{db:.0f} dB")
