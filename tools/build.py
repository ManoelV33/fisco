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
    a = ap.parse_args()
    if len(a.codigo) < 4:
        raise SystemExit("A senha precisa ter pelo menos 4 caracteres.")
    temas, questoes = [], []
    for f in sorted(glob.glob(os.path.join(a.pacotes, "tema-*.json"))):
        t = json.load(open(f))
        temas.append({k: t[k] for k in ("id", "materia", "titulo") if k in t} | ({"resumoTexto": t["resumoTexto"]} if t.get("resumoTexto") else {}))
    for f in sorted(glob.glob(os.path.join(a.pacotes, "pacote-*.json"))):
        p = json.load(open(f))
        for q in p["questoes"]:
            d = {k: q[k] for k in ("id", "tipo", "enunciado", "alternativas", "gabarito", "comentario", "fonteProva", "banca", "reserva", "sim", "prioridade") if k in q and q[k] not in (None, "", [])}
            d["temaId"] = p["temaId"]
            questoes.append(d)
    cards = []
    if a.extra and os.path.exists(a.extra):
        ex = json.load(open(a.extra))
        cards = ex.get("cards", [])
        res = ex.get("resumos", {})
        for t in temas:
            if t["id"] in res:
                t["resumo"] = res[t["id"]]
    marca = re.compile(r"==[0-9a-f]{6}==")
    def limpar(o):
        if isinstance(o, str): return marca.sub("", o)
        if isinstance(o, list): return [limpar(x) for x in o]
        if isinstance(o, dict): return {k: limpar(v) for k, v in o.items()}
        return o
    temas, questoes = limpar(temas), limpar(questoes)
    conteudo = {"geradoEm": int(time.time() * 1000), "temas": temas, "questoes": questoes, "cards": cards}
    bruto = gzip.compress(json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")).encode(), 9)
    salt, iv = secrets.token_bytes(16), secrets.token_bytes(12)
    chave = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(a.codigo.encode())
    cifrado = AESGCM(chave).encrypt(iv, bruto, None)
    os.makedirs(os.path.join(RAIZ, "data"), exist_ok=True)
    with open(os.path.join(RAIZ, "data", "conteudo.enc"), "wb") as f:
        f.write(struct.pack(">I", ITER) + salt + iv + cifrado)
    versao = time.strftime("%Y%m%d%H%M%S")
    sw = open(os.path.join(RAIZ, "sw.js")).read()
    sw = re.sub(r'const VERSAO = "[^"]*";', f'const VERSAO = "{versao}";', sw)
    open(os.path.join(RAIZ, "sw.js"), "w").write(sw)
    print(f"{len(temas)} temas, {len(questoes)} questões, {len(cards)} cards -> data/conteudo.enc ({len(cifrado)//1024} KB), versão {versao}")

if __name__ == "__main__":
    main()
