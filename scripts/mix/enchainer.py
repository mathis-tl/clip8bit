"""3c : moteur d'enchaînement de deux morceaux. Produit 6 variantes nommées + un rapport chiffré.
Usage : python scripts/enchainer.py <A.wav> <B.wav> <dossier_stems_ou_-> <sortie_dossier> [--nom paire]
Principe : grille de temps de chaque titre (analyse.py), temps fort de mesure (énergie de grosse caisse), B étiré au tempo de A (rubberband),
sortie de A sur une frontière de phrase (8 mesures), B calé sur le temps fort de A. Contrôles : creux de niveau, écrêtage, décalage des temps
mesuré par intercorrélation des attaques dans le chevauchement (et corrigé s'il dépasse 10 ms), décodage ffmpeg.
Limites : le temps fort de mesure est une estimation (grosse caisse) ; la grille est linéaire sur tout le titre (un titre qui dérive en tempo sera moins bien calé).
"""
import sys, os, json, argparse, subprocess, numpy as np, librosa, pyrubberband as pyrb, soundfile as sf
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyse import analyser
SR = 44100

def charger(p):
    y, _ = librosa.load(p, sr=SR, mono=False)
    return np.vstack([y, y]) if y.ndim == 1 else y

def lisse(u): u = np.clip(u, 0, 1); return u * u * (3 - 2 * u)
def lp(x, fc, o=4): return sosfiltfilt(butter(o, fc, "low", fs=SR, output="sos"), x, axis=-1)

def grille(path):
    r_ = analyser(path); r = r_; y, _ = librosa.load(path, sr=22050, mono=True)
    p, a = r["periode_temps_s"], r["premier_temps_s"]
    sos = butter(4, [40, 120], "band", fs=22050, output="sos"); env = np.abs(sosfiltfilt(sos, y)); env = np.convolve(env, np.ones(441) / 441, mode="same")
    n = int((len(y) / 22050 - a) / p)
    idx = np.clip(((a + np.arange(n) * p) * 22050).astype(int), 0, len(env) - 1)
    m = np.array([env[idx[k::4]].mean() for k in range(4)])
    ch = librosa.feature.chroma_cqt(y=y, sr=22050, hop_length=512); tf = librosa.time_to_frames(a + np.arange(n) * p, sr=22050, hop_length=512)
    tf = tf[tf < ch.shape[1] - 1]; cb = np.stack([ch[:, tf[i]:max(tf[i + 1], tf[i] + 1)].mean(axis=1) for i in range(len(tf) - 1)], axis=1)
    c = np.zeros(4)
    for r in range(4):
        d = [np.linalg.norm(cb[:, i:i + 4].mean(axis=1) - cb[:, i - 4:i].mean(axis=1)) for i in range(r + 4, cb.shape[1] - 4, 4)]; c[r] = np.mean(d) if d else 0
    sc = (m / (m.mean() + 1e-9)) + (c / (c.mean() + 1e-9)); ph = int(np.argmax(sc))
    return {"p": p, "a": a, "phase": ph, "bpm": r_["bpm_affine"], "cle": r_["tonalite"]["camelot"], "contraste_phase": round(float(sc.max() / (np.sort(sc)[-2] + 1e-9)), 2),
            "phase_kick": int(np.argmax(m)), "phase_harmonie": int(np.argmax(c)), "duree": len(y) / 22050}

def temps_fort(g, k): return g["a"] + (g["phase"] + 4 * k) * g["p"]      # début de la mesure k

def env_attaques(x, t0, t1, off):
    seg = x[:, int((t0 - off) * SR):int((t1 - off) * SR)].mean(axis=0)
    seg = librosa.resample(seg, orig_sr=SR, target_sr=22050)
    e = librosa.onset.onset_strength(y=librosa.effects.percussive(seg), sr=22050, hop_length=256); return e - e.mean()

def decalage_ms(xa, xb, off_b, t0, t1, max_ms=150):
    a = env_attaques(xa, t0, t1, 0.0); b = env_attaques(xb, t0, t1, off_b)
    n = min(len(a), len(b)); a, b = a[:n], b[:n]; c = np.correlate(a, b, "full"); m = int(max_ms / 1000 * 22050 / 256)
    lags = np.arange(-(n - 1), n); ok = np.abs(lags) <= m; j = np.argmax(np.where(ok, c, -np.inf)); k = float(lags[j])
    if 0 < j < len(c) - 1 and ok[j - 1] and ok[j + 1]:
        y0, y1, y2 = c[j - 1:j + 2]; k += (y0 - y2) / (2 * (y0 - 2 * y1 + y2) + 1e-12)
    return float(k * 256 / 22050 * 1000)   # >0 : B en retard sur A (recherche bornée à ±150 ms)

