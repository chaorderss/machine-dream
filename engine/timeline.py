"""Director timeline: chapters, layers, transitions, keyframed params, titles, glitches.

All times in config/timeline.json are seconds. Chapter params are keyframed in
chapter-local seconds: either a constant or [[t, value], ...] (linear interpolation).
"""
import json
import math
from pathlib import Path

import numpy as np

TRANSITIONS = {"none": 0, "cut": 0, "crossfade": 1, "dissolve": 2, "iris": 3, "zoom": 4, "portal": 5, "match": 6, "whip": 7, "morph": 8,
               # v9 library (shaders/composite.glsl); each takes "var" (0..1) and "ang" (radians) from the transition spec
               "wipe": 9, "push": 10, "barn": 11, "blinds": 12, "tiles": 13, "pixelate": 14, "clock": 15, "shatter": 16,
               "luma": 17, "ripple": 18, "glitch": 19, "spiral": 20, "shape": 21, "scan": 22, "burn": 23, "twirl": 24,
               "film": 25, "flip": 26, "cube": 27, "dip": 28, "slit": 29, "kaleido": 30, "melt": 31, "zoomblur": 32,
               "static": 33, "halftone": 34, "hex": 35, "spin": 36, "quad": 37, "slices": 38, "brush": 39, "leak": 40,
               "rgb": 41, "focus": 42,
               # v12: the five algorithmic families + the pupil of the eye
               "collapse": 43, "split": 44, "sort": 45, "latent": 46, "fracture": 47, "pupil": 48,
               # v13
               "light": 49}
POST_DEFAULTS = dict(exposure=1.0, bloom=0.12, ca=0.0, grain=0.4, vignette=0.35, grade=1.0, sat=1.35, hue=0.0, invert=1.0, teal=0.0)


class Curve:
    def __init__(self, spec):
        if isinstance(spec, (int, float)):
            spec = [[0.0, spec]]
        self.vector = isinstance(spec[0][1], (list, tuple))
        self.xs = np.array([k[0] for k in spec], float)
        self.vs = np.array([k[1] if self.vector else [k[1]] for k in spec], float)

    def __call__(self, x):
        out = tuple(float(np.interp(x, self.xs, self.vs[:, i])) for i in range(self.vs.shape[1]))
        return out if self.vector else out[0]


class Layer:
    def __init__(self, d):
        self.scene = d["scene"]
        self.weight = Curve(d.get("weight", 1.0))
        self.input = bool(d.get("input", False))   # receives previous layer as uInput instead of summing it


class Chapter:
    def __init__(self, d, tl, index):
        self.index = index
        self.id = d["id"]
        self.title = d.get("title", self.id)
        self.start = float(d["start"])
        self.end = float(d["end"])
        self.layers = [Layer(L) for L in d["layers"]]
        tr = d.get("transition", {})
        self.tr_type = tr.get("type", "crossfade")
        self.tr_len = float(tr.get("length", 0.0)) if self.tr_type not in ("none", "cut") else 0.0
        self.tr_pre = float(tr.get("pre", 0.5))
        self.tr_var = float(tr.get("var", 0.0))
        self.tr_ang = float(tr.get("ang", 0.0))
        self.tr_c = tuple(tr.get("c", (0.5, 0.5)))          # top-down screen uv
        self.palette = np.array(tl.palettes[d.get("palette", "default")], float)
        # optional palette morph: "palette_from" → "palette" along the "palette_blend" curve
        self.palette_from = np.array(tl.palettes[d["palette_from"]], float) if "palette_from" in d else None
        self.palette_blend = Curve(d.get("palette_blend", 1.0))
        self.params = {k: Curve(v) for k, v in d.get("params", {}).items()}
        post = d.get("post", {})
        self.post = {k: Curve(post.get(k, v)) for k, v in POST_DEFAULTS.items()}
        self.sim = d.get("sim", {})                  # python-side scene options (rd warm steps, ...)
        self.painting = d.get("painting")             # assets/paintings/<id>.png anchors this chapter
        self.erase = float(d.get("erase", 1.0))       # how much of the memory loss reaches this shot (0: Adam is kept)
        self.space = d.get("space")                   # deep-space image for reveals / overlays
        self.portal = d.get("portal", "focus")        # "focus", "center" or [x, y] screen uv to dive into
        self.atlas = bool(d.get("atlas", False))      # needs the all-paintings atlas (hyper-montage)
        hud = d.get("hud", {})
        self.hud_types = (list(hud.get("types", [])) + [0, 0])[:2]
        self.hud_alpha = Curve(hud.get("alpha", 1.0 if hud.get("types") else 0.0))
        self.hud_color = tuple(hud.get("color", [0.35, 0.9, 1.0]))
        # framing override (close-ups / jump cuts): painting uv point "c" (top-down), zoom over cover-fit "z",
        # optional drift [dx, dy] of the centre across the shot
        fr = d.get("frame")
        self.frame = None if fr is None else {"c": tuple(fr["c"]), "z": Curve(fr.get("z", 1.0)),
                                              "drift": tuple(fr.get("drift", (0.0, 0.0)))}
        # split screen / polyptych / superimposition: sub-chapters drawn into screen rects over this chapter
        self.panels = []
        for k, pd in enumerate(d.get("panels", [])):
            spec = {"layers": [{"scene": "painting"}], "palette": d.get("palette", "default"), "post": post,
                    **pd["chapter"], "id": f"{self.id}/p{k}", "start": self.start, "end": self.end}
            sub = Chapter(spec, tl, 1000 + index * 16 + k)
            sub.rect = tuple(pd.get("rect", (0.0, 0.0, 1.0, 1.0)))   # top-down screen uv x0, y0, x1, y1
            sub.alpha = Curve(pd.get("alpha", 1.0))
            sub.blend = {"over": 0, "screen": 1}[pd.get("blend", "over")]
            sub.border = float(pd.get("border", 1.0 if pd.get("blend", "over") == "over" else 0.0))
            self.panels.append(sub)

    def uniforms(self, t):
        lt = t - self.start
        dur = max(self.end - self.start, 1e-6)
        pal = self.palette
        if self.palette_from is not None:
            pal = self.palette_from + (pal - self.palette_from) * self.palette_blend(lt)
        u = {
            "uLocal": lt,
            "uProgress": min(max(lt / dur, 0.0), 1.0),
            "uPalA": tuple(pal[0]), "uPalB": tuple(pal[1]), "uPalC": tuple(pal[2]), "uPalD": tuple(pal[3]),
        }
        for k, c in self.params.items():
            u[k] = c(lt)
        return u

    def hud_values(self, t):
        """→ (type 0, type 1, alpha, colour) for the HUD / occult line-art overlay (see shaders/hud.glsl)."""
        return float(self.hud_types[0]), float(self.hud_types[1]), self.hud_alpha(t - self.start), self.hud_color

    def post_values(self, t):
        return {k: c(t - self.start) for k, c in self.post.items()}


