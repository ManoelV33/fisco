import pymupdf,sys,re,json
def idx(f):
    d=pymupdf.open(f); out=[]
    for pn,p in enumerate(d):
        prev_bottom=0
        caixas=[dr['rect'] for dr in p.get_drawings() if dr['rect'].width>20 and dr['rect'].height>8 and dr['rect'].width*dr['rect'].height<p.rect.width*p.rect.height*0.5]
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                sp=[s for s in l['spans'] if s['text'].strip()]
                if not sp: continue
                t=re.sub(r'\s+',' ',''.join(s['text'] for s in sp)).strip()
                allb=all(('Bold' in s['font'] or s['flags']&16) for s in sp)
                y=l['bbox'][1]; gap=y-prev_bottom; prev_bottom=l['bbox'][3]
                aula=bool(re.match(r'^\d{1,2}\s*[-–]\s+\S',t))
                if not allb or not (4<len(t)<(200 if aula else 90)) or t in ('CERTO','ERRADO','CORRETO'): continue
                if not aula and re.search(r'[:→\.;,?!]$|→|^["“(=▪•]|^Art\.|:\S|: ',t) or t[0].islower() or not t[0].isalnum(): continue
                if re.match(r'^\d{1,2}\)',t): continue
                if any(c.contains(pymupdf.Rect(l['bbox'])) for c in caixas): continue
                if not (gap>14 or y<80): continue
                n=1 if re.match(r'^\d{1,2}\s*[-–]\s+\S',t) else 2
                out.append({'n':n,'t':t,'p':pn+1})
    return out,len(d)
if __name__=='__main__':
    for f in sys.argv[1:]:
        o,N=idx(f); print(f,N,'pág',len(o),'títulos'); json.dump(o,open(f[:-4]+'.idx.json','w'),ensure_ascii=False)
