/* 拍照摆姿 · photo-first pose atlas. No dependencies. Ideas (thumbnail grid, filter panel, big-photo modal
   with prev/next + keyboard, deep links) are inspired by RuiC-PoseAtlas; no code or assets were copied. */
(() => {
'use strict';
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const LS = { get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} } };
const BATCH = 30;

// ---------- state ----------
const S = { tax: null, dims: [], tagDim: {}, poses: [], byId: {}, seqs: [], useqs: LS.get('ps_useq', []),
  fav: new Set(LS.get('ps_fav', [])), list: LS.get('ps_list', []),
  coll: LS.get('ps_coll', null), speak: LS.get('ps_speak', false), q: '', f: {}, favOnly: false, filtered: [], shown: 0, view: 'lib',
  ctx: [], ctxI: 0, seq: null, stepI: 0, auto: null };
const isPhoto = p => p.type !== 'builtin';

// ---------- data ----------
async function getJSON(u, d) { try { const r = await fetch(u); if (!r.ok) throw 0; return await r.json(); } catch { return d; } }
function normTags(p) {
  let t = p.tags, extra = [...(p.extra || [])];
  if (Array.isArray(t)) { // legacy flat list -> classify against the taxonomy
    const o = {}; t.forEach(w => { const d = S.tagDim[w]; if (d) (o[d] = o[d] || []).push(w); else extra.push(w); });
    ['scene', 'mood'].forEach(k => (p[k] || []).forEach(w => { const a = o[k] = o[k] || []; if (!a.includes(w)) a.push(w); }));
    if (p.posture) (o.posture = o.posture || []).push(p.posture);
    t = o;
  }
  p.tags = t || {}; p.extra = extra;
}
function index(p) {
  normTags(p);
  const words = [p.title, p.kouling, p.note, ...(p.extra || []), ...Object.values(p.tags).flat(), ...(p.tips || []).map(t => Array.isArray(t) ? t.join('') : t)];
  p._s = words.join(' ').toLowerCase();
  p._ts = new Set(Object.entries(p.tags).flatMap(([d, a]) => a.map(v => d + ':' + v)));
}
async function loadAll() {
  const [tax, bi, im, sq, usq] = await Promise.all([getJSON('data/taxonomy.json', { dimensions: [] }), getJSON('data/poses.json', []), getJSON('data/imported.json', []),
    getJSON('data/sequences.json', []), getJSON('data/sequences_user.json', [])]);
  S.tax = tax; S.dims = tax.dimensions;
  S.dims.forEach(d => d.tags.forEach(t => { if (!S.tagDim[t]) S.tagDim[t] = d.key; }));
  const custom = await idbAll().catch(() => []);
  const cp = custom.map(c => ({ id: c.id, type: 'custom', title: c.title, kouling: c.kouling || '', tags: c.tags || {}, extra: c.extra || [], tips: [], note: '', added_at: c.added_at,
    image: URL.createObjectURL(c.blob), thumb: URL.createObjectURL(c.thumb || c.blob), w: c.w, h: c.h }));
  const imp = im.slice().reverse(); // newest imports first
  S.poses = [...cp.reverse(), ...imp, ...bi];
  S.poses.forEach(p => { index(p); S.byId[p.id] = p; });
  S.seqs = [...sq, ...usq].map(s => ({ ...s, poses: (s.poses || []).filter(id => S.byId[id]) })).filter(s => s.poses.length);
  S.useqs.forEach(s => { if (!S.seqs.find(x => x.id === s.id)) S.seqs.push({ ...s, user: true }); });
  S.list = S.list.filter(x => S.byId[x.id]); S.fav = new Set([...S.fav].filter(id => S.byId[id]));
}

// ---------- IndexedDB (custom poses) ----------
let _db;
function db() { return _db || (_db = new Promise((res, rej) => { const r = indexedDB.open('pose-app', 1); r.onupgradeneeded = () => r.result.createObjectStore('custom', { keyPath: 'id' }); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); })); }
async function idbAll() { const d = await db(); return new Promise((res, rej) => { const q = d.transaction('custom').objectStore('custom').getAll(); q.onsuccess = () => res(q.result.sort((a, b) => (a.added_at < b.added_at ? -1 : 1))); q.onerror = () => rej(q.error); }); }
async function idbPut(o) { const d = await db(); return new Promise((res, rej) => { const t = d.transaction('custom', 'readwrite'); t.objectStore('custom').put(o); t.oncomplete = res; t.onerror = () => rej(t.error); }); }
async function idbDel(id) { const d = await db(); return new Promise((res, rej) => { const t = d.transaction('custom', 'readwrite'); t.objectStore('custom').delete(id); t.oncomplete = res; t.onerror = () => rej(t.error); }); }

// ---------- helpers ----------
const thumbOf = p => p.type === 'builtin' ? p.svg : (p.thumb || p.image);
const fullOf = p => p.type === 'builtin' ? p.svg : p.image;
const ratio = p => p.type === 'builtin' ? 1.25 : (p.w && p.h ? p.h / p.w : 1.25);
const dimLabel = k => (S.dims.find(d => d.key === k) || {}).label || k;
function toast(m) { const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), 1800); }
const saveFav = () => LS.set('ps_fav', [...S.fav]);
const saveList = () => { LS.set('ps_list', S.list); renderBadge(); };
const inList = id => S.list.find(x => x.id === id);
function flatTags(p) { return Object.entries(p.tags).flatMap(([d, a]) => a.map(v => [d, v])); }

