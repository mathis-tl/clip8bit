"""Paroles depuis Genius (meilleur sur le jargon rap) :
python lyrics.py <"titre artiste" | url genius> <sortie lyrics.txt>
Sans URL : prend le 1er résultat de la recherche et l'affiche (vérifier que c'est le bon titre).
Cookie de navigateur (cf_clearance) lu dans ~/.config/clip-8bit/genius_cookies.txt, hors dépôt : jamais dans git.
Le texte garde les titres [Couplet…] et les (ad-libs), que align2.py ignore ; les [?] sont des passages que Genius n'a pas transcrits : à relire."""
import sys, re, html, subprocess, json, os, urllib.parse
q, out = sys.argv[1], sys.argv[2]
CJ = os.path.expanduser("~/.config/clip-8bit/genius_cookies.txt")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36"
def get(u): return subprocess.run(["curl", "-s", "-f", "-b", CJ, "-A", UA, u], capture_output=True, text=True, check=True).stdout
if not q.startswith("http"):
    hits = json.loads(get("https://genius.com/api/search/song?per_page=5&q=" + urllib.parse.quote(q)))["response"]["sections"][0]["hits"]
    for h in hits[:5]: print(" -", h["result"]["full_title"], h["result"]["url"])
    q = hits[0]["result"]["url"]
print("page :", q)
def containers(s):
    """contenu de chaque <div data-lyrics-container> en comptant les <div> imbriqués (pubs, annotations) : un simple « jusqu'au 1er </div> » tronque les paroles"""
    out = []
    for m in re.finditer(r'<div data-lyrics-container="true"[^>]*>', s):
        i = m.end(); depth = 1
        for t in re.finditer(r"<div\b|</div>", s[i:]):
            depth += 1 if t.group() != "</div>" else -1
            if depth == 0: out.append(s[i:i + t.start()]); break
    return out
s = get(q); bl = containers(s)
assert bl, "pas de paroles trouvées (cookie expiré ?)"
t = "\n".join(bl); t = re.sub(r"<br\s*/?>", "\n", t); t = html.unescape(re.sub(r"<[^>]+>", "", t))
t = re.sub(r"^.*?Lyrics\s*(?=\[|\n)", "", t, count=1, flags=re.S).strip(); t = re.sub(r"\d*Embed\s*$", "", t).strip()
t = t.translate(str.maketrans("еаоісрх", "eaoicpx"))      # Genius mêle des lettres cyrilliques identiques aux latines (« followеrs ») : elles casseraient l'alignement
open(out, "w").write(t + "\n"); print(f"{len(t.splitlines())} lignes → {out}")
