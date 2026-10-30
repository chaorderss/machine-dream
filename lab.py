#!/usr/bin/env python3
"""Scene lab: render one timeline time under several param overrides, side by side.

  python lab.py 80 'uScaleMB=-1.6' 'uScaleMB=2.2;uIters=8' --out output/lab.png
  python lab.py 18 'ch.hud={"types":[]}' 'post.teal=0'
"""
import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from engine.features import Features   # noqa: E402
from engine.renderer import Engine     # noqa: E402
from engine.timeline import Timeline   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("time", type=float)
ap.add_argument("variants", nargs="*", default=[""])
ap.add_argument("--size", default="960x540")
ap.add_argument("--out", default="output/lab.png")
a = ap.parse_args()
w, h = map(int, a.size.split("x"))
base = json.loads((ROOT / "config/timeline.json").read_text())
tiles = []
for v in a.variants or [""]:
    d = copy.deepcopy(base)
    ch = max((c for c in d["chapters"] if c["start"] <= a.time), key=lambda c: c["start"])
    for kv in filter(None, v.split(";")):
        k, val = kv.split("=")
        if k.startswith("ch."):                       # chapter-level field, e.g. ch.hud={"types":[]}
            ch[k[3:]] = json.loads(val)
            continue
        tgt = ch["post"] if k.startswith("post.") else ch["params"]
        tgt[k.removeprefix("post.")] = json.loads(val)
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=ROOT / "config", delete=False) as f:
        json.dump(d, f)
    tl = Timeline(f.name)
    Path(f.name).unlink()
    eng = Engine(tl, Features(ROOT / tl.features), (w, h), 30)
    eng.preroll(a.time)
    img = Image.frombytes("RGB", (w, h), eng.render_frame(a.time, 1 / 30))
    ImageDraw.Draw(img).text((6, 4), v or "base", fill=(255, 255, 0))
    tiles.append(img)
    eng.ctx.release()
cols = min(2, len(tiles))
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * w, rows * h))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * w, (i // cols) * h))
sheet.save(ROOT / a.out)
print(ROOT / a.out)
