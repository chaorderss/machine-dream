#!/usr/bin/env python3
"""Generate config/timeline.json: a different scene every ~5 s, cuts snapped to note onsets.

Fixed anchors (cold open, glitch, eye reveal, singularity, hush, loop) stay where the music
structure needs them; inside each musical section the slots cycle through scene variants and
palettes so no two neighbours look alike. Edit SECTIONS and re-run:

  .venv/bin/python config/build_timeline.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SLOT = 5.0
SNAP = 0.6

PALETTES = {
    "gold":     [[0.55, 0.40, 0.20], [0.45, 0.35, 0.20], [1.0, 1.0, 1.0], [0.00, 0.10, 0.25]],
    "neon":     [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 1.0], [0.00, 0.33, 0.67]],
    "chrome":   [[0.45, 0.50, 0.60], [0.25, 0.25, 0.30], [1.0, 1.0, 1.0], [0.60, 0.65, 0.75]],
    "machine":  [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 0.7, 0.4], [0.00, 0.15, 0.20]],
    "bio":      [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [2.0, 1.0, 0.0], [0.50, 0.20, 0.25]],
    "alien":    [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 0.5], [0.80, 0.90, 0.30]],
    "singularity": [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 1.0], [0.30, 0.20, 0.20]],
    "stardust": [[0.55, 0.50, 0.55], [0.45, 0.40, 0.45], [1.0, 1.0, 1.0], [0.05, 0.20, 0.45]],
    "sunset":   [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 1.0], [0.00, 0.10, 0.20]],
    "acid":     [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 0.5], [0.80, 0.90, 0.30]],
    "ocean":    [[0.20, 0.45, 0.55], [0.30, 0.40, 0.45], [1.0, 1.0, 1.0], [0.55, 0.45, 0.35]],
    "magma":    [[0.50, 0.30, 0.25], [0.50, 0.40, 0.30], [1.0, 1.0, 1.0], [0.00, 0.05, 0.15]],
    "candy":    [[0.80, 0.50, 0.40], [0.20, 0.40, 0.20], [2.0, 1.0, 1.0], [0.00, 0.25, 0.25]],
    "aurora":   [[0.30, 0.55, 0.50], [0.40, 0.45, 0.50], [1.0, 1.0, 1.0], [0.40, 0.15, 0.80]],
    "royal":    [[0.45, 0.30, 0.60], [0.50, 0.40, 0.40], [1.0, 1.0, 1.0], [0.65, 0.40, 0.20]],
    "electric": [[0.40, 0.45, 0.70], [0.45, 0.45, 0.40], [1.0, 1.5, 1.0], [0.15, 0.55, 0.85]],
    "toxic":    [[0.45, 0.55, 0.35], [0.50, 0.45, 0.50], [1.0, 1.0, 2.0], [0.30, 0.10, 0.65]],
    "ice":      [[0.55, 0.65, 0.80], [0.35, 0.35, 0.30], [1.0, 1.0, 1.0], [0.55, 0.60, 0.70]],
}

DEFAULTS = {
    "mercury":    {"uAppear": 1.0, "uRipple": 1.0, "uShape": 0.0, "uTint": 0.0},
    "mandelbox":  {"uIters": 7, "uScaleMB": -2.5, "uFoldStep": 0.03},
    "dive":       {"uTwist": 0.8, "uStreak": 0.6, "uWarmth": 0.0},
    "organic":    {"uFeed": 0.0367, "uKill": 0.0649, "rd_rate": 2500, "uWarp": 0.5, "rd_warm": 500},
    "kaleido":    {"uSeg": 6, "uKZoom": 1.2, "uKSpin": 0.05, "uKMorph": 0.0},
    "julia":      {"uJZoom": 1.6, "uJC": 0.0},
    "hyperbolic": {"uP": 7, "uQ": 3, "uHMove": 0.15},
    "mandelbulb": {"uPower": 8.0, "uMBDist": 2.6},
    "warp":       {"uWScale": 2.5},
    "voronoi":    {"uVScale": 4.0},
    "truchet":    {"uTScale": 4.0},
    "tunnel2d":   {"uTwist2": 1.0},
    "kifs":       {"uKA": 1.0, "uKB": 0.3},
    "eye":        {"uZoom": 1.0},
    "blackhole":  {"uHoleR": 0.12, "uSpin": 2.0, "uSpaghetti": 0.6, "uDisk": 1.0},
    "particles":  {"uFlow": 0.35, "uDrag": 0.7, "uCollapse": 0.0, "burst": 3.0, "focus": 0.55,
                   "uAperture": 1.3, "uBright": 0.35, "uNebula": 1.0},
}
TRANSITIONS = [("cut", 0.0), ("crossfade", 0.7), ("dissolve", 1.0), ("iris", 0.8), ("cut", 0.0), ("zoom", 0.9), ("crossfade", 0.5)]


def S(scene, palette, p=None, post=None, inp=None, bg=None):
    """Slot: one scene (optionally fed by `inp` chain, or over a faint `bg` layer)."""
    return dict(scene=scene, palette=palette, p=p or {}, post=post or {}, inp=inp, bg=bg)


SECTIONS = [
    # Satie — the acoustic chamber and its echoes
    (15.0, 65.0, "crossfade", [
        S("mercury", "chrome", {"uAppear": [[0, 0.0], [1.5, 1.0]]}),
        S("kaleido", "royal", {"uSeg": 6}),
        S("mercury", "sunset", {"uShape": 1.0, "uTint": 1.0}),
        S("hyperbolic", "aurora", {"uP": 7, "uQ": 3}),
        S("mercury", "gold", {"uTint": 0.8, "uShape": 0.35}),
        S("voronoi", "ice", {"uVScale": 3.0}),
        S("julia", "neon", {"uJZoom": 1.5}),
        S("mercury", "acid", {"uTint": 1.0, "uShape": 0.7}),
        S("warp", "candy", {"uWScale": 2.0}),
        S("kifs", "electric"),
    ]),
    # Bach fugue — machines that fold themselves
    (65.0, 125.0, "zoom", [
        S("mandelbox", "machine", {"uIters": 5, "uScaleMB": -2.4}),
        S("mandelbulb", "magma", {"uPower": 8.0}),
        S("truchet", "neon", {"uTScale": 4.0}),
        S("mandelbox", "ocean", {"uIters": 8, "uScaleMB": -2.8}),
        S("tunnel2d", "acid", {"uTwist2": 1.0}),
        S("kifs", "royal", {"uKA": 1.2, "uKB": 0.6}),
        S("mandelbox", "sunset", {"uIters": 9, "uScaleMB": -2.2}),
        S("mandelbulb", "aurora", {"uPower": 6.0, "uMBDist": 2.2}),
        S("kaleido", "electric", {"uSeg": 10, "uKSpin": 0.3, "uKZoom": 0.8}),
        S("dive", "neon", {"uTwist": 1.5}),
        S("julia", "magma", {"uJZoom": 0.9, "uJC": 2.0}),
        S("mandelbox", "candy", {"uIters": 11, "uScaleMB": -2.9, "uFoldStep": 0.05}),
    ]),
    # Danse macabre — the math is alive (first slot grows out of the frozen machine)
    (125.5, 180.0, "none", [
        S("organic", "bio", {"uFeed": 0.0545, "uKill": 0.062, "rd_warm": 0, "rd_rate": 1500}),
        S("voronoi", "toxic", {"uVScale": 5.0}),
        S("organic", "magma", {"uFeed": 0.0367, "uKill": 0.0649}),
        S("hyperbolic", "candy", {"uP": 5, "uQ": 4, "uHMove": 0.25}),
        S("organic", "aurora", {"uFeed": 0.029, "uKill": 0.057}),
        S("warp", "ocean", {"uWScale": 3.5}),
        S("truchet", "royal", {"uTScale": 6.0}),
        S("organic", "sunset", {"uFeed": 0.039, "uKill": 0.058}),
        S("kaleido", "magma", {"uSeg": 8, "uKMorph": 2.0}),
        S("julia", "bio", {"uJZoom": 1.2, "uJC": 4.0}),
        S("organic", "neon", {"uFeed": 0.0545, "uKill": 0.062}),
    ]),
    # Night on Bald Mountain — the eye, then the singularity eating every world
    (180.0, 255.0, "none", [
        S("eye", "alien", {"uZoom": [[0, 0.0], [5, 0.55]]}, inp=["organic"]),
        S("eye", "alien", {"uZoom": [[0, 0.55], [4, 1.0]]}, inp=["organic"]),
        S("eye", "electric", inp=["julia"]),
        S("eye", "magma", inp=["mandelbulb"]),
        S("eye", "candy", inp=["kaleido"]),
        S("blackhole", "singularity", {"uHoleR": [[0, 0.0], [5, 0.1]], "uSpin": 1.0, "uSpaghetti": 0.3}, inp=["organic", "eye"]),
        S("blackhole", "magma", {"uHoleR": 0.11, "uSpin": 1.4}, inp=["mandelbulb"]),
        S("blackhole", "electric", {"uHoleR": 0.12, "uSpin": 1.6}, inp=["kaleido"]),
        S("blackhole", "aurora", {"uHoleR": 0.13, "uSpin": 1.8}, inp=["hyperbolic"]),
        S("blackhole", "neon", {"uHoleR": 0.14, "uSpin": 2.0}, inp=["julia"]),
        S("blackhole", "royal", {"uHoleR": 0.15, "uSpin": 2.2}, inp=["truchet"]),
        S("blackhole", "candy", {"uHoleR": 0.16, "uSpin": 2.4}, inp=["warp", "eye"]),
        S("blackhole", "acid", {"uHoleR": 0.17, "uSpin": 2.6}, inp=["tunnel2d"]),
        S("blackhole", "sunset", {"uHoleR": 0.18, "uSpin": 2.8}, inp=["mandelbox"]),
        S("blackhole", "singularity", {"uHoleR": [[0, 0.2], [4.3, 0.04], [5.0, 0.002]], "uSpin": 3.0,
                                       "uDisk": [[0, 1.0], [5.0, 0.0]]}, inp=["kifs"]),
    ]),
    # Rêverie — one particle field, a different dream glowing behind it every slot
    (256.0, 294.0, "none", [
        S("particles", "stardust", {"uNebula": [[0, 0.0], [5, 1.0]]}),
        S("particles", "royal", bg="kaleido"),
        S("particles", "aurora", bg="julia"),
        S("particles", "candy", bg="warp"),
        S("particles", "ice", bg="hyperbolic"),
        S("particles", "sunset", bg="voronoi"),
        S("particles", "electric", bg="mandelbulb"),
        S("particles", "stardust"),
    ]),
]


def snap(t, onsets):
    if onsets is None or len(onsets) == 0:
        return t
    i = int(np.argmin(np.abs(onsets - t)))
    return float(onsets[i]) if abs(onsets[i] - t) <= SNAP else t


def kf_shift(v):
    return v


def build():
    tl = json.loads((HERE / "timeline.json").read_text())
    feats = ROOT / "analysis/features.npz"
    onsets = np.load(feats)["note_times"] if feats.exists() else None
    prefix = [c for c in tl["chapters"] if c["end"] <= 15.0]
    loop = [c for c in tl["chapters"] if c["id"] == "loop"]
    chapters = list(prefix)
    tcount = 0
    for (a, b, first_tr, slots) in SECTIONS:
        n = len(slots)
        bounds = [a] + [snap(a + k * SLOT, onsets) for k in range(1, n)] + [b]
        prev_pal = None
        for k, s in enumerate(slots):
            start, end = bounds[k], bounds[k + 1]
            dur = end - start
            layers, params = [], {}
            for sc in (s["inp"] or []):
                layers.append({"scene": sc, **({"input": True} if layers else {})})
                params.update(DEFAULTS.get(sc, {}))
            if s["bg"]:
                layers.append({"scene": s["bg"], "weight": [[0, 0.0], [1.0, 0.3], [dur - 0.5, 0.3], [dur, 0.0]]})
                params.update(DEFAULTS.get(s["bg"], {}))
            layers.append({"scene": s["scene"], **({"input": True} if s["inp"] else {})})
            params.update(DEFAULTS.get(s["scene"], {}))
            params.update(s["p"])
            if s["scene"] == "particles":   # one continuous field across the section
                g0, g1 = (start - 256.0) / 38.0, (end - 256.0) / 38.0
                params["uCamDist"] = [[0, 2.2 + 4.8 * g0], [dur, 2.2 + 4.8 * g1]]
            if k == 0:
                tr = {"type": first_tr, "length": 0.5 if first_tr == "crossfade" else 2.0 if first_tr == "zoom" else 0.0, "pre": 0.0 if first_tr == "crossfade" else 0.5}
            elif s["scene"] in ("blackhole", "eye", "particles"):
                tr = {"type": "cut"}          # same scene on both sides of the seam: switch inputs on a note
            else:
                typ, ln = TRANSITIONS[tcount % len(TRANSITIONS)]
                tcount += 1
                tr = {"type": typ, "length": ln, "pre": 0.5}
            ch = {"id": f"{s['scene']}_{int(start)}", "start": round(start, 3), "end": round(end, 3),
                  "transition": tr, "layers": layers, "palette": s["palette"], "params": params,
                  "post": {"bloom": 0.3, "sat": 1.45, **s["post"]}}
            if s["scene"] == "particles" and prev_pal:
                ch["palette_from"], ch["palette_blend"] = prev_pal, [[0, 0.0], [1.5, 1.0]]
            chapters.append(ch)
            prev_pal = s["palette"]
    for c in loop:
        c["palette_from"] = "stardust"
    chapters += loop
    ids = [c["layers"][-1]["scene"] for c in chapters]
    for i in range(1, len(ids)):
        if ids[i] == ids[i - 1] and ids[i] not in ("blackhole", "eye", "particles", "dive"):
            raise SystemExit(f"neighbouring slots share scene {ids[i]} at {chapters[i]['start']}")
    tl["chapters"] = chapters
    tl["palettes"] = PALETTES
    tl["speed"] = [[0, 0.3], [3, 2.0], [6, 6.0], [14.5, 11.0], [15.2, 0.6], [64.5, 0.6], [65.5, 0.8],
                   [95, 1.6], [124, 3.8], [125, 0.0], [125.5, 0.8], [254, 1.2], [255, 0.0], [300, 0.0]]
    (HERE / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    lens = np.diff([c["start"] for c in chapters] + [300.0])
    print(f"{len(chapters)} chapters, median {np.median(lens):.2f}s, longest {lens.max():.2f}s, shortest {lens.min():.2f}s")


if __name__ == "__main__":
    build()