// ---------- overlays + history ----------
const stack = []; let skipPop = 0;
function openOv(id, hash) {
  const el = $('#' + id); el.hidden = false; el.scrollTop = 0; stack.push(id);
  history.pushState({ ov: id }, '', hash || location.pathname + location.search); document.body.style.overflow = 'hidden';
}
function hideOv(id) {
  $('#' + id).hidden = true; if (id === 'step') stopAuto(); if (id === 'card') speechSynthesis?.cancel?.();
}
function closeTop() { if (stack.length) history.back(); }
function closeAll() { const n = stack.length; if (!n) return; skipPop = 1; stack.splice(0).forEach(hideOv); document.body.style.overflow = ''; history.go(-n); }
window.addEventListener('popstate', () => {
  if (skipPop) { skipPop = 0; return; }
  const id = stack.pop(); if (id) hideOv(id);
  if (!stack.length) document.body.style.overflow = '';
});
$$('[data-close]').forEach(b => b.onclick = closeTop);
document.addEventListener('keydown', e => {
  const top = stack[stack.length - 1];
  if (e.key === 'Escape' && top) closeTop();
  else if (top === 'card') { if (e.key === 'ArrowLeft') cardNav(-1); if (e.key === 'ArrowRight') cardNav(1); }
  else if (top === 'step') { if (e.key === 'ArrowLeft') stepGo(-1); if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); stepGo(1); } }
});
function swipe(el, onL, onR) {
  let x0, y0, t0, id = null;
  el.addEventListener('pointerdown', e => { if (e.target.closest('button,a,input,select,textarea,summary')) return; id = e.pointerId; x0 = e.clientX; y0 = e.clientY; t0 = Date.now(); });
  el.addEventListener('pointerup', e => {
    if (e.pointerId !== id) return; id = null; const dx = e.clientX - x0, dy = e.clientY - y0;
    if (Date.now() - t0 < 900 && Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) (dx < 0 ? onL : onR)();
  });
  el.addEventListener('pointercancel', () => { id = null; });
}

// ---------- filtering ----------
const collItems = () => S.poses.filter(p => S.coll === 'all' || (S.coll === 'photo' ? isPhoto(p) : !isPhoto(p)));
function matches(p, skipDim) {
  if (S.favOnly && !S.fav.has(p.id)) return false;
  for (const [d, set] of Object.entries(S.f)) { if (d === skipDim || !set.size) continue; if (![...set].some(v => p._ts.has(d + ':' + v))) return false; }
  if (S.q) { for (const w of S.q.toLowerCase().split(/\s+/).filter(Boolean)) if (!p._s.includes(w)) return false; }
  return true;
}
const activeCount = () => Object.values(S.f).reduce((n, s) => n + s.size, 0);
function applyFilters() {
  S.filtered = collItems().filter(p => matches(p));
  renderActive(); renderGrid(true);
}
function toggleTag(d, v, on) {
  const s = S.f[d] = S.f[d] || new Set(); (on ?? !s.has(v)) ? s.add(v) : s.delete(v);
}

