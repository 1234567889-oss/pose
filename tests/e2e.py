#!/usr/bin/env python3
"""Headless-Chromium end-to-end test at 390x844. Usage: python tests/e2e.py <app_dir> <tag> [screenshot_dir]
Serves <app_dir> on a local port, runs every feature, prints PASS/FAIL lines and exits non-zero on failure."""
import sys, os, json, threading, http.server, socketserver, functools, itertools, time
from playwright.sync_api import sync_playwright

app, tag = sys.argv[1], sys.argv[2]
shots = sys.argv[3] if len(sys.argv) > 3 else None
if shots: os.makedirs(shots, exist_ok=True)

class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache"); super().end_headers()
class T(socketserver.ThreadingTCPServer): allow_reuse_address = True; daemon_threads = True
srv = T(("127.0.0.1", 0), functools.partial(H, directory=app)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{port}/"

data = lambda n: json.load(open(os.path.join(app, "data", n), encoding="utf-8"))
poses_b, poses_i, tax = data("poses.json"), data("imported.json"), data("taxonomy.json")
res = []
OFF = [False]  # failures while the emulated network is off are expected (uncached full images)

def check(name, ok, detail=""):
    res.append(ok); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)

def tags_of(p):
    t = p["tags"]; return {k: set(v) for k, v in t.items()}
def expected(pool, f, q=""):
    out = []
    for p in pool:
        t = tags_of(p)
        if all(any(v in t.get(d, ()) for v in vs) for d, vs in f.items() if vs): out.append(p)
    return out

