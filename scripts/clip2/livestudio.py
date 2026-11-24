"""Montage « live puis studio » avec fondu enchaîné sonore (clip 7 Tiakola, voir LIVE_STUDIO.md).
python livestudio.py mesure <work_live> <work_studio> [t_live_coupe t_studio_coupe]
    période de battement de chaque version (peigne sur la bande grave 40-200 Hz) → rapport de tempo r (live/studio) ;
    si les deux instants de coupe sont donnés : position de la coupe par rapport au temps (0 = sur le temps) et fin de live conseillée.
python livestudio.py monter <work_live> <work_studio> <work_sortie> <L0> <L1> <S_coupe> <S_fin> [--fondu 2.0] [--r 1.018]
    écrit <work_sortie>/clip.mp4 (live L0→L1 accéléré de r, puis studio S_coupe→S_fin, image : coupe nette sur S_coupe ; son : le studio entre
    <fondu> s avant la coupe en fondu à puissance égale, le live s'éteint sur la même durée), raw/ (960×540, 25 i/s), audio16k.wav, source.json,
    puis les contrôles audio (niveaux live / studio / somme, écrêtage, saut d'échantillon) à relire AVANT le rendu.
Les temps sont ceux des fichiers clip.mp4 des dossiers de travail (fetch.py). La coupe image tombe à O = (L1-L0)/r."""
import sys, os, json, subprocess, shutil, numpy as np
from numpy.fft import rfft
def load(f, a=None, b=None):
    c = ["ffmpeg", "-v", "error"] + (["-ss", str(a), "-t", str(b - a)] if a is not None else []) + ["-i", f, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
    return np.frombuffer(subprocess.run(c, capture_output=True, check=True).stdout, np.int16).astype(float)
def onset(x, lo, hi, hop=160):
    w = np.hanning(512); n = (len(x) - 512) // hop; f = np.fft.rfftfreq(512, 1 / 16000); b = (f >= lo) & (f <= hi)
    s = np.log1p(np.abs(np.array([rfft(x[i * hop:i * hop + 512] * w) for i in range(n)]))[:, b]).sum(1); o = np.maximum(0, np.diff(s))
    return np.maximum(o - np.convolve(o, np.ones(40) / 40, "same"), 0)       # 100 valeurs par seconde
def comb(o, a, b, T):
    s = o[int(a * 100):int(b * 100)]; best = (-1, 0)
    for p in np.arange(0, T, .01):
        i = (np.arange(p, b - a, T) * 100).astype(int); i = i[i < len(s)]
        if len(i) and s[i].sum() / len(i) > best[0]: best = (s[i].sum() / len(i), p)
    return best
def beat(o, a, b):
    sc = sorted((comb(o, a, b, T)[0], T) for T in np.arange(.40, .44, .0005)); return sc[-1][1], sc[-1][0], sc[-2][0]
def mesure(wl, ws, tl=None, ts=None):
    ol, os_ = (onset(load(f"{w}/audio16k.wav"), 40, 200) for w in (wl, ws)); Tl, sl, s2l = beat(ol, 15, ol.size / 100 - 2); Ts, ss, s2s = beat(os_, 60, 130)
    print(f"live   : temps = {Tl:.4f} s ({60 / Tl:.1f} BPM), score {sl:.2f} (suivant {s2l:.2f})\nstudio : temps = {Ts:.4f} s ({60 / Ts:.1f} BPM), score {ss:.2f} (suivant {s2s:.2f})")
    r = Tl / Ts; print(f"rapport de tempo r = live/studio = {r:.4f} → accélérer le live de {100 * (r - 1):.1f} % (--r {r:.3f})")
    if tl and ts:
        for nom, o, T, t, w in (("live", ol, Tl, tl, (t_ := max(20, tl - 9), tl - .2)), ("studio", os_, Ts, ts, (ts - 9, ts - .2))):
            p = comb(o, w[0], w[1], T)[1] + w[0]; k = (t - p) / T; print(f"{nom} : coupe à {t} s = {k % 1:.2f} temps après un temps (0 = pile sur le temps)")
        pl = comb(ol, tl - 9, tl - .2, Tl)[1] + tl - 9; ps = comb(os_, ts - 9, ts - .2, Ts)[1] + ts - 9
        fr_s = ((ts - ps) / Ts) % 1; n = round(((tl - pl) / Tl) - fr_s); print(f"fin de live conseillée (grilles de temps alignées, ≈ {tl} s) : L1 = {pl + (n + fr_s) * Tl:.3f} s  [garder « mais » du live après L1]")
def db(x, a, b): s = x[int(a * 16000):int(b * 16000)]; return 20 * np.log10(np.sqrt((s ** 2).mean()) + 1) if len(s) else float("nan")
def monter(wl, ws, wo, L0, L1, SM, S1, D=2.0, R=1.018):
    O = round((L1 - L0) / R, 3); os.makedirs(f"{wo}/raw", exist_ok=True); NORM = "loudnorm=I=-16:TP=-1.5"
    LA = f"[0:a]atrim={L0}:{L1},asetpts=PTS-STARTPTS,atempo={R},{NORM},afade=t=out:st={O - D:.3f}:d={D}:curve=qsin"
    SA = f"[1:a]atrim={SM - D}:{S1},asetpts=PTS-STARTPTS,{NORM},afade=t=in:st=0:d={D}:curve=qsin,adelay={int((O - D) * 1000)}|{int((O - D) * 1000)}"
    NF0 = int(O * 25)      # images de live (entières) ; le studio démarre exactement à l'image suivante
    V = (f"[0:v]trim={L0}:{L1},setpts=(PTS-STARTPTS)/{R},fps=25,trim=end_frame={NF0},setpts=PTS-STARTPTS[v0];[1:v]trim={SM}:{S1},setpts=PTS-STARTPTS,fps=25[v1];[v0][v1]concat=n=2:v=1:a=0[v]")
    ins = ["-i", f"{wl}/clip.mp4", "-i", f"{ws}/clip.mp4"]
    run = lambda *a: subprocess.run(["ffmpeg", "-y", "-v", "error", *a], check=True)
    run(*ins, "-filter_complex", f"{V};{LA}[a0];{SA}[a1];[a0][a1]amix=inputs=2:normalize=0:duration=longest[a]", "-map", "[v]", "-map", "[a]", "-r", "25", "-c:v", "libx264", "-crf", "14", "-c:a", "aac", f"{wo}/clip.mp4")
    run("-i", f"{wo}/clip.mp4", "-vf", "fps=25,scale=960:540", "-q:v", "2", f"{wo}/raw/f%05d.jpg"); run("-i", f"{wo}/clip.mp4", "-ar", "16000", "-ac", "1", f"{wo}/audio16k.wav")
    json.dump(dict(title="live + studio", live_seg=[L0, L1], studio_seg=[SM, S1], live_tempo=R, coupe_s=O, fondu_s=D, start_s=0, end_s=O + S1 - SM), open(f"{wo}/source.json", "w"))
    t = "/tmp/_ls"; shutil.rmtree(t, ignore_errors=True); os.makedirs(t)         # contrôles : composantes seules + somme
    for nom, f in (("live", LA), ("studio", SA)): run(*ins, "-filter_complex", f"{f}[a]", "-map", "[a]", "-ac", "1", "-ar", "16000", f"{t}/{nom}.wav")
    run(*ins, "-filter_complex", f"{LA}[a0];{SA}[a1];[a0][a1]amix=inputs=2:normalize=0:duration=longest[a]", "-map", "[a]", "-ac", "1", "-ar", "16000", f"{t}/somme.wav")
    a, b, m = (load(f"{t}/{n}.wav") for n in ("live", "studio", "somme"))
    print(f"coupe image à {O} s (image {NF0}) ; durée {len(m) / 16000:.2f} s ; fondu {D} s\n  t(s)  live  studio  somme  (dB, fenêtres 0,25 s)")
    for x in np.arange(O - D - .5, O + 1.01, .25): print(f"{x:6.2f} {db(a, x, x + .25):5.1f} {db(b, x, x + .25):6.1f} {db(m, x, x + .25):6.1f}")
    c = int(O * 16000); d = abs(np.diff(m[c - 4800:c + 4800]))
    print(f"pic {abs(m).max() / 32768:.2f} ; écrêtage {int((abs(m) > 32000).sum())} ; saut d'échantillon max à la coupe {int(d.max())} (médian {int(np.median(d))})\nCRITÈRES : somme sans creux > 3 dB ni bosse > 2 dB sur le recouvrement, pas d'écrêtage, studio plein au plus tard sur la coupe.")
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]; opt = {sys.argv[i]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith("--")}
    if a[0] == "mesure": mesure(a[1], a[2], *(float(x) for x in a[3:5]))
    elif a[0] == "monter": monter(a[1], a[2], a[3], *(float(x) for x in a[4:8]), D=float(opt.get("--fondu", 2.0)), R=float(opt.get("--r", 1.018)))
