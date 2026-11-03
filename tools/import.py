#!/usr/bin/env python3
"""Merge a folder of photos (e.g. saved from 小红书) into data/imported.json.

Usage:
  python3 tools/import.py --images ./incoming --meta ./incoming/meta.csv [--dry-run] [--strict]
  python3 tools/import.py --images ./incoming            # no metadata: tagged 未分类
  python3 tools/import.py --template meta.csv            # write an empty CSV with every column
  python3 tools/import.py --list-tags                    # show the taxonomy

Metadata: JSON list of objects (or {filename: {...}}), or CSV with a header row. Keys:
  file        image filename inside --images (required; also matches without extension)
  source_url  original 小红书 note link          title, note
  kouling     口令 (also: 口令, code)            tips   several tips separated by ; ； or |
  difficulty  1-3                                 焦段/lens  e.g. 85mm
  tags        free-form words, separated by , ， ; ； 、 | or spaces. Words that match a taxonomy tag
              or alias (e.g. 逆光, 沙滩) are filed under the right dimension automatically; the rest
              are kept as free extra tags.
  Dimension columns (Chinese label, ascii key or alias; multiple values allowed, same separators):
              光线/light  场景/scene  风格/style  情绪/mood  体位/posture  景别/shot
              机位/angle  构图/comp  道具/prop  服装/outfit
Taxonomy: data/taxonomy.json. An unknown value in a dimension column is appended to that dimension
(taxonomy grows; the first-seen spelling wins) unless --strict is given, which drops it with a warning.
Behaviour: each photo is copied into imported/<id>.jpg (<=1600px) with a 480px thumbnail in
imported/thumbs/<id>.jpg (needs Pillow). ids are content hashes, so re-running is idempotent
(duplicates skipped; an existing entry gets any non-empty new metadata merged in).
Files are written atomically.
"""
import argparse, csv, datetime, hashlib, json, os, re, shutil, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".bmp"}
SEP = r"[,\uff0c;\uff1b\u3001|\s]+"

def split(v, sep=SEP):
    if v is None: return []
    if isinstance(v, list): return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in re.split(sep, str(v)) if x.strip()]

def atomic_json(path, obj):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

class Taxonomy:
    def __init__(self, path):
        self.path = path; self.dirty = False
        self.t = json.load(open(path, encoding="utf-8"))
        self.dims = {d["key"]: d for d in self.t["dimensions"]}
        self.colname = {}
        for d in self.t["dimensions"]:
            for n in (d["key"], d["label"]): self.colname[n.lower()] = d["key"]
        self.colname.update({"scenes": "scene", "tag_scene": "scene", "lighting": "light", "posture": "posture", "pose": "posture"})
    def lookup(self, dim, word):
        d = self.dims[dim]
        if word in d["tags"]: return word
        al = d.get("aliases", {})
        if word in al: return self._canon(d, al[word])
        for k, v in al.items():
            if k.lower() == word.lower(): return self._canon(d, v)
        for t in d["tags"]:
            if t.lower() == word.lower(): return t
        return None
    def _canon(self, d, tag):
        # taxonomy is pruned to tags that have photos; an alias may point at a pruned tag -> bring it back
        if tag not in d["tags"]: d["tags"].append(tag); self.dirty = True
        return tag
    def classify(self, word):
        """Find the dimension of a free-form word; returns (dim, canonical) or None."""
        for k in self.dims:
            c = self.lookup(k, word)
            if c: return k, c
        return None
    def add(self, dim, word):
        self.dims[dim]["tags"].append(word); self.dirty = True
    def save(self):
        if self.dirty: atomic_json(self.path, self.t); self.dirty = False

def load_meta(path):
    if not path: return {}
    if path.lower().endswith(".csv"):
        with open(path, encoding="utf-8-sig", newline="") as f: rows = list(csv.DictReader(f))
    else:
        with open(path, encoding="utf-8-sig") as f: rows = json.load(f)
        if isinstance(rows, dict): rows = [dict(file=k, **v) for k, v in rows.items()]
    m = {}
    for r in rows:
        fn = (r.get("file") or r.get("filename") or "").strip()
        if not fn: continue
        m[fn] = r; m[os.path.splitext(fn)[0]] = r
    return m

def build_tags(tax, r, strict, warn):
    tags = {}; extra = []
    def put(dim, val):
        if val not in tags.setdefault(dim, []): tags[dim].append(val)
    for col, raw in r.items():
        dim = tax.colname.get(str(col).strip().lower())
        if not dim or raw in (None, ""): continue
        for w in split(raw):
            c = tax.lookup(dim, w)
            if c: put(dim, c)
            elif strict: warn(f"unknown {tax.dims[dim]['label']} tag '{w}' dropped (--strict)")
            else: tax.add(dim, w); put(dim, w); print(f"  + new tag '{w}' added to {tax.dims[dim]['label']}")
    for w in split(r.get("tags")):
        hit = tax.classify(w)
        if hit: put(*hit)
        elif w not in extra: extra.append(w)
    return {k: v for k, v in tags.items() if v}, extra

def process_image(src, dst, thumb):
    """returns (w, h) of the saved full image"""
    os.makedirs(os.path.dirname(thumb), exist_ok=True)
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(src))
        if im.mode not in ("RGB", "L"): im = im.convert("RGB")
        im.thumbnail((1600, 1600)); im.save(dst, "JPEG", quality=85, optimize=True)
        w, h = im.size
        t = im.copy(); t.thumbnail((480, 640)); t.save(thumb, "JPEG", quality=78, optimize=True)
        return w, h
    except Exception as e:
        print(f"  (no resize for {os.path.basename(src)}: {e})", file=sys.stderr)
        shutil.copy2(src, dst); shutil.copy2(src, thumb); return 0, 0