class Timeline:
    def __init__(self, path):
        path = Path(path)
        self.root = path.resolve().parent.parent
        d = json.loads(path.read_text())
        self.data = d
        self.title = d.get("title", "")
        self.duration = float(d["duration"])
        self.audio = d.get("audio")
        self.features = d.get("features")
        self.palettes = d["palettes"]
        self.chapters = [Chapter(c, self, i) for i, c in enumerate(d["chapters"])]
        self.intensity = Curve(d.get("intensity", 0.5))
        self.master = Curve(d.get("master", 1.0))
        self.titles = d.get("titles", [])
        self.glitches = d.get("glitches", [])
        self.memory = Curve(d["memory"]) if "memory" in d else None   # 1 → 0: what the machine still has
        # inserts: short shots that hard-cut over whatever is playing (flash-forwards, memories, Kuleshov eyes)
        self.inserts = [Chapter(c, self, 100000 + i) for i, c in enumerate(d.get("inserts", []))]
        # IRIS-01 robot probe: pos [x, y (top-down screen uv), radius, alpha], look [lx, ly], state [r, g, b, glow, crack, vein]
        pr = d.get("probe")
        self.probe = None if not pr else {k: Curve(pr[k]) for k in ("pos", "look", "state")}
        if pr:
            self.probe["spark"] = bool(pr.get("spark", False))   # draw only a point of light, no robot
        # machine-vision mosaic over the whole frame (shaders/mosaic.glsl): curves in seconds
        mo = d.get("mosaic")
        self.mosaic = None if not mo else {k: Curve(mo.get(k, v)) for k, v in
                                           (("amt", 0.0), ("cell", 0.02), ("shape", 0.0), ("gap", 0.0), ("quant", 0.0),
                                            ("fovea", 0.0), ("flowl", 0.0), ("flowc", 0.0), ("flows", 1.0),
                                            ("flowk", 2.0), ("mask", [[0.0, [0.0, 0.0, 1.0, 1.0]]]),
                                            ("outside", 1.0), ("crystal", 0.0), ("maskcrystal", 0.0))}
        # camera travel = integral of the speed curve, precomputed for exact, fps-independent motion
        speed = Curve(d.get("speed", 1.0))
        self._grid = np.arange(0.0, self.duration + 5.0, 0.005)
        v = np.array([speed(x) for x in self._grid])
        self._travel = np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) * 0.5 * 0.005)])

    def travel(self, t):
        return float(np.interp(t, self._grid, self._travel))

    def in_insert(self, t):
        return any(i.start <= t < i.end for i in self.inserts)

    def chapter_at(self, t):
        cur = self.chapters[0]
        for c in self.chapters:
            if c.start <= t:
                cur = c
        return cur

    def state(self, t):
        """→ (outgoing chapter or None, incoming chapter, mix 0..1, transition type id)."""
        for ins in self.inserts:
            if ins.start <= t < ins.end:
                return None, ins, 1.0, 0
        for j in range(1, len(self.chapters)):
            c = self.chapters[j]
            if c.tr_len > 0:
                w0 = c.start - c.tr_len * c.tr_pre
                if w0 <= t < w0 + c.tr_len:
                    return self.chapters[j - 1], c, (t - w0) / c.tr_len, TRANSITIONS[c.tr_type]
        return None, self.chapter_at(t), 1.0, 0

    def glitch_at(self, t):
        """→ (freeze, tear 0..1). Freeze holds the last frame; tear rips it."""
        for g in self.glitches:
            if g["start"] <= t < g["start"] + g["dur"]:
                x = (t - g["start"]) / g["dur"]
                return g.get("freeze", True), g.get("tear", 1.0) * math.sin(math.pi * min(1.0, x * 1.3)) ** 0.5
        return False, 0.0

    def preroll_start(self, t0, stateful, cap=60.0):
        """Earliest time we must start simulating so stateful scenes look right at t0."""
        _, ch, _, _ = self.state(t0)
        if ch.index >= len(self.chapters):          # an insert: preroll what plays underneath it
            ch = self.chapter_at(t0)
        i = ch.index
        names = {L.scene for L in ch.layers} & stateful
        while i > 0 and names & {L.scene for L in self.chapters[i - 1].layers}:
            i -= 1
        c = self.chapters[i]
        start = c.start - c.tr_len * c.tr_pre - 0.25
        if not names:
            start = t0 - 2.0                       # feedback-only scenes settle fast
        return max(0.0, start, t0 - cap)
