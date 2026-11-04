// Offline PWA. Bump VERSION when shipping app changes.
// v3.9: thumbnails and full images live in SEPARATE caches so browsing full-size photos can never evict thumbnails.
const VERSION = "v4.0.0", SHELL = "ps-shell-" + VERSION;
const THUMBS = "ps-thumbs-v1", FULL = "ps-full-v1", LEGACY_IMG = "ps-img-v1";
const MAX_THUMBS = 3000;   // far above the photo count (606): thumbnails are small and must never be evicted in practice
const MAX_FULL = 400;      // full images are big: keep the 400 most recently viewed (LRU)
// data/imported.json is intentionally NOT precached: it is network-first (new imports show up at once) with cache fallback.
const CORE = ["./", "index.html", "style.css", "app.js", "manifest.webmanifest", "assets/icon.svg", "assets/icon-192.png", "assets/icon-512.png", "data/taxonomy.json"];
self.addEventListener("install", e => e.waitUntil((async () => {
  const c = await caches.open(SHELL);
  await c.addAll(CORE);
  self.skipWaiting();
})()));
self.addEventListener("activate", e => e.waitUntil((async () => {
  const keep = await caches.open(SHELL);
  for (const k of await caches.keys()) {
    if (k.startsWith("ps-shell-") && k !== SHELL) {
      // carry over data files (e.g. imported.json) fetched under the old version so an offline start right after an update still works
      try { const old = await caches.open(k); for (const req of await old.keys()) if (!(await keep.match(req))) { const r = await old.match(req); if (r) await keep.put(req, r); } } catch (_) {}
      await caches.delete(k);
    }
  }
  try { await migrateLegacy(); } catch (_) {}
  await clients.claim();
})()));
// v3.8 kept thumbs + full images in one cache ("ps-img-v1"); split it once, then drop it.
async function migrateLegacy() {
  if (!(await caches.has(LEGACY_IMG))) return;
  const old = await caches.open(LEGACY_IMG), th = await caches.open(THUMBS), fu = await caches.open(FULL);
  for (const req of await old.keys()) {
    const r = await old.match(req); if (!r) continue;
    if (/\/imported\/thumbs\//.test(req.url)) await th.put(req, r); else await fu.put(req, r);
  }
  await caches.delete(LEGACY_IMG); await trim(fu, MAX_FULL);
}
// Cache API keys() is in insertion order, so the front of the list is the oldest. Serialised + awaited (callers waitUntil it).
let trimming = Promise.resolve();
function trim(c, max) {
  return trimming = trimming.catch(() => {}).then(async () => {
    const ks = await c.keys();
    for (let i = 0; i < ks.length - max; i++) await c.delete(ks[i]);
  });
}
self.addEventListener("fetch", e => {
  const r = e.request; if (r.method !== "GET") return;
  const u = new URL(r.url); if (u.origin !== location.origin) return;
  const path = u.pathname;
  if (/\/imported\//.test(path)) {                       // photos: cache-first (never change: content-hashed names)
    const isThumb = /\/imported\/thumbs\//.test(path), name = isThumb ? THUMBS : FULL, max = isThumb ? MAX_THUMBS : MAX_FULL;
    e.respondWith((async () => {
      const c = await caches.open(name), hit = await c.match(r, { ignoreVary: true });
      if (hit) {
        // LRU: re-inserting a viewed full image moves it to the back of keys() so it is evicted last
        if (!isThumb) e.waitUntil(c.put(r, hit.clone()).catch(() => {}));
        return hit;
      }
      const res = await fetch(r);
      if (res.status === 200) e.waitUntil(c.put(r, res.clone()).then(() => trim(c, max)).catch(() => {}));
      return res;
    })()); return;
  }
  // shell + data (incl. data/imported.json): network-first, fall back to cache offline
  e.respondWith((async () => {
    try {
      const res = await fetch(r); if (res.ok) { const cp = res.clone(); e.waitUntil(caches.open(SHELL).then(c => c.put(r.mode === "navigate" ? "index.html" : r, cp)).catch(() => {})); } return res;
    } catch (_) {
      return (await caches.match(r, { ignoreSearch: true })) || (r.mode === "navigate" ? await caches.match("index.html") : Response.error());
    }
  })());
});
