import re, os, json, sys, collections, unicodedata

RAW = "/home/claude/raw"
LAY = "/home/claude/txt"

CPF_RE = re.compile(r"\b\d{11}\b\s*-\s*[A-ZÀ-Úa-zà-ú ]+")
WM_RE = re.compile(r"^==[0-9a-f]+==$")

def norm_furn(l):
    s = re.sub(r"\d+", "#", l.strip())
    return re.sub(r"\s+", " ", s)

ZW_RE = re.compile("[\u200b\u200c\u200d\u2060\u2063\ufeff\u00ad]")
def pages_of(path):
    t = ZW_RE.sub("", open(path, encoding="utf-8", errors="replace").read())
    t = re.sub(r"==[0-9a-f]{6}==", "", t)
    pg = t.split("\f")
    if pg and not pg[-1].strip():
        pg = pg[:-1]
    return pg

def furniture(pages):
    cnt = collections.Counter()
    for p in pages:
        seen = set(norm_furn(l) for l in p.split("\n") if l.strip())
        cnt.update(seen)
    n = len(pages)
    return {k for k, v in cnt.items() if v >= max(3, 0.35 * n) and not re.match(r'^(Coment|Gabarito|Resposta)', k, re.I)}

def clean_page(p, furn):
    out = []
    for l in p.split("\n"):
        s = l.strip()
        if s and (norm_furn(l) in furn or WM_RE.match(s) or CPF_RE.search(s) or re.fullmatch(r"\d{1,4}", s)):
            continue
        out.append(l.rstrip())
    return out

def index_sections(rawpages):
    """Return list of (title, startpage) from the Índice (raw text keeps page numbers)."""
    head = "\n".join(rawpages[:4])
    lines = [l.strip() for l in head.split("\n")]
    secs = []
    i = 0
    while i < len(lines):
        m = re.match(r"^(\d{1,2})\) (.+)$", lines[i])
        if m:
            title = m.group(2)
            j = i + 1
            # title may wrap; collect until dots line
            while j < len(lines) and not re.fullmatch(r"\.{5,}", lines[j]) and not re.match(r"^\d{1,2}\) ", lines[j]) and j - i < 4:
                if lines[j] and not re.fullmatch(r"\d+", lines[j]):
                    title += " " + lines[j]
                j += 1
            k = j
            page = None
            while k < len(lines) and k - j < 4:
                if re.fullmatch(r"\d{1,4}", lines[k]):
                    page = int(lines[k]); break
                k += 1
            if page is not None and (not secs or page >= secs[-1][1]):
                secs.append((title.strip(), page))
            i = j
        else:
            i += 1
    return secs

HEADER_RE = re.compile(
    r"^\s*(?:\d{1,3}\s*[\.\)–-]\s*)?(?:\((?P<par>[^()]{2,140})\)|(?P<bare>(?:ESTRAT[ÉE]GIA|Estrat[ée]gia|CEBRASPE|CESPE|FGV|FCC|ESAF|VUNESP|CESGRANRIO|IBFC|QUADRIX|IDECAN|AOCP|FUNDATEC|CONSULPLAN|IADES|FEPESE|IBADE|FAURGS|COPEVE|COMPERVE|CONSESP|INSTITUTO|FUNCAB|FUNRIO|UFPR|NC-UFPR|FUMARC|SELECON|AVANÇA|Avança|IGEDUC|OBJETIVA|Inédita|INÉDITA|Questão)[^\n]{0,140}?(?:\d{4}|Inédita|INÉDITA)\)?))\s*(?P<rest>.*)$")
NUM_RE = re.compile(r"^\s*(?!0)\d{1,3}\s*[\.\)–]\s+(?=[A-ZÀ-Úa-zà-ú(\"“])")
ALT_RE = re.compile(r"^\s*(?:\(?([a-eA-E])\))(?:\s+(.*))?$")
COM_RE = re.compile(r"^\s*Coment[áa]rios?\s*[:.]?\s*(.*)$")
GAB_RE = re.compile(r"^\s*Gabarito\s*:?\s*(.*)$", re.I)

def parse_gab(s):
    s = s.strip().rstrip(".").strip()
    u = unicodedata.normalize("NFD", s.lower())
    u = "".join(c for c in u if unicodedata.category(c) != "Mn")
    if re.search(r"anulad|desatualizad|sem gabarito", u):
        return None
    u = re.sub(r"^(a |o )?(questao|item|assertiva|afirmativa|alternativa correta|resposta)\s*(e\s+)?", "", u).strip(" :.")
    m = re.fullmatch(r"(?:letra|alternativa|opcao)?\s*\(?([a-e])\)?", u)
    if m:
        return m.group(1).upper()
    if re.fullmatch(r"(item )?(certo|certa|correto|correta|verdadeiro|v|c)", u):
        return "C"
    if re.fullmatch(r"(item )?(errado|errada|incorreto|incorreta|falso|f|e)", u):
        return "E"
    return None

TABLEISH = re.compile(r"\S\s{3,}\S")