def delta_ms(x, t0, t1, tref, p, max_ms=120):
    """écart (ms) entre les attaques réelles de x sur [t0, t1] et la grille tref + k p ; >0 : les attaques sont en retard sur la grille"""
    seg = librosa.resample(x.mean(axis=0)[int(t0 * SR):int(t1 * SR)], orig_sr=SR, target_sr=22050)
    e = librosa.onset.onset_strength(y=librosa.effects.percussive(seg), sr=22050, hop_length=256); e = e - e.mean(); tt = t0 + np.arange(len(e)) * 256 / 22050
    ks = np.arange(int(np.ceil((t0 - tref) / p)), int(np.floor((t1 - tref) / p)) + 1); ds = np.arange(-max_ms, max_ms + 1, 2)
    sc = np.array([np.interp(tref + ks * p + d / 1000, tt, e, left=0, right=0).sum() for d in ds]); return float(ds[int(np.argmax(sc))])

def echo(x, t0, d, g=0.55, n=8):
    out = np.zeros_like(x); seg = x.copy(); seg[:, int(t0 * SR):] = 0
    for k in range(1, n + 1):
        s = int(k * d * SR); out[:, s:] += (g ** k) * seg[:, :x.shape[1] - s]
    out[:, :int(t0 * SR)] = 0; return out