// ---------- library ----------
function renderColl() {
  const np = S.poses.filter(isPhoto).length, nb = S.poses.length - np;
  const opts = [['photo', '照片', np], ['svg', '示意图', nb], ['all', '全部', S.poses.length]];
  $('#coll').innerHTML = opts.map(([k, l, n]) => `<button role="tab" data-c="${k}" class="${S.coll === k ? 'on' : ''}" aria-selected="${S.coll === k}">${l}<b>${n}</b></button>`).join('');
  $$('#coll button').forEach(b => b.onclick = () => { S.coll = b.dataset.c; LS.set('ps_coll', S.coll); renderColl(); applyFilters(); });
}
function renderActive() {
  const chips = Object.entries(S.f).flatMap(([d, s]) => [...s].map(v => `<button class="chip" data-d="${d}" data-v="${esc(v)}">${esc(v)}<i>✕</i></button>`));
  if (S.q) chips.unshift(`<button class="chip" data-q="1">“${esc(S.q)}”<i>✕</i></button>`);
  const a = $('#active'); a.hidden = !chips.length;
  a.innerHTML = chips.join('') + (chips.length ? '<button class="clr" id="a-clear">清除全部</button>' : '');
  $$('#active .chip').forEach(b => b.onclick = () => { if (b.dataset.q) { S.q = ''; $('#search').value = ''; } else toggleTag(b.dataset.d, b.dataset.v, false); applyFilters(); });
  const c = $('#a-clear'); if (c) c.onclick = clearAll;
  const n = activeCount(); $('#fcount').textContent = n || '';
}
function clearAll() { S.f = {}; S.q = ''; S.favOnly = false; $('#search').value = ''; $('#favf').setAttribute('aria-pressed', 'false'); applyFilters(); }
let cols = [], heights = [];
function renderGrid(reset) {
  const g = $('#grid');
  if (reset) {
    S.shown = 0; heights = [0, 0]; g.innerHTML = '<div class="col"></div><div class="col"></div>'; cols = [...g.children];
    const np = S.poses.some(isPhoto);
    $('#nophotos').hidden = np;
    $('#noresult').hidden = S.filtered.length > 0;
    const n = S.filtered.length, tot = collItems().length;
    $('#count').textContent = (activeCount() || S.q || S.favOnly ? `${n} / ${tot} 个动作` : `${tot} 个动作`);
  }
  const next = S.filtered.slice(S.shown, S.shown + BATCH);
  for (const p of next) {
    const i = heights[0] <= heights[1] ? 0 : 1; heights[i] += ratio(p) + 0.34;
    cols[i].insertAdjacentHTML('beforeend', cardHTML(p));
  }
  S.shown += next.length;
}
function cardHTML(p) {
  const tg = flatTags(p).filter(([d]) => ['scene', 'light', 'style', 'posture'].includes(d)).slice(0, 3).map(x => x[1]).join(' · ');
  const r = ratio(p);
  return `<div class="pc ${p.type === 'builtin' ? 'svg' : ''}" data-id="${p.id}" tabindex="0" role="button" aria-label="${esc(p.title)}">
    <div class="art" style="aspect-ratio:${(1 / r).toFixed(3)}"><img src="${esc(thumbOf(p))}" alt="${esc(p.title)}" loading="lazy" decoding="async"></div>
    ${p.type === 'builtin' ? '<span class="badge">示意</span>' : ''}${inList(p.id) ? '<span class="in">清单</span>' : ''}
    <div class="qa"><button data-fav="${p.id}" class="${S.fav.has(p.id) ? 'on' : ''}" aria-label="收藏">${S.fav.has(p.id) ? '♥' : '♡'}</button></div>
    <div class="t">${esc(p.title)}<div class="s">${esc(tg)}</div></div></div>`;
}
$('#grid').addEventListener('click', e => {
  const f = e.target.closest('[data-fav]');
  if (f) { e.stopPropagation(); toggleFav(f.dataset.fav); return; }
  const c = e.target.closest('.pc'); if (c) openCard(c.dataset.id, S.filtered.map(p => p.id));
});
$('#grid').addEventListener('keydown', e => { if (e.key === 'Enter') { const c = e.target.closest('.pc'); if (c) openCard(c.dataset.id, S.filtered.map(p => p.id)); } });
new IntersectionObserver(es => { if (es[0].isIntersecting && S.view === 'lib' && S.shown < S.filtered.length) renderGrid(false); }, { rootMargin: '600px' }).observe($('#sentinel'));
function toggleFav(id) {
  S.fav.has(id) ? S.fav.delete(id) : S.fav.add(id); saveFav(); toast(S.fav.has(id) ? '已收藏' : '已取消收藏');
  $$(`[data-fav="${id}"]`).forEach(b => { b.classList.toggle('on', S.fav.has(id)); b.textContent = S.fav.has(id) ? '♥' : '♡'; });
  if (S.favOnly) applyFilters();
  if (!$('#card').hidden && S.ctx[S.ctxI] === id) renderCardBtns();
}
let st; $('#search').addEventListener('input', e => { clearTimeout(st); st = setTimeout(() => { S.q = e.target.value.trim(); applyFilters(); }, 150); });
$('#favf').onclick = () => { S.favOnly = !S.favOnly; $('#favf').setAttribute('aria-pressed', S.favOnly); $('#favf').textContent = S.favOnly ? '♥' : '♡'; applyFilters(); };
$('#clearall').onclick = clearAll;

// ---------- filter sheet / tag picker ----------
function buildPicker(root, sel, opt) {
  // sel: {dim:Set}; opt.counts(dim,tag)->n or null; opt.items: poses for presence; opt.onchange
  root.innerHTML = '';
  S.dims.forEach(d => {
    const present = opt.all ? d.tags : d.tags.filter(t => opt.items.some(p => p._ts.has(d.key + ':' + t)) || (sel[d.key] && sel[d.key].has(t)));
    if (!present.length) return;
    const div = document.createElement('div'); div.className = 'dim'; div.dataset.dim = d.key;
    const sc = sel[d.key] ? sel[d.key].size : 0;
    div.innerHTML = `<b>${esc(d.label)}${sc ? `<small>已选 ${sc}</small>` : ''}</b><div class="chips">` + present.map(t => {
      const on = sel[d.key] && sel[d.key].has(t), n = opt.counts ? opt.counts(d.key, t) : null;
      return `<button type="button" class="chip ${on ? 'on' : ''} ${n === 0 && !on ? 'off' : ''}" data-d="${d.key}" data-t="${esc(t)}" aria-pressed="${!!on}">${esc(t)}${n != null ? `<small>${n}</small>` : ''}</button>`;
    }).join('') + '</div>';
    root.appendChild(div);
  });
  root.onclick = e => {
    const b = e.target.closest('.chip'); if (!b) return; const d = b.dataset.d, t = b.dataset.t;
    const s = sel[d] = sel[d] || new Set(); s.has(t) ? s.delete(t) : s.add(t); opt.onchange && opt.onchange();
  };
}
function renderSheet() {
  const items = collItems(), keep = $('#fbody').scrollTop;
  buildPicker($('#fbody'), S.f, { items, counts: (d, t) => items.filter(p => p._ts.has(d + ':' + t) && matches(p, d)).length, onchange() { S.filtered = collItems().filter(p => matches(p)); renderSheet(); } });
  $('#fbody').scrollTop = keep; $('#f-done').textContent = `查看 ${S.filtered.length} 个`;
  renderActive();
}
$('#filterbtn').onclick = () => { renderSheet(); openOv('fsheet'); };
$('#f-done').onclick = () => { closeTop(); applyFilters(); };
$('#f-clear').onclick = () => { S.f = {}; S.filtered = collItems().filter(p => matches(p)); renderSheet(); };
$('#fsheet').addEventListener('click', e => { if (e.target.id === 'fsheet') { closeTop(); applyFilters(); } });

