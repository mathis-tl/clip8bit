"""Moteur v2 (règles tirées des mixes DJ MEDDAY / Rastine / DOV'X, 134 transitions : le DJ transite au niveau normal du mix, pas sur un outro ; chevauchement médian 20-24 s).
Règles : (1) sortie de A sur une frontière de phrase (8 mesures) située dans un passage dense : niveau >= corps de A - 3 dB sur tout le chevauchement ;
(2) B entre de façon que son premier passage fort tombe au milieu du chevauchement (échange de basses) ; (3) voix de A posée sur une attaque de phrase vocale ;
(4) niveau final aligné sur le niveau médian de A. Variantes : a_fondu_16, b_fondu_4_spotify, c_voix_A_sur_instru_B.
Usage : enchainer2.py A.wav B.wav <stems|-> <sortie> --nom N"""
import sys, os, json, argparse, subprocess, numpy as np, librosa, pyrubberband as pyrb, soundfile as sf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from enchainer import charger, lisse, lp, grille, temps_fort, delta_ms, niveau_db, SR

def principal(A, B, stems, sortie, nom):
    os.makedirs(sortie, exist_ok=True)
    gA, gB = grille(A), grille(B); rate = gB["p"] / gA["p"]; p = gA["p"]; bar = 4 * p
    xa, xb = charger(A), charger(B); xb = pyrb.time_stretch(xb.T, SR, rate).T
    gBs = {"p": p, "a": gB["a"] / rate, "phase": gB["phase"]}; tB0 = temps_fort(gBs, 0)
    nA = niveau_db(xa, 0, gA["duree"]); corpsA = float(np.percentile(nA[int(.1 * len(nA)):int(.9 * len(nA))], 60))
    gain_b = float(np.clip(10 ** ((corpsA - float(np.percentile(niveau_db(xb, tB0 + 10, tB0 + 80), 60))) / 20), .5, 2.0)); xb = xb * gain_b
    corpsB = float(np.percentile(niveau_db(xb, tB0 + 10, tB0 + 80), 60))
    def entree_B(k0=0):
        for k in range(k0, 80, 4):
            t = tB0 + k * bar
            if float(np.median(niveau_db(xb, t, t + 4 * bar))) >= corpsB - 3: return t
        return tB0 + k0 * bar
    tBf = entree_B()
    def tA_dense(L, avant_fin=2.0):
        c = []
        for k in range(0, 400, 8):
            t = temps_fort(gA, k)
            if t < 30 or t + L > gA["duree"] - avant_fin: continue
            if float(np.percentile(niveau_db(xa, t, t + L), 20)) >= corpsA - 3.5: c.append(t)
        return c[-1] if c else None
    rap = {"A": gA, "B": gB, "rate_B": round(rate, 4), "corpsA_db": round(corpsA, 1), "corpsB_db": round(corpsB, 1), "tB_premier_passage_fort_s": round(tBf, 1), "variantes": {}}
    def canevas(tA, tBin, extra=0):
        N = int(max(xa.shape[1], (tA - tBin) * SR + xb.shape[1]) + 5 * SR); Af = np.zeros((2, N)); Af[:, :xa.shape[1]] = xa
        Bf = np.zeros((2, N)); seg = xb[:, int(tBin * SR):]; Bf[:, int(tA * SR):int(tA * SR) + seg.shape[1]] = seg[:, :N - int(tA * SR)]; return Af, Bf, np.arange(N) / SR
    def sauver(cle, out, t0, t1, extra):
        refc = float(np.median(niveau_db(out, t0 - 10, t0))); lv2 = np.convolve(niveau_db(out, t0, t1), np.ones(10) / 10, mode="same"); tt2 = t0 + (np.arange(len(lv2)) + .5) * .1
        tt_ = np.arange(out.shape[1]) / SR; comp = np.interp(tt_, tt2, np.clip(refc - lv2, 0, 6), left=0, right=0); out = out * (10 ** (comp / 20))[None, :]
        a, b = max(t0 - 14, 0), min(t1 + 14, out.shape[1] / SR); x = out[:, int(a * SR):int(b * SR)].copy()
        cible = corpsA; cur = float(np.percentile(niveau_db(x, 0, x.shape[1] / SR), 60)); x *= 10 ** ((cible - cur) / 20)
        x = np.tanh(x * 1.0 / .9) * .9 if np.abs(x).max() > .95 else x
        f = int(.2 * SR); x[:, :f] *= np.linspace(0, 1, f); x[:, -f:] *= np.linspace(1, 0, f)
        wav = f"{sortie}/{nom}_{cle}.wav"; sf.write(wav, x.T, SR, subtype="PCM_16"); mp3 = wav[:-4] + ".mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-b:a", "192k", mp3], check=True)
        dec = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-f", "null", "-"], capture_output=True, text=True).stderr.strip()
        lv = niveau_db(out, t0 - bar, t1 + bar); lv = np.convolve(lv, np.ones(5) / 5, mode="valid"); ref = min(np.median(niveau_db(out, t0 - 10, t0 - 1)), np.median(niveau_db(out, t1 + 1, t1 + 10)))
        r = {"fichier": mp3, "t_sortie_A_s": round(t0, 1), "t_sortie_A_pct": round(100 * t0 / gA["duree"]), "fin_chevauchement_s": round(t1, 1), "creux_niveau_db": round(float(max(ref - lv.min(), 0)), 1),
             "decodage_ffmpeg": "ok" if not dec else dec[:100]}; r.update(extra); rap["variantes"][cle] = r; print(cle, r)
    def fondu(cle, nb):
        L = nb * bar; tA = tA_dense(L)
        if tA is None: print(cle, "aucun passage dense de A assez long"); return
        tBin = max(tBf - L / 2, 0); Af, Bf, t = canevas(tA, tBin)
        W = max(L, min(8 * bar, gA["duree"] - tA - 1)); sh = delta_ms(Bf, tA, tA + W, tA, p) - delta_ms(Af, tA, tA + W, tA, p)
        for _ in range(2):
            if abs(sh) > 8: Bf = np.roll(Bf, -int(round(sh / 1000 * SR)), axis=1)
            W = max(L, min(8 * bar, gA["duree"] - tA - 1)); sh = delta_ms(Bf, tA, tA + W, tA, p) - delta_ms(Af, tA, tA + W, tA, p)
        vA = delta_ms(Af, tA, tA + W, tA, p); vB = delta_ms(Bf, tA, tA + W, tA, p)
        ref = float(np.median(niveau_db(Af, tA - 10, tA))); lv = np.convolve(niveau_db(Bf, tA, tA + L + 4 * bar), np.ones(5) / 5, mode="same")
        tt = tA + (np.arange(len(lv)) + .5) * .1; g = np.interp(t, tt, np.clip(ref - lv, 0, 6), left=0, right=0) * (1 - lisse((t - (tA + L)) / (2 * bar))); Bf = Bf * (10 ** (g / 20))[None, :]
        r = lisse((t - tA) / L); tm = tA + L / 2; Alo, Blo = lp(Af, 150), lp(Bf, 150)
        out = (1 - lisse((t - tm) / p)) * Alo + np.cos(r * np.pi / 2) * (Af - Alo) + lisse((t - tm) / p) * Blo + np.sin(r * np.pi / 2) * (Bf - Blo)
        out[:, t < tA - 1e-9] = Af[:, t < tA - 1e-9]
        sauver(cle, out, tA, tA + L, {"decalage_temps_ms": round(vB - vA, 1), "decalage_ok": abs(vB - vA) < 20, "entree_B_s": round(tBin, 1)})
    fondu("a_fondu_16_mesures", 16); fondu("b_fondu_4_mesures_spotify", 4)
    # c : voix de A sur l'instru de B
    if stems != "-" and os.path.exists(f"{stems}/A/vocals.wav"):
        av, ai = charger(f"{stems}/A/vocals.wav"), charger(f"{stems}/A/no_vocals.wav")
        st = lambda f: pyrb.time_stretch(charger(f).T, SR, rate).T * gain_b
        bv, bi = st(f"{stems}/B/vocals.wav"), st(f"{stems}/B/no_vocals.wav"); vm = av.mean(axis=0); ev = lambda a, b: float(np.sqrt((vm[int(a * SR):int(b * SR)] ** 2).mean()) + 1e-9)
        best = None
        for k in range(8, 400, 8):
            t = temps_fort(gA, k)
            if t < .3 * gA["duree"] or t + 10 * bar > .85 * gA["duree"]: continue
            if float(np.percentile(nA[int(t):int(t + 9 * bar)], 20)) < corpsA - 3.5: continue
            sc = min(ev(t, t + 8 * bar) / ev(t - bar, t), 4.0)           # la voix repart sur une attaque (plafonné)
            soutien = ev(t, t + 8 * bar)
            if best is None or sc * soutien > best[0]: best = (sc * soutien, t, sc)
        if best:
            tA = best[1]; tBin = tBf; N = int(max(av.shape[1], (tA - tBin) * SR + bi.shape[1]) + 5 * SR); t = np.arange(N) / SR; o = int(tA * SR)
            def pos(x, src):
                z = np.zeros((2, N))
                if src == "A": z[:, :x.shape[1]] = x
                else: seg = x[:, int(tBin * SR):]; z[:, o:o + seg.shape[1]] = seg[:, :N - o]
                return z
            hp = lambda x: x - lp(x, 110)
            Av, Ai, Bv, Bi = hp(pos(av, "A")), pos(ai, "A"), pos(bv, "B"), pos(bi, "B")
            r2 = lisse((t - tA) / (2 * bar)); tm = tA + bar; Alo, Blo = lp(Ai, 150), lp(Bi, 150)
            inst = (1 - lisse((t - tm) / p)) * Alo + np.cos(r2 * np.pi / 2) * (Ai - Alo) + lisse((t - tm) / p) * Blo + np.sin(r2 * np.pi / 2) * (Bi - Blo)
            tV = tA + 8 * bar; out = inst + (1 - lisse((t - (tV - bar)) / bar)) * Av * 1.1 + lisse((t - tV) / p) * Bv
            sauver("c_voix_A_sur_instru_B", out, tA, tV + bar, {"attaque_vocale_ratio": round(best[2], 1), "note": "voix isolée demucs, passe-haut 110 Hz, pas de correction de tonalité"})
    json.dump(rap, open(f"{sortie}/{nom}_rapport_v2.json", "w"), indent=1, default=float)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("A"); ap.add_argument("B"); ap.add_argument("stems"); ap.add_argument("sortie"); ap.add_argument("--nom", default="paire")
    a = ap.parse_args(); principal(a.A, a.B, a.stems, a.sortie, a.nom)