def paragraphs(lines):
    """Join wrapped lines into paragraphs; keep table-like lines verbatim (dedented)."""
    # dedent
    ind = [len(l) - len(l.lstrip()) for l in lines if l.strip()]
    base = min(ind) if ind else 0
    out = []
    buf = ""
    def flush():
        nonlocal buf
        if buf.strip():
            out.append(buf.strip())
        buf = ""
    for l in lines:
        raw = l[base:] if len(l) >= base else l.strip()
        s = re.sub(r"\s{2,}", " ", l.strip())
        if re.fullmatch(r"\(?[CE]\)\s*(Certo|Errado|Certa|Errada)\.?", s):
            continue
        if not s:
            flush(); continue
        rs = re.sub(r"^([•▪●✔➢►\-–])\s{2,}", r"\1 ", raw.strip())
        rs = re.sub(r"\.{4,}", " … ", rs)
        gaps = len(re.findall(r"\S\s{3,}\S", rs))
        numend = re.search(r"\S\s{3,}\(?-?(R\$\s*)?[\d][\d\.,]*\)?%?$", rs)
        toks = rs.split()
        prose = len(toks) >= 6 and sum(1 for t in toks if re.search(r"\d", t)) == 0
        if ((gaps >= 2 and not prose) or numend) and not re.match(r"^[a-eA-E]\)\s", s):
            flush(); out.append("\u2063" + raw.rstrip()); continue  # table line
        s = re.sub(r"\.{4,}", " … ", re.sub(r"^([•▪●✔➢►])\s{2,}", r"\1 ", s))
        if False:
            flush(); out.append("⁣" + raw.rstrip()); continue  # marker for table line
        starts_item = re.match(r"^(\(?[IVX]{1,4}[\)\.\-–]|[a-eA-E]\)|Item\b|Letra\b|\(\+\)|\(-\)|\(=\)|[-•–▪]\s|\d{1,2}[\.\)]\s|Assertiva|Afirmativa)", s)
        if starts_item:
            flush(); buf = s
        else:
            if buf and buf.endswith("-") and not buf.endswith(" -"):
                buf = buf[:-1] + s
            else:
                buf = (buf + " " + s) if buf else s
    flush()
    # merge consecutive table lines into blocks
    res = []
    for p in out:
        if p.startswith("⁣") and res and res[-1].startswith("⁣"):
            res[-1] += "\n" + p[1:]
        elif p.startswith("⁣"):
            res.append(p)
        else:
            res.append(p)
    return res

def render(pars):
    out = []
    for p in pars:
        if p.startswith("⁣"):
            body = p[1:]
            # dedent table block
            ls = body.split("\n")
            ind = min(len(x) - len(x.lstrip()) for x in ls if x.strip())
            out.append("```\n" + "\n".join(x[ind:] for x in ls) + "\n```")
        else:
            out.append(p)
    return "\n\n".join(out)

def bank_of(src):
    u = src.upper()
    for k, pat in [("CEBRASPE", r"CEBRASPE|CESPE"), ("FGV", r"\bFGV\b"), ("FCC", r"\bFCC\b"), ("CESGRANRIO", r"CESGRANRIO"), ("ESAF", r"\bESAF\b"), ("VUNESP", r"VUNESP")]:
        if re.search(pat, u):
            return k
    return ""

