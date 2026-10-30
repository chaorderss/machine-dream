#!/usr/bin/env python3
"""Hero masks + clean plates → assets/analysis/mask/<id>_<name>.png, plate/<id>_<name>.png.

SAM 2.1 base-plus is prompted with hand-picked points on the subject, on a crop round it, so the mask edge is sharp.
The plate is the painting with that subject filled in by pull-push (pure image maths, no generative inpainting);
depth is filled the same way and stored in the plate's alpha.

  .venv-music/bin/python tools/analyze_heroes.py
"""
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_paintings import OUT, PAINT, Sam      # noqa: E402

# id, name, crop (x0, y0, x1, y1 uv top-down), positive points, negative points (uv top-down)
HEROES = [
    ("adam", "godarm", (0.355, 0.32, 0.60, 0.53), [(0.385, 0.452), (0.419, 0.458), (0.45, 0.447), (0.486, 0.432), (0.527, 0.40)],
     [(0.42, 0.38), (0.45, 0.50), (0.56, 0.47)]),
    ("adam", "adamarm", (0.2, 0.34, 0.40, 0.56), [(0.34, 0.432), (0.31, 0.43), (0.287, 0.452)], [(0.33, 0.50), (0.33, 0.38)]),
    ("babel", "tower", (0.1, 0.0, 0.9, 0.82), [(0.5, 0.15), (0.45, 0.32), (0.55, 0.4), (0.35, 0.55), (0.62, 0.3)], [(0.1, 0.1), (0.9, 0.2), (0.85, 0.6)]),
    ("narcissus", "boy", (0.0, 0.05, 1.0, 0.6), [(0.27, 0.22), (0.58, 0.2), (0.15, 0.4), (0.52, 0.42), (0.85, 0.42)], [(0.5, 0.5), (0.8, 0.1)]),
    ("wanderer", "figure", (0.3, 0.3, 0.7, 0.72), [(0.5, 0.46), (0.47, 0.37), (0.49, 0.6)], [(0.35, 0.45), (0.65, 0.45)]),
    ("nightmare", "demon", (0.5, 0.0, 0.8, 0.3), [(0.62, 0.1), (0.63, 0.17)], [(0.55, 0.05), (0.75, 0.2)]),
    ("nightmare", "woman", (0.0, 0.25, 1.0, 1.0), [(0.5, 0.5), (0.25, 0.51), (0.8, 0.62)], [(0.5, 0.25), (0.5, 0.85)]),
    ("melencolia", "solid", (0.0, 0.3, 0.5, 0.7), [(0.28, 0.48), (0.2, 0.5)], [(0.45, 0.65)]),
    ("medusa", "face", (0.1, 0.1, 0.9, 0.9), [(0.52, 0.47), (0.5, 0.62), (0.57, 0.41)], [(0.2, 0.2), (0.2, 0.8)]),
    ("oiwa", "face", (0.2, 0.2, 1.0, 0.8), [(0.6, 0.46), (0.68, 0.4), (0.6, 0.56)], [(0.3, 0.5), (0.9, 0.2)]),
    ("saturn", "body", (0.0, 0.05, 1.0, 1.0), [(0.33, 0.2), (0.6, 0.3), (0.55, 0.48), (0.25, 0.72), (0.75, 0.85)], [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9)]),
    ("liberty", "flag", (0.2, 0.0, 0.75, 0.2), [(0.33, 0.11), (0.48, 0.09)], [(0.7, 0.05)]),
    ("fabrica_muscle", "body", (0.0, 0.03, 1.0, 1.0), [(0.5, 0.45), (0.56, 0.2), (0.15, 0.2), (0.55, 0.75), (0.2, 0.42)], [(0.1, 0.72), (0.85, 0.2), (0.9, 0.75)]),
    ("fabrica_deep", "body", (0.0, 0.03, 1.0, 1.0), [(0.5, 0.42), (0.38, 0.7), (0.6, 0.65), (0.2, 0.55), (0.82, 0.55)], [(0.15, 0.2), (0.15, 0.75)]),
    ("fabrica_skeleton", "body", (0.0, 0.03, 1.0, 1.0), [(0.5, 0.25), (0.52, 0.4), (0.42, 0.75), (0.6, 0.75), (0.85, 0.5)], [(0.85, 0.2), (0.1, 0.7)]),
    ("arnolfini", "couple", (0.0, 0.05, 1.0, 1.0), [(0.3, 0.45), (0.25, 0.2), (0.72, 0.45), (0.7, 0.2)], [(0.49, 0.28), (0.5, 0.9)]),
]


