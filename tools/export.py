import os, re, json, gzip, base64, time, unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import parse

OUT = "/home/claude/out"
os.makedirs(OUT, exist_ok=True)
ATIVAS = 15
RESERVA = 30

MATERIA = {
    "PDFs Estratégia Contabilidade": "Contabilidade Geral e Avançada",
    "PDFs Estratégia Direito Administrativo": "Direito Administrativo",
    "PDFs Estratégia Direito Constitucional": "Direito Constitucional",
    "PDFs Estratégia Direito Tributário": "Direito Tributário",
    "PDFs Estratégia Português": "Português",
    "pdfs Raciocínio Lógico": "Raciocínio Lógico",
    "Pdfs Tecnologia da Informação": "Tecnologia da Informação",
}
TITULO = {
    "1 - CONT. GERAL E AVANÇADA (ASPECTOS INTROD)": "01 – Aspectos introdutórios",
    "2 - CONT. GERAL E AVANÇADA (PATRIMONIO)": "02 – Patrimônio",
    "3 - CONT. GERAL E AVANÇADA (ATOS E FATOS)": "03 – Atos e fatos contábeis",
    "4 - CONT. GERAL E AVANÇADA (ESCRITURACAO)": "04 – Escrituração",
    "5- CONT. GERAL E AVANÇADA (DCs)": "05 – Demonstrações contábeis e Balanço Patrimonial",
    "6- CONT. GERAL E AVANÇADA (DRE)": "06 – DRE",
    "7 - CONT. GERAL E AVANÇADA (RESERVA DE LUCROS E DIVIDENDOS)": "07 – Reservas de lucros e dividendos",
    "8 - CONT. GERAL E AVANÇADA (DLPA)": "08 – DLPA",
    "9 - CONT. GERAL E AVANÇADA (DMPL)": "09 – DMPL",
    "10 - CONT. GERAL E AVANÇADA (DFC)": "10 – DFC",
    "11 - CONT. GERAL E AVANÇADA (DVA)": "11 – DVA",
    "1 - DIREITO ADM": "01 – Regime jurídico e princípios administrativos",
    "2 - DIREITO ADM": "02 – Noções iniciais e Administração Pública",
    "3 - DIREITO ADM": "03 – Organização administrativa (parte 1): direta, indireta e autarquias",
    "4 - DIREITO ADM": "04 – Organização administrativa (parte 2): empresas estatais e fundações",
    "5 - DIREITO ADM": "05 – Terceiro setor: Sistema S, OS, OSCIP e OSC",
    "1 - Direito Constitucional": "01 – Teoria da Constituição, poder constituinte e princípios fundamentais",
    "2 - Direito Constitucional": "02 – Aplicação no tempo e interpretação constitucional",
    "3 - Direito Constitucional": "03 – Teoria geral dos direitos fundamentais",
    "4 - Direito Constitucional": "04 – Direitos individuais e coletivos (art. 5º, I a XXXI)",
    "5 - Direito Constitucional": "05 – Art. 5º (XXXII a LXXIX) e remédios constitucionais",
    "6 - Direito Constitucional": "06 – Direitos sociais",
    "1 - DT": "01 – Conceito e espécies de tributos",
    "2 - DT": "02 – Limitações ao poder de tributar e princípios",
    "3 - DT": "03 – Imunidades tributárias",
    "4 - DT": "04 – Competência tributária",
    "5 - DT": "05 – Legislação tributária: vigência, aplicação, interpretação e integração",
    "6 - DT": "06 – Obrigação tributária, fato gerador e sujeitos",
    "1 - PORTUGUÊS": "01 – Ortografia e acentuação",
    "2 - PORTUGUÊS": "02 – Classes de palavras I",
    "3 - PORTUGUÊS": "03 – Classes de palavras II: preposições e conjunções",
    "4 - PORTUGUÊS": "04 – Verbos",
    "1 - RACIOCINIO LOGICO": "01 – Proposições, conectivos e tabela-verdade",
    "Aula 02 - Conceitos Básicos de Bancos de Dados": "02 – Conceitos básicos de bancos de dados",
    "Aula 03": "03 – Modelagem conceitual",
    "Aula 04 - Modelagem Relacional": "04 – Modelagem relacional",
    "Aula 05 - Normalizacao": "05 – Normalização",
}
PULAR = {"1o - CONT. GERAL E AVANÇADA (DFC)"}  # cópia do 10 (DFC)

