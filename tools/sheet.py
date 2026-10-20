import sys,os,json
from PIL import Image, ImageDraw
d=sys.argv[1]; idx=json.load(open(os.path.join(d,'index.json')))
per=20; cols=4; tw,th=330,230
for s in range(0,len(idx),per):
    grp=idx[s:s+per]; rows=(len(grp)+cols-1)//cols
    sh=Image.new('RGB',(cols*tw,rows*(th+18)),'white'); dr=ImageDraw.Draw(sh)
    for i,e in enumerate(grp):
        im=Image.open(os.path.join(d,e['arq'])); im.thumbnail((tw-8,th-8))
        x,y=(i%cols)*tw,(i//cols)*(th+18)
        sh.paste(im,(x+4,y+18)); dr.text((x+4,y+3),f"{s+i} {e['arq']} {e['secao']}",fill='red')
    sh.save(os.path.join(d,f'_sheet{s//per}.png'))
print(len(idx))