def pull_push(rgb, hole):
    """Fill hole (bool) by a mip pyramid of known pixels: smooth, structure-free, purely arithmetic."""
    a = rgb.astype(np.float32)
    w = (~hole).astype(np.float32)
    pyr = [(a * w[..., None], w)]
    while min(pyr[-1][1].shape) > 2:
        c, m = pyr[-1]
        h, wd = (c.shape[0] // 2) * 2, (c.shape[1] // 2) * 2
        c2 = c[:h, :wd].reshape(h // 2, 2, wd // 2, 2, -1).mean((1, 3))
        m2 = m[:h, :wd].reshape(h // 2, 2, wd // 2, 2).mean((1, 3))
        pyr.append((c2, m2))
    cur = pyr[-1][0] / np.maximum(pyr[-1][1], 1e-4)[..., None]
    for c, m in reversed(pyr[:-1]):
        ups = np.stack([np.array(Image.fromarray(cur[..., k]).resize(m.shape[::-1], Image.BILINEAR)) for k in range(cur.shape[-1])], -1)
        k = np.clip(m, 0, 1)[..., None]
        cur = c / np.maximum(m, 1e-4)[..., None] * (k > 0.98) + ups * (k <= 0.98)
    return cur


def main():
    (OUT / "mask").mkdir(exist_ok=True)
    (OUT / "plate").mkdir(exist_ok=True)
    sam = Sam()
    from scipy.ndimage import binary_dilation
    for pid, name, crop, pos, neg in HEROES:
        f = OUT / "mask" / f"{pid}_{name}.png"
        if f.exists():
            continue
        im = Image.open(PAINT / f"{pid}.png").convert("RGB")
        W, H = im.size
        box = (int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H))
        c = im.crop(box)
        s = 1024 / max(c.size)
        c = c.resize((round(c.width * s), round(c.height * s)), Image.LANCZOS)
        sam.embed(c)
        px = lambda p: [(p[0] * W - box[0]) * s, (p[1] * H - box[1]) * s]
        while True:
            try:
                m, iou = sam.points([[px(p) for p in pos + neg]], [[1] * len(pos) + [0] * len(neg)])
                break
            except torch.OutOfMemoryError:
                torch.cuda.empty_cache()
        k = int(iou[0].argmax())
        lo = m[0, k][None, None]
        up = torch.nn.functional.interpolate(lo, size=(box[3] - box[1], box[2] - box[0]), mode="bicubic")[0, 0].cpu().numpy()
        full = np.zeros((H, W), np.uint8)
        full[box[1]:box[3], box[0]:box[2]] = (up > 0).astype(np.uint8) * 255
        Image.fromarray(full).save(f)
        print("mask", pid, name, f"iou {float(iou[0, k]):.3f} area {(full > 0).mean():.4f}", flush=True)
        # clean plate, depth in alpha
        dp = np.array(Image.open(OUT / "depth" / f"{pid}.png").resize((W, H), Image.BILINEAR), np.float32) / 65535.0
        hole = binary_dilation(full > 0, iterations=max(3, W // 500))
        rgba = np.dstack([np.array(im, np.float32) / 255.0, dp])
        fill = pull_push(rgba, hole)
        out = np.where(hole[..., None], fill, rgba)
        Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGBA").save(OUT / "plate" / f"{pid}_{name}.png")
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
