"""Recorta esquema vetorial: python3 vetor.py pdf saida.jpg pagina x0 y0 x1 y1 (pt, aproximado)"""
import sys, pdfplumber
pdf, out, pg = sys.argv[1], sys.argv[2], int(sys.argv[3]); ax0, ay0, ax1, ay1 = map(float, sys.argv[4:8])
with pdfplumber.open(pdf) as d:
    p = d.pages[pg - 1]
    objs = p.rects + p.lines + p.curves + p.chars + p.images
    bx = [ax1, ay1, ax0, ay0]
    for o in objs:
        if o["x0"] >= ax0 - 2 and o["x1"] <= ax1 + 2 and o["top"] >= ay0 - 2 and o["bottom"] <= ay1 + 2:
            bx = [min(bx[0], o["x0"]), min(bx[1], o["top"]), max(bx[2], o["x1"]), max(bx[3], o["bottom"])]
    bx = [max(0, bx[0] - 6), max(0, bx[1] - 6), min(p.width, bx[2] + 6), min(p.height * 0.94, bx[3] + 6)]
    p.crop(bx).to_image(resolution=220).original.convert("RGB").save(out, quality=88)
    print(out, [round(x) for x in bx])
