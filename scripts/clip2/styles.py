"""Styles de montage : quelle palette quantifiée chaque style utilise, et préréglages de cycle.
`config.json` : "cycle" (nom de préréglage ou liste de styles), "gbc_mode" (vif|doux|mixte|off), "fond_mode" (vert|bw|doux)."""
GBC_PAL = {"vif": "gbcy", "doux": "gbcd", "mixte": "gbcm"}
PRESETS = {
    "classique": ["gbc", "gb", "raw", "gbc", "bw", "raw", "gbc", "gb", "raw", "gbc", "bw", "raw"],
    # équilibré : gb, bw, gbc (selon gbc_mode), fond (personnage net, fond pixellisé), crt (original + effet) ; le brut reste 1 scène sur 3
    "equilibre": ["gb", "bw", "raw", "gbc", "crt", "raw", "bw", "gb", "raw", "gbc", "crt", "raw"],
    # vert d'abord, n&b deuxième, couleur troisième, sans crt (clip 2 : gb 32 %, bw 17 %, gbc 14 %, brut 28 %, cartes 10 %)
    "vert_nb_couleur": ["gb", "bw", "raw", "gb", "gbc", "raw", "bw", "gb", "raw", "gbc", "bw", "raw", "gb", "bw", "raw"],
    # plus de brut, n&b = vert (clip 2 avec pulse_every 25 : brut 35 %, gbc 27 %, bw 15 %, gb 15 %, cartes 8 %)
    "brut_plus": ["gb", "raw", "bw", "raw", "gbc", "raw", "bw", "gb", "raw", "gbc"],
    # sans couleur vif, brut ≈ 47 % (clip 2 avec pulse_every 20 : raw 47 %, gb 24 %, bw 22 %, cartes 8 %)
    "brut_vert_nb": ["bw", "raw", "bw", "raw", "gb", "raw", "raw", "bw", "raw", "gb", "raw"],
    # brut 45 %, n&b 22 %, vif 13 %, vert 13 %, cartes 8 % (clip 2 : gbc_mode vif, gamma 1.3, n3_every 0, pulse_every 45)
    "brut_vif10": ["bw", "raw", "gb", "raw", "bw", "raw", "raw", "gb", "raw", "bw", "raw", "gbc", "raw", "gb", "raw", "bw", "raw", "raw"],
    # couleur seule : comparer les variantes de gbc_mode, tout le reste identique
    "couleur": ["gbc", "gbc", "raw"],
}
ORIG = ("raw", "crt", "rouge_plat")            # styles « clip original » (pas pixellisés) : ni transition entre eux, ni impulsion brute dans crt
def resolve(st, CF):
    """remplace les styles génériques par le style effectif : gbc (selon gbc_mode), fond (selon fond_mode)"""
    if st == "gbc" and CF.get("gbc_mode", "vif") == "off": return "crt"
    if st == "fond": return "fond_" + CF.get("fond_mode", "vert")
    return st
def pal_of(st, CF):
    """palette quantifiée d'un style (None si le style n'en utilise pas : raw, crt, bit1, card)"""
    if st == "gbc": return GBC_PAL.get(CF.get("gbc_mode", "vif"))
    return {"gb": "gb", "rouge": "gbr", "bw": "gbcy", "fond_vert": "gb", "fond_bw": "gbcy", "fond_doux": "gbcd"}.get(st)
def cycle_of(CF):
    c = CF.get("cycle", "classique"); return PRESETS[c] if isinstance(c, str) else c
