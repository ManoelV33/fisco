// Versão trocada a cada publicação pelo tools/build.py
const VERSAO = "20261020201750";
const CACHE = "calc-" + VERSAO;
const FIGURAS = [];
const DOCS = ["data/doc/1430ee1a507e.bin", "data/doc/1457f271b4d2.bin", "data/doc/1edcc42ea83e.bin", "data/doc/26794ad25130.bin", "data/doc/2950d444da60.bin", "data/doc/381f9628b0ce.bin", "data/doc/3eb1829f3f7d.bin", "data/doc/429996356132.bin", "data/doc/4620242d419a.bin", "data/doc/4ead5b6bc445.bin", "data/doc/52ac6b074ef5.bin", "data/doc/52fffdea4097.bin", "data/doc/555682456f9a.bin", "data/doc/590163145c08.bin", "data/doc/5d219b15d31e.bin", "data/doc/5e25a0aadd13.bin", "data/doc/5f85ed8afb0b.bin", "data/doc/68ac5cef1f96.bin", "data/doc/753a091f7934.bin", "data/doc/7865e325ee0a.bin", "data/doc/7c03334f34b4.bin", "data/doc/7f2395701e09.bin", "data/doc/833886c426ca.bin", "data/doc/843e859f3920.bin", "data/doc/8bdcebd5ab6e.bin", "data/doc/9ce669d15de2.bin", "data/doc/a1ca72684479.bin", "data/doc/a9033a1d85c3.bin", "data/doc/aa7f8635807e.bin", "data/doc/b39b49282b3a.bin", "data/doc/b4b8c6e9f024.bin", "data/doc/b8bcfc75843d.bin", "data/doc/bc8ac8b02e62.bin", "data/doc/bfd036cec4a8.bin", "data/doc/c188d6375dd6.bin", "data/doc/c75e1a979741.bin", "data/doc/cc601e05d41d.bin", "data/doc/d0833efed430.bin", "data/doc/d34bb105d642.bin", "data/doc/d6d9e5ce3bcf.bin", "data/doc/e947dd127e9f.bin", "data/doc/ec98fcc5c3cc.bin", "data/doc/f07e14c355ab.bin", "data/doc/f1fd27c4eab8.bin"];
const CACHE_DOC = "fisco-pdfs";  // PDFs: baixados quando abertos pela primeira vez, guardados para uso offline
const ARQUIVOS = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "data/conteudo.enc", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png", "vendor/pdf.min.mjs", "vendor/pdf.worker.min.mjs"];
const CACHE_FIG = "fisco-figuras";  // figuras não mudam entre versões: baixa só as novas
self.addEventListener("install", e => { e.waitUntil(Promise.all([
  caches.open(CACHE).then(c => c.addAll(ARQUIVOS)),
  caches.open(CACHE_FIG).then(async c => { for (const f of FIGURAS) { if (!(await c.match(f))) await c.add(f).catch(() => { }); } })
]).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE && k !== CACHE_FIG && k !== CACHE_DOC).map(k => caches.delete(k))))
  .then(() => caches.open(CACHE_FIG)).then(c => c.keys().then(rs => Promise.all(rs.filter(r => !FIGURAS.some(f => r.url.endsWith(f))).map(r => c.delete(r)))))
  .then(() => caches.open(CACHE_DOC)).then(c => c.keys().then(rs => Promise.all(rs.filter(r => !DOCS.some(f => r.url.endsWith(f))).map(r => c.delete(r)))))
  .then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.origin !== location.origin) {           // fontes do Google: usa cache quando houver
    e.respondWith(caches.open(CACHE).then(c => c.match(e.request).then(r => r || fetch(e.request).then(res => { if (res.ok) c.put(e.request, res.clone()); return res; }).catch(() => r))));
    return;
  }
  if (url.pathname.includes("/data/doc/")) {   // PDF: usa o salvo; senão baixa e guarda
    e.respondWith(caches.open(CACHE_DOC).then(c => c.match(e.request).then(r => r || fetch(e.request).then(res => { if (res.ok) c.put(e.request, res.clone()); return res; }))));
    return;
  }
  // arquivos do app: cache primeiro (funciona offline), atualiza quando o sw.js muda
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request)));
});
