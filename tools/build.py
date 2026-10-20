"""Empacota o conteúdo do Caderno Fiscal num arquivo criptografado.

Uso:
    python3 tools/build.py --codigo 123456 --pacotes /caminho/out [--extra /caminho/extra.json]

--pacotes : pasta com tema-*.json e pacote-*.json (gerados por tools/export.py)
--extra   : JSON opcional {"cards":[...], "resumos":{temaId: resumo}} exportado do app no claude.ai
Saída     : data/conteudo.enc  (nunca publique o conteúdo sem criptografia)
"""
import argparse, glob, gzip, json, os, re, struct, time, secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 210000

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codigo", required=True)
    ap.add_argument("--pacotes", required=True)
    ap.add_argument("--extra")
    ap.add_argument("--figuras", help="JSON {temaId: [{sec, img, legenda, mapa}]} com a posição das figuras nos resumos")
    ap.add_argument("--figdir", help="pasta com <temaId>/<img>.webp")
    ap.add_argument("--teoria", help="pasta com <temaId>.pdf/.json (conteúdo do PDF sem questões)")
    ap.add_argument("--meus", help="pasta com <slug>.pdf/.json (resumos do Manoel, por matéria)")
    ap.add_argument("--sem-resumo", action="store_true", help="não inclui o Resumo Fisco")
    a = ap.parse_args()
    if len(a.codigo) < 4:
        raise SystemExit("A senha precisa ter pelo menos 4 caracteres.")
    temas, questoes = [], []
    for f in sorted(glob.glob(os.path.join(a.pacotes, "tema-*.json"))):
        t = json.load(open(f))
        temas.append({k: t[k] for k in ("id", "materia", "titulo") if k in t})
    for f in sorted(glob.glob(os.path.join(a.pacotes, "pacote-*.json"))):
        p = json.load(open(f))
        for q in p["questoes"]:
            d = {k: q[k] for k in ("id", "tipo", "enunciado", "alternativas", "gabarito", "comentario", "fonteProva", "banca", "reserva", "sim", "prioridade", "nivel") if k in q and q[k] not in (None, "", [])}
            d["temaId"] = p["temaId"]
            questoes.append(d)
    cards = []
    if a.extra and os.path.exists(a.extra):
        ex = json.load(open(a.extra))
        cards = ex.get("cards", [])
        res = ex.get("resumos", {})
        for t in temas:
            if t["id"] in res and not a.sem_resumo:
                t["resumo"] = res[t["id"]]
    marca = re.compile(r"==[0-9a-f]{6}==")
    def limpar(o):
        if isinstance(o, str): return marca.sub("", o)
        if isinstance(o, list): return [limpar(x) for x in o]
        if isinstance(o, dict): return {k: limpar(v) for k, v in o.items()}
        return o
    temas, questoes = limpar(temas), limpar(questoes)
    usadas = {}
    if a.figuras:
        figs = json.load(open(a.figuras))
        for t in temas:
            fl = figs.get(t["id"])
            if not fl or "resumo" not in t: continue
            r = json.loads(json.dumps(t["resumo"]))
            extra_sec = []
            # insere de trás para frente para os índices de posição continuarem válidos
            for f in fl:
                caminho = os.path.join(a.figdir, t["id"], f["img"] + ".webp")
                if not os.path.exists(caminho): raise SystemExit("figura não encontrada: " + caminho)
                usadas[f["img"]] = caminho
                b = {"tipo": "figura", "img": f["img"], "legenda": f.get("legenda", ""), "mapa": bool(f.get("mapa"))}
                if f["sec"] == "mapas": extra_sec.append(b); continue
                s = r["secoes"][f["sec"]]
                s.setdefault("_fig", []).append(b)
            for s in r["secoes"]:
                fb = s.pop("_fig", None)
                if fb: s["blocos"] = s["blocos"][:1] + fb + s["blocos"][1:]
            if extra_sec:
                r["secoes"].append({"titulo": "Mapas mentais e esquemas do PDF", "blocos": extra_sec})
            t["resumo"] = r
    docs = {}  # id do documento -> caminho do PDF
    import hashlib
    def doc_id(caminho):
        h = hashlib.sha1(open(caminho, "rb").read()).hexdigest()[:12]; docs[h] = caminho; return h
    if a.teoria:
        for t in temas:
            j = os.path.join(a.teoria, t["id"] + ".json")
            if os.path.exists(j):
                m = json.load(open(j)); t["teoria"] = {"doc": doc_id(os.path.join(a.teoria, t["id"] + ".pdf")), "paginas": m["paginas"], "indice": m["indice"]}
    meus = {}
    if a.meus:
        for j in glob.glob(os.path.join(a.meus, "*.json")):
            m = json.load(open(j)); meus[m["materia"]] = {"doc": doc_id(j[:-5] + ".pdf"), "paginas": m["paginas"], "indice": m["indice"]}
    conteudo = {"geradoEm": int(time.time() * 1000), "temas": temas, "questoes": questoes, "cards": cards, "meus": meus}
    bruto = gzip.compress(json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")).encode(), 9)
    destino = os.path.join(RAIZ, "data", "conteudo.enc")
    salt = None
    if os.path.exists(destino):  # reaproveita o salt se a senha for a mesma (evita recifrar as figuras)
        old = open(destino, "rb").read()
        s0 = old[4:20]
        k0 = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=s0, iterations=struct.unpack(">I", old[:4])[0]).derive(a.codigo.encode())
        try:
            AESGCM(k0).decrypt(old[20:32], old[32:], None); salt = s0
        except Exception:
            pass
    salt = salt or secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    chave = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(a.codigo.encode())
    cifrado = AESGCM(chave).encrypt(iv, bruto, None)
    os.makedirs(os.path.join(RAIZ, "data"), exist_ok=True)
    with open(os.path.join(RAIZ, "data", "conteudo.enc"), "wb") as f:
        f.write(struct.pack(">I", ITER) + salt + iv + cifrado)
    import hashlib
    imgdir = os.path.join(RAIZ, "data", "img"); os.makedirs(imgdir, exist_ok=True)
    for nome in os.listdir(imgdir):
        if nome[:-4] not in usadas: os.remove(os.path.join(imgdir, nome))
    for fid, caminho in usadas.items():
        dados = open(caminho, "rb").read()
        fiv = hashlib.sha256(chave + fid.encode() + hashlib.sha256(dados).digest()).digest()[:12]
        out = fiv + AESGCM(chave).encrypt(fiv, dados, None)
        alvo = os.path.join(imgdir, fid + ".bin")
        if not (os.path.exists(alvo) and open(alvo, "rb").read() == out):
            open(alvo, "wb").write(out)
    docdir = os.path.join(RAIZ, "data", "doc"); os.makedirs(docdir, exist_ok=True)
    for nome in os.listdir(docdir):
        if nome[:-4] not in docs: os.remove(os.path.join(docdir, nome))
    for did, caminho in docs.items():
        alvo = os.path.join(docdir, did + ".bin")
        dados = open(caminho, "rb").read()
        fiv = hashlib.sha256(chave + b"doc" + did.encode()).digest()[:12]
        out = fiv + AESGCM(chave).encrypt(fiv, dados, None)
        if not (os.path.exists(alvo) and open(alvo, "rb").read() == out): open(alvo, "wb").write(out)
    versao = time.strftime("%Y%m%d%H%M%S")
    sw = open(os.path.join(RAIZ, "sw.js")).read()
    sw = re.sub(r'const VERSAO = "[^"]*";', f'const VERSAO = "{versao}";', sw)
    lista = json.dumps(sorted(f"data/img/{x}.bin" for x in usadas))
    sw = re.sub(r'const FIGURAS = \[[^\]]*\];', f'const FIGURAS = {lista};', sw)
    sw = re.sub(r'const DOCS = \[[^\]]*\];', 'const DOCS = ' + json.dumps(sorted(f"data/doc/{x}.bin" for x in docs)) + ';', sw)
    open(os.path.join(RAIZ, "sw.js"), "w").write(sw)
    print(f"{len(temas)} temas, {len(questoes)} questões, {len(cards)} cards -> data/conteudo.enc ({len(cifrado)//1024} KB), {len(usadas)} figuras, {len(docs)} PDFs ({sum(os.path.getsize(c) for c in docs.values())//1048576} MB), versão {versao}")

if __name__ == "__main__":
    main()
