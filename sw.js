// Offline PWA. Bump VERSION when shipping app changes.
const VERSION = "v2.1.0", SHELL = "ps-shell-" + VERSION, IMG = "ps-img-v1", MAX_IMG = 800;
const CORE = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "assets/icon.svg", "assets/icon-192.png", "assets/icon-512.png",
  "data/taxonomy.json", "data/poses.json", "data/imported.json", "data/sequences.json"];
self.addEventListener("install", e => e.waitUntil((async () => {
  const c = await caches.open(SHELL);
  await c.addAll(CORE);
  try { const poses = await (await fetch("data/poses.json", { cache: "no-store" })).json(); await c.addAll(poses.filter(p => p.svg).map(p => p.svg)); } catch (_) {}
  self.skipWaiting();
})()));
self.addEventListener("activate", e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k.startsWith("ps-shell-") && k !== SHELL) await caches.delete(k);
  await clients.claim();
})()));
async function trim(c) { const ks = await c.keys(); for (let i = 0; i < ks.length - MAX_IMG; i++) await c.delete(ks[i]); }
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET") return;
  const u = new URL(r.url); if (u.origin !== location.origin) return;
  const path = u.pathname;
  if (/\/imported\//.test(path)) {                       // photos: cache-first (never change: content-hashed names)
    e.respondWith((async () => {
      const c = await caches.open(IMG), hit = await c.match(r, { ignoreVary: true }); if (hit) return hit;
      const res = await fetch(r); if (res.ok) { c.put(r, res.clone()); trim(c); } return res;
    })()); return;
  }
  if (/\/assets\/builtin\//.test(path)) {                // built-in SVGs: cache-first
    e.respondWith(caches.match(r).then(h => h || fetch(r).then(res => { const cp = res.clone(); caches.open(SHELL).then(c => c.put(r, cp)); return res; }))); return;
  }
  // shell + data: network-first (new imports show up at once), fall back to cache offline
  e.respondWith((async () => {
    try {
      const res = await fetch(r); if (res.ok) { const cp = res.clone(); caches.open(SHELL).then(c => c.put(r.mode === "navigate" ? "index.html" : r, cp)); } return res;
    } catch (_) {
      return (await caches.match(r, { ignoreSearch: true })) || (r.mode === "navigate" ? await caches.match("index.html") : Response.error());
    }
  })());
});