FISCAL = re.compile(r"Auditor|AFRFB|AFRE|AFTE|Receita|RFB|SEFAZ|SEF[-/ ]|SEFIN|SEFA\b|SEMEF|SMF|Fiscal|Tribut|\bISS\b|Fazenda|Fazendári", re.I)

# concursos de nível parecido com o fiscal (boas questões para treinar)
SIMILAR = re.compile(r"\bPF\b|Pol[ií]cia Federal|\bPRF\b|\bMPU\b|\bMP[A-Z]{0,2}\b|Minist[ée]rio P[úu]blico|\bTRT|\bTRF|\bTRE|\bTSE\b|\bSTJ\b|\bSTF\b|\bTST\b|\bTCU\b|\bTCE|\bTCM|\bTC-?DF\b|\bCGU\b|\bCGE|\bCGM|\bAGU\b|\bPGE|\bPGM|\bPGFN\b|\bBACEN\b|Banco Central|\bCVM\b|\bSUSEP\b|\bANAC\b|\bANTT\b|\bANP\b|\bANEEL\b|\bANS\b|\bANVISA\b|Senado|C[âa]mara dos Deputados|\bDPU\b|\bDPE|Delegado|Procurador|Perito|Controle Externo|Controle Interno|Analista", re.I)
# cargos de nível médio (peso menor)
MEDIO = re.compile(r"T[ée]cnico|Assistente|Auxiliar|Escritur[áa]rio|Agente Administrativo|N[íi]vel M[ée]dio|Soldado|Oficial de Promotoria", re.I)

def slug(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]

def chave(s):
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))[:120]

def depende_dados(q, materia):
    e = q["enunciado"]
    if "```" in e:
        return False
    if q["tipo"] == "me":
        nums = sum(1 for a in q["alternativas"] if re.match(r"^\s*(R\$\s*)?[\d\.\,]+", a))
        if nums >= 3 and len(e) < 320:
            return True
    if re.match(r"^[a-zà-ú]", e.strip()):
        return True
    f = q["fonteProva"]
    if not re.search(r"(19[89]\d|20[0-2]\d)", f) and not q["banca"]:
        return True
    if re.search(r"(seguinte|abaixo|a seguir|desse|deste|nesse|neste|do|no)\s+(trecho de\s+)?(diagrama|figura|esquema|imagem|gráfico|organograma|fluxograma|mapa)\b", e, re.I) and "```" not in e:
        return True
    if re.search(r"(informações|dados|situação hipotética|texto|tabela|quadro|rol)\s+(precedentes?|anteriores?)|com base no texto|considerando o texto|de acordo com o texto", e, re.I) and "```" not in e and len(e) < 900:
        return True
    if re.search(r"(informações|dados|tabela|quadro|balancete|texto)\s+(a seguir|abaixo|acima|anterior)|questões seguintes|questão anterior|mesmos dados", e, re.I) and len(e) < 400:
        return True
    if re.search(r"\b(texto|trecho|fragmento)\b", e, re.I) and re.search(r"linha|parágrafo|no texto|do texto", e, re.I) and len(e) < 600 and materia == "Português":
        return True
    return False

PESO = {"Direito Tributário": 3, "Contabilidade Geral e Avançada": 3}

def quantas(materia, teoria_kb, pool):
    """Quantas questões principais e extras o conteúdo recebe.
    Tamanho do assunto (teoria) + quanto ele é cobrado (questões no PDF) + peso da matéria para auditor fiscal."""
    sc = teoria_kb / 10 + pool / 12
    base = 10 if sc < 8 else 12 if sc < 15 else 15 if sc < 25 else 18 if sc < 35 else 20
    base += PESO.get(materia, 0)
    ativ = max(min(10, pool), min(base, int(pool * 0.6)))
    return ativ, min(30, pool - ativ)

