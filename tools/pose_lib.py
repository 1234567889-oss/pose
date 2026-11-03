ARM = {"hang": (10, 6), "hip": (50, -37), "pocket": (25, -22), "hair": (125, -100), "cheek": (62, -140),
       "chest": (30, -120), "cross": (30, -100), "back": (12, -25), "up": (165, 172), "wave": (110, 170),
       "wide": (85, 88), "diag": (130, 135), "front": (20, -65), "hat": (130, -125), "skirt": (38, 14), "low": (30, 10)}
def resolve(spec):
    d = dict(spec)
    for k in ("R", "L"):
        if k in d:
            a, f = ARM[d.pop(k)]
            if k == "L": a, f = -a, -f
            d["a" + k], d["f" + k] = a, f
    return d
FIELDS = ["name", "scene", "mood", "kouling", "hand", "eye", "chin", "shoulder", "avoid", "lens", "angle", "orient"]
def parse(line):
    t = [x.strip() for x in line.split("|")]
    assert len(t) == 12, (len(t), line)
    r = dict(zip(FIELDS, t)); r["scene"] = r["scene"].split(","); r["mood"] = r["mood"].split(",")
    return r