def niveau_db(x, t0, t1):
    s = x.mean(axis=0)[int(max(t0, 0) * SR):int(t1 * SR)]; n = int(.1 * SR); b = s[:len(s) // n * n].reshape(-1, n)
    return 20 * np.log10(np.sqrt((b ** 2).mean(axis=1)) + 1e-9)

def principal(A, B, stems, sortie, nom):
    os.makedirs(sortie, exist_ok=True)
    gA, gB = grille(A), grille(B); rate = gB["p"] / gA["p"]; pA = gA["p"]
    xa, xb = charger(A), charger(B); xb = pyrb.time_stretch(xb.T, SR, rate).T
    aB = gB["a"] / rate; gBs = {"p": pA, "a": aB, "phase": gB["phase"]}
    # même niveau moyen (±6 dB) sur les 30 s qui comptent
    la = np.median(niveau_db(xa, gA["duree"] - 40, gA["duree"] - 10)); lb = np.median(niveau_db(xb, temps_fort(gBs, 0) + 5, temps_fort(gBs, 0) + 35))
    gain_b = float(np.clip(10 ** ((la - lb) / 20), .5, 2.0)); xb = xb * gain_b
    rapport = {"A": gA, "B": gB, "rate_B": round(rate, 4), "gain_B_db": round(20 * np.log10(gain_b), 1), "variantes": {}}
    tB0 = temps_fort(gBs, 0)                      # 1re mesure de B (étiré)
    bar = 4 * pA

    def bornes_mesure(t_max):                     # plus grande frontière de phrase (8 mesures) <= t_max
        k = int((t_max - gA["a"] - gA["phase"] * pA) // (8 * bar)) * 8; return temps_fort(gA, k)
    tA_fin = bornes_mesure(gA["duree"] - 8 * bar - 4)
    tA_mid = bornes_mesure(0.6 * gA["duree"])

    lb_all = niveau_db(xb, tB0, tB0 + 80); corps = float(np.percentile(lb_all, 75))
    def entree_B(apres_mesures=0):            # 1re mesure (pas de 4 mesures) dont les 4 suivantes atteignent corps - 4 dB
        for k in range(apres_mesures, 80, 4):
            t = tB0 + k * bar
            if float(np.median(niveau_db(xb, t, t + 4 * bar))) >= corps - 4: return t, k
        return tB0 + apres_mesures * bar, apres_mesures
    tB_fort, kB_fort = entree_B(0); tB_fort16, kB_fort16 = entree_B(16)
    rapport["entree_B_forte"] = {"mesure": kB_fort, "t_s": round(tB_fort, 1), "mesure_milieu": kB_fort16, "niveau_corps_db": round(corps, 1)}

    def canevas(tA, tB_in):
        oB = tA - tB_in; N = int(max(xa.shape[1], (oB * SR) + xb.shape[1]) + 5 * SR)
        Af = np.zeros((2, N)); Af[:, :xa.shape[1]] = xa; Bf = np.zeros((2, N)); s0 = int(tB_in * SR); seg = xb[:, s0:]
        Bf[:, int(tA * SR):int(tA * SR) + seg.shape[1]] = seg[:, :N - int(tA * SR)]
        return Af, Bf, np.arange(N) / SR, oB

    def sauver(cle, out, t_ref, t_fin, chev=None):
        t0 = max(t_ref - 14, 0); t1 = min(t_fin + 14, out.shape[1] / SR); x = out[:, int(t0 * SR):int(t1 * SR)].copy()
        crete = float(np.abs(x).max()); sc = 1.0
        if crete > .97: sc = .97 / crete; x *= sc
        f = int(.2 * SR); x[:, :f] *= np.linspace(0, 1, f); x[:, -f:] *= np.linspace(1, 0, f)
        wav = f"{sortie}/{nom}_{cle}.wav"; sf.write(wav, x.T, SR, subtype="PCM_16"); mp3 = wav[:-4] + ".mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-b:a", "192k", mp3], check=True)
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-f", "null", "-"], capture_output=True, text=True).stderr.strip()
        win = niveau_db(out, t_ref - bar, t_fin + bar); win = np.convolve(win, np.ones(5) / 5, mode="valid")
        ref = min(np.median(niveau_db(out, t_ref - 10, t_ref - 2)), np.median(niveau_db(out, t_fin + 2, t_fin + 10)))
        creux = float(max(ref - win.min(), 0))
        r = {"fichier": mp3, "duree_s": round(x.shape[1] / SR, 1), "t_sortie_A_s": round(t_ref, 1), "t_sortie_A_pct": round(100 * t_ref / gA["duree"]),
             "creux_niveau_db": round(creux, 1), "creux_ok": creux <= 3.0, "crete_avant_normalisation": round(crete, 3), "attenuation_normalisation_db": round(float(-20 * np.log10(sc)), 1), "decodage_ffmpeg": "ok" if not dec else dec[:120]}
        if chev is not None: r["decalage_temps_ms"] = chev; r["decalage_ok"] = abs(chev) < 20
        rapport["variantes"][cle] = r; print(cle, r)

    # --- 1 et 2 : fondu avec échange de basses
    def fondu(cle, nb):
        tA = tA_fin; Af, Bf, t, oB = canevas(tA, tB0); L = nb * bar
        # alignement : écart des attaques de chaque titre à la grille, ajusté AVANT le chevauchement (A) / sur les 8 premières mesures de B,
        # puis vérifié hors échantillon sur la fenêtre de chevauchement
        dA = delta_ms(Af, tA - 8 * bar, tA, tA, pA); dB = delta_ms(Bf, tA, tA + 8 * bar, tA, pA); chev = dB - dA
        if abs(chev) > 8: Bf = np.roll(Bf, -int(round(chev / 1000 * SR)), axis=1)
        rapport.setdefault("recalage_ms", {})[cle] = {"ecart_A": round(dA, 1), "ecart_B": round(dB, 1), "decalage_B_applique": round(chev if abs(chev) > 8 else 0.0, 1)}
        vA = delta_ms(Af, tA, tA + L, tA, pA); vB = delta_ms(Bf, tA, tA + L, tA, pA); resid = vB - vA
        # intro de B plus faible que A : gain progressif (max +8 dB) qui s'efface après le chevauchement
        ref = float(np.median(niveau_db(Af, tA - 10, tA))); lv = np.convolve(niveau_db(Bf, tA, tA + L + 4 * bar), np.ones(5) / 5, mode="same")
        boost = np.clip(ref - lv, 0, 8); tt = tA + (np.arange(len(boost)) + .5) * .1; g = np.interp(t, tt, boost, left=0, right=0) * (1 - lisse((t - (tA + L + 3 * bar)) / bar))
        Bf = Bf * (10 ** (g / 20))[None, :]
        r = lisse((t - tA) / L); tm = tA + L / 2
        Alo, Blo = lp(Af, 150), lp(Bf, 150); Ahi, Bhi = Af - Alo, Bf - Blo
        out = (1 - lisse((t - tm) / pA)) * Alo + np.cos(r * np.pi / 2) * Ahi + lisse((t - tm) / pA) * Blo + np.sin(r * np.pi / 2) * Bhi
        out[:, t < tA - 1e-9] = Af[:, t < tA - 1e-9]; sauver(cle, out, tA, tA + L, resid)
    fondu("1_fondu_8_mesures_swap_basse", 8); fondu("2_fondu_4_mesures_style_spotify", 4)

    # --- 3 coupe sèche sur le temps fort
    tA = tA_fin; Af, Bf, t, _ = canevas(tA, tB_fort); w = lisse((t - tA) / .008)
    sauver("3_coupe_seche", (1 - w) * Af + w * Bf, tA, tA + 4)

    # --- 4 et 6 : filtre + écho en sortie, B entre sec ; 4 à la fin, 6 en milieu de morceau
    def sortie_echo(cle, tA, tB_in):
        Af, Bf, t, _ = canevas(tA, tB_in); L2 = 2 * bar
        A1, A2, A3 = lp(Af, 6000), lp(Af, 2000), lp(Af, 500); u = np.clip((t - (tA - L2)) / L2, 0, 1)
        w1, w2, w3 = np.clip(1 - 2 * u, 0, 1), 1 - np.abs(2 * u - 1) * 1.0, np.clip(2 * u - 1, 0, 1)
        Ap = np.where(u[None, :] < 1e-9, Af, (1 - u) * Af + u * (w1 * A1 + w2 * A2 + w3 * A3) / (w1 + w2 + w3 + 1e-9))
        cut = lisse((t - tA) / .008); Ap = Ap * (1 - cut); e = echo(Ap, tA, .75 * pA)
        sauver(cle, Ap + e + cut * Bf, tA, tA + 4)
    sortie_echo("4_filtre_echo_fin", tA_fin, tB_fort)
    sortie_echo("6_sortie_milieu_echo_B_apres_intro", tA_mid, tB_fort16)

    # --- 5 voix de A sur l'instrumental de B (demucs)
    if stems != "-" and os.path.exists(f"{stems}/A/vocals.wav") and os.path.exists(f"{stems}/B/no_vocals.wav"):
        av, ai = charger(f"{stems}/A/vocals.wav"), charger(f"{stems}/A/no_vocals.wav")
        bv = pyrb.time_stretch(charger(f"{stems}/B/vocals.wav").T, SR, rate).T * gain_b; bi = pyrb.time_stretch(charger(f"{stems}/B/no_vocals.wav").T, SR, rate).T * gain_b
        # tA : mesure multiple de 8 où la voix de A est la plus présente sur les 8 mesures suivantes (entre 40 % et la fin - 10 mesures)
        cands = [temps_fort(gA, k) for k in range(0, 400, 8) if .4 * gA["duree"] <= temps_fort(gA, k) <= gA["duree"] - 10 * bar]
        if cands:
            tA = max(cands, key=lambda c: float(np.sqrt((av.mean(axis=0)[int(c * SR):int((c + 8 * bar) * SR)] ** 2).mean())))
            n = int(max(av.shape[1], (tA - tB_fort) * SR + bi.shape[1]) + 5 * SR); t = np.arange(n) / SR; s0 = int(tB_fort * SR); o = int(tA * SR)
            def pos(x, src):
                z = np.zeros((2, n)); z[:, :x.shape[1]] = x if src == "A" else 0
                if src == "B": seg = x[:, s0:]; z[:, o:o + seg.shape[1]] = seg[:, :n - o]
                return z
            Av, Ai, Bv, Bi = pos(av, "A"), pos(ai, "A"), pos(bv, "B"), pos(bi, "B")
            r2 = lisse((t - tA) / (2 * bar)); tm = tA + bar; Ailo, Bilo = lp(Ai, 150), lp(Bi, 150)
            inst = (1 - lisse((t - tm) / pA)) * Ailo + np.cos(r2 * np.pi / 2) * (Ai - Ailo) + lisse((t - tm) / pA) * Bilo + np.sin(r2 * np.pi / 2) * (Bi - Bilo)
            tV = tA + 8 * bar; voixA = 1 - lisse((t - (tV - bar)) / bar); voixB = lisse((t - tV) / pA)
            out = inst + voixA * Av + voixB * Bv; sauver("5_voix_A_sur_instru_B", out, tA, tV + bar)
            rapport["variantes"]["5_voix_A_sur_instru_B"]["note"] = "voix de A isolée par demucs ; peut contenir des résidus d'instru"
    else: print("variante 5 ignorée : stems absents")
    json.dump(rapport, open(f"{sortie}/{nom}_rapport.json", "w"), indent=1, default=float)
    return rapport

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("A"); ap.add_argument("B"); ap.add_argument("stems"); ap.add_argument("sortie"); ap.add_argument("--nom", default="paire")
    a = ap.parse_args(); principal(a.A, a.B, a.stems, a.sortie, a.nom)