def parse_block(lines, sec_banca):
    """lines: question + comment + gabarito line. Returns dict or (None, reason)."""
    gi = max(i for i, l in enumerate(lines) if GAB_RE.match(l))
    gtxt = GAB_RE.match(lines[gi]).group(1)
    gab = parse_gab(gtxt)
    if gab is None:
        return None, "gab"
    letra_explicita = bool(re.search(r"\b(letra|alternativa|op[çc][ãa]o)\b", gtxt, re.I))
    ci = None
    for i, l in enumerate(lines[:gi]):
        if COM_RE.match(l):
            ci = i; break
    if ci is None:
        return None, "nocom"
    # reject blocks that swallowed more than one question
    if sum(1 for l in lines[:gi] if COM_RE.match(l)) > 1:
        return None, "multi"
    for l in lines[ci + 1:gi]:
        if re.match(r"^\s*(\d{1,3}\s*[\.\)–-]\s*)?\([^()]{0,100}(19[89]\d|20[0-2]\d)[^()]{0,40}\)", l) or re.match(r"^\s*\d{1,3}\s*[\.\)]\s*(CEBRASPE|CESPE|FGV|FCC|VUNESP|CESGRANRIO|ESAF)\b", l):
            return None, "multi"
    q = lines[:ci]
    # header: last line matching HEADER or numbered start
    hi = None
    def fonte_ok(l):
        m = HEADER_RE.match(l)
        if not m:
            return False
        src = m.group("par") or m.group("bare") or ""
        return bool(re.search(r"(19[89]\d|20[0-2]\d)|/|\b(CEBRASPE|CESPE|FGV|FCC|ESAF|VUNESP|CESGRANRIO|SEFAZ|SEFIN|Receita|TCE|TCU|TRF|TJ|MP|ISS|Pref)", src))
    for i, l in enumerate(q):
        if fonte_ok(l):
            hi = i
    if hi is None:
        for i, l in enumerate(q):
            if NUM_RE.match(l):
                hi = i; break
    if hi is None:
        return None, "nohead"
    q = q[hi:]
    m = HEADER_RE.match(q[0])
    fonte = ""
    if m:
        fonte = (m.group("par") or m.group("bare") or "").strip().strip("()")
        rest = m.group("rest") or ""
        q[0] = rest
    else:
        q[0] = re.sub(r"^\s*\d{1,3}\s*[\.\)–-]\s*", "", q[0])
    # alternatives
    alts = []
    enun_lines = []
    cur = None
    letters = "abcde"
    for l in q:
        am = ALT_RE.match(l)
        if am and am.group(1).lower() == letters[len(alts)] if len(alts) < 5 else False:
            alts.append([am.group(2) or ""]); continue
        if alts:
            alts[-1].append(l)
        else:
            enun_lines.append(l)
    com_first = re.sub(r"^\s*(Completo|completo)\s*:\s*", "", COM_RE.match(lines[ci]).group(1))
    com_lines = [com_first] + lines[ci + 1:gi]
    enun = render(paragraphs(enun_lines))
    com = render(paragraphs(com_lines))
    if gab in "CE" and not alts and not letra_explicita:
        tipo = "ce"
    elif gab in "ABCDE" and len(alts) in (4, 5) and "ABCDE".index(gab) < len(alts):
        tipo = "me"
    else:
        return None, "shape"
    alt_txt = []
    for a in alts:
        t = render(paragraphs(a))
        alt_txt.append(t)
    if tipo == "me" and any(len(a.strip()) < 1 for a in alt_txt):
        return None, "emptyalt"
    if len(enun) < 25:
        return None, "short"
    if re.search(r"\b(figura|imagem|gráfico|grafico|ilustração|a seguir ilustrad|charge|tirinha)\b", enun, re.I) and not re.search(r"```", enun):
        return None, "figure"
    if len(com) < 15:
        return None, "nocomtext"
    banca = bank_of(fonte) or sec_banca
    return {"tipo": tipo, "enunciado": enun, "alternativas": alt_txt if tipo == "me" else None,
            "gabarito": gab, "comentario": com, "fonteProva": fonte[:140], "banca": banca}, None

def process(name):
    rawp = pages_of(os.path.join(RAW, name))
    layp = pages_of(os.path.join(LAY, name))
    secs = index_sections(rawp)
    furn = furniture(layp)
    npg = len(layp)
    # page -> section index
    def sec_of(pg):  # pg 1-based
        s = None
        for i, (t, p) in enumerate(secs):
            if p <= pg:
                s = i
        return s
    cleaned = [clean_page(p, furn) for p in layp]
    # group lines by section
    bysec = collections.defaultdict(list)
    for i, lines in enumerate(cleaned):
        s = sec_of(i + 1)
        bysec[s].extend(lines + [""])
    questions = []
    reasons = collections.Counter()
    theory = []
    resumo = []
    for si, lines in sorted(bysec.items(), key=lambda x: (-1 if x[0] is None else x[0])):
        title = secs[si][0] if si is not None else ""
        tl = title.lower()
        if "lista de quest" in tl:
            continue
        if "resumo" in tl and "comentad" not in tl:
            resumo.append((title, lines)); continue
        if "comentad" not in tl:
            theory.append((title, lines))
            # questions embedded in theory are still parsed below
        sec_banca = bank_of(title)
        assunto = re.sub(r"\s*-\s*(Quest(õ|o)es Comentadas|Teoria)\s*", " - ", title)
        assunto = re.sub(r"\s*-\s*(CEBRASPE|Cebraspe|CESPE|FGV|FCC|CESGRANRIO|ESAF|VUNESP)\s*$", "", assunto)
        assunto = re.sub(r"^\s*-\s*|\s*-\s*$", "", assunto.replace("Questões Comentadas", "")).strip(" -")
        start = 0
        for i, l in enumerate(lines):
            if re.match(r"^\s*Gabarito\b\s*:?\s*\S", l, re.I) and len(l.strip()) < 60:
                block = lines[start:i + 1]
                start = i + 1
                if not any(COM_RE.match(x) for x in block):
                    continue
                q, why = parse_block(block, sec_banca)
                if q:
                    q["assunto"] = assunto[:90]
                    q["secao"] = si
                    q["ordem"] = len(questions)
                    q["comentada"] = "comentad" in tl
                    questions.append(q)
                else:
                    reasons[why] += 1
    return {"secs": secs, "questions": questions, "reasons": dict(reasons), "theory": theory, "resumo": resumo, "pages": npg}

def theory_text(sections):
    out = []
    for title, lines in sections:
        out.append("## " + title)
        out.append(render(paragraphs(lines)))
    return "\n\n".join(out)

if __name__ == "__main__":
    for name in sorted(os.listdir(RAW)):
        r = process(name)
        tot = len(r["questions"])
        ce = sum(1 for q in r["questions"] if q["tipo"] == "ce")
        print(f"{tot:4d} q ({ce} ce) secs={len(r['secs'])} rej={r['reasons']} resumo={len(r['resumo'])} | {name}")
