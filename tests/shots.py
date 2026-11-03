"""Extra screenshots for the photo-first UI. Usage: python tests/shots.py <app_dir> <out_dir> <tag>
(run it against a copy that has imported photos)."""
import sys, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright
app, out, tag = sys.argv[1:4]
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
H = functools.partial(Q, directory=app)
srv = socketserver.TCPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, has_touch=True, is_mobile=True)
    page = ctx.new_page(); page.goto(URL); page.wait_for_selector("body[data-ready='1']"); page.wait_for_timeout(500)
    page.screenshot(path=f"{out}/{tag}-a-photo-home.png")
    page.locator("#filterbtn").click(); page.wait_for_timeout(300)
    page.locator('#fbody .chip[data-d="light"]:not(.off)').first.click(); page.wait_for_timeout(200); page.locator('#fbody .chip[data-d="posture"]:not(.off)').first.click(); page.wait_for_timeout(300)
    page.screenshot(path=f"{out}/{tag}-b-photo-filter.png")
    page.locator("#f-done").click(); page.wait_for_timeout(300); page.screenshot(path=f"{out}/{tag}-c-photo-filtered.png")
    page.locator("#a-clear").click(); page.locator(".pc").first.click(); page.wait_for_selector("#card:not([hidden])"); page.wait_for_timeout(800)
    page.screenshot(path=f"{out}/{tag}-d-photo-card.png")
    page.locator("#card").evaluate("e => e.scrollTo(0, 99999)"); page.wait_for_timeout(200)
    page.screenshot(path=f"{out}/{tag}-e-photo-card-tips.png")
    b.close()