// ---------- card ----------
function openCard(id, ctx) {
  S.ctx = ctx && ctx.length ? ctx : [id]; S.ctxI = Math.max(0, S.ctx.indexOf(id));
  openOv('card', '#pose=' + id); renderCard();
}
function cardNav(d) {
  if (S.ctx.length < 2) return; S.ctxI = (S.ctxI + d + S.ctx.length) % S.ctx.length;
  history.replaceState({ ov: 'card' }, '', '#pose=' + S.ctx[S.ctxI]); renderCard();
}
function renderCardBtns() {
  const id = S.ctx[S.ctxI];
  $('#btn-fav').textContent = S.fav.has(id) ? '♥ 已收藏' : '♡ 收藏'; $('#btn-fav').classList.toggle('on', S.fav.has(id));
  const li = inList(id); $('#btn-list').textContent = li ? '移出清单' : '＋清单'; $('#btn-list').classList.toggle('on', !!li);
  const bd = $('#btn-done'); bd.hidden = !li; if (li) { bd.textContent = li.done ? '↺ 取消已拍' : '✓ 已拍'; bd.classList.toggle('on', !!li.done); }
}
function renderCard() {
  const p = S.byId[S.ctx[S.ctxI]]; if (!p) return;
  const art = $('#c-art'); art.querySelectorAll('img').forEach(i => i.remove());
  const img = new Image(); img.alt = p.title; img.src = thumbOf(p); art.prepend(img);
  if (navigator.onLine && p.type !== 'builtin' && p.image !== thumbOf(p)) { const full = new Image(); full.onload = () => { if (S.byId[S.ctx[S.ctxI]] === p) img.src = full.src; }; full.src = p.image; }
  const preload = i => { const q = S.byId[S.ctx[(S.ctxI + i + S.ctx.length) % S.ctx.length]]; if (navigator.onLine && q && q.type !== 'builtin') new Image().src = q.image; };
  if (S.ctx.length > 1) { preload(1); preload(-1); }
  $('#c-pos').textContent = `${S.ctxI + 1} / ${S.ctx.length}`; $('#c-pos').hidden = S.ctx.length < 2;
  $('#c-aprev').hidden = $('#c-anext').hidden = S.ctx.length < 2;
  $('#c-title').textContent = p.title;
  const groups = {}; flatTags(p).forEach(([d, v]) => (groups[d] = groups[d] || []).push(v));
  const order = S.dims.map(d => d.key).filter(k => groups[k]);
  $('#c-tags').innerHTML = order.map(k => `<div class="tg"><em>${esc(dimLabel(k))}</em>${groups[k].map(v => `<button data-d="${k}" data-t="${esc(v)}">${esc(v)}</button>`).join('')}</div>`).join('')
    + (p.extra.length ? `<div class="tg"><em>其他</em>${p.extra.map(v => `<button data-q="${esc(v)}">${esc(v)}</button>`).join('')}</div>` : '');
  $('#c-kou').hidden = !p.kouling; $('#c-kouText').textContent = p.kouling || ''; $('#c-kou').classList.remove('xl');
  $('#c-speak').hidden = !('speechSynthesis' in window) || !p.kouling; $('#c-copy').hidden = !p.kouling;
  const tips = (p.tips || []).map(t => Array.isArray(t) ? `<li class="${t[0] === '避坑' ? 'warn' : ''}"><b>${esc(t[0])}</b>${esc(t[1])}</li>` : `<li>${esc(t)}</li>`).join('');
  const det = $('#c-details'); det.hidden = !tips; det.innerHTML = tips ? `<h4>动作要点</h4><ul>${tips}</ul>` : '';
  const shot = p.shot ? Object.entries(p.shot).map(([k, v]) => `<span>${esc(k)} ${esc(v)}</span>`).join('') : '';
  const sh = $('#c-shot'); sh.hidden = !shot; sh.innerHTML = shot ? `<h4>拍摄建议</h4><div class="shots">${shot}</div>` : '';
  const ex = $('#c-extra'); const bits = [];
  if (p.note) bits.push(`<div>${esc(p.note)}</div>`);
  const links = []; if (p.source_url) links.push(`<a href="${esc(p.source_url)}" target="_blank" rel="noopener noreferrer">查看原帖 ↗</a>`);
  if (p.type === 'image') links.push(`<a href="${esc(p.image)}" download="${esc(p.title)}.jpg">下载原图</a>`);
  if (links.length) bits.push(`<div class="src">${links.join('')}</div>`);
  ex.hidden = !bits.length; ex.innerHTML = bits.join('');
  renderCardBtns();
}
$('#c-tags').onclick = e => {
  const b = e.target.closest('button'); if (!b) return;
  closeAll();
  if (b.dataset.q) { S.q = b.dataset.q; $('#search').value = S.q; } else { S.q = ''; $('#search').value = ''; S.f = {}; toggleTag(b.dataset.d, b.dataset.t, true); }
  const p = S.byId[S.ctx[S.ctxI]]; if (p && S.coll !== 'all' && (S.coll === 'photo') !== isPhoto(p)) { S.coll = p.type === 'builtin' ? 'svg' : 'photo'; renderColl(); }
  setView('lib'); applyFilters(); window.scrollTo(0, 0);
};
$('#c-prev').onclick = $('#c-aprev').onclick = () => cardNav(-1);
$('#c-next').onclick = $('#c-anext').onclick = () => cardNav(1);
$('#c-rand').onclick = () => { if (S.ctx.length > 1) { S.ctxI = (S.ctxI + 1 + Math.floor(Math.random() * (S.ctx.length - 1))) % S.ctx.length; history.replaceState({ ov: 'card' }, '', '#pose=' + S.ctx[S.ctxI]); renderCard(); } };
$('#btn-fav').onclick = () => toggleFav(S.ctx[S.ctxI]);
$('#btn-list').onclick = () => { const id = S.ctx[S.ctxI]; toggleList(id); renderCardBtns(); };
$('#btn-done').onclick = () => { const li = inList(S.ctx[S.ctxI]); if (li) { li.done = !li.done; saveList(); renderCardBtns(); renderChecklist(); } };
function toggleList(id) {
  const i = S.list.findIndex(x => x.id === id);
  if (i >= 0) { S.list.splice(i, 1); toast('已移出清单'); } else { S.list.push({ id, done: false }); toast('已加入清单'); }
  saveList(); renderChecklist(); $$(`.pc[data-id="${id}"]`).forEach(c => { c.querySelector('.in')?.remove(); if (inList(id)) c.insertAdjacentHTML('afterbegin', '<span class="in">清单</span>'); });
}
$('#c-kou').onclick = () => $('#c-kou').classList.toggle('xl');
$('#c-kou').onkeydown = e => { if (e.key === 'Enter') $('#c-kou').click(); };
function speak(t) { if (!('speechSynthesis' in window) || !t) return; speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'zh-CN'; u.rate = .95; speechSynthesis.speak(u); }
$('#c-speak').onclick = () => speak(S.byId[S.ctx[S.ctxI]].kouling);
$('#c-copy').onclick = async () => { const t = S.byId[S.ctx[S.ctxI]].kouling; try { await navigator.clipboard.writeText(t); toast('口令已复制'); } catch { toast('复制失败'); } };
$('#c-share').onclick = async () => { const u = location.origin + location.pathname + '#pose=' + S.ctx[S.ctxI]; try { await navigator.clipboard.writeText(u); toast('链接已复制'); } catch { toast(u); } };
swipe($('#card'), () => cardNav(1), () => cardNav(-1));
function randomPose() {
  const pool = S.filtered.length ? S.filtered : collItems(); if (!pool.length) return toast('没有可选的动作');
  const p = pool[Math.floor(Math.random() * pool.length)];
  const pl = $('#card').hidden ? null : 1; if (pl) { S.ctxI = S.ctx.indexOf(p.id); renderCard(); } else openCard(p.id, pool.map(x => x.id));
}
$('#rand').onclick = () => { if (S.view !== 'lib') setView('lib'); randomPose(); };