with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, has_touch=True, is_mobile=True, locale="zh-CN", accept_downloads=True)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type == "error" and not OFF[0] else None)
    page.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))
    page.on("response", lambda r: errors.append("404: "+r.url) if r.status==404 else None)
    page.on("requestfailed", lambda r: errors.append(f"requestfailed@{len(res)}: " + r.url) if ("favicon" not in r.url and not OFF[0]) else None)
    page.on("dialog", lambda d: d.accept("测试连拍") if d.type == "prompt" else d.accept())
    page.goto(URL); page.wait_for_selector("body[data-ready='1']")
    photos = len(poses_i)
    # --- boot / collections
    check("app boots, taxonomy loaded", page.locator("#coll button").count() == 3)
    ndim = len(tax["dimensions"]); ntag = sum(len(d["tags"]) for d in tax["dimensions"])
    check(f"taxonomy: {ndim} dimensions / {ntag} tags", ndim >= 8 and ntag >= 100)
    if photos:
        check("default collection = 照片 when photos exist", page.locator("#coll button.on").get_attribute("data-c") == "photo")
        page.wait_for_selector(".pc")
        check("nophotos banner hidden", page.locator("#nophotos").is_hidden())
        check("photo cards use thumbnails", page.locator(".pc img").first.get_attribute("src").startswith("imported/thumbs/"))
    else:
        check("empty-state banner shown when no photos + falls back to 示意图", page.locator("#nophotos").is_visible() and page.locator("#coll button.on").get_attribute("data-c") == "svg")
    if shots: page.screenshot(path=f"{shots}/{tag}-1-home.png")
    # --- batch render + lazy load
    page.locator("#coll button[data-c=svg]").click(); page.wait_for_timeout(200)
    n0 = page.locator(".pc").count()
    page.mouse.wheel(0, 20000); page.wait_for_timeout(600); page.mouse.wheel(0, 20000); page.wait_for_timeout(600)
    n1 = page.locator(".pc").count()
    check("示意图 grid renders in chunks and loads more on scroll", n0 == 30 and n1 > n0, f"{n0}->{n1} of {len(poses_b)}")
    page.evaluate("window.scrollTo(0,0)")
    # --- search
    page.fill("#search", "咖啡"); page.wait_for_timeout(400)
    exp = [p for p in poses_b if "咖啡" in json.dumps(p, ensure_ascii=False)]
    got = page.locator("#count").inner_text()
    check("search filters results", f"{len(exp)} /" in got or True and str(len(exp)) in got, got)
    page.fill("#search", ""); page.wait_for_timeout(300)
    # --- multi-select filters (OR within dim, AND across)
    pool = poses_b
    page.locator("#filterbtn").click(); page.wait_for_selector("#fsheet:not([hidden])")
    dims_shown = page.locator("#fbody .dim").count()
    check("filter sheet shows multiple dimensions", dims_shown >= 5, f"{dims_shown} dims")
    for d, t in [("scene", "街道"), ("scene", "海边"), ("posture", "站")]:
        page.locator(f'#fbody .chip[data-d="{d}"][data-t="{t}"]').click()
    exp = expected(pool, {"scene": ["街道", "海边"], "posture": ["站"]})
    btn = page.locator("#f-done").inner_text()
    check("multi-select: scene(街道 OR 海边) AND posture(站) count correct", btn == f"查看 {len(exp)} 个", f"{btn} expected {len(exp)}")
    cnt = page.locator('#fbody .chip[data-d="scene"][data-t="咖啡馆"] small').inner_text()
    exp2 = len([p for p in expected(pool, {"posture": ["站"]}) if "咖啡馆" in p["tags"].get("scene", [])])
    check("facet counts recomputed against other dimensions", cnt == str(exp2), f"{cnt} vs {exp2}")
    if shots: page.screenshot(path=f"{shots}/{tag}-2-filter-sheet.png")
    page.locator("#f-done").click(); page.wait_for_timeout(300)
    check("sheet closed, active chips shown", page.locator("#fsheet").is_hidden() and page.locator("#active .chip").count() == 3)
    check("grid reflects filter", f"{len(exp)} /" in page.locator("#count").inner_text(), page.locator("#count").inner_text())
    page.locator("#active .chip").first.click(); page.wait_for_timeout(200)
    check("removing an active chip updates filter", page.locator("#active .chip").count() == 2)
    page.locator("#a-clear").click(); page.wait_for_timeout(200)
    check("clear all", page.locator("#active").is_hidden())
    # --- card
    page.locator(".pc").first.click(); page.wait_for_selector("#card:not([hidden])")
    t0 = page.locator("#c-title").inner_text()
    check("card opens with title, 口令, tips, shot advice", bool(t0) and page.locator("#c-kouText").inner_text() != "" and page.locator("#c-details").is_visible() and page.locator("#c-shot").is_visible())
    page.locator("#c-next").click(); t1 = page.locator("#c-title").inner_text()
    check("card next", t1 != t0)
    page.locator("#c-prev").click(); check("card prev", page.locator("#c-title").inner_text() == t0)
    def swipe(dx):
        cdp = ctx.new_cdp_session(page); y = 300; x0 = 300 if dx < 0 else 90
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": x0, "y": y}]})
        for i in range(1, 7): cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x0 + dx * i / 6, "y": y + 2}]}); time.sleep(0.02)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); page.wait_for_timeout(250)
    swipe(-190); check("swipe left -> next", page.locator("#c-title").inner_text() == t1, page.locator("#c-title").inner_text())
    swipe(190); check("swipe right -> previous", page.locator("#c-title").inner_text() == t0)
    page.keyboard.press("ArrowRight"); check("keyboard → next", page.locator("#c-title").inner_text() == t1); page.keyboard.press("ArrowLeft")
    page.locator("#c-kou").click(); check("口令 enlarges on tap", "xl" in page.locator("#c-kou").get_attribute("class"))
    page.locator("#btn-fav").click(); check("favorite from card", "已收藏" in page.locator("#btn-fav").inner_text())
    page.locator("#btn-list").click(); check("add to checklist from card", page.locator("#btn-done").is_visible() and page.locator("#listbadge").inner_text() == "1")
    page.locator("#btn-done").click(); check("mark shot (已拍)", "取消" in page.locator("#btn-done").inner_text())
    if shots: page.screenshot(path=f"{shots}/{tag}-3-card.png")
    # tag click -> filter
    first_tag = page.locator("#c-tags button[data-d]").first; d_, t_ = first_tag.get_attribute("data-d"), first_tag.get_attribute("data-t")
    first_tag.click(); page.wait_for_timeout(300)
    check("tapping a tag in the card applies that filter", page.locator("#card").is_hidden() and page.locator("#active .chip").count() == 1, f"{d_}:{t_}")
    page.locator("#a-clear").click()
    # back button closes overlay
    page.locator(".pc").first.click(); page.wait_for_selector("#card:not([hidden])"); page.go_back(); page.wait_for_timeout(200)
    check("browser back closes the card (history overlays)", page.locator("#card").is_hidden())
    # favourites filter
    page.locator("#favf").click(); page.wait_for_timeout(200)
    check("favorites-only filter", page.locator(".pc").count() == 1)
    page.locator("#favf").click(); page.wait_for_timeout(200)
    # random respects filters
    page.locator("#filterbtn").click(); page.locator('#fbody .chip[data-d="posture"][data-t="躺"]').click(); page.locator("#f-done").click(); page.wait_for_timeout(300)
    lie = {p["title"] for p in poses_b if "躺" in p["tags"].get("posture", [])}
    ok = True
    for _ in range(6):
        page.locator("#rand").click(); page.wait_for_selector("#card:not([hidden])")
        ok &= page.locator("#c-title").inner_text() in lie; page.go_back(); page.wait_for_timeout(120)
    check("random button respects active filters (6/6 within 躺)", ok)
    page.locator("#a-clear").click()
    # deep link
    pid = (poses_i or poses_b)[0]["id"]
    page.goto(URL + "#pose=" + pid); page.wait_for_selector("body[data-ready='1']"); page.wait_for_selector("#card:not([hidden])", timeout=3000)
    check("deep link #pose=<id> opens the card", (poses_i or poses_b)[0]["title"] == page.locator("#c-title").inner_text())
    page.go_back() if False else page.keyboard.press("Escape"); page.wait_for_timeout(200)
    # --- checklist tab
    page.locator("#tabs button[data-v=list]").click(); page.wait_for_timeout(200)
    check("checklist shows saved item (persisted across reload) with progress", page.locator("#checklist .li").count() == 1 and "1" in page.locator("#progress").inner_text())
    page.locator("#l-rand").click(); page.wait_for_timeout(200)
    check("random add 5", page.locator("#checklist .li").count() == 6)
    page.locator("#checklist .li input").nth(1).check(); page.wait_for_timeout(100)
    check("check off item updates progress", "2" in page.locator("#progress b").inner_text())
    page.locator("#l-reset").click(); check("reset ticks", page.locator("#checklist .li.done").count() == 0)
    if shots:
        page.locator("#checklist .li input").nth(0).check(); page.locator("#checklist .li input").nth(2).check(); page.wait_for_timeout(150)
        page.screenshot(path=f"{shots}/{tag}-5-checklist.png"); page.locator("#l-reset").click()
    page.locator("#l-start").click(); page.wait_for_selector("#step:not([hidden])")
    check("step mode from checklist", "1 / 6" in page.locator("#st-count").inner_text())
    page.locator("#st-done").click(); check("step: ✓已拍 marks & advances", "2 / 6" in page.locator("#st-count").inner_text())
    page.go_back(); page.wait_for_timeout(150)
    page.locator("#l-saveseq").click(); page.wait_for_timeout(200)
    page.locator("#tabs button[data-v=seq]").click(); page.wait_for_timeout(200)
    check("checklist saved as own 连拍", page.locator("#seqlist .sc .mine").count() == 1)
    # --- sequences
    seqs = data("sequences.json")
    check(f"{len(seqs)} built-in sequences listed", page.locator("#seqlist .sc").count() == len(seqs) + 1)
    page.locator("#seqlist .sc").first.click(); page.wait_for_selector("#seqd:not([hidden])")
    n = page.locator("#sd-steps .li").count(); check("sequence detail lists 5-8 steps", 5 <= n <= 8, str(n))
    page.locator("#seq-start").click(); page.wait_for_selector("#step:not([hidden])")
    check("step-through opens at 1", f"1 / {n}" in page.locator("#st-count").inner_text() and page.locator("#st-dots i").count() == n)
    if shots: page.screenshot(path=f"{shots}/{tag}-4-sequence-step.png")
    page.locator("#st-next").click(); page.locator("#st-next").click()
    check("step next", f"3 / {n}" in page.locator("#st-count").inner_text())
    swipe(190); check("step swipe back", f"2 / {n}" in page.locator("#st-count").inner_text(), page.locator("#st-count").inner_text())
    page.locator("#st-auto").click(); check("auto-advance toggles", "7秒" in page.locator("#st-auto").inner_text()); page.locator("#st-auto").click()
    for _ in range(n):
        if page.locator("#step").is_visible(): page.locator("#st-next").click()
    page.wait_for_timeout(300)
    check("finishing the last step closes step mode", page.locator("#step").is_hidden())
    page.go_back() if not page.locator("#seqd").is_hidden() else None
    # --- custom pose (IndexedDB)
    from PIL import Image
    Image.new("RGB", (1600, 2000), (200, 120, 140)).save("/tmp/up_test.jpg")
    page.locator("#tabs button[data-v=mine]").click(); page.locator("#c-new").click(); page.wait_for_selector("#cform:not([hidden])")
    page.set_input_files("#f-file", "/tmp/up_test.jpg"); page.fill("#f-name", "我的窗边回眸"); page.fill("#f-kou", "慢慢回头看我"); page.fill("#f-tags", "海风,氛围")
    page.locator('#f-picker .chip[data-d="light"][data-t="逆光"]').click(); page.locator('#f-picker .chip[data-d="scene"][data-t="室内窗边"]').click()
    page.locator("#f-save").click(); page.wait_for_selector("#cform", state="hidden"); page.wait_for_timeout(300)
    check("custom pose saved & listed", page.locator("#customlist .li").count() == 1)
    page.reload(); page.wait_for_selector("body[data-ready='1']"); page.locator("#tabs button[data-v=mine]").click(); page.wait_for_timeout(200)
    check("custom pose persisted in IndexedDB across reload", page.locator("#customlist .li").count() == 1)
    stored = page.evaluate("""() => new Promise(r => { const q = indexedDB.open('pose-app'); q.onsuccess = () => { const g = q.result.transaction('custom').objectStore('custom').getAll(); g.onsuccess = () => r(g.result.map(x => [x.blob.type, x.blob.size, x.w, x.h, x.thumb.size])); }; })""")
    check("IndexedDB holds the photo blob downscaled to 1200px + thumb", stored and stored[0][0] == "image/jpeg" and max(stored[0][2:4]) == 1200, str(stored))
    page.locator("#tabs button[data-v=lib]").click(); page.locator("#coll button[data-c=photo]").click(); page.wait_for_timeout(300)
    page.locator("#filterbtn").click(); page.locator('#fbody .chip[data-d="light"][data-t="逆光"]').click(); page.locator("#f-done").click(); page.wait_for_timeout(300)
    check("custom pose is filterable by its tags (光线:逆光)", page.locator(".pc", has_text="我的窗边回眸").count() == 1)
    page.locator("#a-clear").click()
    page.locator("#search").fill("海风"); page.wait_for_timeout(400)
    check("custom pose searchable by free tag", page.locator(".pc", has_text="我的窗边回眸").count() == 1)
    page.fill("#search", "")
    page.locator("#tabs button[data-v=mine]").click(); page.locator("#customlist .del").click(); page.wait_for_timeout(300)
    check("custom pose delete", page.locator("#customlist .li").count() == 0)
    # --- dark mode
    bg0 = page.evaluate("getComputedStyle(document.body).backgroundColor")
    page.locator('#theme-seg button[data-t=dark]').click(); bg1 = page.evaluate("getComputedStyle(document.body).backgroundColor")
    check("dark mode changes theme and persists", bg0 != bg1 and page.evaluate("localStorage.getItem('ps_theme')") == '"dark"', f"{bg0} -> {bg1}")
    if shots: page.locator("#tabs button[data-v=lib]").click(); page.wait_for_timeout(300); page.screenshot(path=f"{shots}/{tag}-6-dark.png")
    page.locator('#tabs button[data-v=mine]').click(); page.locator('#theme-seg button[data-t=light]').click()
    # --- PWA
    sw = page.evaluate("navigator.serviceWorker.ready.then(r => !!r.active)")
    check("service worker registered and active", sw is True)
    page.reload(); page.wait_for_selector("body[data-ready='1']")
    check("page controlled by service worker after reload", page.evaluate("!!navigator.serviceWorker.controller"))
    man = page.evaluate("fetch(document.querySelector('link[rel=manifest]').href).then(r => r.json())")
    check("manifest has 192/512/maskable PNG icons", {i["sizes"] for i in man["icons"] if i["type"] == "image/png"} == {"192x192", "512x512"} and any(i["purpose"] == "maskable" for i in man["icons"]))
    cdp = ctx.new_cdp_session(page); cdp.send("Page.enable")
    ie = cdp.send("Page.getInstallabilityErrors")["installabilityErrors"]
    check("installable (CDP Page.getInstallabilityErrors empty)", ie == [], str(ie))
    # offline
    page.locator("#coll button[data-c=all]").click(); page.wait_for_timeout(300); page.mouse.wheel(0, 500); page.wait_for_timeout(500); page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(300)
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    OFF[0] = True; ctx.set_offline(True)
    page.goto(URL); page.wait_for_selector("body[data-ready='1']", timeout=8000)
    cards = page.locator(".pc").count()
    check("OFFLINE reload works and renders the library", cards > 0, f"{cards} cards")
    bad = page.evaluate("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).length")
    check("OFFLINE images render from cache", bad == 0, f"{bad} broken: " + str(page.evaluate("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i=>i.src)")))
    page.locator(".pc").first.click(); page.wait_for_selector("#card:not([hidden])")
    check("OFFLINE card detail works", page.locator("#c-title").inner_text() != "", "onLine=" + str(page.evaluate("navigator.onLine")))
    page.keyboard.press("Escape"); page.locator("#tabs button[data-v=seq]").click(); page.locator("#seqlist .sc").first.click(); page.locator("#seq-start").click()
    check("OFFLINE sequence step mode works", page.locator("#step").is_visible())
    ctx.set_offline(False); page.wait_for_timeout(500); OFF[0] = False
    # offline download button
    if photos:
        page.reload(); page.wait_for_selector("body[data-ready='1']"); page.locator("#tabs button[data-v=mine]").click(); page.locator("#offline").click(); page.wait_for_timeout(1500)
        check("offline thumbnail download", "已保存" in page.locator("#offline-st").inner_text(), page.locator("#offline-st").inner_text())
    errs = [e for e in errors]
    check("zero console errors / page errors / failed requests", not errs, "; ".join(errs[:5]))
    b.close()
print(f"\n{sum(res)}/{len(res)} checks passed")
sys.exit(0 if all(res) else 1)
