"""Ajuda a reescrever blocos: item(t, trecho) devolve '(BANCA) "enunciado" (GABARITO)' com o texto literal do PDF."""
import json, gzip, base64, re
_cache = {}
PRE = re.compile(r"^(?:.{0,260}?(?:julgue|Julgue|Considerando|Com base|À luz|A respeito|Acerca|No que (?:se refere|tange)|Em relação|Quanto|Relativamente)[^.]{0,220}?(?:item|itens|seguinte|seguintes|subsequente|subsecutivo|próximo|a seguir)[^.]{0,60}?\.)\s+")
def _itens(t):
    if t in _cache: return _cache[t]
    d = json.load(open(f"/home/claude/out/fonte-{t}.json")); txt = re.sub(r"\s+", " ", gzip.decompress(base64.b64decode(d["gz"])).decode())
    p = json.load(open(f"/home/claude/out/pacote-{t}.json")); its = []
    for q in p["questoes"]:
        if q["tipo"] == "ce": its.append((q.get("fonteProva") or "?", re.sub(r"\s+", " ", q["enunciado"]), "CERTO" if q["gabarito"] in ("C", "CERTO") else "ERRADO"))
    for m in re.finditer(r"\(([^()]{3,60}?/?\d{4}[^()]{0,15}|[A-ZÉ][A-Za-zÉ\- ]{2,25})\)\s*(.{20,900}?)\s*Comentários?:?(.{0,2500}?)Gabarito:?\s*(Certo|Errado|CERTO|ERRADO|Correto|Errada|Questão correta|Questão incorreta)", txt):
        g = m.group(4).lower(); its.append((m.group(1), m.group(2), "ERRADO" if g.startswith(("e", "questão inc")) else "CERTO"))
    _cache[t] = its; return its
def banca(f):
    f = re.sub(r"\s*-\s*(Auditor|Analista|Técnico|Procurador|Contador|AUDITOR|Juiz|Regulador)[^/]*", "", f)
    f = re.sub(r"/(Auditor|Analista|Técnico|Procurador|Contador|Regulador)[^/]*/", "/", f)
    return f.strip()
def item(t, trecho, extra="", cortar=True):
    for f, e, g in _itens(t):
        if trecho.lower() in e.lower():
            if cortar: e = PRE.sub("", e)
            e = e.strip().rstrip(".") + "."
            return f'({banca(f)}) "{e}" ({g}{": " + extra if extra else ""})'
    raise SystemExit(f"não achei: {trecho}")