// ---------- sequences ----------
const seqPoses = s => s.poses.map(id => S.byId[id]).filter(Boolean);
function renderSeqs() {
  $('#seqlist').innerHTML = S.seqs.map(s => `<button class="sc" data-s="${s.id}"><div class="ttl"><b>${esc(s.title)}</b>${s.user ? '<span class="mine">我的</span>' : ''}</div>
    <div class="muted">${seqPoses(s).length} 个动作${s.desc ? ' · ' + esc(s.desc) : ''}</div>
    <div class="thumbs">${seqPoses(s).slice(0, 6).map(p => `<div class="art"><img src="${esc(thumbOf(p))}" alt="" loading="lazy"></div>`).join('')}</div></button>`).join('') || '<div class="empty">还没有连拍组合</div>';
}
$('#seqlist').onclick = e => { const b = e.target.closest('[data-s]'); if (b) openSeq(b.dataset.s); };
function openSeq(id) {
  const s = S.seqs.find(x => x.id === id); S.seq = s;
  $('#sd-title').textContent = s.title; $('#sd-desc').textContent = s.desc || ''; $('#sd-tip').textContent = s.tip ? '📷 ' + s.tip : ''; $('#sd-tip').hidden = !s.tip;
  const tg = [...(Array.isArray(s.scene) ? s.scene : s.scene ? [s.scene] : []), ...(s.mood ? [s.mood] : [])];
  $('#sd-tags').innerHTML = tg.map(t => `<span>${esc(t)}</span>`).join('');
  $('#sd-steps').innerHTML = seqPoses(s).map((p, i) => `<div class="li" data-id="${p.id}"><div class="art"><img src="${esc(thumbOf(p))}" alt=""></div><div class="m"><b>${i + 1}. ${esc(p.title)}</b><div>${esc(p.kouling)}</div></div></div>`).join('');
  $('#sd-del').hidden = !s.user; openOv('seqd', '#seq=' + id);
}
$('#sd-steps').onclick = e => { const l = e.target.closest('.li'); if (l) openCard(l.dataset.id, seqPoses(S.seq).map(p => p.id)); };
$('#sd-addall').onclick = () => { let n = 0; seqPoses(S.seq).forEach(p => { if (!inList(p.id)) { S.list.push({ id: p.id, done: false }); n++; } }); saveList(); renderChecklist(); toast(`已加入 ${n} 个到清单`); };
$('#sd-del').onclick = () => { if (!confirm('删除这个连拍？')) return; S.useqs = S.useqs.filter(x => x.id !== S.seq.id); LS.set('ps_useq', S.useqs); S.seqs = S.seqs.filter(x => x.id !== S.seq.id); closeTop(); renderSeqs(); };
function startStep(ids, title) {
  S.stepIds = ids; S.stepI = 0; S.stepTitle = title; openOv('step', '#step'); renderStep();
}
$('#seq-start').onclick = () => startStep(S.seq.poses.filter(id => S.byId[id]), S.seq.title);
function renderStep() {
  $('#st-speak').hidden = !('speechSynthesis' in window); $('#st-speak').textContent = '🔊 自动朗读：' + (S.speak ? '开' : '关');
  const p = S.byId[S.stepIds[S.stepI]], n = S.stepIds.length;
  $('#st-dots').innerHTML = S.stepIds.map((_, i) => `<i class="${i === S.stepI ? 'on' : i < S.stepI ? 'past' : ''}"></i>`).join('');
  $('#st-count').textContent = `${S.stepTitle || ''} · 第 ${S.stepI + 1} / ${n} 个`;
  $('#st-art').innerHTML = `<img src="${esc(thumbOf(p))}" alt="${esc(p.title)}">`;
  if (navigator.onLine && p.type !== 'builtin' && p.image !== thumbOf(p)) { const f = new Image(); f.onload = () => { if (S.byId[S.stepIds[S.stepI]] === p) $('#st-art img').src = f.src; }; f.src = p.image; }
  $('#st-title').textContent = p.title; $('#st-kou').textContent = p.kouling || '（没有口令，按照片摆姿）';
  const t0 = (p.tips || [])[0]; $('#st-hint').textContent = t0 ? (Array.isArray(t0) ? t0.join('：') : t0) : '';
  $('#st-next').textContent = S.stepI === n - 1 ? '完成 ✓' : '下一步 ›'; $('#st-prev').disabled = S.stepI === 0;
  const li = inList(p.id); $('#st-done').hidden = !li; if (li) { $('#st-done').textContent = li.done ? '↺ 取消已拍' : '✓ 已拍'; }
  if (S.speak) speak(p.kouling);
}
function stepGo(d) {
  const n = S.stepIds.length, i = S.stepI + d;
  if (i >= n) { toast('这组拍完啦 🎉'); closeTop(); return; } if (i < 0) return;
  S.stepI = i; renderStep(); if (S.auto) startAuto();
}
$('#st-next').onclick = () => stepGo(1); $('#st-prev').onclick = () => stepGo(-1);
$('#st-done').onclick = () => { const li = inList(S.stepIds[S.stepI]); if (li) { li.done = !li.done; saveList(); renderChecklist(); if (li.done) stepGo(1); else renderStep(); } };
function startAuto() { clearInterval(S.autoT); S.autoT = setInterval(() => stepGo(1), 7000); }
function stopAuto() { clearInterval(S.autoT); S.auto = false; $('#st-auto').textContent = '⏱ 自动：关'; $('#st-auto').classList.remove('on'); }
$('#st-auto').onclick = () => { if (S.auto) stopAuto(); else { S.auto = true; $('#st-auto').textContent = '⏱ 自动：7秒'; $('#st-auto').classList.add('on'); startAuto(); } };
$('#st-speak').onclick = () => { S.speak = !S.speak; LS.set('ps_speak', S.speak); $('#st-speak').textContent = '🔊 自动朗读：' + (S.speak ? '开' : '关'); if (S.speak) speak(S.byId[S.stepIds[S.stepI]].kouling); else speechSynthesis?.cancel?.(); };
swipe($('#step'), () => stepGo(1), () => stepGo(-1));

