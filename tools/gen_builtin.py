#!/usr/bin/env python3
"""Generate built-in SVG pose illustrations, data/poses.json and data/sequences.json.
Sources: tools/poses_*.py (one line per pose + joint angles), tools/sequences_src.py.
Run: python3 tools/gen_builtin.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from pose_lib import parse, resolve
from pose_render import render
import poses_stand, poses_sit, poses_squat_lie, poses_lie, poses_walk
from sequences_src import SEQS


SCENE_MAP = {"街拍": ["街道"], "草地花丛": ["草地", "花丛"], "楼梯台阶": ["楼梯"], "靠墙": ["墙面"], "咖啡馆": ["咖啡馆"], "室内窗边": ["室内窗边"],
             "海边": ["海边"], "床边": ["床边"], "栏杆": ["栏杆"], "道具": []}
ENV_SCENE = {"grass": "草地", "sea": "海边", "stairs": "楼梯", "rail": "栏杆", "bed": "床边", "rug": "室内窗边", "wallL": "墙面", "wallR": "墙面",
             "windowL": "室内窗边", "windowR": "室内窗边", "tableL": "咖啡馆", "tableR": "咖啡馆", "chairL": "咖啡馆", "chairR": "咖啡馆"}
STYLE = {"日系", "甜美", "清冷", "文艺", "性感"}
HOLD_PROP = {"cup": "咖啡杯", "flower": "花束", "bag": "包", "phone": "手机", "book": "书", "umbrella": "伞", "camera": "相机"}
LENS_SHOT = {"85": "半身", "50": "七分身", "35": "全身"}
def builtin_tags(P, posture, spec):
    def uniq(l): return list(dict.fromkeys(l))
    scene = uniq([t for x in P["scene"] for t in SCENE_MAP.get(x, [x])])
    if not scene and spec.get("env") in ENV_SCENE: scene = [ENV_SCENE[spec["env"]]]
    if not scene: scene = ["街道"]
    ang = P["angle"]; angle = []
    if "低机位" in ang: angle.append("低机位")
    if "仰" in ang: angle.append("仰拍")
    if "俯" in ang: angle.append("俯拍")
    if not angle: angle.append("平视")
    props = [HOLD_PROP[spec[k]] for k in ("holdR", "holdL") if spec.get(k) in HOLD_PROP]
    if spec.get("hat"): props.append("帽子")
    t = {"posture": [posture], "scene": scene, "style": [m for m in P["mood"] if m in STYLE],
         "mood": [m for m in P["mood"] if m not in STYLE], "shot": [LENS_SHOT.get(P["lens"], "全身")],
         "angle": angle, "comp": [P["orient"]], "prop": uniq(props)}
    if spec.get("skirt"): t["outfit"] = ["连衣裙"]
    return {k: v for k, v in t.items() if v}

os.makedirs(os.path.join(ROOT, "assets/builtin"), exist_ok=True)
for f in os.listdir(os.path.join(ROOT, "assets/builtin")): os.remove(os.path.join(ROOT, "assets/builtin", f))
out, by_name, n = [], {}, 0
for mod in (poses_stand, poses_sit, poses_squat_lie, poses_lie, poses_walk):
    for line, spec in mod.POSES:
        n += 1; P = parse(line); pid = f"b{n:03d}"
        assert P["name"] not in by_name, "duplicate name " + P["name"]
        by_name[P["name"]] = pid
        fn = f"assets/builtin/{pid}.svg"
        open(os.path.join(ROOT, fn), "w", encoding="utf-8").write(render(resolve(spec), P["name"], P["mood"][0]))
        spec2 = resolve(spec)
        out.append(dict(id=pid, type="builtin", title=P["name"], svg=fn, aspect=1.25, kouling=P["kouling"],
                        tags=builtin_tags(P, mod.POSTURE, spec2),
                        tips=[["手", P["hand"]], ["眼神", P["eye"]], ["下巴", P["chin"]], ["肩膀", P["shoulder"]], ["避坑", P["avoid"]]],
                        shot={"焦段": P["lens"] + "mm", "角度": P["angle"], "构图": P["orient"]}, subject="单人女生"))
json.dump(out, open(os.path.join(ROOT, "data/poses.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
seqs = []
for i, (title, scene, mood, desc, tip, names) in enumerate(SEQS, 1):
    assert 5 <= len(names) <= 8, title
    seqs.append(dict(id=f"s{i:02d}", title=title, scene=[t for x in scene.replace("，",",").split(",") for t in SCENE_MAP.get(x.strip(), [x.strip()])] if isinstance(scene,str) else scene, mood=mood, desc=desc, tip=tip, poses=[by_name[x] for x in names]))
json.dump(seqs, open(os.path.join(ROOT, "data/sequences.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("poses:", len(out), "sequences:", len(seqs))
