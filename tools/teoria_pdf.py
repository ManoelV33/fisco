"""Gera, para cada tema, um PDF só com o conteúdo (sem questões), sem dados pessoais, com margens cortadas e índice.
Uso: python3 teoria_pdf.py <saida> [filtro]
Saída: <saida>/<temaId>.pdf e <saida>/<temaId>.json {paginas, indice:[{n,t,p}]}"""
import sys, os, re, json, collections, glob
import pymupdf, io, pytesseract
from PIL import Image
sys.path.insert(0, "/home/claude")
import parse, export

UP = "/mnt/user-data/uploads"
PII = re.compile(r"03815729513|Manoel\s+Victor|==[0-9a-f]{6}==")

def tid_de(sub, base):
    for f in glob.glob("/home/claude/out/tema-*.json"):
        t = json.load(open(f))
        if t.get("arquivo", "").startswith(base): return t["id"], t["titulo"]
    return None, None

def secoes(sub, base):
    rp = parse.pages_of(os.path.join(parse.RAW, f"{sub}__{base}.txt"))
    return parse.index_sections(rp)

def limpar(t): return re.sub(r"\s+", " ", t).strip()

def processar(pdf, out):
    sub = os.path.basename(os.path.dirname(pdf)); base = os.path.basename(pdf)[:-4]
    tid, titulo = tid_de(sub, base)
    if not tid: print("sem tema:", pdf); return
    secs = secoes(sub, base)
    doc = pymupdf.open(pdf); N = len(doc)
    manter = []  # (página 0-based, título da seção)
    for i, (t, p) in enumerate(secs):
        tl = t.lower()
        if "quest" in tl or "lista" in tl or "gabarito" in tl: continue
        fim = secs[i + 1][1] - 1 if i + 1 < len(secs) else N
        for n in range(p, min(fim, N) + 1): manter.append((n - 1, t))
    if not manter: print("sem teoria:", pdf); return
    # linhas que se repetem em muitas páginas = cabeçalho/rodapé
    freq = collections.Counter()
    for n, _ in manter:
        for l in doc[n].get_text("text").split("\n"):
            l = limpar(l)
            if l: freq[l] += 1
    repet = {l for l, c in freq.items() if c >= max(4, len(manter) * 0.3)}
    # tamanho do corpo do texto
    tam = collections.Counter()
    for n, _ in manter[: min(len(manter), 25)]:
        for b in doc[n].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                for s in l["spans"]: tam[round(s["size"])] += len(s["text"])
    corpo = tam.most_common(1)[0][0] if tam else 12
    novo = pymupdf.open(); novo.insert_pdf(doc, from_page=0, to_page=N - 1)
    keep = [n for n, _ in manter]
    novo.select(keep)
    indice, sec_ant = [], None
    for k, (n, st) in enumerate(manter):
        pg = novo[k]; H, W = pg.rect.height, pg.rect.width
        if st != sec_ant:
            indice.append({"n": 1, "t": re.sub(r"\s*-\s*Teoria$", "", st), "p": k + 1}); sec_ant = st
        # títulos internos: letra maior que o corpo
        for b in pg.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                sp = [s for s in l["spans"] if s["text"].strip()]
                if not sp: continue
                t = limpar("".join(s["text"] for s in sp)); sz = max(s["size"] for s in sp)
                if t in repet or len(t) < 4 or len(t) > 95 or PII.search(t): continue
                if l["bbox"][1] < H * 0.07 or l["bbox"][1] > H * 0.93: continue
                if sz >= corpo + 1.7 and len(t) <= 80 and not re.search(r"[\.:;,?!]$", t):
                    nv = 2
                    tt = t[:1] + t[1:].lower() if t.isupper() else t
                    so = lambda s: re.sub(r"[^a-zà-ú0-9]", "", s.lower())
                    if not indice or so(indice[-1]["t"]) != so(tt):
                        indice.append({"n": nv, "t": tt, "p": k + 1})
        # títulos desenhados (caixa de fundo + letras vetoriais): lê por OCR
        R = pg.rect
        caixas = []
        for im in sorted(pg.get_image_info(), key=lambda i: (round(i["bbox"][1]), i["bbox"][0])):
            bb = pymupdf.Rect(im["bbox"])
            if im["width"] <= 4 and im["height"] <= 4 and 14 <= bb.height <= 36:
                if caixas and abs(caixas[-1].y0 - bb.y0) < 3 and bb.x0 <= caixas[-1].x1 + 12: caixas[-1] |= bb
                else: caixas.append(bb)
        for bb in caixas:
            if 50 <= bb.width <= R.width * 0.97 and bb.y0 > R.y0 + 8 and bb.y1 < R.y1 - 8:
                try:
                    pix = pg.get_pixmap(clip=bb, dpi=220)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    t = limpar(pytesseract.image_to_string(img, lang="por", config="--psm 7 --tessdata-dir /home/claude/tessdata"))
                except Exception:
                    continue
                t = re.sub(r"^[^A-Za-zÀ-ú0-9]+|[^A-Za-zÀ-ú0-9\)]+$", "", t)
                so = lambda s: re.sub(r"[^a-zà-ú0-9]", "", s.lower())
                if 3 <= len(t) <= 80 and sum(c.isalpha() for c in t) >= 0.7 * len(t.replace(" ", "")) and (not indice or so(indice[-1]["t"]) != so(t)):
                    indice.append({"n": 2, "t": t, "p": k + 1, "y": bb.y0})
        # dados pessoais e marcas ocultas
        for w in pg.get_text("words"):
            if PII.search(w[4]) or w[4] in ("03815729513",):
                pg.add_redact_annot(pymupdf.Rect(w[:4]) + (-2, -2, 2, 2), fill=(1, 1, 1))
        for r in pg.search_for("Manoel Victor"): pg.add_redact_annot(r + (-2, -2, 2, 2), fill=(1, 1, 1))
        pg.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE, graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)
        # margens: área útil = texto/imagens entre cabeçalho e rodapé
        x0, y0, x1, y1 = W, H, 0, 0
        def soma(bb):
            nonlocal_vals[0] = min(nonlocal_vals[0], bb[0]); nonlocal_vals[1] = min(nonlocal_vals[1], bb[1])
            nonlocal_vals[2] = max(nonlocal_vals[2], bb[2]); nonlocal_vals[3] = max(nonlocal_vals[3], bb[3])
        nonlocal_vals = [W, H, 0, 0]
        for b in pg.get_text("dict")["blocks"]:
            if b.get("type") == 0:
                for l in b.get("lines", []):
                    t = limpar("".join(s["text"] for s in l["spans"]))
                    if not t or t in repet or re.fullmatch(r"\d{1,3}", t): continue
                    cy = (l["bbox"][1] + l["bbox"][3]) / 2
                    if cy < H * 0.06 or cy > H * 0.94: continue
                    soma(l["bbox"])
            else:
                bb = b["bbox"]; cy = (bb[1] + bb[3]) / 2
                if H * 0.06 < cy < H * 0.94 and (bb[3] - bb[1]) < H * 0.9: soma(bb)
        for dr in pg.get_drawings():
            bb = dr["rect"]; cy = (bb.y0 + bb.y1) / 2
            if cy < H * 0.06 or cy > H * 0.94 or bb.width > W * 0.95: continue
            soma((bb.x0, bb.y0, bb.x1, bb.y1))
        x0, y0, x1, y1 = nonlocal_vals
        if x1 > x0 and y1 > y0:
            r = pymupdf.Rect(max(0, x0 - 10), max(0, y0 - 10), min(W, x1 + 10), min(H, y1 + 10)) & pg.mediabox
            if r.width > W * 0.4 and r.height > 60: pg.set_cropbox(r)
    # sem títulos (ex.: aulas por incisos da CF): usa o início de cada inciso citado
    if len(indice) < len(manter) / 8:
        for k in range(len(novo)):
            for b in novo[k].get_text("dict")["blocks"]:
                ls = b.get("lines", [])
                if not ls: continue
                t = limpar("".join(s["text"] for s in ls[0]["spans"]))
                m = re.match(r"^([IVXL]{1,7})\s*[-–—]\s*(.+)", t)
                if m and len(m.group(2)) > 8:
                    tt = f"Inciso {m.group(1)} – {m.group(2)}"
                    tt = tt if len(tt) <= 70 else tt[:67].rsplit(" ", 1)[0] + "…"
                    if not any(e["t"].startswith(f"Inciso {m.group(1)} ") for e in indice):
                        indice.append({"n": 2, "t": tt, "p": k + 1})
        indice.sort(key=lambda e: (e["p"], e["n"]))
    # junta títulos quebrados em várias linhas e descarta faixas em caixa-alta (repetem a seção)
    fin = []
    for e in indice:
        if e["n"] == 2 and "y" in e and e["t"].upper() == e["t"] and len(e["t"]) > 3: continue
        if fin and e["n"] == 2 and "y" in e and fin[-1].get("y") is not None and fin[-1]["p"] == e["p"] and 0 < e["y"] - fin[-1]["y2"] < 0:
            fin[-1]["t"] = re.sub(r"\s\S$", "", fin[-1]["t"]) + " " + re.sub(r"^\S\s", "", e["t"]); fin[-1]["y2"] = e["y"]; continue
        if "y" in e: e["y2"] = e["y"]
        fin.append(e)
    indice = [{"n": e["n"], "t": e["t"], "p": e["p"]} for e in fin]
    novo.rewrite_images(dpi_threshold=140, dpi_target=110, quality=62)
    txt = "".join(p.get_text() for p in novo)
    assert not re.search(r"03815729513|Manoel Victor", txt), "PII em " + pdf
    novo.save(os.path.join(out, tid + ".pdf"), garbage=4, deflate=True, clean=True)
    json.dump({"temaId": tid, "titulo": titulo, "paginas": len(novo), "indice": indice}, open(os.path.join(out, tid + ".json"), "w"), ensure_ascii=False)
    print(f"{tid[:45]:46s} {len(novo):3d} pág {os.path.getsize(os.path.join(out, tid + '.pdf'))//1024:5d} KB  índice {len(indice)}")

if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for pdf in sys.argv[2:]: processar(pdf, out)