// ---------- checklist ----------
function renderBadge() { const n = S.list.filter(x => !x.done).length; $('#listbadge').textContent = n || ''; }
function renderChecklist() {
  const done = S.list.filter(x => x.done).length, n = S.list.length;
  $('#progress').innerHTML = n ? `<div>已拍 <b>${done}</b> / ${n}</div><div class="bar-p"><i style="width:${Math.round(done / n * 100)}%"></i></div>` : '<div class="empty">清单是空的<br>在图鉴里打开一个动作，点「＋清单」，或点「随机加5个」</div>';
  $('#checklist').innerHTML = S.list.map(x => { const p = S.byId[x.id];
    return `<div class="li ${x.done ? 'done' : ''}" data-id="${p.id}"><input type="checkbox" ${x.done ? 'checked' : ''} aria-label="已拍"><div class="art"><img src="${esc(thumbOf(p))}" alt="" loading="lazy"></div><div class="m"><b>${esc(p.title)}</b><div>${esc(p.kouling)}</div></div><button class="rm" aria-label="移出">✕</button></div>`; }).join('');
  renderBadge();
}
$('#checklist').onclick = e => {
  const l = e.target.closest('.li'); if (!l) return; const id = l.dataset.id;
  if (e.target.closest('.rm')) { toggleList(id); return; }
  if (e.target.matches('input')) { const li = inList(id); li.done = e.target.checked; saveList(); renderChecklist(); return; }
  openCard(id, S.list.map(x => x.id));
};
$('#l-add').onclick = () => setView('lib');
$('#l-rand').onclick = () => {
  const pool = (S.filtered.length ? S.filtered : collItems()).filter(p => !inList(p.id)); let n = 0;
  while (pool.length && n < 5) { const p = pool.splice(Math.floor(Math.random() * pool.length), 1)[0]; S.list.push({ id: p.id, done: false }); n++; }
  saveList(); renderChecklist(); toast(n ? `随机加入了 ${n} 个` : '没有更多可加的了');
};
$('#l-reset').onclick = () => { S.list.forEach(x => x.done = false); saveList(); renderChecklist(); toast('已重置勾选'); };
$('#l-clear').onclick = () => { if (!S.list.length || !confirm('清空今日清单？')) return; S.list = []; saveList(); renderChecklist(); $$('.pc .in').forEach(e => e.remove()); };
$('#l-start').onclick = () => { const ids = S.list.filter(x => !x.done).map(x => x.id); if (!ids.length) return toast(S.list.length ? '都拍完啦' : '清单是空的'); startStep(ids, '今日清单'); };
$('#l-saveseq').onclick = () => {
  if (S.list.length < 2) return toast('清单里至少要 2 个动作');
  const title = (prompt('给这个连拍起个名字', '我的连拍 ' + (S.useqs.length + 1)) || '').trim(); if (!title) return;
  const s = { id: 'u' + Date.now(), title, desc: '自建连拍', poses: S.list.map(x => x.id), user: true };
  S.useqs.push(s); LS.set('ps_useq', S.useqs); S.seqs.push(s); renderSeqs(); toast('已保存到「连拍」');
};