def nivel(q):
    """Nível estimado (1 básico, 2 intermediário, 3 avançado): cargo/órgão da prova, banca e complexidade da questão.
    É uma estimativa: os PDFs não trazem o percentual real de acerto dos candidatos."""
    f = q.get("fonteProva", ""); d = 0.0
    if re.search(r"Auditor|AFRFB|AFRE|AFTE|AFTM|Fiscal de Rendas|Fiscal de Tributos|Agente Fiscal|Analista Tribut", f, re.I): d += 2
    elif re.search(r"SEFAZ|SEFIN|SEF[-/ ]|Receita|RFB|\bISS\b|\bSMF\b|Fazenda|SEFA\b|SEMEF", f, re.I): d += 1.5
    elif re.search(r"Analista|Fiscal|Procurador|Delegado|Perito|Controle Externo|Controle Interno|Especialista|Consultor|Juiz|Promotor|Defensor", f, re.I): d += 1
    elif SIMILAR.search(f): d += 0.75
    if re.search(r"T[ée]cnico|Assistente|Auxiliar|Escritur|Soldado|Agente Administrativo", f, re.I) and not re.search(r"Auditor|Analista|Fiscal", f, re.I): d -= 1
    b = q.get("banca", "")
    if b == "FGV": d += 0.5
    elif b not in ("CEBRASPE", "FCC", "ESAF", ""): d -= 0.5
    n = len(q["enunciado"] + " " + " ".join(q.get("alternativas") or []))
    d += 0.5 * ((n > 700) + (n > 1100) + (n > 1700))
    if "```" in q["enunciado"]: d += 1
    if re.search(r"(^|\n)\s*(I|II|III|IV)\s*[\-–.)]", q["enunciado"]): d += 0.5
    return 1 if d <= 0.5 else 2 if d <= 2.0 else 3

def score(q):
    s = 0.0
    f = q["fonteProva"]
    if FISCAL.search(f):
        s += 3
    elif SIMILAR.search(f):
        s += 1.5
    if MEDIO.search(f) and not re.search(r"Auditor|Analista|Fiscal", f, re.I):
        s -= 1
    ys = [int(y) for y in re.findall(r"(?<!\d)(19[89]\d|20[0-2]\d)(?!\d)", f)]
    y = max(ys) if ys else 0
    if y >= 2021: s += 2
    elif y >= 2016: s += 1
    elif 0 < y < 2010: s -= 1
    if re.search(r"Inédit", f, re.I): s -= 2.5
    elif re.search(r"Adaptad", f, re.I): s -= 0.5
    if not f: s -= 1
    return s, y

def build(subdir, fname):
    base = fname[:-4]
    name = subdir + "__" + base + ".txt"
    r = parse.process(name)
    materia = MATERIA[subdir]
    titulo = TITULO[base]
    tid = "imp-" + slug(materia)[:12] + "-" + slug(titulo)[:30]
    # dedupe and filter
    seen = set(); qs = []
    for q in r["questions"]:
        k = chave(q["enunciado"] + "|".join(q["alternativas"] or []))
        if k in seen: continue
        seen.add(k)
        if depende_dados(q, materia): continue
        qs.append(q)
    n = len(qs)
    if n == 0:
        return None
    texts = [q["enunciado"] + " " + " ".join(q["alternativas"] or []) + " " + q["assunto"] for q in qs]
    vec = TfidfVectorizer(strip_accents="unicode", lowercase=True, min_df=1, ngram_range=(1, 2), max_features=20000, token_pattern=r"(?u)\b\w\w\w+\b")
    X = vec.fit_transform(texts)
    S = cosine_similarity(X)
    np.fill_diagonal(S, 0)
    sc = []
    for i, q in enumerate(qs):
        s, y = score(q)
        rec = float((S[i] > 0.25).sum())
        s += min(2.0, 0.5 * rec)
        if not q.get("comentada", True): s -= 0.5
        sc.append(s)
    sc = np.array(sc)
    teoria_kb = len(parse.theory_text(r["theory"]).encode()) / 1000
    n_ativ, n_res = quantas(materia, teoria_kb, n)
    limite_tipo = max(1, int(round(n_ativ * 2 / 3)))
    # MMR selection for the 12 active
    sel = []
    tipos = {"ce": 0, "me": 0}
    cand = list(range(n))
    nv = [nivel(q) for q in qs]
    # proporção de dificuldade de uma prova fiscal: ~20% básico, 50% intermediário, 30% avançado
    alvo = min(n_ativ, n)
    disp = {k: nv.count(k) for k in (1, 2, 3)}
    cota = {1: round(alvo * .2), 3: round(alvo * .3)}
    cota[2] = alvo - cota[1] - cota[3]
    for _ in range(3):  # redistribui o que faltar num nível para os vizinhos
        for k in (1, 2, 3):
            falta = cota[k] - disp[k]
            if falta > 0:
                cota[k] = disp[k]
                for viz in ((2,) if k != 2 else (3, 1)):
                    cota[viz] += falta; break
    usados = {1: 0, 2: 0, 3: 0}
    while len(sel) < alvo:
        best, bv = None, -1e9
        for i in cand:
            if i in sel: continue
            if usados[nv[i]] >= cota[nv[i]] and any(usados[k] < cota[k] and any(nv[j] == k and j not in sel for j in cand) for k in (1, 2, 3)):
                continue
            if tipos[qs[i]["tipo"]] >= limite_tipo and sum(1 for j in cand if j not in sel and qs[j]["tipo"] != qs[i]["tipo"]) > 0:
                continue
            red = max((S[i][j] for j in sel), default=0)
            v = sc[i] - 3.0 * red
            if v > bv: bv, best = v, i
        if best is None: break
        sel.append(best); tipos[qs[best]["tipo"]] += 1; usados[nv[best]] += 1
    rest = sorted([i for i in range(n) if i not in sel], key=lambda i: -sc[i])
    reserva = rest[:n_res]
    keep = sel + reserva
    import hashlib
    ids = {i: f"{tid}-" + hashlib.sha1(chave(qs[i]["enunciado"] + "|".join(qs[i]["alternativas"] or [])).encode()).hexdigest()[:10] for i in keep}
    out = []
    for i in keep:
        q = qs[i]
        sims = [j for j in np.argsort(-S[i]) if j in ids and S[i][j] > 0.12][:6]
        d = {"id": ids[i], "tipo": q["tipo"], "enunciado": q["enunciado"], "gabarito": q["gabarito"],
             "comentario": q["comentario"], "fonteProva": q["fonteProva"], "banca": q["banca"],
             "assunto": q["assunto"], "origem": "material", "prioridade": round(float(sc[i]), 2),
             "sim": [ids[j] for j in sims], "nivel": nivel(q)}
        if q["tipo"] == "me": d["alternativas"] = q["alternativas"]
        if i in reserva: d["reserva"] = True
        out.append(d)
    theory = parse.theory_text(r["theory"])
    resumo = parse.theory_text(r["resumo"]) if r["resumo"] else ""
    return {"tid": tid, "materia": materia, "titulo": titulo, "arquivo": fname + "", "questoes": out,
            "total": n, "theory": theory, "resumo": resumo}

