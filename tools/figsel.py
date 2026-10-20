"""Converte as figuras escolhidas para webp (mapas girados), sem duplicatas.
Uso: python3 figsel.py sel.json  ->  figsel/<tid>/<id>.webp + figsel/<tid>/figs.json"""
import sys, os, json, hashlib
from PIL import Image

sel = json.load(open(sys.argv[1]))  # {tid: {"dir": figs/..., "ids": [n,...], "girar": [n,...]}}
for tid, s in sel.items():
    idx = json.load(open(os.path.join(s["dir"], "index.json")))
    out = os.path.join("/home/claude/figsel", tid); os.makedirs(out, exist_ok=True)
    lst = []
    for n in s["ids"]:
        e = idx[n]
        im = Image.open(os.path.join(s["dir"], e["arq"])).convert("RGB")
        if n in s.get("girar", []) or e["secao"] == "mapa":
            if im.height > im.width: im = im.rotate(-90, expand=True)
        maxw = 2400 if e["secao"] == "mapa" else 1500
        if im.width > maxw: im = im.resize((maxw, round(im.height * maxw / im.width)), Image.LANCZOS)
        h = hashlib.sha1(im.tobytes()).hexdigest()[:12]
        nome = f"{h}.webp"
        im.save(os.path.join(out, nome), "WEBP", quality=74, method=6)
        lst.append({"id": h, "arq": nome, "pag": e["pag"], "secao": e["secao"], "acima": e["acima"], "w": im.width, "h": im.height,
                    "kb": os.path.getsize(os.path.join(out, nome)) // 1024, "nota": s.get("notas", {}).get(str(n), "")})
    json.dump(lst, open(os.path.join(out, "figs.json"), "w"), ensure_ascii=False, indent=1)
    print(tid, len(lst), sum(x["kb"] for x in lst), "KB")
