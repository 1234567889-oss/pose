#!/usr/bin/env python3
"""Headless-Chromium end-to-end test at 390x844. Needs: pip install playwright pillow && playwright install chromium.  Usage: python tests/e2e.py <app_dir> <tag> [screenshot_dir]  (photo-only app, v3)
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
poses_i, tax = data("imported.json"), data("taxonomy.json")
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
    requested = []; page.on("request", lambda r: requested.append(r.url))
    page.on("response", lambda r: errors.append("404: "+r.url) if r.status==404 else None)
    page.on("requestfailed", lambda r: errors.append(f"requestfailed@{len(res)}: " + r.url) if ("favicon" not in r.url and not OFF[0] and "ERR_ABORTED" not in str(r.failure)) else None)
    page.on("dialog", lambda d: d.accept("测试连拍") if d.type == "prompt" else d.accept())
    # v2 -> v3 migration: stale favourites / checklist / own sequences / collection switch pointing at the removed diagram ids
    page.goto(URL); page.wait_for_selector("body[data-ready='1']")
    page.evaluate("""() => { localStorage.setItem('ps_fav', JSON.stringify(['b001', 'b050'])); localStorage.setItem('ps_list', JSON.stringify([{id: 'b003', done: false}]));
        localStorage.setItem('ps_coll', '"svg"'); localStorage.setItem('ps_useq', JSON.stringify([{id: 'u1', title: '旧连拍', poses: ['b001', 'b002'], user: true}])); }""")
    page.reload(); page.wait_for_selector("body[data-ready='1']"); page.wait_for_selector(".pc")
    check("stale v2 localStorage (favs/list/own sequences/ps_coll) is silently dropped, no crash",
          page.evaluate("JSON.parse(localStorage.getItem('ps_fav')).length") == 0 and page.evaluate("JSON.parse(localStorage.getItem('ps_list')).length") == 0
          and page.evaluate("JSON.parse(localStorage.getItem('ps_useq')).length") == 0 and page.evaluate("localStorage.getItem('ps_coll')") is None
          and page.locator("#listbadge").inner_text() == "" and page.locator("#seqlist .sc").count() == 0)
    page.goto(URL + "#pose=b001"); page.wait_for_selector("body[data-ready='1']"); page.wait_for_timeout(300)
    check("deep link to a removed diagram id (#pose=b001) is ignored", page.locator("#card").is_hidden() and page.locator(".pc").count() > 0)
    page.goto(URL); page.wait_for_selector("body[data-ready='1']"); page.wait_for_selector(".pc")
    photos = len(poses_i)
    # --- boot / photo-only UI
    check("no 示意图/照片 source switch, no 示意 badge, no builtin images", page.locator("#coll").count() == 0 and page.locator(".badge").count() == 0
          and page.locator('img[src*="builtin"], img[src$=".svg"]').count() == 0)
    check("no built-in diagram data/assets are requested", not [u for u in requested if "poses.json" in u or "assets/builtin" in u or "sequences.json" in u], str([u for u in requested if "poses.json" in u or "builtin" in u][:3]))
    ndim = len(tax["dimensions"]); ntag = sum(len(d["tags"]) for d in tax["dimensions"])
    check(f"taxonomy: {ndim} dimensions / {ntag} tags", ndim >= 8 and ntag >= 50)
    used = {(d, v) for p in poses_i for d, a in p["tags"].items() for v in a}
    check("every taxonomy tag is used by at least one photo", all((d["key"], t) in used for d in tax["dimensions"] for t in d["tags"]))
    check("all poses are real photos (type image, with thumb)", photos > 0 and all(p["type"] == "image" and p["thumb"] for p in poses_i))
    check("home shows all photos in the count line", page.locator("#count").inner_text() == f"{photos} 个动作", page.locator("#count").inner_text())
    check("nophotos banner hidden", page.locator("#nophotos").is_hidden())
    check("photo cards use thumbnails", page.locator(".pc img").first.get_attribute("src").startswith("imported/thumbs/"))
    if shots: page.screenshot(path=f"{shots}/{tag}-1-home.png")
    # --- batch render + lazy load
    n0 = page.locator(".pc").count()
    page.mouse.wheel(0, 20000); page.wait_for_timeout(600); page.mouse.wheel(0, 20000); page.wait_for_timeout(600)
    n1 = page.locator(".pc").count()
    check("grid renders in chunks and loads more on scroll", n0 == 30 and n1 > n0, f"{n0}->{n1} of {photos}")
    page.evaluate("window.scrollTo(0,0)")
    # --- search
    def hay(p): return " ".join([p.get("title") or "", p.get("kouling") or "", p.get("note") or "", *(p.get("extra") or []), *[v for a in p["tags"].values() for v in a],
                                   *["".join(t) if isinstance(t, list) else t for t in (p.get("tips") or [])]]).lower()
    page.fill("#search", "珠江"); page.wait_for_timeout(400)
    exp = [p for p in poses_i if "珠江" in hay(p)]
    got = page.locator("#count").inner_text()
    check("search filters results (title/口令/标签/要点)", got == f"{len(exp)} / {photos} 个动作" and len(exp) > 0, f"{got} expected {len(exp)}")
    page.fill("#search", "zzzz不存在"); page.wait_for_timeout(400)
    check("search with no match shows the empty state", page.locator("#noresult").is_visible() and page.locator(".pc").count() == 0)
    page.locator("#clearall").click(); page.wait_for_timeout(300)
    check("clear-filter button on the empty state restores the grid", page.locator("#noresult").is_hidden() and page.locator(".pc").count() > 0 and page.locator("#search").input_value() == "")
    # --- multi-select filters (OR within dim, AND across)
    pool = poses_i
    page.locator("#filterbtn").click(); page.wait_for_selector("#fsheet:not([hidden])")
    dims_shown = page.locator("#fbody .dim").count()
    check("filter sheet shows multiple dimensions", dims_shown >= 5, f"{dims_shown} dims")
    for d, t in [("scene", "街道"), ("scene", "公园"), ("posture", "站")]:
        page.locator(f'#fbody .chip[data-d="{d}"][data-t="{t}"]').click()
    exp = expected(pool, {"scene": ["街道", "公园"], "posture": ["站"]})
    btn = page.locator("#f-done").inner_text()
    check("multi-select: scene(街道 OR 公园) AND posture(站) count correct", btn == f"查看 {len(exp)} 个", f"{btn} expected {len(exp)}")
    cnt = page.locator('#fbody .chip[data-d="scene"][data-t="栏杆"] small').inner_text()
    exp2 = len([p for p in expected(pool, {"posture": ["站"]}) if "栏杆" in p["tags"].get("scene", [])])
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
    page.locator(".pc .t").first.click(); page.wait_for_selector("#card:not([hidden])")
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
    page.locator(".pc .t").first.click(); page.wait_for_selector("#card:not([hidden])"); page.go_back(); page.wait_for_timeout(200)
    check("browser back closes the card (history overlays)", page.locator("#card").is_hidden())
    # favourites filter
    page.locator("#favf").click(); page.wait_for_timeout(200)
    check("favorites-only filter", page.locator(".pc").count() == 1)
    page.locator("#favf").click(); page.wait_for_timeout(200)
    check("favourite persisted in localStorage (photo id)", page.evaluate("JSON.parse(localStorage.getItem('ps_fav')).length") == 1)
    # random respects filters
    page.locator("#filterbtn").click(); page.locator('#fbody .chip[data-d="posture"][data-t="坐"]').click(); page.locator("#f-done").click(); page.wait_for_timeout(300)
    lie = {p["title"] for p in poses_i if "坐" in p["tags"].get("posture", [])}
    ok = True
    for _ in range(6):
        page.locator("#rand").click(); page.wait_for_selector("#card:not([hidden])")
        ok &= page.locator("#c-title").inner_text() in lie; page.go_back(); page.wait_for_timeout(120)
    check("random button respects active filters (6/6 within 坐)", ok)
    page.locator("#a-clear").click()
    # deep link
    pid = poses_i[0]["id"]
    page.goto(URL + "#pose=" + pid); page.wait_for_selector("body[data-ready='1']"); page.wait_for_selector("#card:not([hidden])", timeout=3000)
    check("deep link #pose=<id> opens the card", poses_i[0]["title"] == page.locator("#c-title").inner_text())
    page.go_back() if False else page.keyboard.press("Escape"); page.wait_for_timeout(200)

    # ================= v3.9: fullscreen album viewer + favorites =================
    ui_ids = [p["id"] for p in reversed(poses_i)]          # grid order = newest import first
    by_id = {p["id"]: p for p in poses_i}
    cdp = ctx.new_cdp_session(page)
    def _tp(fr): return [{"x": x, "y": y, "id": k} for k, (x, y) in enumerate(fr)]
    def cdp_touch(frames, wait=550, end=True, start=True, gap=0.02):
        """frames: list of touch-point lists. First frame = touchStart (if start), rest = touchMove, then touchEnd (if end)."""
        for k, fr in enumerate(frames):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchStart" if (k == 0 and start) else "touchMove", "touchPoints": _tp(fr)}); time.sleep(gap)
        if end: cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        page.wait_for_timeout(wait)
    def vswipe(dx, dy=0, x0=195, y0=420, steps=8, wait=550):
        cdp_touch([[(x0 + dx * i / steps, y0 + dy * i / steps)] for i in range(0, steps + 1)], wait)
    vid = lambda: page.evaluate("document.querySelector('#viewer').dataset.id")
    vopen = lambda: page.evaluate("!document.querySelector('#viewer').hidden")
    page.locator("#tabs button[data-v=lib]").click(); page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(200)
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(500)
    box = page.locator("#viewer").bounding_box()
    check("viewer: tapping a grid photo opens a fullscreen (390x844) black viewer", box["x"] == 0 and box["y"] == 0 and box["width"] == 390 and box["height"] == 844
          and page.evaluate("getComputedStyle(document.querySelector('#viewer')).backgroundColor") == "rgb(0, 0, 0)" and page.locator("#card").is_hidden(), str(box))
    check("viewer: shows only the image, no caption/text by default", page.locator("#viewer").inner_text().strip() == "" and page.locator("#vw-bar").is_hidden() and page.locator("#viewer .vimg:visible").count() >= 1,
          repr(page.locator("#viewer").inner_text()))
    check("viewer: starts at the tapped photo (1/682) and swaps thumb -> full image", vid() == ui_ids[0] and page.evaluate("document.querySelector('#viewer').dataset.index") == "0"
          and page.wait_for_function("document.querySelectorAll('#viewer .vpane')[1].querySelector('img').getAttribute('src').indexOf('thumbs')<0", timeout=8000) is not None)
    page.keyboard.press("ArrowRight"); page.wait_for_timeout(600)
    check("viewer: arrow key -> next photo in the same (grid) order", vid() == ui_ids[1], vid())
    vswipe(-220)
    check("viewer: touch swipe left -> next photo", vid() == ui_ids[2], vid())
    vswipe(220)
    check("viewer: touch swipe right -> previous photo", vid() == ui_ids[1], vid())
    cdp_touch([[(300, 420)], [(285, 420)], [(270, 421)], [(255, 421)], [(240, 421)]], 150, end=False, gap=0.1)
    mid = page.evaluate("getComputedStyle(document.querySelector('#vw-track')).transform")
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []}); page.wait_for_timeout(500)
    check("viewer: track follows the finger while dragging and snaps back on a short drag", mid not in ("none", "matrix(1, 0, 0, 1, 0, 0)") and "-" in mid and vid() == ui_ids[1]
          and page.evaluate("getComputedStyle(document.querySelector('#vw-track')).transform") in ("none", "matrix(1, 0, 0, 1, 0, 0)"), mid)
    check("viewer: neighbours are preloaded (prev/next panes hold the adjacent photos)", page.evaluate("[...document.querySelectorAll('#viewer .vpane')].map(p => p.querySelector('img').getAttribute('src') || '').filter(Boolean).length") == 3)
    page.touchscreen.tap(195, 420); page.wait_for_timeout(600)
    check("viewer: single tap shows the minimal toolbar (✕, index, ♡, ℹ)", page.locator("#vw-bar").is_visible() and page.locator("#vw-count").inner_text() == f"2/{photos}"
          and page.locator("#vw-close").is_visible() and page.locator("#vw-fav").is_visible() and page.locator("#vw-info").is_visible(), page.locator("#vw-count").inner_text())
    if shots: page.screenshot(path=f"{shots}/{tag}-viewer-toolbar.png")
    page.touchscreen.tap(195, 420); page.wait_for_timeout(600)
    check("viewer: tapping again hides the toolbar", page.locator("#vw-bar").is_hidden())
    page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    check("viewer: toolbar auto-hides after a few seconds", page.locator("#vw-bar").is_visible() and page.wait_for_function("getComputedStyle(document.querySelector('#vw-bar')).visibility==='hidden'", timeout=6000) is not None)
    if shots: page.screenshot(path=f"{shots}/{tag}-viewer-fullscreen.png")
    # zoom (double tap) disables swipe, double tap again resets
    page.touchscreen.tap(195, 420); page.wait_for_timeout(120); page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    z = float(page.evaluate("document.querySelector('#viewer').dataset.zoom"))
    vswipe(-200); same = vid() == ui_ids[1]
    check("viewer: double-tap zooms in; swiping while zoomed pans instead of changing photo", z > 2 and same, f"zoom={z}")
    page.touchscreen.tap(195, 420); page.wait_for_timeout(120); page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    check("viewer: double-tap again resets zoom", float(page.evaluate("document.querySelector('#viewer').dataset.zoom")) == 1.0)
    cdp_touch([[(150 - 8 * i, 420), (240 + 8 * i, 420)] for i in range(0, 8)], 500)
    check("viewer: pinch gesture zooms in", float(page.evaluate("document.querySelector('#viewer').dataset.zoom")) > 1.5, page.evaluate("document.querySelector('#viewer').dataset.zoom"))
    page.touchscreen.tap(195, 420); page.wait_for_timeout(120); page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    # favourite toggle in the viewer
    favs0 = page.evaluate("JSON.parse(localStorage.getItem('ps_fav')).length")
    page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    page.locator("#vw-fav").click(); page.wait_for_timeout(200)
    check("viewer: ♡ toggles favourite (persisted, icon turns ♥)", page.evaluate("JSON.parse(localStorage.getItem('ps_fav')).length") == favs0 + 1 and page.locator("#vw-fav").inner_text() == "♥", page.locator("#vw-fav").inner_text())
    # ℹ -> detail card of the shown photo
    page.locator("#vw-info").click(); page.wait_for_selector("#card:not([hidden])"); page.wait_for_timeout(300)
    check("viewer: ℹ opens the detail card of the current photo", not vopen() and page.locator("#c-title").inner_text() == by_id[ui_ids[1]]["title"], page.locator("#c-title").inner_text())
    # detail page -> 全屏 button -> viewer; back returns to the card
    page.locator("#c-full").click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    check("detail: 全屏 button opens the viewer on the same photo", vid() == ui_ids[1] and page.locator("#viewer").inner_text().strip() == "")
    page.keyboard.press("ArrowRight"); page.wait_for_timeout(600); page.go_back(); page.wait_for_timeout(300)
    check("viewer: browser back button (Android) closes only the viewer; card follows the photo", not vopen() and page.locator("#card").is_visible() and page.locator("#c-title").inner_text() == by_id[ui_ids[2]]["title"])
    page.go_back(); page.wait_for_timeout(300)
    check("viewer/card: second back closes the card too", page.locator("#card").is_hidden() and not vopen())
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    check("viewer: Esc closes", not vopen())
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    vswipe(0, 300); page.wait_for_timeout(200)
    check("viewer: swipe down closes", not vopen())
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    page.touchscreen.tap(195, 420); page.wait_for_timeout(500); page.locator("#vw-close").click(); page.wait_for_timeout(300)
    check("viewer: ✕ closes", not vopen())
    # viewer walks the CURRENT (searched / filtered) list, not the whole library
    page.fill("#search", "珠江"); page.wait_for_timeout(400)
    ids_s = [p["id"] for p in reversed(poses_i) if "珠江" in hay(p)]
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    seen = [vid()]
    for _ in range(len(ids_s)): page.keyboard.press("ArrowRight"); page.wait_for_timeout(420); seen.append(vid())
    check("viewer from a search result walks only that result list, in order, and stops at the end", seen == ids_s + [ids_s[-1]] and page.evaluate("document.querySelector('#viewer').dataset.index") == str(len(ids_s) - 1), f"{len(ids_s)} results")
    page.keyboard.press("Escape"); page.wait_for_timeout(300); page.fill("#search", ""); page.wait_for_timeout(300)
    # ---- favourites view
    favs_now = page.evaluate("JSON.parse(localStorage.getItem('ps_fav'))")
    for pid_ in ui_ids[5:8]:     # make sure there are several
        if pid_ not in favs_now: page.evaluate("id => document.querySelector(`[data-fav=\"${id}\"]`)?.click()", pid_)
    page.locator("#grid").evaluate("g => g.scrollIntoView()"); page.wait_for_timeout(100)
    favs_now = page.evaluate("JSON.parse(localStorage.getItem('ps_fav'))")
    page.locator("#tabs button[data-v=fav]").click(); page.wait_for_timeout(400)
    shown = page.evaluate("[...document.querySelectorAll('#favgrid .fi')].map(e => e.dataset.id)")
    check("favorites tab: lists exactly the favorited photos (newest first) with a count", sorted(shown) == sorted(favs_now) and shown == list(reversed(favs_now)) and len(shown) >= 3
          and page.locator("#fav-n").inner_text() == f"{len(shown)} 张" and page.locator("#favbadge").inner_text() == str(len(shown)) and page.locator("#fav-empty").is_hidden(), f"{len(shown)} favs; {page.locator('#fav-n').inner_text()}")
    page.wait_for_timeout(2600)
    if shots: page.screenshot(path=f"{shots}/{tag}-favorites.png")
    page.locator("#favgrid .fi img").nth(1).click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(400)
    seen = [vid()]
    for _ in range(len(shown) + 2): page.keyboard.press("ArrowRight"); page.wait_for_timeout(420); seen.append(vid())
    check("viewer from favorites starts at the tapped photo and only ever shows favorites (stops at the last)", seen[0] == shown[1] and set(seen) <= set(favs_now) and seen[-1] == shown[-1] and seen[1:len(shown) - 1] == shown[2:], str(seen[:3]))
    for _ in range(len(shown) + 2): page.keyboard.press("ArrowLeft"); page.wait_for_timeout(420)
    check("viewer from favorites: going back stops at the first favorite", vid() == shown[0] and page.evaluate("document.querySelector('#viewer').dataset.index") == "0")
    vswipe(-220); check("viewer from favorites: touch swipe stays within favorites", vid() == shown[1])
    page.touchscreen.tap(195, 420); page.wait_for_timeout(500)
    check("viewer from favorites: index counts favorites only", page.locator("#vw-count").inner_text() == f"2/{len(shown)}", page.locator("#vw-count").inner_text())
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    check("closing the viewer returns to the favorites tab", page.locator("#v-fav").is_visible() and not vopen())
    page.locator("#fav-play").click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    check("favorites ▶ 全屏浏览 starts at the first favorite", vid() == shown[0]); page.keyboard.press("Escape"); page.wait_for_timeout(300)
    with page.expect_download() as dl: page.locator("#fav-export").click()
    dlp = dl.value.path(); exp_json = json.load(open(dlp, encoding="utf-8"))
    check("导出收藏 downloads a JSON file with the favorite ids", dl.value.suggested_filename.startswith("pose-favorites-") and dl.value.suggested_filename.endswith(".json")
          and sorted(exp_json["favorites"]) == sorted(favs_now) and exp_json["count"] == len(favs_now), dl.value.suggested_filename)
    # unfavourite from the grid
    page.locator("#favgrid .fi .un").first.click(); page.wait_for_timeout(300)
    left = page.evaluate("JSON.parse(localStorage.getItem('ps_fav'))")
    check("favorites tab: ♥ removes a photo (grid, count and storage update)", len(left) == len(favs_now) - 1 and page.locator("#favgrid .fi").count() == len(left) and page.locator("#fav-n").inner_text() == f"{len(left)} 张")
    # unfavouriting inside the viewer keeps the photo in the swipe list until closing
    page.locator("#favgrid .fi img").first.click(); page.wait_for_selector("#viewer:not([hidden])"); page.wait_for_timeout(300)
    page.touchscreen.tap(195, 420); page.wait_for_timeout(500); page.locator("#vw-fav").click(); page.wait_for_timeout(200)
    check("viewer in favorites: ♥ un-favorites but the photo stays swipeable (like an album)", page.locator("#vw-fav").inner_text() == "♡" and page.locator("#vw-count").inner_text().endswith(f"/{len(left)}"))
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    check("closing the viewer refreshes the favorites grid", page.locator("#favgrid .fi").count() == len(left) - 1)
    while page.locator("#favgrid .fi .un").count(): page.locator("#favgrid .fi .un").first.click(); page.wait_for_timeout(120)
    check("favorites tab: empty state when nothing is favorited", page.locator("#fav-empty").is_visible() and page.locator("#favgrid .fi").count() == 0 and page.locator("#fav-n").inner_text() == "" and page.locator("#favbadge").inner_text() == "")
    if shots: page.screenshot(path=f"{shots}/{tag}-favorites-empty.png")
    page.locator("#fav-go").click(); page.wait_for_timeout(200)
    check("favorites empty state links back to the library", page.locator("#v-lib").is_visible())
    # bottom bar labels are not truncated (390 and a narrower 360px phone)
    page.locator(".pc .t").first.click(); page.wait_for_selector("#card:not([hidden])")
    st0 = (page.locator("#btn-done").is_visible(), page.locator("#btn-done").inner_text())   # remember the card's list/done state, restored below
    if page.locator("#btn-done").is_hidden(): page.locator("#btn-list").click()
    if "取消" not in page.locator("#btn-done").inner_text(): page.locator("#btn-done").click()
    def trunc(): return page.evaluate("[...document.querySelectorAll('#card .bar button:not([hidden])')].filter(b => b.scrollWidth > b.clientWidth + 0.5 || b.getBoundingClientRect().right > innerWidth || b.getBoundingClientRect().left < 0).map(b => b.id)")
    t390 = trunc(); page.set_viewport_size({"width": 360, "height": 740}); page.wait_for_timeout(200); t360 = trunc(); page.set_viewport_size({"width": 390, "height": 844}); page.wait_for_timeout(200)
    check("card bottom bar: 取消已拍 and all labels fully visible at 390px and 360px", "取消已拍" in page.locator("#btn-done").inner_text() and not t390 and not t360, f"390:{t390} 360:{t360}")
    if not st0[0] or "取消" not in st0[1]: page.locator("#btn-done").click()      # back to not-done
    if not st0[0]: page.locator("#btn-list").click()                               # back to not-in-list
    page.keyboard.press("Escape"); page.wait_for_timeout(200)
    page.evaluate("window.scrollTo(0,0)")
    page.wait_for_timeout(2600)   # let toasts fade
    if shots: page.screenshot(path=f"{shots}/{tag}-home.png")
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
    # --- sequences (no built-in ones any more; own sequences only)
    check("only the user's own 连拍 is listed (no built-in sequences)", page.locator("#seqlist .sc").count() == 1)
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
    page.locator('#f-picker .chip[data-d="light"][data-t="逆光"]').click(); page.locator('#f-picker .chip[data-d="scene"][data-t="公园"]').click()
    page.locator("#f-save").click(); page.wait_for_selector("#cform", state="hidden"); page.wait_for_timeout(300)
    check("custom pose saved & listed", page.locator("#customlist .li").count() == 1)
    page.reload(); page.wait_for_selector("body[data-ready='1']"); page.locator("#tabs button[data-v=mine]").click(); page.wait_for_timeout(200)
    check("custom pose persisted in IndexedDB across reload", page.locator("#customlist .li").count() == 1)
    stored = page.evaluate("""() => new Promise(r => { const q = indexedDB.open('pose-app'); q.onsuccess = () => { const g = q.result.transaction('custom').objectStore('custom').getAll(); g.onsuccess = () => r(g.result.map(x => [x.blob.type, x.blob.size, x.w, x.h, x.thumb.size])); }; })""")
    check("IndexedDB holds the photo blob downscaled to 1200px + thumb", stored and stored[0][0] == "image/jpeg" and max(stored[0][2:4]) == 1200, str(stored))
    page.locator("#tabs button[data-v=lib]").click(); page.wait_for_timeout(300)
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
    page.locator("#tabs button[data-v=lib]").click(); page.wait_for_timeout(300); page.mouse.wheel(0, 500); page.wait_for_timeout(500); page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(300)
    page.wait_for_load_state("networkidle"); page.wait_for_timeout(800)
    OFF[0] = True; ctx.set_offline(True)
    page.goto(URL); page.wait_for_selector("body[data-ready='1']", timeout=8000)
    cards = page.locator(".pc").count()
    check("OFFLINE reload works and renders the library", cards > 0, f"{cards} cards")
    bad = page.evaluate("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).length")
    check("OFFLINE images render from cache", bad == 0, f"{bad} broken: " + str(page.evaluate("[...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0).map(i=>i.src)")))
    page.locator(".pc .t").first.click(); page.wait_for_selector("#card:not([hidden])")
    check("OFFLINE card detail works", page.locator("#c-title").inner_text() != "", "onLine=" + str(page.evaluate("navigator.onLine")))
    page.keyboard.press("Escape"); page.locator("#tabs button[data-v=seq]").click(); page.locator("#seqlist .sc").first.click(); page.locator("#seq-start").click()
    check("OFFLINE sequence step mode works", page.locator("#step").is_visible())
    ctx.set_offline(False); page.wait_for_timeout(500); OFF[0] = False
    # offline download button
    page.reload(); page.wait_for_selector("body[data-ready='1']"); page.locator("#tabs button[data-v=mine]").click(); page.locator("#offline").click(); page.wait_for_function("document.querySelector('#offline-st').innerText.includes('已保存')", timeout=20000)
    check("offline thumbnail download", "已保存" in page.locator("#offline-st").inner_text(), page.locator("#offline-st").inner_text())
    check("about line shows photos / custom / sequences, no 示意图", "示意图" not in page.locator("#about").inner_text() and f"照片 {photos}" in page.locator("#about").inner_text(), page.locator("#about").inner_text()[:60])
    sw_keys = page.evaluate("caches.keys()")
    check("service worker cache is v4.1.0 and old shell caches are gone", "ps-shell-v4.1.0" in sw_keys and not [k for k in sw_keys if k.startswith("ps-shell-") and k != "ps-shell-v4.1.0"], str(sw_keys))
    # viewer again, online and SW-controlled, so full images flow through the service worker
    page.locator("#tabs button[data-v=lib]").click(); page.evaluate("window.scrollTo(0,0)"); page.wait_for_timeout(300)
    page.locator(".pc .art").first.click(); page.wait_for_selector("#viewer:not([hidden])")
    for _ in range(3): page.wait_for_timeout(700); page.keyboard.press("ArrowRight")
    page.wait_for_timeout(1200); page.keyboard.press("Escape"); page.wait_for_timeout(300)
    cs = page.evaluate("""async () => { const o = {}; for (const k of await caches.keys()) { const c = await caches.open(k); o[k] = (await c.keys()).map(r => new URL(r.url).pathname); } return o; }""")
    th, fu = cs.get("ps-thumbs-v1", []), cs.get("ps-full-v1", [])
    check("thumbnails and full images use separate caches (ps-thumbs-v1 / ps-full-v1), legacy ps-img-v1 gone", "ps-thumbs-v1" in cs and "ps-full-v1" in cs and "ps-img-v1" not in cs, str(list(cs)))
    check("thumbs cache holds only thumbs (all %d after 离线保存), full cache holds only full images" % photos, len(th) >= photos and all("/imported/thumbs/" in u for u in th) and len(fu) >= 1 and all("/imported/" in u and "/thumbs/" not in u for u in fu), f"thumbs={len(th)} full={len(fu)}")
    swsrc = open(os.path.join(app, "sw.js"), encoding="utf-8").read()
    import re as _re
    core = _re.search(r"const CORE = \[(.*?)\]", swsrc, _re.S).group(1)
    caps = {k: int(v) for k, v in _re.findall(r"const (MAX_\w+) = (\d+)", swsrc)}
    check("sw.js: imported.json not precached; thumbs cap > photo count; full cap is an LRU limit; trim is awaited", "imported.json" not in core and caps.get("MAX_THUMBS", 0) >= photos * 2 and 0 < caps.get("MAX_FULL", 0) < photos
          and "trim(c, max)" in swsrc and "e.waitUntil" in swsrc and "VERSION = \"v4.1.0\"" in swsrc, str(caps))
    shell_keys = page.evaluate("caches.open('ps-shell-v4.1.0').then(c => c.keys()).then(ks => ks.map(r => new URL(r.url).pathname))")
    check("data/imported.json is still cached (network-first fallback) for offline use", any(u.endswith("data/imported.json") for u in shell_keys), str(len(shell_keys)))
    errs = [e for e in errors]
    check("zero console errors / page errors / failed requests", not errs, "; ".join(errs[:5]))
    b.close()
print(f"\n{sum(res)}/{len(res)} checks passed")
sys.exit(0 if all(res) else 1)
