import sys, importlib; sys.path.insert(0, '.')
from pose_lib import parse, resolve
from pose_render import render
import cairosvg
from PIL import Image, ImageDraw, ImageFont
mod = importlib.import_module(sys.argv[1]); a = int(sys.argv[2]); b = int(sys.argv[3])
items = mod.POSES[a:b]
cols = 8; w, h = 200, 250
rows = (len(items) + cols - 1) // cols
m = Image.new("RGB", (cols * w, rows * h), "white")
font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", 12) if False else None
for i, (line, spec) in enumerate(items):
    P = parse(line)
    cairosvg.svg2png(bytestring=render(resolve(spec), P["name"], P["mood"][0]).encode(), write_to="/tmp/x.png", output_width=w)
    m.paste(Image.open("/tmp/x.png").convert("RGB"), ((i % cols) * w, (i // cols) * h))
    ImageDraw.Draw(m).text(((i % cols) * w + 4, (i // cols) * h + 2), str(a + i), fill="red")
m.save(f"/tmp/sheet_{sys.argv[1]}_{a}.png"); print(len(mod.POSES))
