// Versão trocada a cada publicação pelo tools/build.py
const VERSAO = "20261019231351";
const CACHE = "calc-" + VERSAO;
const ARQUIVOS = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "data/conteudo.enc", "icons/icon-192.png", "icons/icon-512.png", "icons/apple-touch-icon.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ARQUIVOS)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  if (url.origin !== location.origin) {           // fontes do Google: usa cache quando houver
    e.respondWith(caches.open(CACHE).then(c => c.match(e.request).then(r => r || fetch(e.request).then(res => { if (res.ok) c.put(e.request, res.clone()); return res; }).catch(() => r))));
    return;
  }
  // arquivos do app: cache primeiro (funciona offline), atualiza quando o sw.js muda
  e.respondWith(caches.match(e.request, { ignoreSearch: true }).then(r => r || fetch(e.request)));
});
