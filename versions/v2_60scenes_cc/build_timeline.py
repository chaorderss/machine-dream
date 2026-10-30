#!/usr/bin/env python3
"""Generate config/timeline.json from the director blueprint: 60 scenes x 5 s, one masterpiece each.

Every slot: the painting appears intact (~1 s), its master algorithm takes over (M0 depth, M1 kaleido/sort,
M2 fluid, M3 bio, M4 swarm), optionally cracks open onto a math world (a raymarched scene chained underneath),
shifts once per pulse (~1/s), and in its last 0.8 s the camera dives through the painting's focus (portal)
into the next one. Breath slots relax for ~1.5 s roughly every 45 s. Edit SCENES and re-run:

  .venv/bin/python config/build_timeline.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SNAP = 0.5
PORTAL = 0.8

PALETTES = {
    "gold":     [[0.55, 0.40, 0.20], [0.45, 0.35, 0.20], [1.0, 1.0, 1.0], [0.00, 0.10, 0.25]],
    "neon":     [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 1.0], [0.00, 0.33, 0.67]],
    "chrome":   [[0.45, 0.50, 0.60], [0.25, 0.25, 0.30], [1.0, 1.0, 1.0], [0.60, 0.65, 0.75]],
    "bio":      [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [2.0, 1.0, 0.0], [0.50, 0.20, 0.25]],
    "electric": [[0.40, 0.45, 0.70], [0.45, 0.45, 0.40], [1.0, 1.5, 1.0], [0.15, 0.55, 0.85]],
    "magma":    [[0.50, 0.30, 0.25], [0.50, 0.40, 0.30], [1.0, 1.0, 1.0], [0.00, 0.05, 0.15]],
    "stardust": [[0.55, 0.50, 0.55], [0.45, 0.40, 0.45], [1.0, 1.0, 1.0], [0.05, 0.20, 0.45]],
}

# math worlds that can sit under a painting (revealed through cracks / peel / iris / tear)
WORLD = {
    "cathedral":  {"uPose": [[0, 0], [5, 4]], "uShatter": 0.0, "uGlow": 0.6},
    "dive":       {"uTwist": [[0, 0.3], [5, 1.2]], "uStreak": 0.6, "uWarmth": 0.6},
    "mandelbox":  {"uIters": 8, "uScaleMB": -2.6, "uFoldStep": 0.04},
    "mandelbulb": {"uPower": 8.0, "uMBDist": 2.4},
    "kifs":       {"uKA": 1.1, "uKB": 0.4},
    "hyperbolic": {"uP": 7, "uQ": 3, "uHMove": 0.2},
    "tunnel2d":   {"uTwist2": 1.0},
    "julia":      {"uJZoom": 1.4, "uJC": 1.0},
    "organic":    {"uFeed": 0.0545, "uKill": 0.062, "rd_rate": 1800, "uWarp": 0.5, "rd_warm": 0, "uPaintTint": 0.7},
    "blackhole":  {"uHoleR": [[0, 0.0], [5, 0.14]], "uSpin": 1.6, "uSpaghetti": 0.5, "uDisk": 1.0},
    "particles":  {"uFlow": 0.3, "uDrag": 0.7, "uCollapse": 0.0, "burst": 2.0, "focus": 0.55,
                   "uAperture": 1.3, "uBright": 0.45, "uNebula": 0.0, "uCamDist": 4.0},
}
CRACK, PEEL, IRIS, TEAR, PEEL_NEAR = 0, 1, 2, 3, 4


def S(n, painting, mode, var=0, *, world=None, reveal=None, style=CRACK, hud=(), hudcol=None, space=None,
      spacemix=0.0, text=None, fx=None, relief=None, micro=1.0, breath=False, portal="focus", tr="portal",
      after=None, p=None, post=None, layers=None):
    """One blueprint scene. after = layer stacked on top of the painting (e.g. blackhole lensing it)."""
    return dict(n=n, painting=painting, mode=mode, var=var, world=world, reveal=reveal, style=style, hud=list(hud),
                hudcol=hudcol, space=space, spacemix=spacemix, text=text, fx=fx, relief=relief, micro=micro,
                breath=breath, portal=portal, tr=tr, after=after, p=p or {}, post=post or {}, layers=layers)


CYAN, GOLD, RED, GREEN, WHITE = [0.35, 0.9, 1.0], [1.0, 0.78, 0.35], [1.0, 0.25, 0.2], [0.4, 1.0, 0.55], [0.9, 0.9, 1.0]
# (start, end, music section) — scene slots inside are spread evenly and snapped to note onsets
SECTIONS = [(0.0, 65.0, "toccata+satie"), (65.0, 125.0, "fugue"), (125.0, 180.0, "danse"),
            (180.0, 255.0, "baldmountain"), (255.0, 300.0, "reverie")]

SCENES = [
    # ── I. order collapses, hypnotic entrance (Toccata → Gnossienne)
    [S(1, "adam", 0, 0, world="cathedral", reveal=[[0, 0], [2.2, 0], [4.2, 0.55]], hud=[1], hudcol=GOLD,
       relief=[[0, 0.0], [1.2, 0.3], [4.5, 1.6]], micro=[[0, 0.0], [1.0, 1.0]]),
     S(2, "carceri", 0, 0, world="dive", reveal=[[0, 0], [2.6, 0], [4.4, 1.0]], style=IRIS, hud=[2], hudcol=GOLD,
       relief=[[0, 0.4], [4, 1.5]]),
     S(3, "athens", 4, 0, hud=[7], hudcol=GOLD, fx=[[0, 0], [1.4, 0.1], [4.6, 1.2]]),
     S(4, "pearl", 2, 1, hud=[10], hudcol=WHITE),
     S(5, "narcissus", 2, 2, hud=[3], hudcol=CYAN, text="[ NARCISSISM: 99% ]"),
     S(6, "kircher", 1, 0, hud=[8], hudcol=GOLD),
     S(7, "magdalene", 0, 0, hud=[7], hudcol=GOLD, relief=[[0, 0.2], [4, 1.2]]),
     S(8, "drapery", 2, 0, hud=[6], hudcol=GOLD, p={"uPalPaint": 0.3}),
     S(9, "wanderer", 0, 0, reveal=[[0, 0], [1.0, 0], [4.0, 0.75]], style=PEEL_NEAR, space="space_carina", breath=True),
     S(10, "ancient", 1, 2, hud=[4], hudcol=GOLD),
     S(11, "jatte", 4, 2, hud=[11], hudcol=WHITE),
     S(12, "voynich", 3, 0, hud=[13], hudcol=GREEN, text="[ DECRYPTION FAILED // 0x00 ]"),
     S(13, "ambassadors", 0, 2, breath=True, fx=[[0, 0.0], [1.0, 0.4], [3.0, 1.0]])],
    # ── II. geometry grows and copies itself (Fugue)
    [S(14, "babel", 0, 0, world="mandelbox", reveal=[[0, 0], [1.5, 0], [3.8, 1.0]], hud=[2], hudcol=CYAN, tr="zoom"),
     S(15, "vitruvian", 1, 0, hud=[3], hudcol=GOLD),
     S(16, "tulp", 1, 1, hud=[3], hudcol=CYAN, text="[ SCAN 400x ]"),
     S(17, "cellarius", 2, 3, hud=[11], hudcol=GOLD, space="space_udf", spacemix=0.8),
     S(18, "melencolia", 0, 0, world="kifs", reveal=[[0, 0], [2.0, 0], [4.0, 0.9]], style=IRIS, hud=[14], hudcol=GOLD),
     S(19, "sanromano", 1, 2, hud=[5], hudcol=RED),
     S(20, "mandala", 1, 0, hud=[9], hudcol=GOLD, breath=True),
     S(21, "arnolfini", 0, 2, hud=[3], hudcol=CYAN),
     S(22, "fludd", 2, 4, hud=[6], hudcol=WHITE),
     S(23, "redfuji", 0, 1, hud=[2], hudcol=CYAN, text="[ ELEV 3776 m // SLICE 36 ]"),
     S(24, "odalisque", 1, 3, world="mandelbulb", reveal=[[0, 0], [3.0, 0], [4.6, 0.5]], hud=[1], hudcol=GOLD),
     S(25, "vesalius", 3, 3, hud=[13], hudcol=GREEN, breath=True)],
    # ── III. flesh mutates: uncanny life (Danse macabre)
    [S(26, "garden", 0, 0, world="organic", reveal=[[0, 0], [0.6, 0], [3.0, 1.0]], style=PEEL, tr="none",
       relief=0.0, micro=0.5),
     S(27, "haeckel", 3, 4, space="space_orion", spacemix=0.4),
     S(28, "winter", 0, 0, world="organic", reveal=[[0, 0], [1.2, 0], [3.5, 0.8]], style=PEEL,
       p={"uFeed": 0.039, "uKill": 0.058}),
     S(29, "saturn", 3, 1, hud=[3], hudcol=RED),
     S(30, "medusa", 2, 3, reveal=[[0, 0], [1.0, 0.0], [4.0, 0.35]], hud=[6], hudcol=GREEN),
     S(31, "rebels", 3, 2, breath=True),
     S(32, "nightmare", 2, 5, hud=[12], hudcol=CYAN),
     S(33, "cyclops", 4, 0, reveal=[[0, 0], [2.6, 0], [4.6, 0.8]], style=IRIS, space="space_orion"),
     S(34, "oiwa", 2, 4, hud=[13], hudcol=RED),
     S(35, "damned", 2, 5, fx=[[0, 0], [0.8, 0.3], [4.5, 1.4]]),
     S(36, "voynich2", 3, 0, text="[ OVERLOAD IN 3..2..1.. ]", portal="center", breath=True,
       fx=[[0, 0.2], [3.0, 1.0], [5.0, 1.6]])],
    # ── IV. divine overload, dimensional collapse (Night on Bald Mountain)
    [S(37, "judgment", 4, 1, after="blackhole", tr="cut", fx=[[0, 0.6], [1.0, 1.0], [5, 1.5]],
       p={"uHoleR": [[0, 0.02], [5, 0.16]]}),
     S(38, "wrath", 2, 0, fx=[[0, 0.3], [2, 1.3]]),
     S(39, "snowstorm", 2, 3, space="space_orion", spacemix=0.7, fx=[[0, 0.3], [4, 1.8]]),
     S(40, "starry", 0, 3, fx=[[0, 0.3], [2, 1.0]]),
     S(41, "empyrean", 1, 0, world="mandelbulb", reveal=[[0, 0], [2.0, 0], [4.0, 1.0]], style=IRIS, hud=[9], hudcol=GOLD),
     S(42, "wave", 4, 0, text="[ VRAM: 99.9% CRITICAL ]"),
     S(43, "ascent", 0, 3, post={"ca": 1.2}, fx=[[0, 0.5], [3, 1.0]]),
     S(44, "kiss", 1, 0, breath=True, hud=[1], hudcol=GOLD),
     S(45, "ninthwave", 2, 0, hud=[6], hudcol=GOLD),
     S(46, "comp8", 0, 0, hud=[10], hudcol=WHITE, relief=[[0, 0.3], [4, 1.8]]),
     S(47, "liberty", 1, 0, fx=[[0, 0.2], [2, 1.2]]),
     S(48, "crows", 4, 3, fx=[[0, 0.1], [4.5, 1.6]]),
     S(49, "flammarion", 0, 0, reveal=[[0, 0], [1.2, 0], [4.0, 0.9]], style=TEAR, space="space_pillars",
       hud=[13], hudcol=GREEN),
     S(50, "adam", 4, 4, portal="center", fx=[[0, 0.0], [4.0, 0.85], [4.9, 1.0]], p={"uPalPaint": 0.0}),
     S(51, "cmb", 4, 5, tr="crossfade", portal="center", micro=0.0, fx=[[0, 0.0], [1.5, 0.6], [5, 1.0]])],
    # ── V. stardust reborn, perfect loop (Rêverie)
    [S(52, "lilies", 2, 1, tr="crossfade", micro=0.4, fx=[[0, 0.0], [2, 0.5]], layers="dust"),
     S(53, "dnieper", 0, 0, p={"uPaintGain": 1.7}, micro=0.4, relief=[[0, 0.2], [5, 0.7]], fx=[[0, 0.0], [3, 0.2]]),
     S(54, "ophelia", 2, 0, micro=0.4, fx=[[0, 0.0], [3, 0.45]], layers="dust"),
     S(55, "serpents", 2, 0, micro=0.4, fx=[[0, 0.0], [3, 0.5]], hud=[11], hudcol=GOLD),
     S(56, "almond", 0, 0, micro=0.4, fx=[[0, 0.0], [4, 0.3]], relief=[[0, 0.2], [5, 1.0]]),
     S(57, "etoiles", 4, 1, micro=0.3, fx=[[0, 0.3], [4, 0.0]], text="[ DREAM SEQUENCE COMPLETE ]", hud=[3], hudcol=CYAN),
     S(58, "sunrise", 2, 1, micro=0.3, fx=[[0, 0.0], [3, 0.4]]),
     S(59, "sistine", 0, 0, micro=0.2, relief=[[0, 1.0], [4.2, 0.0]], fx=[[0, 0.4], [4.0, 0.0]]),
     S(60, "adam", 0, 0, micro=0.0, fx=0.0, relief=0.0, p={"uKB": 0.0})],
]


def snap(t, onsets):
    if onsets is None or len(onsets) == 0:
        return t
    i = int(np.argmin(np.abs(onsets - t)))
    return float(onsets[i]) if abs(onsets[i] - t) <= SNAP else t


def env(dur, *keys):
    """Keyframes given against a nominal 5 s slot, rescaled to the real slot length."""
    return [[round(min(t, 5.0) * dur / 5.0, 3), v] for t, v in keys]


def scale(curve, dur):
    if isinstance(curve, (int, float)):
        return curve
    return env(dur, *curve)


def build():
    tl = json.loads((HERE / "timeline.json").read_text())
    feats = ROOT / "analysis/features.npz"
    onsets = np.load(feats)["note_times"] if feats.exists() else None
    chapters, titles = [], []
    for (a, b, _), scenes in zip(SECTIONS, SCENES):
        n = len(scenes)
        bounds = [a] + [snap(a + k * (b - a) / n, onsets) for k in range(1, n)] + [b]
        for k, s in enumerate(scenes):
            start, end = bounds[k], bounds[k + 1]
            dur = end - start
            params = {"uPMode": s["mode"], "uPVar": s["var"], "uKB": 1.0, "uPaintGain": 1.0, "uPalPaint": 0.75,
                      "uFx": scale(s["fx"], dur) if s["fx"] is not None else env(dur, (0, 0.0), (0.9, 0.15), (2.0, 1.0)),
                      "uRelief": scale(s["relief"], dur) if s["relief"] is not None else env(dur, (0, 0.0), (1, 0.3), (3, 1.2)),
                      "uMicro": scale(s["micro"], dur), "uReveal": 0.0, "uRevealStyle": s["style"],
                      "uSpaceMix": s["spacemix"]}
            if s["breath"]:      # ~1.5 s of stillness before the next push
                params["uMicro"] = env(dur, (0, 1.0), (3.2, 1.0), (3.8, 0.0))
                params["uFx"] = env(dur, (0, 0.0), (0.9, 0.15), (2.0, 1.0), (3.4, 1.0), (4.6, 0.25))
            layers = []
            if s["world"]:
                layers.append({"scene": s["world"], "weight": 0.0})
                params.update(WORLD[s["world"]])
            if s["reveal"] is not None:
                params["uReveal"] = scale(s["reveal"], dur)
            layers.append({"scene": "painting", **({"input": True} if s["world"] else {})})
            if s["after"]:
                layers.append({"scene": s["after"], "input": True})
                params.update(WORLD[s["after"]])
            if s["layers"] == "dust":
                layers.append({"scene": "particles", "weight": env(dur, (0, 0.0), (1.5, 0.35), (4.5, 0.35), (5, 0.0))})
                params.update(WORLD["particles"])
            params.update(s["p"])
            if s["tr"] == "portal":
                tr = {"type": "portal", "length": PORTAL, "pre": 1.0}
            elif s["tr"] == "crossfade":
                tr = {"type": "crossfade", "length": 1.2, "pre": 0.5}
            elif s["tr"] == "zoom":
                tr = {"type": "zoom", "length": 1.0, "pre": 0.5}
            else:
                tr = {"type": s["tr"]}
            if k == 0 and a == 0.0:
                tr = {"type": "none"}
            ch = {"id": f"S{s['n']:02d}_{s['painting']}", "start": round(start, 3), "end": round(end, 3),
                  "painting": s["painting"], "transition": tr, "layers": layers, "palette": "gold",
                  "params": params, "portal": s["portal"],
                  "post": {"bloom": 0.18, "sat": 1.3, "teal": 0.5, "grain": 0.35, **s["post"]}}
            if s["space"]:
                ch["space"] = s["space"]
            if s["mode"] == 4 and s["var"] == 4:
                ch["atlas"] = True
            if s["hud"]:
                ch["hud"] = {"types": s["hud"], "color": s["hudcol"] or CYAN,
                             "alpha": env(dur, (0, 0.0), (0.7, 0.0), (1.2, 0.9), (4.2, 0.9), (4.8, 0.0))}
            chapters.append(ch)
            if s["text"]:
                titles.append({"text": s["text"], "start": round(start + 1.1 * dur / 5, 3), "end": round(start + 3.9 * dur / 5, 3),
                               "x": 0.06, "y": 0.12, "size": 0.022, "box": True, "fade": 0.06, "blink": 2.0 if "CRITICAL" in s["text"] or "OVERLOAD" in s["text"] else 0,
                               "font": "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf", "tracking": 0.04,
                               "color": [int(255 * c) for c in (RED if any(w in s["text"] for w in ("CRITICAL", "OVERLOAD", "FAILED")) else s["hudcol"] or CYAN)]})
    titles.insert(0, {"text": "MASTERPIECES REWRITTEN BY MATH & FREQUENCY", "start": 0.25, "end": 1.85,
                      "y": 0.87, "size": 0.026, "fade": 0.2})
    titles.append({"text": "[ FATAL ERROR: BIOLOGY OVERFLOW ]  fold_space() — core dumped", "start": 124.6, "end": 125.48,
                   "y": 0.5, "size": 0.026, "font": "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf",
                   "color": [255, 70, 60], "tracking": 0.02, "fade": 0.03, "box": True})
    tl["chapters"] = chapters
    tl["titles"] = titles
    tl["palettes"] = PALETTES
    tl["glitches"] = [{"start": 125.0, "dur": 0.5, "freeze": True, "tear": 1.0}]
    tl["master"] = [[0, 1.0], [249.8, 1.0], [250.3, 0.15], [251.2, 0.15], [251.8, 1.0], [300, 1.0]]
    tl["intensity"] = [[0, 0.8], [15, 0.9], [16, 0.3], [65, 0.4], [124, 0.85], [126, 0.5], [180, 0.8], [245, 1.0], [250, 0.2], [300, 0.3]]
    tl["speed"] = [[0, 0.3], [5, 2.0], [10, 6.0], [14.5, 8.0], [15.2, 0.6], [64.5, 0.6], [65.5, 0.8],
                   [95, 1.6], [124, 3.8], [125, 0.0], [125.5, 0.8], [249, 3.0], [250, 0.2], [300, 0.2]]
    (HERE / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    lens = np.diff([c["start"] for c in chapters] + [300.0])
    print(f"{len(chapters)} scenes, median {np.median(lens):.2f}s, longest {lens.max():.2f}s, shortest {lens.min():.2f}s")
    missing = [c["painting"] for c in chapters if not (ROOT / "assets/paintings" / f"{c['painting']}.png").exists()]
    if missing:
        print("paintings not on disk yet:", ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    build()