// ---------- custom poses ----------
const cSel = {};
function renderCustom() {
  const mine = S.poses.filter(p => p.type === 'custom');
  $('#customlist').innerHTML = mine.map(p => `<div class="li" data-id="${p.id}"><div class="art"><img src="${esc(p.thumb)}" alt=""></div><div class="m"><b>${esc(p.title)}</b><div>${esc(p.kouling || '（无口令）')}</div></div><button class="del">删除</button></div>`).join('') || '<div class="empty">还没有自建动作</div>';
}
$('#customlist').onclick = async e => {
  const l = e.target.closest('.li'); if (!l) return; const id = l.dataset.id;
  if (e.target.closest('.del')) {
    if (!confirm('删除这个自建动作？')) return;
    await idbDel(id); S.poses = S.poses.filter(p => p.id !== id); delete S.byId[id]; S.fav.delete(id); saveFav(); S.list = S.list.filter(x => x.id !== id); saveList();
    S.seqs.forEach(s => s.poses = s.poses.filter(x => x !== id));
    renderAll(); toast('已删除'); return;
  }
  openCard(id, S.poses.filter(p => p.type === 'custom').map(p => p.id));
};
$('#c-new').onclick = () => {
  $('#c-form').reset(); $('#f-preview').hidden = true; Object.keys(cSel).forEach(k => delete cSel[k]);
  const draw = () => buildPicker($('#f-picker'), cSel, { all: true, onchange: draw }); draw(); openOv('cform', '#new');
};
$('#f-file').onchange = e => { const f = e.target.files[0]; if (f) { $('#f-preview').src = URL.createObjectURL(f); $('#f-preview').hidden = false; if (!$('#f-name').value) $('#f-name').value = f.name.replace(/\.[^.]+$/, '').slice(0, 30); } };
function toBlob(img, max, q) {
  const r = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight)), w = Math.round(img.naturalWidth * r), h = Math.round(img.naturalHeight * r);
  const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').drawImage(img, 0, 0, w, h);
  return new Promise(res => c.toBlob(b => res({ b, w, h }), 'image/jpeg', q));
}
$('#c-form').onsubmit = async e => {
  e.preventDefault(); const f = $('#f-file').files[0]; if (!f) return;
  try {
    const url = URL.createObjectURL(f), img = new Image(); img.src = url; await img.decode();
    const full = await toBlob(img, 1200, .85), th = await toBlob(img, 480, .8); URL.revokeObjectURL(url);
    const tags = {}; Object.entries(cSel).forEach(([k, s]) => { if (s.size) tags[k] = [...s]; });
    const extra = $('#f-tags').value.split(/[,，;；、\s]+/).filter(Boolean);
    const rec = { id: 'c' + Date.now().toString(36), title: $('#f-name').value.trim(), kouling: $('#f-kou').value.trim(), tags, extra, blob: full.b, thumb: th.b, w: full.w, h: full.h, added_at: new Date().toISOString() };
    await idbPut(rec);
    const p = { id: rec.id, type: 'custom', title: rec.title, kouling: rec.kouling, tags, extra, tips: [], note: '', image: URL.createObjectURL(full.b), thumb: URL.createObjectURL(th.b), w: full.w, h: full.h };
    index(p); S.poses.unshift(p); S.byId[p.id] = p;
    closeTop(); renderAll(); toast('已保存到「照片」');
  } catch (err) { console.error(err); toast('保存失败：' + (err.message || err)); }
};

