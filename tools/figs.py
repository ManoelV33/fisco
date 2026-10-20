"""Recorta figuras (esquemas, mapas mentais) das partes de teoria/mapa/resumo dos PDFs.
Uso: python3 figs.py <pasta-saida> <arquivo.pdf> [...]
Gera <saida>/<base>/pNNN_k.jpg e um index.json com página, caixa e texto anterior.
A marca d'água (rodapé da página) fica fora do recorte; o recorte é conferido depois."""
import sys, os, json, re, hashlib, collections
import pdfplumber
sys.path.insert(0, "/home/claude")
import parse

UP = "/mnt/user-data/uploads"

def secoes(pdf):
    sub = os.path.basename(os.path.dirname(pdf)); base = os.path.basename(pdf)[:-4]
    rp = parse.pages_of(os.path.join(parse.RAW, f"{sub}__{base}.txt"))
    return parse.index_sections(rp)

def main(out, pdfs):
    for pdf in pdfs:
        base = os.path.basename(pdf)[:-4]
        secs = secoes(pdf)
        bons = []  # (ini, fim, rótulo) das seções úteis
        for i, (t, p) in enumerate(secs):
            tl = t.lower()
            if "quest" in tl or "lista" in tl or "gabarito" in tl: continue
            fim = secs[i + 1][1] - 1 if i + 1 < len(secs) else 10**6
            rot = "mapa" if "mapa" in tl else "resumo" if "resumo" in tl else "teoria"
            bons.append((p, fim, rot))
        d = os.path.join(out, base); os.makedirs(d, exist_ok=True)
        idx = []
        with pdfplumber.open(pdf) as doc:
            # imagens que se repetem em muitas páginas = decoração
            cont = collections.Counter()
            for pg in doc.pages:
                for im in pg.images:
                    cont[(round(im["x1"] - im["x0"]), round(im["bottom"] - im["top"]), im.get("srcsize"))] += 1
            for (ini, fim, rot) in bons:
                for n in range(ini, min(fim, len(doc.pages)) + 1):
                    pg = doc.pages[n - 1]
                    W, H = pg.width, pg.height
                    caixas = []
                    for im in pg.images:
                        w, h = im["x1"] - im["x0"], im["bottom"] - im["top"]
                        if w < 120 or h < 45: continue
                        if cont[(round(w), round(h), im.get("srcsize"))] > 3: continue
                        if w > W * 0.97 and h > H * 0.9: continue  # fundo de página inteira
                        caixas.append([max(0, im["x0"]), max(0, im["top"]), min(W, im["x1"]), min(H * 0.94, im["bottom"])])
                    # junta caixas sobrepostas (imagem + máscara)
                    caixas.sort()
                    junt = []
                    for c in caixas:
                        for j in junt:
                            if not (c[0] > j[2] + 4 or c[2] < j[0] - 4 or c[1] > j[3] + 4 or c[3] < j[1] - 4):
                                j[:] = [min(j[0], c[0]), min(j[1], c[1]), max(j[2], c[2]), max(j[3], c[3])]; break
                        else:
                            junt.append(list(c))
                    for k, c in enumerate(junt):
                        if c[3] - c[1] < 40: continue
                        acima = pg.crop((0, max(0, c[1] - 140), W, c[1])).extract_text() or ""
                        acima = re.sub(r"\s+", " ", acima).strip()[-300:]
                        res = 220 if rot == "mapa" else 170
                        img = pg.crop(c).to_image(resolution=res).original.convert("RGB")
                        nome = f"p{n:03d}_{k}.jpg"
                        img.save(os.path.join(d, nome), quality=82, optimize=True)
                        idx.append({"arq": nome, "pag": n, "secao": rot, "caixa": [round(x) for x in c], "acima": acima,
                                    "w": img.width, "h": img.height})
        json.dump(idx, open(os.path.join(d, "index.json"), "w"), ensure_ascii=False, indent=1)
        print(base, len(idx))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
