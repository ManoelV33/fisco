(function () {
"use strict";

/* =========================================================
   Fisco: tela de entrada "Rumo ao Fisco" + caderno de estudo offline
   O conteúdo fica em data/conteudo.enc, criptografado com
   AES-GCM; a chave vem da senha digitada na entrada.
   ========================================================= */

const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtInline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/==(.+?)==/g, '<mark class="mk">$1</mark>')
  .replace(/\((CERTO|ERRADO)(:[^)]*)?\)/g, (m, g, r) => `(<strong class="gab gab-${g === "CERTO" ? "c" : "e"}">${g}</strong>${r || ""})`).replace(/\n/g, "<br>");
const fmt = s => String(s ?? "").split(/```\n?/).map((p, i) => i % 2 ? `<pre class="tbl">${esc(p.replace(/\n$/, ""))}</pre>` : fmtInline(p)).join("");
const fmtDoc = s => String(s ?? "").split(/```\n?/).map((p, i) => i % 2 ? `<pre class="tbl">${esc(p.replace(/\n$/, ""))}</pre>` : fmtInline(p).replace(/^## (.+)$/gm, '<span class="res-h">$1</span>')).join("");
const L = ["A", "B", "C", "D", "E"];
const NIVEL = { 1: "Básico", 2: "Intermediário", 3: "Avançado" };
const DAY = 86400000;
const now = () => Date.now();
const ordem = (a, b) => String(a).localeCompare(String(b), "pt", { numeric: true, sensitivity: "base" });

/* resumo v2 (mesmo formato do gerador) */
/* ---------- resumo v2: formato de estudo (compartilhado entre o gerador e o Fisco) ---------- */
const RES_TIPOS = ["texto", "lista", "tabela", "atencao", "excecao", "cai", "dica", "lei", "mnemonico", "esquema", "figura"];
function limparResumo(r) {
  const S = x => String(x == null ? "" : x).trim();
  const out = { visaoGeral: S(r && r.visaoGeral), secoes: [], autoteste: [], alertas: [] };
  for (const s of (r && r.secoes) || []) {
    if (!s || !Array.isArray(s.blocos)) continue;
    const blocos = [];
    for (const b of s.blocos) {
      if (!b || !RES_TIPOS.includes(b.tipo)) continue;
      if (b.tipo === "lista" || b.tipo === "esquema") { const it = (b.itens || []).map(S).filter(Boolean); if (it.length) blocos.push({ tipo: b.tipo, titulo: S(b.titulo), itens: it }); }
      else if (b.tipo === "tabela") { const c = (b.colunas || []).map(S); const l = (b.linhas || []).filter(Array.isArray).map(x => x.map(S)); if (c.length && l.length) blocos.push({ tipo: "tabela", titulo: S(b.titulo), colunas: c, linhas: l }); }
      else if (b.tipo === "mnemonico") { if (S(b.nome)) blocos.push({ tipo: "mnemonico", nome: S(b.nome), explicacao: S(b.explicacao) }); }
      else if (b.tipo === "figura") { if (/^[0-9a-f]{12}$/.test(S(b.img))) blocos.push({ tipo: "figura", img: S(b.img), legenda: S(b.legenda), mapa: !!b.mapa }); }
      else if (b.tipo === "lei") { if (S(b.texto)) blocos.push({ tipo: "lei", ref: S(b.ref), texto: S(b.texto) }); }
      else if (S(b.texto)) blocos.push({ tipo: b.tipo, texto: S(b.texto) });
    }
    if (blocos.length) out.secoes.push({ titulo: S(s.titulo), blocos });
  }
  for (const q of (r && r.autoteste) || []) if (q && S(q.p) && S(q.r)) out.autoteste.push({ p: S(q.p), r: S(q.r) });
  out.alertas = ((r && r.alertas) || []).map(S).filter(Boolean);
  return out;
}
const PROMPT_RESUMO_V2 = `Tarefa: escrever o RESUMO DE ESTUDO deste trecho, no padrão de quem ensina técnicas de resumo eficientes para concursos. Ele será lido no celular e revisado várias vezes.

Como escrever (técnicas obrigatórias):
- Divida em seções curtas por assunto (uma ideia central por seção), na ordem lógica do material.
- Frases curtas e diretas, estilo "telegráfico", sem enrolação. Use "→" para consequência e "≠" para distinções.
- Marca-texto com ==assim== SOMENTE nas palavras-chave que decidem questões (no máximo um trecho marcado por bloco). Use **negrito** para termos técnicos e nomes de institutos.
- Sempre que houver comparação (A x B, regra x exceção, tipos, prazos, competências), monte uma TABELA.
- Use quadros: "atencao" para pegadinhas clássicas; "excecao" para exceções à regra; "cai" para o que mais é cobrado (especialmente CEBRASPE/CESPE e FGV); "dica" para macetes de interpretação; "lei" para trechos literais de lei ou súmula que estejam no material.
- "esquema" para sequências e etapas (ex.: passos de um procedimento, estrutura de uma demonstração).
- Mnemônico só quando ajudar a decorar uma lista do próprio material (pode ser sigla com as iniciais dos itens).
- No fim, 4 a 8 perguntas de autoteste (recuperação ativa), com respostas curtas tiradas do material.

Responda SOMENTE com JSON:
{"visaoGeral":"2 frases que situam o assunto",
 "secoes":[{"titulo":"","blocos":[
   {"tipo":"texto","texto":"..."},
   {"tipo":"lista","titulo":"opcional","itens":["..."]},
   {"tipo":"tabela","titulo":"","colunas":["",""],"linhas":[["",""]]},
   {"tipo":"atencao","texto":""},{"tipo":"excecao","texto":""},{"tipo":"cai","texto":""},{"tipo":"dica","texto":""},
   {"tipo":"lei","ref":"art. X da Lei Y","texto":"trecho literal do material"},
   {"tipo":"esquema","titulo":"","itens":["etapa 1","etapa 2"]},
   {"tipo":"mnemonico","nome":"","explicacao":""}]}],
 "autoteste":[{"p":"pergunta","r":"resposta"}],
 "alertas":["observação sua para conferir na fonte, se notar erro ou desatualização no material; senão lista vazia"]}`;
function htmlResumoV2(r, fmt, esc) {
  const icone = { atencao: "Atenção", excecao: "Exceção", cai: "Cai em prova", dica: "Dica", lei: "Letra da lei", mnemonico: "Para memorizar" };
  const bloco = b => {
    if (b.tipo === "texto") return `<p class="rz-p">${fmt(b.texto)}</p>`;
    if (b.tipo === "lista") return `${b.titulo ? `<p class="rz-lt">${fmt(b.titulo)}</p>` : ""}<ul class="rz-ul">${b.itens.map(x => `<li>${fmt(x)}</li>`).join("")}</ul>`;
    if (b.tipo === "esquema") return `<div class="rz-esq">${b.titulo ? `<p class="rz-lt">${fmt(b.titulo)}</p>` : ""}<ol>${b.itens.map(x => `<li>${fmt(x)}</li>`).join("")}</ol></div>`;
    if (b.tipo === "tabela") return `<div class="rz-tw">${b.titulo ? `<p class="rz-lt">${fmt(b.titulo)}</p>` : ""}<table class="rz-tb"><thead><tr>${b.colunas.map(c => `<th>${fmt(c)}</th>`).join("")}</tr></thead><tbody>${b.linhas.map(l => `<tr>${l.map(c => `<td>${fmt(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    if (b.tipo === "mnemonico") return `<div class="rz-box rz-mnemonico"><span class="rz-tag">${icone.mnemonico}</span><p><strong>${fmt(b.nome)}</strong>${b.explicacao ? " — " + fmt(b.explicacao) : ""}</p></div>`;
    if (b.tipo === "figura") return `<figure class="rz-fig${b.mapa ? " rz-mapa" : ""}"><button class="rz-figb" data-act="fig" data-fig="${b.img}" aria-label="Ampliar figura"><img data-fig="${b.img}" alt="${esc(b.legenda || "Esquema do PDF")}"></button>${b.legenda ? `<figcaption>${fmt(b.legenda)}<span class="rz-figdica">Toque para ampliar</span></figcaption>` : ""}</figure>`;
    if (b.tipo === "lei") return `<blockquote class="rz-box rz-lei"><span class="rz-tag">${b.ref ? esc(b.ref) : icone.lei}</span><p>${fmt(b.texto)}</p></blockquote>`;
    return `<div class="rz-box rz-${b.tipo}"><span class="rz-tag">${icone[b.tipo]}</span><p>${fmt(b.texto)}</p></div>`;
  };
  return `<article class="rz">
    ${r.visaoGeral ? `<p class="rz-vg">${fmt(r.visaoGeral)}</p>` : ""}
    ${r.secoes.map((s, i) => `<section class="rz-sec"><h3 class="rz-h"><span class="rz-n">${String(i + 1).padStart(2, "0")}</span>${fmt(s.titulo)}</h3>${s.blocos.map(bloco).join("")}</section>`).join("")}
    ${r.autoteste.length ? `<section class="rz-sec rz-auto"><h3 class="rz-h">Teste-se</h3><p class="rz-p small">Tente responder antes de abrir.</p>${r.autoteste.map(q => `<details class="rz-q"><summary>${fmt(q.p)}</summary><p>${fmt(q.r)}</p></details>`).join("")}</section>` : ""}
    ${r.alertas.length ? `<div class="rz-box rz-atencao"><span class="rz-tag">Conferir na fonte</span><ul class="rz-ul">${r.alertas.map(x => `<li>${fmt(x)}</li>`).join("")}</ul></div>` : ""}
  </article>`;
}

/* ---------------- progresso local (só neste aparelho) ---------------- */
const PKEY = "cf.progresso.v1";
let P = { q: {}, c: {} };
function carregarP() { try { const v = JSON.parse(localStorage.getItem(PKEY) || "null"); if (v && v.q && v.c) P = v; } catch (_) { } }
function salvarP() { try { localStorage.setItem(PKEY, JSON.stringify(P)); } catch (_) { } }
carregarP();

/* ---------------- conteúdo ---------------- */
let C = null;          // conteúdo decifrado (só em memória)
let QS = [], QMAP = new Map(), TEMAS = [], CARDS = [];
function montarIndices() {
  TEMAS = C.temas.slice();
  QS = C.questoes.map(q => Object.assign({}, q, { materia: (C.temas.find(t => t.id === q.temaId) || {}).materia || "" }));
  QMAP = new Map(QS.map(q => [q.id, q]));
  CARDS = (C.cards || []).slice();
}
const prog = q => P.q[q.id] || {};
const qv = q => Object.assign({}, q, prog(q));
const tema = id => TEMAS.find(t => t.id === id);
const visivel = q => !q.reserva || (prog(q).t || 0) > 0;

/* ---------------- cripto ---------------- */
let encBytes = null, CHAVE = null;
/* figuras (esquemas do PDF): cada uma num arquivo cifrado com a mesma chave, abertas sob demanda */
const FIGS = new Map();
async function figura(id) {
  if (FIGS.has(id)) return FIGS.get(id);
  const pr = (async () => {
    const r = await fetch(`data/img/${id}.bin`).catch(() => null) || await caches.match(`data/img/${id}.bin`);
    if (!r || !r.ok) throw new Error("figura");
    const b = new Uint8Array(await r.arrayBuffer());
    const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: b.slice(0, 12) }, CHAVE, b.slice(12));
    return URL.createObjectURL(new Blob([plain], { type: "image/webp" }));
  })();
  FIGS.set(id, pr); pr.catch(() => FIGS.delete(id));
  return pr;
}
function carregarFiguras(raiz) {
  raiz.querySelectorAll("img[data-fig]:not([src])").forEach(img => {
    figura(img.dataset.fig).then(u => { img.src = u; }).catch(() => { img.closest("figure") && img.closest("figure").classList.add("rz-fig-erro"); });
  });
}
function abrirFigura(id) {
  const ov = document.createElement("div");
  ov.className = "figov"; ov.setAttribute("role", "dialog"); ov.setAttribute("aria-label", "Figura ampliada");
  ov.innerHTML = `<div class="figov-bar"><button data-z="1" class="figov-z">Tamanho real</button><button class="figov-x">Fechar</button></div><div class="figov-in"><img alt=""></div>`;
  document.body.appendChild(ov); document.body.classList.add("sem-rolar");
  figura(id).then(u => { ov.querySelector("img").src = u; });
  const fechar = () => { ov.remove(); document.body.classList.remove("sem-rolar"); };
  ov.querySelector(".figov-x").onclick = fechar;
  ov.querySelector(".figov-z").onclick = ev => { const real = ov.classList.toggle("real"); ev.target.textContent = real ? "Ajustar à tela" : "Tamanho real"; };
  ov.addEventListener("keydown", ev => { if (ev.key === "Escape") fechar(); });
  ov.querySelector(".figov-x").focus();
}
async function baixarConteudo() {
  if (encBytes) return encBytes;
  const r = await fetch("data/conteudo.enc", { cache: "no-cache" }).catch(() => null) || await caches.match("data/conteudo.enc");
  if (!r || !r.ok) throw new Error("sem conteúdo");
  encBytes = new Uint8Array(await r.arrayBuffer());
  return encBytes;
}
async function decifrar(codigo) {
  const b = await baixarConteudo();
  const salt = b.slice(4, 20), iv = b.slice(20, 32), dados = b.slice(32);
  const it = new DataView(b.buffer, b.byteOffset, 4).getUint32(0);
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(codigo), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey({ name: "PBKDF2", salt, iterations: it, hash: "SHA-256" }, base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, dados);  // lança erro se o código estiver errado
  CHAVE = key;
  const txt = await new Response(new Blob([plain]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
  return JSON.parse(txt);
}
window.__cfDecifrar = decifrar; // usado nos testes

/* ---------------- tela de entrada ---------------- */
const form = $("#gate-form"), senha = $("#gate-senha"), msg = $("#gate-msg"), okBtn = $("#gate-ok");
form.addEventListener("submit", async e => {
  e.preventDefault();
  const v = senha.value;
  if (!v) return;
  okBtn.disabled = true; msg.className = "gate-msg"; msg.textContent = "";
  try {
    const conteudo = await decifrar(v);
    msg.className = "gate-msg ok"; msg.textContent = "Acertô, mizerávi!";
    senha.blur();
    await new Promise(r => setTimeout(r, 1300));
    senha.value = ""; msg.textContent = ""; okBtn.disabled = false;
    abrirApp(conteudo);
  } catch (err) {
    okBtn.disabled = false;
    msg.textContent = err && err.message === "sem conteúdo" ? "Sem internet na primeira abertura. Conecte e tente de novo." : "Senha incorreta.";
    form.classList.remove("erro"); void form.offsetWidth; form.classList.add("erro");
    senha.select();
  }
});
baixarConteudo().catch(() => { });

/* ---------------- app ---------------- */
const S = { view: "estudar", temaId: null, tab: "questoes", session: null, opts: { materia: "", temaId: "", modo: "questoes" } };
const main = $("#main");
function abrirApp(conteudo) {
  C = conteudo; montarIndices();
  $("#gate").hidden = true; $("#app").hidden = false;
  S.view = "estudar"; S.session = null;
  render(); scrollTo(0, 0);
}
function bloquear() {
  C = null; QS = []; QMAP = new Map(); TEMAS = []; CARDS = []; S.session = null; CHAVE = null;
  for (const pr of FIGS.values()) pr.then(u => URL.revokeObjectURL(u)).catch(() => { }); FIGS.clear();
  document.querySelectorAll(".figov,.lv").forEach(x => x.remove()); document.body.classList.remove("sem-rolar");
  main.innerHTML = "";
  $("#app").hidden = true; $("#gate").hidden = false;
  setTimeout(() => senha.focus(), 50);
}
document.addEventListener("visibilitychange", () => { if (document.hidden && C && S.bloquearAoSair) bloquear(); });

/* repetição espaçada */
function agendar(c, q) {
  let interval = c.interval || 0, ease = c.ease || 2.5, reps = c.reps || 0, due;
  if (q === 0) { reps = 0; interval = 0; ease = Math.max(1.3, ease - 0.2); due = now() + 10 * 60000; }
  else {
    reps++;
    if (reps === 1) interval = q === 3 ? 3 : 1;
    else if (reps === 2) interval = q === 1 ? 2 : q === 3 ? 7 : 4;
    else interval = Math.max(1, Math.round(interval * ease * (q === 1 ? 0.6 : q === 3 ? 1.3 : 1)));
    ease = Math.max(1.3, ease + (q === 1 ? -0.15 : q === 3 ? 0.15 : 0));
    due = now() + interval * DAY;
  }
  return { interval, ease, reps, due };
}
const cardP = c => Object.assign({}, c, P.c[c.id] || {});
const prevDias = (c, q) => { const a = agendar(c, q); return q === 0 ? "10 min" : a.interval + (a.interval === 1 ? " dia" : " dias"); };
const vencido = c => (c.due || 0) <= now();

/* similares */
const palavras = s => new Set(String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").split(/[^a-z0-9]+/).filter(w => w.length > 3));
function simsOf(q) {
  if (q.sim && q.sim.length) return q.sim.map(id => QMAP.get(id)).filter(Boolean);
  const a = palavras(q.enunciado);
  return QS.filter(x => x.temaId === q.temaId && x.id !== q.id).map(x => { const b = palavras(x.enunciado); let c = 0; a.forEach(w => { if (b.has(w)) c++; }); return [c / (a.size + b.size - c || 1), x]; }).filter(v => v[0] > 0.12).sort((u, v) => v[0] - u[0]).slice(0, 6).map(v => v[1]);
}

/* sessões */
function sessao(itens, origem, extra) { return Object.assign({ itens, i: 0, rev: false, resp: null, feitas: 0, acertos: 0, cardsFeitos: 0, origem }, extra || {}); }
function montarSessao(o) {
  const filtro = x => (!o.temaId || x.temaId === o.temaId) && (!o.materia || (x.materia || (tema(x.temaId) || {}).materia) === o.materia);
  const n = o.n || 10;
  if (o.modo === "extras") {
    const qs = QS.filter(q => q.temaId === o.temaId && q.reserva && !prog(q).t && !prog(q).anulada).sort((a, b) => (b.prioridade || 0) - (a.prioridade || 0)).slice(0, n);
    return sessao(qs.map(q => ({ k: "q", id: q.id })), o);
  }
  if (o.modo === "reforco") {
    const alvo = q => (!o.temaId || q.temaId === o.temaId) && (!o.materia || q.materia === o.materia);
    const erradas = QS.filter(q => alvo(q) && visivel(q) && prog(q).e && !prog(q).anulada).sort((a, b) => (prog(b).u || 0) - (prog(a).u || 0));
    const vistos = new Set(erradas.map(q => q.id)), out = [];
    const pend = x => !prog(x).anulada && !prog(x).t;
    const filas = erradas.map(q => simsOf(q).filter(pend));
    let k = 0;
    while (out.length < n && filas.some(f => f.length)) { const f = filas[k++ % filas.length]; while (f.length) { const x = f.shift(); if (!vistos.has(x.id)) { vistos.add(x.id); out.push({ k: "q", id: x.id }); break; } } }
    const temasErro = new Set(erradas.map(q => q.temaId));
    const resto = QS.filter(q => alvo(q) && pend(q) && !vistos.has(q.id)).sort((a, b) => (temasErro.has(b.temaId) - temasErro.has(a.temaId)) || ((a.reserva ? 1 : 0) - (b.reserva ? 1 : 0)) || (b.prioridade || 0) - (a.prioridade || 0));
    for (const q of resto) { if (out.length >= n) break; out.push({ k: "q", id: q.id }); }
    if (out.length < n) for (const q of erradas) { if (out.length >= n) break; out.push({ k: "q", id: q.id }); }
    return sessao(out, o);
  }
  if (o.modo === "parecidas") {
    const bases = o.bases ? o.bases.map(id => QMAP.get(id)).filter(Boolean) : o.base ? [QMAP.get(o.base)].filter(Boolean) : QS.filter(q => visivel(q) && prog(q).e && filtro(q)).sort((a, b) => (prog(b).u || 0) - (prog(a).u || 0));
    const vistos = new Set(bases.map(b => b.id)), out = [];
    const filas = bases.map(b => simsOf(b).filter(x => !prog(x).anulada && (!prog(x).t || prog(x).e)));
    let k = 0;
    while (out.length < n && filas.some(f => f.length)) { const f = filas[k++ % filas.length]; while (f.length) { const x = f.shift(); if (!vistos.has(x.id)) { vistos.add(x.id); out.push({ k: "q", id: x.id }); break; } } }
    return sessao(out, o, { semBase: !bases.length });
  }
  if (o.modo === "cards-todos") return sessao(CARDS.filter(filtroCard(o)).map(c => ({ k: "c", id: c.id })), Object.assign({}, o, { modo: "cards" }));
  let cards = [];
  if (o.modo !== "questoes") {
    const cs = CARDS.filter(filtroCard(o)).map(cardP);
    const venc = cs.filter(c => c.reps > 0 && vencido(c)).sort((a, b) => (a.due || 0) - (b.due || 0));
    const novos = cs.filter(c => !c.reps && vencido(c));
    cards = venc.concat(novos).map(c => ({ k: "c", id: c.id }));
  }
  let qitens = [];
  if (o.modo !== "cards") {
    const peso = q => prog(q).e ? 0 : !prog(q).t ? 1 : 2;
    qitens = QS.filter(q => visivel(q) && filtro(q) && !prog(q).anulada).sort((a, b) => peso(a) - peso(b) || (b.prioridade || 0) - (a.prioridade || 0) || (prog(a).u || 0) - (prog(b).u || 0)).map(q => ({ k: "q", id: q.id }));
  }
  let itens;
  if (o.modo === "misto") {
    const nc = Math.min(cards.length, Math.ceil(n / 2)), nq = Math.min(qitens.length, n - nc);
    const c2 = cards.slice(0, nc + (n - nc - nq)), q2 = qitens.slice(0, nq);
    itens = []; let i = 0, j = 0; while (i < c2.length || j < q2.length) { if (i < c2.length) itens.push(c2[i++]); if (j < q2.length) itens.push(q2[j++]); }
  } else itens = o.modo === "questoes" ? qitens.slice(0, n) : cards.slice(0, n);
  return sessao(itens, o);
}
const filtroCard = o => c => (!o.temaId || c.temaId === o.temaId) && (!o.materia || (tema(c.temaId) || {}).materia === o.materia);
function iniciar(o) { S.session = montarSessao(o); S.view = "estudar"; render(); scrollTo(0, 0); }
function itemAtual() { const s = S.session, it = s.itens[s.i]; if (!it) return null; return it.k === "c" ? { k: "c", x: CARDS.find(c => c.id === it.id) } : { k: "q", x: QMAP.get(it.id) }; }

/* render */
function render() {
  if (!C) return;
  document.querySelectorAll("nav.bottom button").forEach(b => b.setAttribute("aria-current", b.dataset.v === (S.view === "resumo" ? "estudar" : S.view) ? "page" : "false"));
  let h = "";
  if (S.view === "desempenho") h = vDesempenho();
  else if (S.view === "estudar") h = S.session ? vSessao() : vEstudar();
  else if (S.view === "resumo") h = vResumoTela();
  main.innerHTML = (S.msg ? `<div class="notice info row between" role="status"><span>${esc(S.msg)}</span><button class="ghost" data-act="msgx">Fechar</button></div>` : "") + h;
  if (CHAVE) carregarFiguras(main);
}
function stats() {
  const cs = CARDS.map(cardP), qs = QS.filter(visivel).filter(q => !prog(q).anulada);
  return { venc: cs.filter(c => c.reps > 0 && vencido(c)).length, novosC: cs.filter(c => !c.reps).length, novasQ: qs.filter(q => !prog(q).t).length, erradas: qs.filter(q => prog(q).e).length };
}
const materias = () => [...new Set(TEMAS.map(t => t.materia))].sort(ordem);
const META = 80, MIN_Q = 5;
function placar(filtro) {
  let t = 0, a = 0, erros = 0;
  QS.forEach(q => { if (!filtro(q)) return; const p = prog(q); if (!p.t || p.anulada) return; t += p.t; a += p.a || 0; if (p.e) erros++; });
  return { t, a, erros, pct: t ? Math.round(100 * a / t) : null };
}
function barra(pct) {
  const cor = pct === null ? "var(--line)" : pct >= META ? "var(--ok)" : pct >= 60 ? "var(--warn)" : "var(--bad)";
  return `<div class="meta-bar" role="img" aria-label="${pct === null ? "sem dados" : pct + "% de acertos"}"><i style="width:${pct || 0}%;background:${cor}"></i><span class="meta-linha" style="left:${META}%"></span></div>`;
}
function vDesempenho() {
  const geral = placar(() => true);
  const ordemM = materias().map(m => ({ m, p: placar(q => q.materia === m) })).sort((x, y) => (x.p.pct === null) - (y.p.pct === null) || (x.p.pct ?? 0) - (y.p.pct ?? 0) || ordem(x.m, y.m)).map(x => x.m);
  const linhas = ordemM.map(m => {
    const pm = placar(q => q.materia === m);
    const temas = temasDe(m).map(t => ({ t, p: placar(q => q.temaId === t.id) })).filter(x => x.p.t);
    const status = pm.pct === null ? `<span class="chip">sem questões resolvidas</span>` : pm.t < MIN_Q ? `<span class="chip">poucas questões</span>` : pm.pct >= META ? `<span class="chip ok">meta atingida</span>` : `<span class="chip bad">abaixo da meta</span>`;
    const alerta = pm.pct !== null && pm.t >= MIN_Q && pm.pct < META;
    return `<section class="panel dm ${alerta ? "dm-alerta" : ""}">
      <div class="row between"><h3>${esc(m)}</h3>${status}</div>
      <div class="row between"><span class="dm-pct">${pm.pct === null ? "—" : pm.pct + "%"}</span><span class="num">${pm.a}/${pm.t} acertos</span></div>
      ${barra(pm.pct)}
      ${alerta ? `<p class="small"><strong>Abaixo dos 80%.</strong> Treine com questões parecidas com as que você errou nesta matéria.</p><button class="primary" data-act="reforco" data-m="${esc(m)}">Treinar ${esc(m)}</button>` : ""}
      ${temas.length ? `<details class="dm-temas"><summary class="small">Ver por conteúdo (${temas.length})</summary>${temas.map(({ t, p }) => `<div class="dm-tema"><div class="row between"><span class="small">${esc(t.titulo)}</span><span class="num">${p.pct}% · ${p.a}/${p.t}</span></div>${barra(p.pct)}${p.t >= MIN_Q && p.pct < META ? `<button class="ghost small" data-act="reforco" data-t="${esc(t.id)}" style="align-self:flex-start;padding-left:0">Treinar este conteúdo →</button>` : ""}</div>`).join("")}</details>` : ""}
    </section>`;
  }).join("");
  return `<header class="stack" style="gap:6px"><span class="eyebrow">Meta: ${META}% de acertos</span><h1>Desempenho</h1></header>
  <section class="panel">
    <div class="row between"><h2>Geral</h2><span class="num">${geral.a}/${geral.t} acertos</span></div>
    <span class="dm-pct dm-geral">${geral.pct === null ? "—" : geral.pct + "%"}</span>
    ${barra(geral.pct)}
    ${geral.t ? `<div class="dm-niveis">${[1, 2, 3].map(n => { const p = placar(q => q.nivel === n); return `<div><span class="chip nv nv${n}">${NIVEL[n]}</span><b>${p.pct === null ? "—" : p.pct + "%"}</b><span class="num">${p.a}/${p.t}</span></div>`; }).join("")}</div>` : ""}
    <p class="small muted">${geral.t ? "A linha vertical marca a meta de 80%. O aviso só aparece com pelo menos " + MIN_Q + " questões resolvidas na matéria, para não pesar um começo com poucas questões." : "Resolva questões na aba Estudar para acompanhar seu desempenho aqui."} Fica salvo neste aparelho.</p>
  </section>
  ${linhas}`;
}
function itemTema(t) {
  const nq = QS.filter(q => q.temaId === t.id && !q.reserva).length, nc = CARDS.filter(c => c.temaId === t.id).length;
  const feitas = QS.filter(q => q.temaId === t.id && prog(q).t).length;
  return `<button class="item" data-act="tema" data-id="${esc(t.id)}"><span class="t"><strong>${esc(t.titulo)}</strong><span class="small muted">${nq} questões · ${nc} cards${feitas ? ` · ${feitas} resolvidas` : ""}</span></span></button>`;
}
function vConteudo() {
  return `<header class="stack" style="gap:6px"><span class="eyebrow">Seu material</span><h1>Temas</h1></header>
  ${materias().map(m => `<section class="stack" style="gap:4px"><h3 class="materia-h">${esc(m)}</h3><div class="panel" style="padding-block:4px"><div class="list">${TEMAS.filter(t => t.materia === m).sort((a, b) => ordem(a.titulo, b.titulo)).map(itemTema).join("")}</div></div></section>`).join("")}`;
}
function temasDe(m) { return TEMAS.filter(t => !m || t.materia === m).sort((a, b) => ordem(a.materia, b.materia) || ordem(a.titulo, b.titulo)); }
function vEstudar() {
  const o = S.opts, ts = temasDe(o.materia);
  if (o.temaId && !ts.some(t => t.id === o.temaId)) o.temaId = "";
  const t = tema(o.temaId);
  const nq = QS.filter(q => q.temaId === o.temaId && !q.reserva).length, nc = CARDS.filter(c => c.temaId === o.temaId).length;
  const nres = o.temaId ? QS.filter(q => q.temaId === o.temaId && q.reserva && !prog(q).t).length : 0;
  const erradas = QS.filter(q => (!o.temaId || q.temaId === o.temaId) && (!o.materia || q.materia === o.materia) && visivel(q) && prog(q).e).length;
  if (o.modo === "resumo") o.modo = "teoria";
  const seg = (lista, rot) => `<div class="stack" style="gap:6px"><span class="lbl">${rot}</span><div class="seg" style="grid-template-columns:repeat(${lista.length},1fr)" role="radiogroup" aria-label="${rot}">${lista.map(([k, n]) => `<button role="radio" aria-checked="${o.modo === k}" data-act="modo" data-v="${k}">${n}</button>`).join("")}</div></div>`;
  const meu = (C.meus || {})[o.materia || (t && t.materia) || ""];
  let info = "", botoes = "";
  if (o.modo === "teoria") {
    const te = t && t.teoria;
    if (!o.temaId) info = "Escolha um conteúdo para abrir o PDF.";
    else if (!te) info = "Este conteúdo ainda não tem o PDF.";
    else {
      const ult = leituraDe(te.doc);
      info = `Conteúdo do PDF, sem as questões · ${te.paginas} páginas${docSalvo(te.doc) ? " · disponível offline" : " · baixa na primeira vez"}`;
      botoes = `<button class="primary wide" data-act="ler" data-tipo="teoria">Abrir índice</button>${ult > 1 ? `<button class="wide" data-act="ler" data-tipo="teoria" data-pg="${ult}">Continuar de onde parei (pág. ${ult})</button>` : ""}`;
    }
  } else if (o.modo === "meu") {
    if (!o.materia && !t) info = "Escolha a matéria para abrir o seu resumo.";
    else if (!meu) info = "Você ainda não mandou o resumo desta matéria.";
    else {
      const ult = leituraDe(meu.doc);
      info = `Seu resumo de ${esc(o.materia || t.materia)} · ${meu.paginas} páginas`;
      botoes = `<button class="primary wide" data-act="ler" data-tipo="meu">Abrir índice</button>${ult > 1 ? `<button class="wide" data-act="ler" data-tipo="meu" data-pg="${ult}">Continuar de onde parei (pág. ${ult})</button>` : ""}`;
    }
  } else {
    info = o.temaId ? `${nq} questões principais${nres ? ` · ${nres} extras` : ""} · ${nc} flashcards` : "";
    botoes = `<button class="primary wide" data-act="iniciar">${o.modo === "cards" ? "Revisar flashcards" : "Resolver questões"}</button>`
      + (o.modo === "questoes" && nres ? `<button class="wide" data-act="extras">Fazer as questões extras (${nres})</button>` : "")
      + (o.modo === "questoes" && erradas ? `<button class="wide" data-act="parecidas-sel">Parecidas com as que errei (${erradas} ${erradas === 1 ? "erro" : "erros"})</button>` : "");
  }
  return `<header class="stack" style="gap:6px"><span class="eyebrow">O que vamos estudar?</span><h1>Rumo ao Fisco</h1></header>
  <section class="panel">
    <label for="o-materia">Matéria<select id="o-materia"><option value="">Todas as matérias</option>${materias().map(m => `<option ${o.materia === m ? "selected" : ""}>${esc(m)}</option>`).join("")}</select></label>
    <label for="o-tema">Conteúdo<select id="o-tema"><option value="">${o.modo === "teoria" ? "Escolha um conteúdo" : "Todos os conteúdos"}</option>${ts.map(x => `<option value="${esc(x.id)}" ${o.temaId === x.id ? "selected" : ""}>${o.materia ? "" : esc(x.materia) + " · "}${esc(x.titulo)}</option>`).join("")}</select></label>
    ${seg([["teoria", "Conteúdo do PDF"], ["meu", "Meu resumo"]], "Ler")}
    ${seg([["questoes", "Questões"], ["cards", "Flashcards"]], "Praticar")}
    ${info ? `<p class="small muted">${info}</p>` : ""}${botoes}
  </section>`;
}
function vResumoTela() {
  const t = tema(S.temaId); if (!t) { S.view = "estudar"; return vEstudar(); }
  const r = t.resumo && t.resumo.v === 2 ? limparResumo(t.resumo) : null;
  return `<header class="stack" style="gap:8px"><button class="ghost" data-act="voltar" style="align-self:flex-start;padding-left:0">← Rumo ao Fisco</button><span class="eyebrow">${esc(t.materia)}</span><h1>${esc(t.titulo)}</h1></header>
  ${r ? `<section class="panel">${htmlResumoV2(r, fmt, esc)}</section>` : `<section class="panel empty"><p>O resumo deste conteúdo entra na próxima atualização.</p></section>`}
  <div class="stack" style="gap:8px"><button class="primary wide" data-act="ir-questoes">Resolver as questões deste conteúdo</button>${CARDS.some(c => c.temaId === t.id) ? `<button class="wide" data-act="ir-cards">Revisar os flashcards</button>` : ""}</div>`;
}
function vSessao() {
  const s = S.session, tot = s.itens.length;
  if (!tot && s.origem.modo === "parecidas") return `<header class="stack"><span class="eyebrow">Parecidas com as que errei</span><h1>${s.semBase ? "Nenhum erro ainda" : "Sem parecidas pendentes"}</h1></header><div class="panel"><p>${s.semBase ? "Você ainda não errou questões com esse filtro." : "Não há mais questões parecidas ainda não resolvidas no seu material para esses erros."}</p><div class="row"><button data-act="sair">Voltar</button></div></div>`;
  if (!tot && s.origem.modo === "cards" && CARDS.some(filtroCard(s.origem))) return `<header class="stack"><span class="eyebrow">Flashcards</span><h1>Tudo em dia</h1></header><div class="panel"><p>Nenhum card vencido aqui agora. Pela repetição espaçada, eles voltam no dia certo.</p><div class="row"><button class="primary" data-act="cards-todos">Revisar todos mesmo assim</button><button data-act="sair">Voltar</button></div></div>`;
  if (!tot) return `<header class="stack"><span class="eyebrow">Sessão</span><h1>Nada por aqui ainda</h1></header><div class="panel"><p>${s.origem.modo === "cards" ? "Os flashcards deste conteúdo entram na próxima atualização." : "Não há questões pendentes com essa escolha."}</p><div class="row"><button data-act="sair">Voltar</button></div></div>`;
  if (s.i >= tot) {
    const p = s.feitas ? Math.round(100 * s.acertos / s.feitas) : null;
    return `<header class="stack" style="gap:6px"><span class="eyebrow">Sessão concluída</span><h1>${p === null ? "Revisão feita" : p + "% de acertos"}</h1></header>
    <section class="panel"><div class="today"><div><b>${s.acertos}/${s.feitas}</b><span class="small muted">questões certas</span></div><div><b>${s.cardsFeitos}</b><span class="small muted">cards revisados</span></div><div><b>${tot}</b><span class="small muted">itens</span></div></div>
    ${(() => { const o = s.origem; const nres = o.temaId ? QS.filter(q => q.temaId === o.temaId && q.reserva && !prog(q).t).length : 0; return o.modo === "questoes" && nres ? `<button class="wide" data-act="extras-de" data-id="${esc(o.temaId)}">Fazer as questões extras (${nres})</button>` : ""; })()}
    ${s.feitas > s.acertos ? `<button class="wide" data-act="parecidas-sessao">Parecidas com as que errei nesta sessão</button>` : ""}
    <div class="row"><button class="primary" data-act="denovo">Repetir</button><button data-act="sair">${s.origem.modo === "reforco" ? "Voltar" : "Voltar ao início"}</button></div></section>`;
  }
  const cur = itemAtual(); if (!cur || !cur.x) { s.i++; return vSessao(); }
  const t = tema(cur.x.temaId) || {};
  const head = `<div class="stack" style="gap:8px"><div class="row between"><span class="eyebrow">${s.i + 1} de ${tot} · ${esc(t.materia || "")}</span><button class="ghost" data-act="sair">Encerrar</button></div><div class="prog"><i style="width:${100 * s.i / tot}%"></i></div></div>`;
  return head + (cur.k === "c" ? vCard(cardP(cur.x)) : vQuestao(qv(cur.x)));
}
function vCard(c) {
  const s = S.session;
  return `<section class="panel card"><span class="eyebrow">Flashcard${c.reps ? ` · revisão ${c.reps + 1}` : " · novo"}</span><p>${fmt(c.frente)}</p>${s.rev ? `<div class="back">${fmt(c.verso)}</div>` : ""}</section>
  ${s.rev ? `<div class="grades">${["Errei", "Difícil", "Bom", "Fácil"].map((g, i) => `<button data-act="nota" data-q="${i}" ${i === 0 ? 'class="danger"' : ""}>${g}<small>${prevDias(c, i)}</small></button>`).join("")}</div>` : `<button class="primary wide" data-act="revelar">Mostrar resposta</button>`}`;
}
function vQuestao(q) {
  const s = S.session, resp = s.resp;
  const ops = q.tipo === "ce" ? [["C", "Certo"], ["E", "Errado"]] : q.alternativas.map((a, i) => [L[i], a]);
  const cls = k => !resp ? "" : k === q.gabarito ? "right" : k === resp ? "wrong" : "";
  const ok = resp && resp === q.gabarito;
  return `<section class="panel">
    <div class="qhead">${q.banca ? `<span class="chip acc">${esc(q.banca)}</span>` : ""}<span class="chip">${q.tipo === "ce" ? "Certo ou errado" : "Múltipla escolha"}</span>${q.nivel ? `<span class="chip nv nv${q.nivel}">${NIVEL[q.nivel]}</span>` : ""}${q.reserva ? `<span class="chip">extra</span>` : ""}${q.t ? `<span class="chip">${q.a || 0}/${q.t} antes</span>` : ""}</div>
    ${q.fonteProva ? `<span class="num">${esc(q.fonteProva)}</span>` : ""}
    <div class="enun">${fmt(q.enunciado)}</div>
    <div class="${q.tipo === "ce" ? "ce" : "alts"}" role="group" aria-label="Alternativas">
      ${ops.map(([k, txt]) => `<button class="alt ${cls(k)}" data-act="responder" data-k="${k}" ${resp ? "disabled" : ""}><span class="bub">${k}</span>${q.tipo === "ce" ? esc(txt) : `<span>${fmt(txt)}</span>`}</button>`).join("")}
    </div>
    ${resp ? `<div class="coment"><span class="verdict ${ok ? "ok" : "bad"}">${ok ? "Acertou" : "Errou"} · gabarito ${q.tipo === "ce" ? (q.gabarito === "C" ? "Certo" : "Errado") : q.gabarito}</span><div>${q.comentario ? fmt(q.comentario) : `<span class="muted">O material não traz resolução desta questão.</span>`}</div></div>` : ""}
  </section>
  ${resp ? `<div class="stack" style="gap:8px"><button class="primary wide" data-act="proxima">Próxima</button>${!ok ? `<button class="wide" data-act="parecidas-de" data-id="${esc(q.id)}">Treinar questões parecidas com esta</button>` : ""}</div>` : ""}`;
}
function vTema() {
  const t = tema(S.temaId); if (!t) { S.view = "conteudo"; return vConteudo(); }
  const qs = QS.filter(q => q.temaId === t.id && visivel(q)).map(qv), cs = CARDS.filter(c => c.temaId === t.id).map(cardP);
  const nres = QS.filter(q => q.temaId === t.id && q.reserva && !prog(q).t).length;
  const tabs = [["questoes", `Questões (${qs.length})`], ["resumo", "Resumo"], ["cards", `Flashcards (${cs.length})`]];
  let body = "";
  if (S.tab === "questoes") {
    const st = q => q.anulada ? `<span class="chip">anulada</span>` : !q.t ? `<span class="chip">nova</span>` : q.e ? `<span class="chip bad">errou</span>` : `<span class="chip ok">acertou</span>`;
    body = `<section class="panel">
      ${qs.length ? `<button class="primary" data-act="sess-tema" data-modo="questoes">Resolver as questões deste tema</button>` : ""}
      ${qs.some(q => q.e) ? `<button data-act="parecidas-tema">Parecidas com as que errei neste tema</button>` : ""}
      ${nres ? `<button data-act="extras-tema">Fazer questões extras (${nres})</button>` : ""}
      <p class="small muted">Questões do seu PDF, com gabarito e comentário do professor. As principais priorizam provas da área fiscal e de nível parecido, mais recentes, e os assuntos que mais se repetem no PDF, misturando os níveis na proporção de uma prova fiscal (cerca de 20% básicas, 50% intermediárias e 30% avançadas).</p>
    </section>
    <section class="panel" style="padding-block:6px">${qs.map(q => `<details><summary><span class="s clamp">${esc(q.enunciado.replace(/```/g, ""))}</span>${st(q)}</summary><div class="stack small" style="margin-top:8px;gap:6px">${q.tipo === "me" ? `<div>${q.alternativas.map((a, i) => `<div><strong>${L[i]})</strong> ${fmt(a)}</div>`).join("")}</div>` : ""}<div><strong>Gabarito: ${q.tipo === "ce" ? (q.gabarito === "C" ? "Certo" : "Errado") : q.gabarito}</strong>${q.fonteProva ? " · " + esc(q.fonteProva) : ""}</div><div style="white-space:pre-wrap">${fmt(q.comentario)}</div></div></details>`).join("")}</section>`;
  } else if (S.tab === "resumo") {
    const r = t.resumo && t.resumo.v === 2 ? limparResumo(t.resumo) : null;
    const prof = t.resumoTexto ? `<details class="panel prof-box" ${r ? "" : "open"}><summary>Resumo do professor <span class="chip ok">texto do PDF</span></summary><div class="prof">${fmtDoc(t.resumoTexto)}</div></details>` : "";
    body = r ? `<section class="panel">${htmlResumoV2(r, fmt, esc)}</section>${prof}` :
      prof || `<section class="panel empty"><p>O resumo deste tema entra na próxima atualização do conteúdo.</p></section>`;
  } else {
    const venc = cs.filter(vencido).length;
    body = cs.length ? `<section class="panel"><button class="primary" data-act="sess-tema" data-modo="cards" ${venc ? "" : "disabled"}>Revisar cards deste tema${venc ? ` (${venc})` : ""}</button>${venc ? "" : `<p class="small muted">Nenhum card vencido neste tema agora.</p>`}</section>
      <section class="panel" style="padding-block:6px">${cs.map(c => `<details><summary><span class="s">${fmt(c.frente)}</span></summary><p class="small" style="margin-top:8px;white-space:pre-wrap">${fmt(c.verso)}</p></details>`).join("")}</section>`
      : `<section class="panel empty"><p>Os flashcards deste tema entram na próxima atualização do conteúdo.</p></section>`;
  }
  return `<header class="stack" style="gap:8px"><button class="ghost" data-act="nav" data-v="conteudo" style="align-self:flex-start;padding-left:0">← Temas</button><span class="eyebrow">${esc(t.materia)}</span><h1>${esc(t.titulo)}</h1></header>
  <div class="tabs" role="tablist">${tabs.map(([k, n]) => `<button role="tab" aria-selected="${S.tab === k}" data-act="tab" data-v="${k}">${n}</button>`).join("")}</div>${body}`;
}

/* ações */
document.addEventListener("change", e => {
  if (e.target.id === "o-materia") { S.opts.materia = e.target.value; S.opts.temaId = ""; render(); }
  if (e.target.id === "o-tema") { S.opts.temaId = e.target.value; render(); }
});
document.addEventListener("click", e => {
  const b = e.target.closest("[data-act]"); if (!b || b.disabled || !C) return;
  const a = b.dataset.act, s = S.session;
  if (a === "nav") { S.view = b.dataset.v; if (S.view !== "estudar") S.session = null; render(); scrollTo(0, 0); }
  else if (a === "bloquear") bloquear();
  else if (a === "fig") abrirFigura(b.dataset.fig);
  else if (a === "msgx") { S.msg = null; render(); }
  else if (a === "tema") { S.view = "tema"; S.temaId = b.dataset.id; S.tab = "questoes"; render(); scrollTo(0, 0); }
  else if (a === "tab") { S.tab = b.dataset.v; render(); }
  else if (a === "rapida") iniciar({ materia: "", modo: "misto", n: 10 });
  else if (a === "reforco") iniciar({ modo: "reforco", n: 15, materia: b.dataset.m || "", temaId: b.dataset.t || "" });
  else if (a === "modo") { S.opts.modo = b.dataset.v; render(); }
  else if (a === "ler") {
    const o = S.opts, t = tema(o.temaId);
    if (b.dataset.tipo === "teoria" && t && t.teoria) abrirLeitor({ ...t.teoria, titulo: t.titulo, sub: t.materia }, +b.dataset.pg || 0);
    else { const m = o.materia || (t && t.materia), r = (C.meus || {})[m]; if (r) abrirLeitor({ ...r, titulo: "Meu resumo", sub: m, alvo: t && t.titulo }, +b.dataset.pg || 0); }
  }
  else if (a === "iniciar") {
    const o = S.opts;
    if (o.modo === "resumo") { if (!o.temaId) return; S.view = "resumo"; S.temaId = o.temaId; render(); scrollTo(0, 0); }
    else iniciar({ modo: o.modo, materia: o.materia, temaId: o.temaId, n: o.modo === "cards" ? 500 : (o.temaId ? 60 : 20) });
  }
  else if (a === "voltar") { S.view = "estudar"; S.session = null; render(); scrollTo(0, 0); }
  else if (a === "ir-questoes") iniciar({ modo: "questoes", temaId: S.temaId, n: 60 });
  else if (a === "ir-cards") iniciar({ modo: "cards", temaId: S.temaId, n: 500 });
  else if (a === "extras") iniciar({ modo: "extras", n: 30, temaId: S.opts.temaId });
  else if (a === "extras-de") iniciar({ modo: "extras", n: 30, temaId: b.dataset.id });
  else if (a === "parecidas-sel") iniciar({ modo: "parecidas", n: 15, materia: S.opts.materia, temaId: S.opts.temaId });
  else if (a === "parecidas-sessao") { const ids = s.itens.filter(it => it.k === "q" && prog(QMAP.get(it.id) || {}).e).map(it => it.id); S.session = null; if (ids.length) iniciar({ modo: "parecidas", n: 15, base: ids[0], bases: ids }); }
  else if (a === "cards-todos") iniciar(Object.assign({}, s.origem, { modo: "cards-todos" }));
  else if (a === "sess-tema") iniciar({ materia: "", modo: b.dataset.modo, n: 40, temaId: S.temaId });
  else if (a === "extras-tema") iniciar({ modo: "extras", n: 30, temaId: S.temaId });
  else if (a === "parecidas-home") iniciar({ modo: "parecidas", n: 10 });
  else if (a === "parecidas-tema") iniciar({ modo: "parecidas", n: 10, temaId: S.temaId });
  else if (a === "parecidas-de") iniciar({ modo: "parecidas", n: 10, base: b.dataset.id });
  else if (a === "denovo") iniciar(s.origem);
  else if (a === "sair") { const volta = s && s.origem && s.origem.modo === "reforco" ? "desempenho" : "estudar"; S.session = null; S.view = volta; render(); scrollTo(0, 0); }
  else if (a === "revelar") { s.rev = true; render(); }
  else if (a === "nota") {
    const c = cardP(itemAtual().x), q = +b.dataset.q;
    P.c[c.id] = agendar(c, q); salvarP();
    s.cardsFeitos++; if (q === 0) s.itens.push({ k: "c", id: c.id });
    s.i++; s.rev = false; render(); scrollTo(0, 0);
  }
  else if (a === "responder") {
    const q = itemAtual().x, k = b.dataset.k, ok = k === q.gabarito, p = P.q[q.id] || {};
    s.resp = k; s.feitas++; if (ok) s.acertos++;
    P.q[q.id] = Object.assign(p, { t: (p.t || 0) + 1, a: (p.a || 0) + (ok ? 1 : 0), e: !ok, u: now() }); salvarP();
    render();
  }
  else if (a === "proxima") { s.i++; s.resp = null; render(); scrollTo(0, 0); }
});

/* ---------------- leitor de PDF (conteúdo e meus resumos) ---------------- */
const LKEY = "cf.leitura.v1";
function leituraDe(doc) { try { return (JSON.parse(localStorage.getItem(LKEY) || "{}")[doc]) || 0; } catch (_) { return 0; } }
function salvarLeitura(doc, p) { try { const v = JSON.parse(localStorage.getItem(LKEY) || "{}"); v[doc] = p; localStorage.setItem(LKEY, JSON.stringify(v)); } catch (_) { } }
const SALVOS = new Set();
const docSalvo = id => SALVOS.has(id);
(async () => { try { const ks = await (await caches.open("fisco-pdfs")).keys(); ks.forEach(r => { const m = r.url.match(/doc\/([0-9a-f]{12})\.bin/); if (m) SALVOS.add(m[1]); }); } catch (_) { } })();
let PDFJS = null;
async function carregarPdfjs() {
  if (PDFJS) return PDFJS;
  PDFJS = await import("./vendor/pdf.min.mjs");
  PDFJS.GlobalWorkerOptions.workerSrc = "vendor/pdf.worker.min.mjs";
  return PDFJS;
}
async function baixarDoc(id, aoProgresso) {
  const r = await fetch(`data/doc/${id}.bin`).catch(() => null);
  if (!r || !r.ok) throw new Error("offline");
  const total = +r.headers.get("content-length") || 0;
  let bytes;
  if (r.body && total) {
    const leitor = r.body.getReader(); const partes = []; let n = 0;
    for (;;) { const { done, value } = await leitor.read(); if (done) break; partes.push(value); n += value.length; aoProgresso && aoProgresso(n / total); }
    bytes = new Uint8Array(n); let o = 0; for (const p of partes) { bytes.set(p, o); o += p.length; }
  } else bytes = new Uint8Array(await r.arrayBuffer());
  const plain = await crypto.subtle.decrypt({ name: "AES-GCM", iv: bytes.slice(0, 12) }, CHAVE, bytes.slice(12));
  SALVOS.add(id);
  return new Uint8Array(plain);
}
const semAcento = s => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

async function abrirLeitor(d, pgInicial) {
  document.querySelectorAll(".lv").forEach(x => x.remove());
  const ov = document.createElement("div");
  ov.className = "lv"; ov.setAttribute("role", "dialog"); ov.setAttribute("aria-label", d.titulo);
  ov.innerHTML = `<div class="lv-bar"><button class="ghost lv-idx">☰ Índice</button><span class="lv-t"></span><span class="lv-pg">–</span><button class="ghost lv-x" aria-label="Fechar">✕</button></div>
    <div class="lv-scroll"><div class="lv-pages"></div></div>
    <div class="lv-base"><button class="lv-ant">‹ Anterior</button><button class="lv-zoom">Zoom 100%</button><button class="lv-prox">Próxima ›</button></div>
    <div class="lv-ixp" hidden><div class="lv-ixtopo"><button class="ghost lv-ixx">✕ Fechar</button><div><span class="eyebrow">${esc(d.sub || "")}</span><h3>${esc(d.titulo)} · Índice</h3></div></div>
      <input class="lv-busca" type="search" placeholder="Buscar no conteúdo (ex.: domicílio)" aria-label="Buscar no conteúdo"><div class="lv-lista"></div></div>
    <div class="lv-load"><p>Abrindo…</p></div>`;
  document.body.appendChild(ov); document.body.classList.add("sem-rolar");
  const $o = s => ov.querySelector(s);
  const scroll = $o(".lv-scroll"), pagesEl = $o(".lv-pages"), ixp = $o(".lv-ixp"), lista = $o(".lv-lista"), busca = $o(".lv-busca"), load = $o(".lv-load");
  const indice = d.indice || [];
  let pdf = null, N = d.paginas || 0, zoom = 1, atual = pgInicial || 1, fechado = false;
  const fechar = () => { fechado = true; ov.remove(); document.body.classList.remove("sem-rolar"); if (pdf) pdf.destroy(); render(); };
  $o(".lv-x").onclick = fechar;
  ov.addEventListener("keydown", e => { if (e.key === "Escape") { if (!ixp.hidden) ixp.hidden = true; else fechar(); } });
  const secao = p => { let s = null; for (const e of indice) { if (e.p <= p) s = e; else break; } return s; };
  const listaIndice = () => {
    const cur = secao(atual);
    lista.innerHTML = indice.length ? indice.map((e, i) => `<button class="lv-ix lv-ix${e.n}${e === cur ? " atual" : ""}" data-p="${e.p}" data-i="${i}"><span>${esc(e.t)}</span><span class="lv-pn">${e.p}</span></button>`).join("")
      : `<p class="small muted" style="padding:12px">Este PDF não tem títulos reconhecíveis. Use a busca acima.</p>`;
  };
  const abrirIndice = () => {
    listaIndice(); ixp.hidden = false;
    const alvo = lista.querySelector(".atual"); if (alvo) alvo.scrollIntoView({ block: "center" });
  };
  $o(".lv-idx").onclick = abrirIndice; $o(".lv-ixx").onclick = () => { ixp.hidden = true; };
  lista.addEventListener("click", e => { const b = e.target.closest("[data-p]"); if (!b) return; ixp.hidden = true; irPara(+b.dataset.p); });
  // tela cheia ao tocar
  let toque = null;
  scroll.addEventListener("pointerdown", e => { toque = { x: e.clientX, y: e.clientY, t: Date.now() }; });
  scroll.addEventListener("pointerup", e => { if (toque && Math.abs(e.clientX - toque.x) < 8 && Math.abs(e.clientY - toque.y) < 8 && Date.now() - toque.t < 350) ov.classList.toggle("cheia"); toque = null; });
  // carrega
  try {
    await carregarPdfjs();
    const bytes = await baixarDoc(d.doc, f => { load.innerHTML = `<p>Baixando… ${Math.round(f * 100)}%</p>`; });
    if (fechado) return;
    pdf = await PDFJS.getDocument({ data: bytes, isEvalSupported: false }).promise;
    N = pdf.numPages;
  } catch (err) {
    load.innerHTML = `<p>${err && err.message === "offline" ? "Sem internet. Abra este conteúdo uma vez com internet para ele ficar salvo no aparelho." : "Não foi possível abrir o PDF."}</p><button class="lv-x2">Fechar</button>`;
    load.querySelector(".lv-x2").onclick = fechar; return;
  }
  load.remove();
  const p1 = await pdf.getPage(1); const v1 = p1.getViewport({ scale: 1 });
  const proporcao = v1.height / v1.width;
  pagesEl.innerHTML = Array.from({ length: N }, (_, i) => `<div class="lv-p" data-n="${i + 1}" style="aspect-ratio:1/${proporcao.toFixed(4)}"></div>`).join("");
  const divs = [...pagesEl.children];
  const feitas = new Map();  // n -> canvas
  const renderizar = async n => {
    if (feitas.has(n) || fechado) return;
    feitas.set(n, null);
    const page = await pdf.getPage(n); const vp0 = page.getViewport({ scale: 1 });
    const div = divs[n - 1]; div.style.aspectRatio = `1/${(vp0.height / vp0.width).toFixed(4)}`;
    const larg = div.clientWidth; const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    const vp = page.getViewport({ scale: larg / vp0.width * dpr });
    const cv = document.createElement("canvas"); cv.width = Math.floor(vp.width); cv.height = Math.floor(vp.height);
    await page.render({ canvasContext: cv.getContext("2d"), viewport: vp }).promise.catch(() => { });
    if (fechado || !feitas.has(n)) return;
    div.innerHTML = ""; div.appendChild(cv); feitas.set(n, cv);
    if (feitas.size > 16) {  // libera memória das páginas distantes
      for (const [k] of [...feitas].sort((a, b) => Math.abs(b[0] - atual) - Math.abs(a[0] - atual)).slice(0, feitas.size - 16)) { if (Math.abs(k - atual) > 4) { divs[k - 1].innerHTML = ""; feitas.delete(k); } }
    }
  };
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) renderizar(+e.target.dataset.n); }), { root: scroll, rootMargin: "900px 0px" });
  divs.forEach(dv => io.observe(dv));
  const atualizar = () => {
    const meio = scroll.scrollTop + scroll.clientHeight * 0.35;
    let n = 1; for (const dv of divs) { if (dv.offsetTop <= meio) n = +dv.dataset.n; else break; }
    atual = n;
    $o(".lv-pg").textContent = `${n} / ${N}`;
    const s = secao(n); $o(".lv-t").textContent = s ? s.t : d.titulo;
    salvarLeitura(d.doc, n);
  };
  let rq = 0; scroll.addEventListener("scroll", () => { if (!rq) rq = requestAnimationFrame(() => { rq = 0; atualizar(); }); }, { passive: true });
  const irPara = n => { n = Math.max(1, Math.min(N, n)); const dv = divs[n - 1]; if (dv) scroll.scrollTop = dv.offsetTop - 6; renderizar(n); atualizar(); };
  $o(".lv-ant").onclick = () => irPara(atual - 1);
  $o(".lv-prox").onclick = () => irPara(atual + 1);
  $o(".lv-zoom").onclick = () => {
    zoom = zoom === 1 ? 1.5 : zoom === 1.5 ? 2 : 1;
    $o(".lv-zoom").textContent = `Zoom ${zoom * 100}%`;
    const n = atual; pagesEl.style.width = `${zoom * 100}%`;
    for (const [k] of feitas) divs[k - 1].innerHTML = ""; feitas.clear();
    requestAnimationFrame(() => irPara(n));
  };
  // busca no texto
  const textos = [];
  let buscaId = 0;
  busca.addEventListener("input", () => {
    const termo = semAcento(busca.value.trim()); const id = ++buscaId;
    if (termo.length < 3) { listaIndice(); return; }
    setTimeout(async () => {
      if (id !== buscaId) return;
      const res = [];
      for (let n = 1; n <= N && res.length < 40; n++) {
        if (id !== buscaId) return;
        if (textos[n] == null) { const tc = await (await pdf.getPage(n)).getTextContent(); textos[n] = tc.items.map(i => i.str).join(" ").replace(/\s+/g, " "); }
        const t = textos[n], ts = semAcento(t); let k = ts.indexOf(termo);
        while (k >= 0 && res.length < 40) { res.push({ n, s: t.slice(Math.max(0, k - 50), k + termo.length + 60) }); k = ts.indexOf(termo, k + termo.length + 80); }
        if (n % 10 === 0) lista.innerHTML = `<p class="small muted" style="padding:12px">Buscando… página ${n} de ${N}</p>`;
      }
      if (id !== buscaId) return;
      lista.innerHTML = res.length ? res.map(r => `<button class="lv-ix lv-ix2" data-p="${r.n}"><span>…${esc(r.s)}…</span><span class="lv-pn">${r.n}</span></button>`).join("") : `<p class="small muted" style="padding:12px">Nada encontrado.</p>`;
    }, 350);
  });
  // posição inicial
  if (pgInicial) irPara(pgInicial);
  else {
    atualizar();
    if (d.alvo && indice.length) {  // meu resumo: destaca o assunto escolhido
      const pal = semAcento(d.alvo).split(/\W+/).filter(w => w.length > 3);
      let melhor = null, mv = 0;
      indice.forEach(e => { const t = semAcento(e.t); const v = pal.filter(w => t.includes(w)).length; if (v > mv) { mv = v; melhor = e; } });
      if (melhor) { atual = melhor.p; }
    }
    abrirIndice();
    if (d.alvo) atual = 1;
  }
}

/* service worker (offline) + aviso de atualização */
if ("serviceWorker" in navigator && location.protocol === "https:") {
  navigator.serviceWorker.register("sw.js").then(reg => {
    reg.update().catch(() => { });
  }).catch(() => { });
  // versão nova instalada: recarrega sozinho (ou avisa se estiver no meio de uma sessão)
  let recarregou = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (recarregou) return;
    if (!S.session) { recarregou = true; location.reload(); }
    else { S.msg = "Versão nova do Fisco disponível: ao terminar esta sessão, feche e abra o app (ou atualize a página)."; render(); }
  });
}
})();
