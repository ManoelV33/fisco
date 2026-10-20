"""Lista os blocos do resumo com CERTO/ERRADO fora do padrão e, para cada um, os itens de prova mais parecidos (pacote + teoria).
Uso: python3 revisar.py <temaId>"""
import json, gzip, base64, re, sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

t = sys.argv[1]
ex = json.load(open("/home/claude/extra.json")); r = ex["resumos"][t]
d = json.load(open(f"/home/claude/out/fonte-{t}.json")); txt = re.sub(r"\s+", " ", gzip.decompress(base64.b64decode(d["gz"])).decode())
p = json.load(open(f"/home/claude/out/pacote-{t}.json"))
itens = []
for q in p["questoes"]:
    if q["tipo"] == "ce":
        itens.append((q.get("fonteProva") or "?", re.sub(r"\s+", " ", q["enunciado"]), "CERTO" if q["gabarito"] in ("C", "CERTO") else "ERRADO"))
for m in re.finditer(r"\(([^()]{3,60}?/?\d{4}[^()]{0,15}|[A-ZÉ][A-Za-zÉ\- ]{2,25})\)\s*(.{20,700}?)\s*Comentários?:?(.{0,2500}?)Gabarito:?\s*(Certo|Errado|CERTO|ERRADO|Correto|Errada|Questão correta|Questão incorreta|C\b|E\b)", txt):
    g = m.group(4).lower()
    itens.append((m.group(1), m.group(2), "ERRADO" if g.startswith(("e", "questão inc")) else "CERTO"))
vis = set(); its = []
for i in itens:
    k = i[1][:80]
    if k not in vis: vis.add(k); its.append(i)
blocos = []
pat = re.compile(r"(ERRAD[OA]|CERT[OA]\b)")
for si, s in enumerate(r["secoes"]):
    for bi, b in enumerate(s["blocos"]):
        vals = [b.get("texto", "")] + b.get("itens", []) + [c for l in b.get("linhas", []) for c in l]
        v = " | ".join(x for x in vals if x)
        if pat.search(v) and not all(re.search(r'"\s*\((?:CERTO|ERRADO)', m) for m in [v]):
            # ignora se todas as marcas já estão no padrão novo
            marcas = [m for m in pat.finditer(v) if not re.search(r'"\s*\($', v[max(0, m.start() - 4):m.start()])]
            if marcas: blocos.append((si, bi, b["tipo"], v))
if not blocos: print("0 blocos"); sys.exit()
docs = [i[1] for i in its] + [b[3] for b in blocos]
X = TfidfVectorizer(strip_accents="unicode", ngram_range=(1, 2), min_df=1).fit_transform(docs)
S = cosine_similarity(X[len(its):], X[:len(its)])
print(f"{len(blocos)} blocos, {len(its)} itens\n")
for k, (si, bi, tp, v) in enumerate(blocos):
    print(f"## [{si},{bi}] {tp}: {v}")
    for j in S[k].argsort()[::-1][:4]:
        if S[k][j] > 0.08: print(f"   - ({its[j][0]}) {its[j][1][:330]} ({its[j][2]})")
    print()
