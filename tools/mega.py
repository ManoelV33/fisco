import sys,os,json
from PIL import Image, ImageDraw
out=sys.argv[1]; dirs=sys.argv[2:]
items=[]
for d in dirs:
    for i,e in enumerate(json.load(open(os.path.join(d,'index.json')))): items.append((os.path.basename(d.rstrip('/'))[:14],i,os.path.join(d,e['arq'])))
cols=5; tw,th=300,210; per=30
for s in range(0,len(items),per):
    g=items[s:s+per]; rows=(len(g)+cols-1)//cols
    sh=Image.new('RGB',(cols*tw,rows*(th+16)),'white'); dr=ImageDraw.Draw(sh)
    for k,(n,i,f) in enumerate(g):
        im=Image.open(f); im.thumbnail((tw-6,th-6)); x,y=(k%cols)*tw,(k//cols)*(th+16)
        sh.paste(im,(x+3,y+16)); dr.text((x+3,y+2),f"{n}#{i}",fill='red')
    sh.save(f"{out}{s//per}.png")
print(len(items))