// ---------- tabs, theme, install, offline ----------
function setView(v) {
  S.view = v; $$('main > section').forEach(s => s.hidden = s.id !== 'v-' + v);
  $$('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  if (v === 'list') renderChecklist(); if (v === 'seq') renderSeqs(); if (v === 'mine') renderCustom();
  if (v === 'lib' && S.shown < Math.min(BATCH, S.filtered.length)) renderGrid(false);
}
$$('#tabs button').forEach(b => b.onclick = () => { if (stack.length) closeAll(); setView(b.dataset.v); window.scrollTo(0, 0); });
function setTheme(t) { document.documentElement.dataset.theme = t; LS.set('ps_theme', t); $$('#theme-seg button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  document.querySelector('meta[name=theme-color]').content = (t === 'dark' || (t === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches)) ? '#241d28' : '#e8788f'; }
$$('#theme-seg button').forEach(b => b.onclick = () => setTheme(b.dataset.t));
let deferred; window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); deferred = e; $('#install').hidden = false; });
$('#install').onclick = async () => { if (!deferred) return; deferred.prompt(); await deferred.userChoice; deferred = null; $('#install').hidden = true; };
window.addEventListener('appinstalled', () => { $('#install').hidden = true; toast('已安装'); });
$('#offline').onclick = async () => {
  if (!('caches' in window)) return toast('此浏览器不支持离线缓存');
  const urls = S.poses.filter(p => p.type === 'image').map(p => p.thumb), c = await caches.open('ps-img-v1'); let n = 0;
  if (!urls.length) { $('#offline-st').textContent = '还没有导入的照片'; return; }
  for (const u of urls) { try { if (!(await c.match(u))) await c.add(u); } catch {} n++; $('#offline-st').textContent = `${n} / ${urls.length}`; }
  $('#offline-st').textContent = `已保存 ${urls.length} 张缩略图`;
};
function renderAbout() {
  const np = S.poses.filter(p => p.type === 'image').length, nb = S.poses.filter(p => p.type === 'builtin').length, nc = S.poses.filter(p => p.type === 'custom').length;
  const ntag = S.dims.reduce((n, d) => n + d.tags.length, 0);
  $('#about').innerHTML = `照片 ${np} · 自建 ${nc} · 示意图 ${nb} · 连拍 ${S.seqs.length} · ${S.dims.length} 个维度 / ${ntag} 个标签<br>收藏、清单、自建动作只保存在本机浏览器。<br>界面思路参考开源项目 RuiC-PoseAtlas（MIT，仅借鉴交互思路，未使用其代码与图片）。`;
}
function renderAll() { renderColl(); applyFilters(); renderSeqs(); renderChecklist(); renderCustom(); renderAbout(); }

function openFromHash() {
  const m = location.hash.match(/^#pose=(.+)$/); if (!m || !S.byId[decodeURIComponent(m[1])]) return;
  const p = S.byId[decodeURIComponent(m[1])];
  if (stack.length) { stack.splice(0).forEach(hideOv); document.body.style.overflow = ''; }
  if (S.coll !== 'all' && (S.coll === 'photo') !== isPhoto(p)) { S.coll = isPhoto(p) ? 'photo' : 'svg'; renderColl(); applyFilters(); }
  history.replaceState(null, '', location.pathname + location.search);
  openCard(p.id, S.filtered.map(x => x.id));
}
// ---------- boot ----------
(async function boot() {
  setTheme(LS.get('ps_theme', 'auto'));
  await loadAll();
  if (!S.coll || !['photo', 'svg', 'all'].includes(S.coll)) S.coll = null;
  if (!S.coll) S.coll = S.poses.some(isPhoto) ? 'photo' : 'svg';
  if (S.coll === 'photo' && !S.poses.some(isPhoto)) S.coll = 'svg';
  renderAll();
  openFromHash(); window.addEventListener('hashchange', openFromHash);
  document.body.dataset.ready = '1';
  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(e => console.warn('sw', e));
})();
})();
