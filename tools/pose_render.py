"""Forward-kinematics stick-figure -> SVG. Angles in degrees, 0 = pointing down, 90 = screen right,
180 = up, -90 = screen left. tilt: torso lean (0 upright, +right, -90 = lying with head to the left)."""
import math

CLOTH = {"甜美": "#ec7fa0", "清冷": "#7a93b5", "文艺": "#8aa57a", "活泼": "#f2a03d", "性感": "#a8324f", "日系": "#6fb3d9"}
SKIN, HAIR, LINE = "#f2c4a8", "#3a2a2a", "#a89aa0"
UA, FA, TH, SH, TORSO, R = 44, 40, 62, 60, 78, 19

def vec(a, l):
    r = math.radians(a); return (l * math.sin(r), l * math.cos(r))
def add(p, v): return (p[0] + v[0], p[1] + v[1])
def f(x): return f"{x:.1f}"

def render(d, title, mood="甜美"):
    side = d.get("side", False)
    shw, hpw = (8, 4) if side else (20, 12)
    tilt = d.get("tilt", 0); tr = math.radians(tilt)
    pel = (0.0, 0.0)
    neck = (TORSO * math.sin(tr), -TORSO * math.cos(tr))
    perp = (math.cos(tr), math.sin(tr))
    def off(p, k): return (p[0] + perp[0] * k, p[1] + perp[1] * k)
    shR, shL, hpR, hpL = off(neck, shw), off(neck, -shw), off(pel, hpw), off(pel, -hpw)
    A = lambda k, dflt: d.get(k, dflt)
    elR = add(shR, vec(A("aR", 10), UA)); wrR = add(elR, vec(A("fR", 6), FA))
    elL = add(shL, vec(A("aL", -10), UA)); wrL = add(elL, vec(A("fL", -6), FA))
    knR = add(hpR, vec(A("tR", 4), TH)); anR = add(knR, vec(A("sR", 2), SH))
    knL = add(hpL, vec(A("tL", -4), TH)); anL = add(knL, vec(A("sL", -2), SH))
    ha = tilt + A("head", 0); hr = math.radians(ha)
    up = (math.sin(hr), -math.cos(hr)); rt = (math.cos(hr), math.sin(hr))
    hc = add(neck, (up[0] * (10 + R), up[1] * (10 + R)))
    face = d.get("face", 0)
    # feet
    def foot(an, s, k):
        if "foot" + k in d: a = d["foot" + k]
        elif face: a = s + 90 * (1 if face > 0 else -1)
        else: a = s + (70 if k == "R" else -70)
        return add(an, vec(a, 13))
    ftR, ftL = foot(anR, A("sR", 2), "R"), foot(anL, A("sL", -2), "L")
    pts = [pel, neck, shR, shL, elR, wrR, elL, wrL, knR, anR, knL, anL, ftR, ftL, hc,
           add(hc, (up[0] * R, up[1] * R)), add(hc, (-up[0] * R, -up[1] * R))]
    if d.get("hair", "long") == "long":
        pts.append(add(hc, (-up[0] * 40, -up[1] * 40)))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    floor = max(maxy + 6, pel[1] + 11)
    env = d.get("env", "").split()
    out = []
    # ----- environment (behind)
    def wall(side_, window=False):
        if side_ == "R": x = max(shR[0], shL[0], hpR[0], hpL[0], neck[0], pel[0]) + 13
        else: x = min(shR[0], shL[0], hpR[0], hpL[0], neck[0], pel[0]) - 13
        top = miny - 18
        out.append(f'<line x1="{f(x)}" y1="{f(top)}" x2="{f(x)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="3"/>')
        dx = 9 if side_ == "R" else -9
        yy = top + 8
        while yy < floor:
            out.append(f'<line x1="{f(x)}" y1="{f(yy)}" x2="{f(x+dx)}" y2="{f(yy-9)}" stroke="{LINE}" stroke-width="1.2" opacity=".6"/>'); yy += 14
        if window:
            wx = x + (6 if side_ == "R" else -6); w = 34 * (1 if side_ == "R" else -1)
            y0, y1 = miny, miny + 120
            out.append(f'<rect x="{f(min(wx, wx+w))}" y="{f(y0)}" width="34" height="120" fill="#cfe6f5" stroke="{LINE}" stroke-width="2" opacity=".9"/>')
            out.append(f'<line x1="{f(wx+w/2)}" y1="{f(y0)}" x2="{f(wx+w/2)}" y2="{f(y1)}" stroke="{LINE}" stroke-width="1.5"/><line x1="{f(min(wx,wx+w))}" y1="{f(y0+60)}" x2="{f(min(wx,wx+w)+34)}" y2="{f(y0+60)}" stroke="{LINE}" stroke-width="1.5"/>')
    for e in env:
        if e in ("wallR", "wallL"): wall(e[-1])
        elif e in ("windowR", "windowL"): wall(e[-1], True)
        elif e == "rail":
            y = pel[1] - 12
            out.append(f'<line x1="{f(minx-30)}" y1="{f(y)}" x2="{f(maxx+30)}" y2="{f(y)}" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/>')
            for x in (minx - 24, (minx + maxx) / 2, maxx + 24):
                out.append(f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="2.5"/>')
        elif e == "grass":
            x = minx - 40
            while x < maxx + 40:
                out.append(f'<path d="M{f(x)} {f(floor)} l-2 -9 M{f(x)} {f(floor)} l2 -11 M{f(x)} {f(floor)} l5 -7" stroke="#7fb069" stroke-width="1.6" fill="none"/>')
                if int(x) % 3 == 0: out.append(f'<circle cx="{f(x+3)}" cy="{f(floor-13)}" r="3" fill="#f6a5c0"/>')
                x += 17
        elif e == "sea":
            x = minx - 50
            out.append(f'<path d="M{f(minx-50)} {f(floor+9)} ' + " ".join(f'q8 -7 16 0 t16 0' for _ in range(int((maxx - minx + 100) / 32) + 1)) + f'" stroke="#6fb3d9" stroke-width="2.5" fill="none"/>')
            out.append(f'<path d="M{f(minx-40)} {f(floor+17)} ' + " ".join(f'q8 -7 16 0 t16 0' for _ in range(int((maxx - minx + 80) / 32) + 1)) + f'" stroke="#9fd0ea" stroke-width="2" fill="none"/>')
        elif e in ("tableR", "tableL"):
            sg = 1 if e == "tableR" else -1
            x0 = (maxx if sg > 0 else minx) + sg * 6; ty = pel[1] - 14
            out.append(f'<line x1="{f(x0)}" y1="{f(ty)}" x2="{f(x0+sg*56)}" y2="{f(ty)}" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/><line x1="{f(x0+sg*38)}" y1="{f(ty)}" x2="{f(x0+sg*38)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="3"/>')
            out.append(f'<rect x="{f(x0+sg*28-(0 if sg>0 else 9))}" y="{f(ty-12)}" width="9" height="11" rx="2" fill="#fff" stroke="{LINE}" stroke-width="1.5"/>')
        elif e == "stairs":
            x = maxx + 8; y = floor
            for i in range(3):
                out.append(f'<rect x="{f(x+i*26)}" y="{f(y-(i+1)*22)}" width="{f(26*(3-i)+10)}" height="22" fill="#e6dde0" stroke="{LINE}" stroke-width="1.5"/>')
        elif e in ("chairR", "chairL"):  # chair back on the R/L side of figure
            sg = 1 if e == "chairR" else -1; sy = pel[1] + 9
            out.append(f'<line x1="{f(pel[0]-26)}" y1="{f(sy)}" x2="{f(pel[0]+26)}" y2="{f(sy)}" stroke="{LINE}" stroke-width="5" stroke-linecap="round"/>')
            out.append(f'<line x1="{f(pel[0]+sg*26)}" y1="{f(sy)}" x2="{f(pel[0]+sg*26)}" y2="{f(sy-70)}" stroke="{LINE}" stroke-width="4" stroke-linecap="round"/>')
            for xx in (-22, 22): out.append(f'<line x1="{f(pel[0]+xx)}" y1="{f(sy)}" x2="{f(pel[0]+xx)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="3"/>')
        elif e == "stool":
            sy = pel[1] + 9
            out.append(f'<line x1="{f(pel[0]-24)}" y1="{f(sy)}" x2="{f(pel[0]+24)}" y2="{f(sy)}" stroke="{LINE}" stroke-width="6" stroke-linecap="round"/>')
            for xx in (-18, 18): out.append(f'<line x1="{f(pel[0]+xx)}" y1="{f(sy)}" x2="{f(pel[0]+xx)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="3"/>')
        elif e == "step":  # sit on a step: block from seat level to floor
            sy = pel[1] + 9
            out.append(f'<rect x="{f(pel[0]-90)}" y="{f(sy)}" width="110" height="{f(max(floor-sy,6))}" fill="#e6dde0" stroke="{LINE}" stroke-width="1.5"/>')
        elif e == "bed":
            sy = pel[1] + 9
            out.append(f'<rect x="{f(minx-30)}" y="{f(sy)}" width="{f(maxx-minx+60)}" height="{f(max(floor-sy,10))}" rx="6" fill="#efe3e8" stroke="{LINE}" stroke-width="1.5"/>')
        elif e == "rug":
            out.append(f'<ellipse cx="{f((minx+maxx)/2)}" cy="{f(floor)}" rx="{f((maxx-minx)/2+45)}" ry="8" fill="#f1dce3"/>')
    out.append(f'<line x1="{f(minx-45)}" y1="{f(floor)}" x2="{f(maxx+45)}" y2="{f(floor)}" stroke="{LINE}" stroke-width="2" opacity=".7"/>')
    # ----- figure
    cloth = CLOTH.get(mood, "#ec7fa0")
    def ln(a, b, w, c=SKIN): return f'<line x1="{f(a[0])}" y1="{f(a[1])}" x2="{f(b[0])}" y2="{f(b[1])}" stroke="{c}" stroke-width="{w}" stroke-linecap="round"/>'
    # back limbs first (R side = far in side view)
    legs = [ln(hpL, knL, 12), ln(knL, anL, 9), ln(anL, ftL, 6, "#6b5a60"), ln(hpR, knR, 12), ln(knR, anR, 9), ln(anR, ftR, 6, "#6b5a60")]
    out += legs
    hair_style = d.get("hair", "long")
    if hair_style == "long":
        out.append(ln(add(hc, (-up[0] * 2, -up[1] * 2)), add(hc, (-up[0] * 30, -up[1] * 30)), 2 * R + 2, HAIR))
    elif hair_style == "pony":
        px = -1 if face > 0 else 1
        tip = add(hc, (rt[0] * px * 30 - up[0] * 22, rt[1] * px * 30 - up[1] * 22))
        out.append(ln(add(hc, (rt[0] * px * 12, rt[1] * px * 12)), tip, 9, HAIR))
    elif hair_style == "bun":
        b = add(hc, (up[0] * (R + 6), up[1] * (R + 6)))
        out.append(f'<circle cx="{f(b[0])}" cy="{f(b[1])}" r="9" fill="{HAIR}"/>')
    out.append(ln(add(neck, (up[0] * 0, up[1] * 0)), add(hc, (-up[0] * 12, -up[1] * 12)), 8))
    out.append(ln(shR, shL, 10, cloth))
    tor = [shR, shL, hpL, hpR]
    out.append('<polygon points="' + " ".join(f"{f(x)},{f(y)}" for x, y in tor) + f'" fill="{cloth}" stroke="{cloth}" stroke-width="10" stroke-linejoin="round"/>')
    if d.get("skirt"):
        k = 34
        b1 = add(add(hpR, vec(A("tR", 4), k)), (10, 0)); b2 = add(add(hpL, vec(A("tL", -4), k)), (-10, 0))
        out.append('<polygon points="' + " ".join(f"{f(x)},{f(y)}" for x, y in [shR, shL, b2, b1]) + f'" fill="{cloth}" stroke="{cloth}" stroke-width="6" stroke-linejoin="round"/>')
    out += [ln(shL, elL, 8), ln(elL, wrL, 6.5), ln(shR, elR, 8), ln(elR, wrR, 6.5)]
    for w in (wrL, wrR): out.append(f'<circle cx="{f(w[0])}" cy="{f(w[1])}" r="4.6" fill="{SKIN}"/>')
    # head
    out.append(f'<circle cx="{f(hc[0])}" cy="{f(hc[1])}" r="{R}" fill="{SKIN}"/>')
    if hair_style != "none" and not d.get("back"):
        # fringe: hair cap over upper half
        a0 = add(hc, (rt[0] * -R + up[0] * 2, rt[1] * -R + up[1] * 2)); a1 = add(hc, (rt[0] * R + up[0] * 2, rt[1] * R + up[1] * 2))
        ctl = add(hc, (up[0] * (R * 2.15), up[1] * (R * 2.15)))
        dip = add(hc, (up[0] * (R * 0.35) + rt[0] * face * 6, up[1] * (R * 0.35) + rt[1] * face * 6))
        out.append(f'<path d="M{f(a0[0])} {f(a0[1])} Q{f(ctl[0])} {f(ctl[1])} {f(a1[0])} {f(a1[1])} Q{f(dip[0])} {f(dip[1])} {f(a0[0])} {f(a0[1])}Z" fill="{HAIR}"/>')
    if d.get("back"):
        out.append(f'<circle cx="{f(hc[0])}" cy="{f(hc[1])}" r="{R+1.5}" fill="{HAIR}"/>')
    # face
    def loc(x, y): return add(hc, (rt[0] * x + up[0] * y, rt[1] * x + up[1] * y))
    if d.get("back"): pass
    elif face == 0:
        for ex in (-6.5, 6.5):
            e = loc(ex, -2); out.append(f'<circle cx="{f(e[0])}" cy="{f(e[1])}" r="1.8" fill="#3a2a2a"/>')
        m = loc(0, -10); out.append(f'<circle cx="{f(m[0])}" cy="{f(m[1])}" r="1.5" fill="#d9707f"/>')
    else:
        sg = 1 if face > 0 else -1
        e = loc(sg * 7, -2); n = loc(sg * R, -5); n2 = loc(sg * (R + 4), -8)
        out.append(f'<circle cx="{f(e[0])}" cy="{f(e[1])}" r="1.8" fill="#3a2a2a"/><path d="M{f(n[0])} {f(n[1])} L{f(n2[0])} {f(n2[1])}" stroke="{SKIN}" stroke-width="3" stroke-linecap="round"/>')
    # held items
    def item(kind, w):
        x, y = w
        if kind == "cup": return f'<rect x="{f(x-5)}" y="{f(y-13)}" width="10" height="13" rx="2" fill="#fff" stroke="#b08968" stroke-width="2"/>'
        if kind == "flower": return f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x)}" y2="{f(y-24)}" stroke="#6a994e" stroke-width="2"/><circle cx="{f(x)}" cy="{f(y-28)}" r="7" fill="#f4a6c0"/><circle cx="{f(x)}" cy="{f(y-28)}" r="2.5" fill="#f6d365"/>'
        if kind == "bag": return f'<path d="M{f(x-7)} {f(y+14)} Q{f(x)} {f(y-4)} {f(x+7)} {f(y+14)}" stroke="#8d6e63" stroke-width="2" fill="none"/><rect x="{f(x-13)}" y="{f(y+12)}" width="26" height="18" rx="3" fill="#c08a6b"/>'
        if kind == "phone": return f'<rect x="{f(x-5)}" y="{f(y-16)}" width="10" height="17" rx="2" fill="#444"/>'
        if kind == "book": return f'<rect x="{f(x-9)}" y="{f(y-12)}" width="18" height="14" rx="1.5" fill="#d8c3a5" stroke="#8a6f4d" stroke-width="1.5"/>'
        if kind == "umbrella": return f'<line x1="{f(x)}" y1="{f(y+14)}" x2="{f(x)}" y2="{f(y-34)}" stroke="#555" stroke-width="2"/><path d="M{f(x-34)} {f(y-34)} Q{f(x)} {f(y-72)} {f(x+34)} {f(y-34)}Z" fill="#9fc5e8" stroke="#6a8caf" stroke-width="1.5"/>'
        if kind == "camera": return f'<rect x="{f(x-9)}" y="{f(y-12)}" width="18" height="12" rx="2" fill="#555"/><circle cx="{f(x)}" cy="{f(y-6)}" r="3.5" fill="#9ad"/>'
        return ""
    for k, w in (("R", wrR), ("L", wrL)):
        if d.get("hold" + k): out.append(item(d["hold" + k], w))
    if d.get("hat"):
        b = add(hc, (up[0] * (R - 2), up[1] * (R - 2)))
        l = add(b, (-rt[0] * 28, -rt[1] * 28)); r_ = add(b, (rt[0] * 28, rt[1] * 28)); top = add(b, (up[0] * 15, up[1] * 15))
        out.append(f'<line x1="{f(l[0])}" y1="{f(l[1])}" x2="{f(r_[0])}" y2="{f(r_[1])}" stroke="#d4a373" stroke-width="5" stroke-linecap="round"/>')
        t1 = add(b, (-rt[0] * 15, -rt[1] * 15)); t2 = add(b, (rt[0] * 15, rt[1] * 15))
        out.append(f'<path d="M{f(t1[0])} {f(t1[1])} Q{f(top[0])} {f(top[1])} {f(t2[0])} {f(t2[1])}Z" fill="#e9c46a"/>')
    # fit
    allx = xs + [minx - 34, maxx + 34]; ally = ys + [miny - 20]
    for e in env:
        if e in ("wallR", "windowR", "stairs", "tableR"): allx.append(maxx + 70)
        if e in ("wallL", "windowL", "tableL"): allx.append(minx - 70)
    W, H = 240, 300
    bw, bh = max(allx) - min(allx), max(ally) - min(ally) + 20
    s = min(1.0, (W - 16) / bw, (H - 16) / bh)
    tx = W / 2 - s * (min(allx) + max(allx)) / 2
    ty = H / 2 - s * ((min(ally) + floor + 9) / 2)
    ty = min(ty, H - 10 - s * (floor + 9))
    body = "\n".join(out)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="{title}">'
            f'<rect width="{W}" height="{H}" rx="14" fill="#fbf1f4"/>'
            f'<g transform="translate({f(tx)} {f(ty)}) scale({s:.3f})">{body}</g></svg>')
