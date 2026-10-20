import pymupdf, json, os, re, sys
sys.path.insert(0, "/home/claude/res"); from idx_res import idx
M = {"234a2e34": "Tecnologia da Informação", "2e2acb4a": "Contabilidade Geral e Avançada", "57f2853e": "Português",
     "c0f2a54e": "Direito Constitucional", "cb9375c4": "Direito Tributário", "eefadca8": "Direito Administrativo", "f4a73f40": "Raciocínio Lógico"}
out = "/home/claude/meus"; os.makedirs(out, exist_ok=True)
for k, mat in M.items():
    f = f"/home/claude/res/{k}.pdf"; ind, N = idx(f)
    d = pymupdf.open(f)
    for pg in d:
        W, H = pg.rect.width, pg.rect.height; v = [W, H, 0, 0]
        def soma(bb): v[0] = min(v[0], bb[0]); v[1] = min(v[1], bb[1]); v[2] = max(v[2], bb[2]); v[3] = max(v[3], bb[3])
        for b in pg.get_text("dict")["blocks"]:
            if b.get("type") == 0 and not "".join(s["text"] for l in b.get("lines", []) for s in l["spans"]).strip(): continue
            soma(b["bbox"])
        for dr in pg.get_drawings():
            r = dr["rect"]
            if r.width < W * 0.98: soma((r.x0, r.y0, r.x1, r.y1))
        if v[2] > v[0] and v[3] > v[1]:
            r = pymupdf.Rect(max(0, v[0] - 12), max(0, v[1] - 12), min(W, v[2] + 12), min(H, v[3] + 12))
            if r.width > W * 0.3: pg.set_cropbox(r)
    d.rewrite_images(dpi_threshold=150, dpi_target=120, quality=65)
    txt = "".join(p.get_text() for p in d)
    assert not re.search(r"\d{3}\.\d{3}\.\d{3}-\d{2}|03815729513", txt)
    slug = re.sub(r"[^a-z]", "", mat.lower().replace("ç", "c").replace("ã", "a").replace("á", "a").replace("ê", "e").replace("ó", "o").replace("í", "i").replace("ú", "u"))[:20]
    d.save(f"{out}/{slug}.pdf", garbage=4, deflate=True, clean=True)
    json.dump({"materia": mat, "slug": slug, "paginas": N, "indice": ind}, open(f"{out}/{slug}.json", "w"), ensure_ascii=False)
    print(mat, N, os.path.getsize(f"{out}/{slug}.pdf") // 1024, "KB", len(ind))