def check_pii(s):
    # marca d'água do Estratégia: CPF (11 dígitos) seguido de " - Nome"
    return bool(re.search(r"\b\d{11}\s*-\s*[A-ZÀ-Ú][a-zà-ú]+ [A-ZÀ-Ú]", s))

if __name__ == "__main__":
    now = int(time.time() * 1000)
    res = []
    for name in sorted(os.listdir(parse.RAW)):
        subdir, base = name[:-4].split("__", 1)
        if base in PULAR: continue
        b = build(subdir, base + ".pdf")
        if not b: print("SEM QUESTOES", name); continue
        blob = json.dumps(b, ensure_ascii=False)
        assert not check_pii(blob.replace(b["arquivo"], "")), name
        res.append(b)
    for i, b in enumerate(res):
        tid = b["tid"]
        pac = {"temaId": tid, "materia": b["materia"], "questoes": b["questoes"]}
        pj = json.dumps(pac, ensure_ascii=False)
        while len(pj.encode()) > 240000:
            # drop the lowest-priority reserve question
            rs = [q for q in pac["questoes"] if q.get("reserva")]
            worst = min(rs, key=lambda q: q["prioridade"])
            pac["questoes"].remove(worst)
            gone = worst["id"]
            for q in pac["questoes"]:
                q["sim"] = [x for x in q["sim"] if x != gone]
            pj = json.dumps(pac, ensure_ascii=False)
        gz = base64.b64encode(gzip.compress(b["theory"].encode())).decode()
        tema = {"id": tid, "materia": b["materia"], "titulo": b["titulo"], "arquivo": b["arquivo"], "banca": "",
                "criadoEm": now + i, "status": "pendente", "questoesImportadas": True, "fonteGz": True,
                "fonte": b["theory"][:15000], "cortado": len(b["theory"]) > 15000,
                "extracao": {"encontradas": b["total"], "salvas": sum(1 for q in pac["questoes"] if not q.get("reserva")),
                             "reserva": sum(1 for q in pac["questoes"] if q.get("reserva")), "em": now}}
        if b["resumo"]:
            tema["resumoTexto"] = b["resumo"][:60000]
        json.dump(tema, open(f"{OUT}/tema-{tid}.json", "w"), ensure_ascii=False)
        json.dump(pac, open(f"{OUT}/pacote-{tid}.json", "w"), ensure_ascii=False)
        json.dump({"temaId": tid, "gz": gz}, open(f"{OUT}/fonte-{tid}.json", "w"), ensure_ascii=False)
        print(f"{tid:70s} total={b['total']:3d} ativas={tema['extracao']['salvas']} reserva={tema['extracao']['reserva']} pac={len(pj.encode())//1000}KB gz={len(gz)//1000}KB resumo={'sim' if b['resumo'] else 'não'}")