def write_template(tax, path):
    cols = ["file", "title", "source_url", "kouling", "tips"] + [d["label"] for d in tax.t["dimensions"]] + ["tags", "note", "difficulty"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        w.writerow(["example.jpg", "逆光侧身回眸", "https://www.xiaohongshu.com/explore/xxxx", "背对光源，慢慢回头看我", "下巴微收;手放松",
                    "逆光;黄金时刻", "海边", "日系 胶片", "安静", "站", "半身", "平视", "竖构图", "帽子", "连衣裙", "海风 氛围", "", "2"][:len(cols)])
    print("template written:", path)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--images", help="folder of images")
    ap.add_argument("--meta", help="JSON or CSV metadata file")
    ap.add_argument("--data", default=os.path.join(ROOT, "data", "imported.json"))
    ap.add_argument("--taxonomy", default=os.path.join(ROOT, "data", "taxonomy.json"))
    ap.add_argument("--dest", default=os.path.join(ROOT, "imported"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--strict", action="store_true", help="do not auto-add unknown dimension values to the taxonomy")
    ap.add_argument("--template", metavar="CSV", help="write an empty metadata CSV and exit")
    ap.add_argument("--list-tags", action="store_true")
    a = ap.parse_args()
    tax = Taxonomy(a.taxonomy)
    if a.template: return write_template(tax, a.template)
    if a.list_tags:
        for d in tax.t["dimensions"]: print(f"{d['label']} ({d['key']}): " + " ".join(d["tags"]))
        return
    if not a.images: ap.error("--images is required")

    meta = load_meta(a.meta)
    data = json.load(open(a.data, encoding="utf-8")) if os.path.exists(a.data) else []
    by_id = {p["id"]: p for p in data}
    thumbs = os.path.join(a.dest, "thumbs"); os.makedirs(a.dest, exist_ok=True)
    rel_dir = "imported" if os.path.abspath(a.dest) == os.path.join(ROOT, "imported") else os.path.basename(os.path.abspath(a.dest))
    added = updated = skipped = 0
    files = sorted(f for f in os.listdir(a.images) if os.path.splitext(f)[1].lower() in EXTS)
    for fn in files:
        src = os.path.join(a.images, fn)
        pid = "x" + hashlib.sha1(open(src, "rb").read()).hexdigest()[:12]
        r = meta.get(fn) or meta.get(os.path.splitext(fn)[0]) or {}
        tags, extra = build_tags(tax, r, a.strict, lambda m: print("warn   ", fn + ":", m))
        new = dict(title=(r.get("title") or "").strip(), source_url=(r.get("source_url") or r.get("url") or "").strip(),
                   kouling=(r.get("kouling") or r.get("口令") or r.get("code") or "").strip(),
                   note=(r.get("note") or "").strip(), tips=split(r.get("tips") or r.get("要点"), r"[;\uff1b|]+"), extra=extra)
        lens = (r.get("lens") or r.get("焦段") or "").strip()
        if lens: new["shot"] = {"焦段": lens if lens.endswith("mm") else lens + "mm"}
        if str(r.get("difficulty") or "").strip(): new["difficulty"] = int(r["difficulty"])
        if pid in by_id:
            cur = by_id[pid]; ch = False
            if isinstance(cur.get("tags"), list): cur["tags"] = {}      # legacy list form
            for k, v in new.items():
                if v and cur.get(k) != v: cur[k] = v; ch = True
            for dim, vals in tags.items():
                merged = list(dict.fromkeys(cur["tags"].get(dim, []) + vals))
                if merged != cur["tags"].get(dim): cur["tags"][dim] = merged; ch = True
            if ch: updated += 1; print(f"update  {fn}")
            else: skipped += 1; print(f"skip    {fn} (already imported)")
            continue
        if not r: print(f"warn    {fn}: no metadata row; tagged 未分类")
        full = os.path.join(a.dest, pid + ".jpg"); th = os.path.join(thumbs, pid + ".jpg"); w = h = 0
        if not a.dry_run: w, h = process_image(src, full, th)
        entry = dict(id=pid, type="image", title=new["title"] or os.path.splitext(fn)[0], image=f"{rel_dir}/{pid}.jpg",
                     thumb=f"{rel_dir}/thumbs/{pid}.jpg", w=w, h=h, source_url=new["source_url"], kouling=new["kouling"],
                     note=new["note"], tags=tags, extra=extra if (r or True) else [], tips=new["tips"], difficulty=new.get("difficulty", 2),
                     subject="单人女生", original_name=fn, added_at=datetime.datetime.now().astimezone().isoformat(timespec="seconds"))
        if not r: entry["extra"] = ["未分类"]
        if "shot" in new: entry["shot"] = new["shot"]
        print(f"add     {fn} -> {entry['image']}  " + " ".join(f"{tax.dims[k]['label']}:{'/'.join(v)}" for k, v in tags.items()))
        data.append(entry); by_id[pid] = entry; added += 1
    if not a.dry_run and (added or updated):
        atomic_json(a.data, data); tax.save()
    print(f"done: {added} added, {updated} updated, {skipped} skipped" + (" (dry run)" if a.dry_run else ""))

if __name__ == "__main__": main()
