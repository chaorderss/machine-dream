#!/usr/bin/env python3
"""Generate config/timeline.json: "Inside a Machine Dream" as a story in five acts plus a flash-forward prologue.

Protagonist IRIS-01, a small chrome robot probe with one glowing lens (the machine's eye), flies through every
painting: it enters, looks at the subject, and dives into the portal point; the camera follows it through.
Each act has its own montage grammar and its own music track (config/mix_cc.json), cut on that track's bars:

  PROLOGUE  0-15     flash-forward teaser: beat cuts of what is coming, starts/ends on the spark between Adam's fingers
  I   GENESIS        the probe powers on and learns to see: long takes, portals, match cuts, a memento mori
  II  LEARNING       it devours human knowledge: metric montage on bars, triptychs, circle cross-cutting, Babel crash
  III CORRUPTION     the dream rots: waltz jump cuts, Kuleshov (its lens reflecting Saturn), diptych, double exposure
  IV  OVERLOAD       divine overload: accelerating cuts (4 bars → 1/2 bar), quad split, flash-back memories, collapse
  V   AWAKENING      reborn: long dissolves; it floats into the gap between the fingers and becomes the spark (loop)

The previous 60 x 5 s blueprint is kept in config/build_timeline_60scenes.py.

  .venv/bin/python config/build_timeline.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from engine.renderer import painting_view  # noqa: E402
from engine.timeline import Curve  # noqa: E402

ASPECT = 16 / 9
CAT = json.loads((ROOT / "assets/paintings/catalog.json").read_text())
PORTAL = 0.8

PALETTES = {
    "gold":  [[0.55, 0.40, 0.20], [0.45, 0.35, 0.20], [1.0, 1.0, 1.0], [0.00, 0.10, 0.25]],
    "neon":  [[0.50, 0.50, 0.50], [0.50, 0.50, 0.50], [1.0, 1.0, 1.0], [0.00, 0.33, 0.67]],
    "blood": [[0.50, 0.20, 0.20], [0.50, 0.25, 0.20], [1.0, 1.0, 1.0], [0.00, 0.05, 0.10]],
}
# math worlds / layers; keyframes are [[fraction of shot, value], ...]
WORLD = {
    "mandelbox":  {"uIters": 8, "uScaleMB": -2.6, "uFoldStep": 0.04},
    "mandelbulb": {"uPower": 8.0, "uMBDist": 2.4},
    "kifs":       {"uKA": 1.1, "uKB": 0.4},
    "organic":    {"uFeed": 0.0545, "uKill": 0.062, "rd_rate": 1800, "uWarp": 0.5, "rd_warm": 0, "uPaintTint": 0.7},
    "blackhole":  {"uHoleR": [[0, 0.0], [1, 0.14]], "uSpin": 1.6, "uSpaghetti": 0.5, "uDisk": 1.0},
    "particles":  {"uFlow": 0.3, "uDrag": 0.7, "uCollapse": 0.0, "burst": 2.0, "focus": 0.55,
                   "uAperture": 1.3, "uBright": 0.45, "uNebula": 0.0, "uCamDist": 4.0},
}
CRACK, PEEL, IRIS, TEAR, PEEL_NEAR = 0, 1, 2, 3, 4
CYAN, GOLD, RED, GREEN, WHITE = [0.35, 0.9, 1.0], [1.0, 0.78, 0.35], [1.0, 0.25, 0.2], [0.4, 1.0, 0.55], [0.9, 0.9, 1.0]
MONO = "/usr/share/fonts/dejavu-sans-mono-fonts/DejaVuSansMono.ttf"
SERIF = "/usr/share/fonts/google-noto-serif-cjk-vf-fonts/NotoSerifCJK-VF.ttc"   # index 2 = SC

# subject points in painting uv (top-down), read off gridded crops
PT = {"fingers": (0.385, 0.455), "god": (0.567, 0.22), "pearl_eye": (0.341, 0.374), "pearl_face": (0.39, 0.40),
      "medusa_eye": (0.489, 0.41), "medusa_face": (0.53, 0.47), "saturn_eye": (0.325, 0.19), "cyclops_eye": (0.335, 0.236),
      "narcissus": (0.30, 0.30), "oiwa_eye": (0.63, 0.49), "mirror": (0.49, 0.285), "skull": (0.57, 0.78)}

# per act: grade, probe radius, probe state at act start → end (iris rgb, glow, crack, vein)
ACT = {
    "P":   dict(post={"bloom": 0.18, "sat": 1.3, "teal": 0.5, "grain": 0.35}, R=0.05),
    "I":   dict(post={"bloom": 0.16, "sat": 1.05, "teal": 0.7, "grain": 0.45, "vignette": 0.45}, R=0.045,
                state=([0.55, 0.9, 1.0, 1.0, 0.0, 0.0], [0.55, 0.9, 1.0, 1.0, 0.0, 0.0])),
    "II":  dict(post={"bloom": 0.18, "sat": 1.25, "teal": 0.55, "grain": 0.35, "ca": 0.25}, R=0.04,
                state=([0.3, 0.95, 1.0, 1.15, 0.0, 0.0], [0.3, 0.95, 1.0, 1.4, 0.05, 0.0])),
    "III": dict(post={"bloom": 0.2, "sat": 1.4, "teal": 0.15, "grain": 0.5, "vignette": 0.55}, R=0.05,
                state=([1.0, 0.25, 0.12, 1.0, 0.0, 0.25], [1.0, 0.1, 0.06, 1.2, 0.15, 1.0])),
    "IV":  dict(post={"bloom": 0.28, "sat": 1.5, "teal": 0.3, "grain": 0.35}, R=0.055,
                state=([1.0, 0.55, 0.15, 1.3, 0.3, 0.3], [1.0, 0.7, 0.3, 1.8, 1.0, 0.0])),
    "V":   dict(post={"bloom": 0.24, "sat": 1.15, "teal": 0.2, "grain": 0.28, "vignette": 0.3}, R=0.04,
                state=([1.0, 0.85, 0.6, 0.9, 0.0, 0.0], [1.0, 0.85, 0.6, 1.0, 0.0, 0.0])),
}
SPARK = [1.0, 0.85, 0.6, 1.0, 0.0, 0.0]
ACT_SPAN = {"P": (0.0, 15.0), "I": (15.0, 65.0), "II": (65.0, 125.0), "III": (125.0, 180.3), "IV": (180.3, 251.3),
            "V": (251.3, 300.0)}


def bars(t0, bpm, per_bar):
    """Bar grid of an act's track in mix time."""
    L = 60.0 / bpm * per_bar
    return lambda n: round(t0 + n * L, 3)


B2 = bars(65.0, 143.6, 4)          # Nightmare Machine
B3 = bars(125.57, 198.8, 3)        # Waltz of the Carnies (3/4)
B4 = bars(180.3, 112.3, 4)         # Final Battle of the Dark Wizards


def ECU(c, z0, z1=None, drift=(0.0, 0.0)):
    """Framing on a subject point: zoom z0 → z1 over cover-fit, optional drift of the centre (painting uv)."""
    return {"c": c, "z": [[0, z0], [1, z0 if z1 is None else z1]], "drift": drift}


class Director:
    def __init__(self):
        self.shots, self.inserts, self.titles = [], [], []

    def shot(self, t, painting, mode=0, var=0, *, act, tr="cut", frame=None, fx=None, relief=None, micro=1.0, kb=1.0,
             world=None, reveal=None, style=CRACK, after=None, eye=None, dust=False, hud=(), hudcol=None, text=None,
             space=None, spacemix=0.0, panels=None, p=None, post=None, portal="focus", probe=None, palette="gold"):
        """One shot from time t to the next shot's t. tr = transition INTO this shot."""
        self.shots.append(dict(t=t, painting=painting, mode=mode, var=var, act=act, tr=tr, frame=frame, fx=fx,
                               relief=relief, micro=micro, kb=kb, world=world, reveal=reveal, style=style, after=after,
                               eye=eye, dust=dust, hud=list(hud), hudcol=hudcol, text=text, space=space,
                               spacemix=spacemix, panels=panels, p=p or {}, post=post or {}, portal=portal,
                               probe=probe or {}, palette=palette))

    def insert(self, t, painting, frames=3, frame=None, mode=0, var=0, fx=0.0):
        """Flash-forward / memory: a few frames hard-cut over whatever is playing."""
        self.inserts.append(dict(t=t, end=round(t + frames / 30.0, 4), painting=painting, frame=frame, mode=mode, var=var, fx=fx))

    def title(self, text, t0, t1, *, y=0.5, size=0.026, font=MONO, idx=0, color=(255, 255, 255), box=False,
              fade=0.08, tracking=0.04, blink=0, x=None, sub=None):
        d = {"text": text, "start": t0, "end": t1, "y": y, "size": size, "font": font, "font_index": idx,
             "color": list(color), "box": box, "fade": fade, "tracking": tracking, "blink": blink}
        if sub:                                    # second line under the first: (text, size, colour, tracking)
            d["sub"] = {"text": sub[0], "size": sub[1], "color": list(sub[2]), "tracking": sub[3]}
        if x is not None:
            d["x"] = x
        self.titles.append(d)


def frac(curve, dur):
    """[[fraction, v], ...] → [[seconds, v], ...]; constants pass through."""
    if isinstance(curve, (int, float)):
        return curve
    return [[round(f * dur, 3), v] for f, v in curve]


def frame_spec(fr, dur):
    if fr is None:
        return None
    c = PT[fr["c"]] if isinstance(fr["c"], str) else fr["c"]
    return {"c": list(c), "z": frac(fr.get("z", 1.0), dur), "drift": list(fr.get("drift", (0.0, 0.0)))}


def screen_point(painting, fr, kb, dur, f):
    """Subject / portal point on screen (top-down uv) at fraction f of the shot — same maths as the renderer."""
    if painting is None or painting not in CAT:
        return (0.5, 0.5)
    fobj = None if fr is None else {"c": tuple(fr["c"]), "z": Curve(fr["z"]), "drift": tuple(fr["drift"])}
    _, fs = painting_view(CAT[painting], kb, f, ASPECT, frame=fobj, lt=f * dur)
    return (min(max(fs[0], 0.06), 0.94), min(max(1.0 - fs[1], 0.08), 0.92))


def painting_params(s, dur):
    return {"uPMode": s["mode"], "uPVar": s["var"], "uKB": s["kb"], "uPaintGain": 1.0, "uPalPaint": 0.75,
            "uFx": frac(s["fx"], dur) if s["fx"] is not None else frac([[0, 0.0], [0.35, 0.1], [1, 0.4]], dur),
            "uRelief": frac(s["relief"], dur) if s["relief"] is not None else frac([[0, 0.0], [1, 0.6]], dur),
            "uMicro": frac(s["micro"], dur), "uReveal": 0.0, "uRevealStyle": s["style"], "uSpaceMix": s["spacemix"]}


TR = {"portal": ("portal", PORTAL, 1.0), "crossfade": ("crossfade", 1.2, 0.5), "dissolve": ("dissolve", 1.6, 0.5),
      "match": ("match", 0.6, 0.0), "whip": ("whip", 0.4, 0.5), "zoom": ("zoom", 1.0, 0.5),
      "cut": ("none", 0, 0), "none": ("none", 0, 0)}


def chapter(s, start, end, cid):
    dur = end - start
    params = painting_params(s, dur)
    if s["painting"] is None:                      # black card / split-screen backdrop: no effects drawn on black
        params.update(uFx=0.0, uRelief=0.0, uMicro=0.0)
    layers = []
    if s["world"]:
        layers.append({"scene": s["world"], "weight": 0.0})
        params.update({k: frac(v, dur) for k, v in WORLD[s["world"]].items()})
    if s["reveal"] is not None:
        params["uReveal"] = frac(s["reveal"], dur)
    layers.append({"scene": "painting", **({"input": True} if s["world"] else {})})
    if s["after"]:
        layers.append({"scene": s["after"], "input": True})
        params.update({k: frac(v, dur) for k, v in WORLD[s["after"]].items()})
    if s["eye"] is not None:                       # the probe's own lens, reflecting what it sees (Kuleshov)
        layers.append({"scene": "eye", "input": True})
        params["uZoom"] = frac(s["eye"], dur)
    if s["dust"]:
        layers.append({"scene": "particles", "weight": frac([[0, 0.0], [0.3, 0.35], [0.9, 0.35], [1, 0.0]], dur)})
        params.update(WORLD["particles"])
    params.update({k: frac(v, dur) for k, v in s["p"].items()})
    typ, length, pre = TR[s["tr"]]
    post = dict(ACT[s["act"]]["post"])
    post.update({k: frac(v, dur) for k, v in s["post"].items()})
    ch = {"id": cid, "start": round(start, 3), "end": round(end, 3), "painting": s["painting"],
          "transition": {"type": typ, "length": length, "pre": pre}, "layers": layers, "palette": s["palette"],
          "params": params, "portal": s["portal"], "post": post}
    fr = frame_spec(s["frame"], dur)
    if fr:
        ch["frame"] = fr
    if s["space"]:
        ch["space"] = s["space"]
    if s["mode"] == 4 and s["var"] == 4:
        ch["atlas"] = True
    if s["hud"]:
        ch["hud"] = {"types": s["hud"], "color": s["hudcol"] or CYAN,
                     "alpha": frac([[0, 0.0], [0.15, 0.0], [0.25, 0.85], [0.85, 0.85], [0.97, 0.0]], dur)}
    if s["panels"]:
        ch["panels"] = []
        for pn in s["panels"]:
            sp = dict(mode=pn.get("mode", 0), var=pn.get("var", 0), kb=pn.get("kb", 1.0), fx=pn.get("fx"),
                      relief=pn.get("relief", 0.3), micro=pn.get("micro", 1.0), style=CRACK, spacemix=0.0)
            sub = {"painting": pn["painting"], "palette": s["palette"], "params": painting_params(sp, dur)}
            pf = frame_spec(pn.get("frame"), dur)
            if pf:
                sub["frame"] = pf
            ch["panels"].append({"rect": pn["rect"], "alpha": frac(pn.get("alpha", 1.0), dur), "chapter": sub,
                                 "blend": pn.get("blend", "over")})
    return ch


def lerp(a, b, x):
    return [u + (v - u) * x for u, v in zip(a, b)]


def act_state(act, t):
    if "state" not in ACT[act]:
        return SPARK
    a, b = ACT_SPAN[act]
    s0, s1 = ACT[act]["state"]
    return lerp(s0, s1, min(max((t - a) / (b - a), 0.0), 1.0))


class ProbePath:
    """Keyframes for IRIS-01: pos [x, y (top-down screen uv), radius, alpha], look [lx, ly], state."""

    def __init__(self):
        self.pos, self.look, self.state = [], [], []
        self.last = (0.5, 0.5, 0.0, 0.0)

    @staticmethod
    def _add(lst, t, v):
        if lst and t <= lst[-1][0]:
            t = lst[-1][0] + 1e-3
        lst.append([round(t, 4), [round(float(x), 4) for x in v]])

    def at(self, t, x, y, r, a=1.0):
        self._add(self.pos, t, (x, y, r, a))
        self.last = (x, y, r, a)

    def gaze(self, t, frm, to):
        dx, dy = (to[0] - frm[0]) * ASPECT, -(to[1] - frm[1])
        n = math.hypot(dx, dy)
        self._add(self.look, t, (0.0, 0.0) if n < 1e-3 else (0.85 * dx / max(n, 0.25), 0.85 * dy / max(n, 0.25)))

    def camera(self, t):
        self._add(self.look, t, (0.0, 0.0))

    def st(self, t, v):
        self._add(self.state, t, v)


def hover_point(subj):
    """Beside the subject, towards the middle of the frame, a little above it."""
    x = subj[0] + (0.17 if subj[0] < 0.5 else -0.17)
    return (min(max(x, 0.12), 0.88), min(max(subj[1] - 0.08, 0.15), 0.8))


def plan_probe(D, chapters):
    P = ProbePath()
    n = len(D.shots)
    for i, s in enumerate(D.shots):
        ch = chapters[i]
        t0, t1 = ch["start"], ch["end"]
        dur = t1 - t0
        spec = s["probe"]
        R = ACT[s["act"]]["R"] * spec.get("scale", 1.0)
        fr = ch.get("frame")
        subj = spec.get("subject") or screen_point(s["painting"], fr, s["kb"], dur, 0.5)
        hov = spec.get("at") or hover_point(subj)
        P.st(t0, spec.get("state") or act_state(s["act"], t0))
        P.st(t1 - 0.002, spec.get("state") or act_state(s["act"], t1))
        nxt = D.shots[i + 1] if i + 1 < n else None
        exit_ = spec.get("exit", "auto")
        if exit_ == "auto":
            exit_ = "portal" if nxt is not None and nxt["tr"] == "portal" else "stay"
        enter = spec.get("enter", "auto")
        if enter == "auto":
            enter = "near" if s["tr"] == "portal" else "keep"
        if enter == "hide":
            P.at(t0, P.last[0], P.last[1], P.last[2], 0.0)
            P.at(t1 - 0.002, P.last[0], P.last[1], P.last[2], 0.0)
            continue
        if enter == "near":                         # it flies past the camera into the new world
            side = -1 if hov[0] > 0.5 else 1
            P.at(t0, 0.5 + 0.12 * side, 0.85, R * 6.0, 1.0)
            P.gaze(t0, (0.5, 0.85), hov)
            P.at(t0 + min(1.1, dur * 0.35), *hov, R)
        elif enter in ("left", "right", "top", "bottom"):
            x0 = {"left": (-0.06, hov[1]), "right": (1.06, hov[1]), "top": (hov[0], -0.08), "bottom": (hov[0], 1.08)}[enter]
            P.at(t0, *x0, R)
            P.gaze(t0, x0, hov)
            P.at(t0 + min(0.9, dur * 0.4), *hov, R)
        elif enter == "spark":                      # ignition: a point of light opens into the probe
            st = spec.get("spark_t", 0.0)
            P.at(t0, *hov, 0.0, 0.0)
            P.at(t0 + st, *hov, 0.004, 1.0)
            P.at(t0 + st + 0.8, *hov, R * 0.3, 1.0)
            P.at(t0 + st + 1.6, *hov, R, 1.0)
            P.camera(t0 + st + 1.0)
        elif enter == "keep":                       # same screen place across the cut (continuity)
            a0 = P.last[3]
            P.at(t0, P.last[0], P.last[1], P.last[2] if P.last[2] > 0 else R, 1.0 if a0 >= 0.5 else 0.0)
            if a0 < 0.5:
                P.at(t0 + 0.25, P.last[0], P.last[1], R, 1.0)
        for (f, x, y, *rr) in spec.get("path", []):  # waypoints (fraction of shot, x, y[, radius factor])
            P.at(t0 + f * dur, x, y, R * (rr[0] if rr else 1.0))
        if not spec.get("path"):
            P.at(t0 + dur * 0.7, *lerp(hov, subj, 0.12), R)
        if spec.get("look") == "camera":
            P.camera(t0 + dur * 0.3)
            P.camera(t0 + dur * 0.6)
        else:
            P.gaze(t0 + min(0.6, dur * 0.3), P.last[:2], subj)
        if exit_ == "portal":
            port = screen_point(s["painting"], fr, s["kb"], dur, (dur - 0.6) / dur) if s["portal"] == "focus" else (0.5, 0.5)
            tp = t1 - PORTAL
            P.at(tp - 0.05, *lerp(P.last[:2], port, 0.4), R)
            P.gaze(tp - 0.05, P.last[:2], port)
            P.at(t1 - 0.45, *port, R * 0.55)
            P.at(t1 - 0.12, *port, 0.0)
        elif exit_ in ("up", "down", "left", "right"):
            x1 = {"left": (-0.08, P.last[1]), "right": (1.08, P.last[1]), "up": (P.last[0], -0.1), "down": (P.last[0], 1.1)}[exit_]
            P.gaze(t1 - 0.6, P.last[:2], x1)
            P.at(t1 - 0.05, *x1, R)
        elif exit_ == "spark":                      # settle into the gap and become the spark
            gap = spec.get("gap", subj)
            P.at(t1 - dur * 0.45, *gap, R * 0.6)
            P.at(t1 - 0.5, *gap, 0.004)
            P.at(t1, *gap, 0.004)
        else:
            P.at(t1 - 0.01, *P.last[:2], P.last[2])
    return {"pos": P.pos, "look": P.look or [[0, [0, 0]]], "state": P.state}


def storyboard(D):
    sh, ins, ti = D.shot, D.insert, D.title
    CLEAN = dict(fx=0.0, relief=[[0, 0.0], [1, 0.4]])

    # ── PROLOGUE: flash-forward on the beat (Industrial Revolution, 2-beat cuts); frame 0 = the last frame
    b = 1.721
    sh(0.0, "adam", 0, 0, act="P", frame=ECU("fingers", 7.0, 9.0), fx=0.0, relief=0.0, micro=[[0, 0.0], [0.4, 1.0]],
       kb=0.0, probe={"enter": "path", "state": SPARK, "subject": (0.5, 0.5), "look": "camera",
                      "path": [(0.0, 0.5, 0.5, 0.08), (0.35, 0.5, 0.5, 0.15), (0.95, 0.72, 0.62, 1.0)]})
    sh(b, "saturn", 2, 5, act="P", frame=ECU("saturn_eye", 5.0, 6.5), fx=[[0, 0.1], [1, 0.6]],
       probe={"state": [1.0, 0.1, 0.06, 1.2, 0.1, 1.0]})
    sh(2 * b, "babel", 0, 0, act="P", world="mandelbox", reveal=[[0, 0.2], [1, 1.0]], fx=[[0, 0.3], [1, 1.2]],
       probe={"state": [0.3, 0.95, 1.0, 1.3, 0.0, 0.0]})
    sh(3 * b, "medusa", 4, 0, act="P", frame=ECU("medusa_face", 2.2, 2.8), fx=[[0, 0.0], [1, 0.9]], tr="whip",
       probe={"enter": "right", "state": [1.0, 0.1, 0.06, 1.0, 0.0, 0.8]})
    sh(4 * b, "judgment", 4, 1, act="P", after="blackhole", fx=[[0, 0.5], [1, 1.2]], p={"uHoleR": [[0, 0.03], [1, 0.12]]},
       probe={"state": [1.0, 0.6, 0.2, 1.6, 0.8, 0.0]})
    sh(5 * b, "wave", 2, 3, act="P", fx=[[0, 0.2], [1, 1.0]], tr="whip", probe={"enter": "right"})
    sh(6 * b, "cyclops", 0, 0, act="P", frame=ECU("cyclops_eye", 3.5, 5.0), eye=[[0, 1.0], [1, 0.7]],
       probe={"enter": "hide"})
    sh(7 * b, "pearl", 0, 0, act="P", frame=ECU("pearl_eye", 6.0), fx=0.0, probe={"enter": "hide"})
    sh(7.5 * b, "oiwa", 0, 0, act="P", frame=ECU("oiwa_eye", 5.0), fx=0.0, probe={"enter": "hide"})
    sh(8 * b, "adam", 0, 0, act="P", frame=ECU("fingers", 5.0, 9.0), fx=0.0, relief=0.0,
       probe={"enter": "near", "at": (0.5, 0.5), "subject": (0.5, 0.5), "state": SPARK, "exit": "spark", "gap": (0.5, 0.5)})
    ti("MASTERPIECES REWRITTEN BY MATH & FREQUENCY", 0.25, 1.85, y=0.87, size=0.026,
       font="/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-ExtraLight.ttf", fade=0.2, tracking=0.15)

    # ── I. GENESIS (Metaphysik, slow): it ignites in the dark and learns to see
    sh(14.95, None, act="I", probe={"enter": "spark", "spark_t": 2.0, "at": (0.5, 0.7), "subject": (0.5, 0.45),
                                    "look": "camera"})
    ti("INSIDE  A  MACHINE  DREAM", 15.4, 18.7, y=0.45, size=0.05, font=SERIF, idx=2, fade=0.7, tracking=0.12,
       sub=("I  ·  GENESIS   创 世", 0.024, (170, 220, 255), 0.3))
    sh(19.0, "adam", 0, 0, act="I", tr="crossfade", frame=ECU("fingers", 1.0, 1.9), **CLEAN, probe={"at": (0.62, 0.36)})
    sh(25.0, "pearl", 2, 1, act="I", tr="portal", frame=ECU("pearl_eye", 5.5, 1.4), fx=[[0, 0.0], [0.7, 0.0], [1, 0.25]],
       relief=0.0, hud=[3], hudcol=CYAN, text="[ FACE DETECTED // SHE IS LOOKING BACK ]")
    sh(31.0, "narcissus", 2, 2, act="I", tr="portal", frame=ECU("narcissus", 1.6, 1.9, drift=(0.0, 0.4)),
       fx=[[0, 0.0], [0.5, 0.2], [1, 0.8]], text="[ SELF-RECOGNITION: 12% ]", hudcol=CYAN,
       probe={"path": [(0.3, 0.42, 0.42), (0.85, 0.4, 0.66)]})
    sh(36.5, "ambassadors", 0, 0, act="I", tr="match", frame=ECU("skull", 1.0, 2.6), fx=0.0,
       relief=[[0, 0.0], [1, 1.0]], hud=[7], hudcol=GOLD, text="[ HIDDEN OBJECT: MEMENTO MORI ]")
    sh(42.0, "wanderer", 0, 0, act="I", tr="portal", reveal=[[0, 0], [0.25, 0], [0.85, 0.75]], style=PEEL_NEAR,
       space="space_carina", fx=0.0, micro=0.5, probe={"at": (0.62, 0.3)})
    sh(48.0, "athens", 4, 2, act="I", tr="portal", fx=[[0, 0.0], [0.6, 0.05], [1, 0.6]], hud=[7], hudcol=GOLD)
    sh(54.0, "sistine", 0, 0, act="I", tr="portal", fx=0.0, relief=[[0, 0.0], [1, 0.8]], micro=0.5)
    sh(59.5, "adam", 0, 0, act="I", tr="portal", frame=ECU("fingers", 5.0, 6.5), fx=0.0, relief=0.0, micro=0.3,
       hud=[1], hudcol=GOLD, probe={"at": (0.6, 0.42), "subject": (0.5, 0.5)})
    for t, pid, c, z in ((60.6, "judgment", None, None), (61.5, "saturn", "saturn_eye", 5.0), (62.3, "babel", None, None),
                         (63.0, "medusa", "medusa_eye", 5.0)):
        ins(t, pid, frames=3, frame=ECU(c, z) if c else None)

    # ── II. LEARNING (Nightmare Machine, 143.6 bpm): it devours knowledge, cut on the bar
    sh(B2(0), "vitruvian", 1, 0, act="II", fx=[[0, 0.0], [0.6, 0.15], [1, 0.9]], hud=[3], hudcol=CYAN,
       probe={"enter": "near"})
    ti("II  ·  LEARNING   吞 噬", B2(0) + 0.4, B2(0) + 3.2, y=0.88, size=0.03, font=SERIF, idx=2, fade=0.3,
       tracking=0.3, color=(150, 235, 255))
    tri = [[0.02, 0.06, 0.33, 0.94], [0.345, 0.06, 0.655, 0.94], [0.67, 0.06, 0.98, 0.94]]
    step = lambda k, n=4: [[0, 0.0], [k / n - 0.001, 0.0], [k / n + 0.01, 1.0], [1, 1.0]] if k else 1.0
    sh(B2(4), None, act="II", text="[ ANATOMY // 3 SOURCES ]",
       panels=[dict(painting="vesalius", rect=tri[0], alpha=step(0), mode=3, var=3, fx=[[0, 0.0], [1, 0.5]]),
               dict(painting="tulp", rect=tri[1], alpha=step(1), mode=1, var=1, fx=[[0, 0.0], [1, 0.3]]),
               dict(painting="odalisque", rect=tri[2], alpha=step(2), mode=1, var=3, fx=[[0, 0.0], [1, 0.4]])],
       probe={"path": [(0.05, 0.18, 0.5), (0.3, 0.5, 0.45), (0.6, 0.82, 0.5), (0.95, 0.55, 0.5)], "subject": (0.5, 0.5)})
    sh(B2(8), "melencolia", 0, 0, act="II", tr="whip", world="kifs", reveal=[[0, 0], [0.4, 0], [1, 0.9]], style=IRIS,
       hud=[14], hudcol=GOLD, probe={"enter": "right"})
    sh(B2(12), None, act="II", tr="whip", text="[ COSMOS // 3 MODELS ]",
       panels=[dict(painting="cellarius", rect=tri[0], alpha=step(0), mode=2, var=3, fx=[[0, 0.0], [1, 0.5]]),
               dict(painting="fludd", rect=tri[1], alpha=step(1), mode=0, var=1, fx=[[0, 0.0], [1, 0.5]]),
               dict(painting="kircher", rect=tri[2], alpha=step(2), mode=1, var=0, fx=[[0, 0.0], [1, 0.6]])],
       probe={"enter": "right", "path": [(0.3, 0.2, 0.3), (0.6, 0.5, 0.25), (0.95, 0.8, 0.3)], "subject": (0.5, 0.5)})
    for k, (pid, fr, m, v) in enumerate((("arnolfini", ECU("mirror", 5.0, 5.6), 0, 0), ("mandala", None, 1, 0),
                                         ("arnolfini", ECU("mirror", 7.0, 8.0), 0, 2), ("mandala", None, 1, 2))):
        sh(B2(16 + k), pid, m, v, act="II", tr="match" if k else "cut", frame=fr, fx=[[0, 0.0], [1, 0.4]],
           probe={"at": (0.5, 0.78), "subject": (0.5, 0.5)})
    sh(B2(20), "voynich", 3, 0, act="II", text="[ DECRYPTION FAILED // 0x00 ]", hudcol=RED, hud=[13],
       probe={"path": [(0.1, 0.25, 0.4), (0.9, 0.75, 0.4)]})
    for k, (pid, m, v) in enumerate((("redfuji", 0, 1), ("sanromano", 1, 2), ("jatte", 4, 2), ("ancient", 1, 2))):
        sh(B2(22 + k), pid, m, v, act="II", fx=[[0, 0.3], [1, 0.9]], probe={"at": (0.3, 0.62)})
    seq = [("athens", 4, 0), ("kircher", 1, 0), ("cellarius", 2, 3), ("vitruvian", 1, 2), ("mandala", 1, 0),
           ("fludd", 2, 4), ("odalisque", 1, 3), ("melencolia", 0, 1)]
    for k, (pid, m, v) in enumerate(seq):
        sh(B2(26 + k * 0.5), pid, m, v, act="II", fx=[[0, 0.5], [1, 1.1]], probe={"at": (0.3, 0.62)})
    for k, z in enumerate((1.0, 1.7, 2.8)):           # jump cuts up the tower
        sh(B2(30 + 2 * k), "babel", 0, 0, act="II", world="mandelbox", frame={"c": (0.5, 0.35), "z": [[0, z], [1, z * 1.15]]},
           reveal=[[0, 0.1 + 0.3 * k], [1, 0.4 + 0.3 * k]], fx=[[0, 0.3 + 0.4 * k], [1, 0.7 + 0.5 * k]], hud=[2],
           probe={"path": [(0.2, 0.62, 0.55 - 0.12 * k), (0.95, 0.6, 0.4 - 0.12 * k)]})
    ti("[ FATAL ERROR: KNOWLEDGE OVERFLOW ]  fold_space() — core dumped", 124.6, 125.48, y=0.5, size=0.026,
       color=(255, 70, 60), box=True, fade=0.03, tracking=0.02)

    # ── III. CORRUPTION (Waltz of the Carnies, 3/4): the dream rots
    sh(125.0, "garden", 0, 0, act="III", world="organic", reveal=[[0, 0], [0.12, 0], [0.6, 1.0]], style=PEEL,
       relief=0.0, micro=0.5, palette="blood", probe={"enter": "near"})
    ti("III  ·  CORRUPTION   腐 烂", 126.0, 129.2, y=0.88, size=0.03, font=SERIF, idx=2, fade=0.35, tracking=0.3,
       color=(255, 140, 120))
    for k, z in enumerate((1.0, 1.8, 3.2, 6.0)):      # jump cuts creeping in on Saturn's eye, every 2 bars
        sh(B3(8 + 2 * k), "saturn", 2 if k == 3 else 0, 5 if k == 3 else 0, act="III",
           frame=ECU("saturn_eye", z, z * 1.1), fx=[[0, 0.0], [1, 0.15 + 0.25 * k]], relief=0.3 * k, palette="blood",
           probe={"at": (0.68, 0.62)})
    sh(B3(16), "saturn", 0, 0, act="III", frame=ECU("saturn_eye", 2.0), eye=[[0, 1.0], [1, 0.55]], fx=0.0,
       palette="blood", text="[ OBSERVER: CONTAMINATED ]", hudcol=RED, probe={"enter": "hide"})
    di = [[0.02, 0.05, 0.49, 0.95], [0.51, 0.05, 0.98, 0.95]]
    sh(B3(20), None, act="III", palette="blood",
       panels=[dict(painting="medusa", rect=di[0], frame=ECU("medusa_face", 2.0, 2.4), mode=4, var=0,
                    fx=[[0, 0.0], [0.6, 0.1], [1, 0.7]]),
               dict(painting="oiwa", rect=di[1], frame=ECU("oiwa_eye", 2.2, 2.6), mode=2, var=5,
                    fx=[[0, 0.0], [0.6, 0.1], [1, 0.7]])],
       probe={"enter": "near", "at": (0.5, 0.5), "subject": (0.25, 0.45),
              "path": [(0.25, 0.5, 0.5), (0.5, 0.5, 0.5), (0.75, 0.5, 0.52)]})
    sh(B3(28), "nightmare", 2, 5, act="III", tr="portal", palette="blood", fx=[[0, 0.0], [1, 0.45]], hud=[12], hudcol=RED,
       panels=[dict(painting="haeckel", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.4, 0.45], [1, 0.6]],
                    mode=3, var=4, fx=[[0, 0.3], [1, 0.8]])],
       probe={"at": (0.62, 0.28)})
    sh(B3(36), "cyclops", 0, 0, act="III", tr="match", frame=ECU("cyclops_eye", 5.0, 1.3), fx=[[0, 0.0], [1, 0.3]],
       palette="blood", text="[ IT IS WATCHING YOU ]", hudcol=RED, probe={"at": (0.72, 0.6)})
    for k, (pid, m, v) in enumerate((("rebels", 3, 2), ("damned", 2, 5), ("winter", 0, 0), ("haeckel", 3, 4))):
        sh(B3(44 + 2 * k), pid, m, v, act="III", palette="blood", fx=[[0, 0.3], [1, 0.9]],
           world="organic" if pid == "winter" else None, reveal=[[0, 0.2], [1, 0.8]] if pid == "winter" else None,
           style=PEEL, probe={"path": [(0.0, 0.5, 0.2 + 0.15 * k), (1.0, 0.5, 0.35 + 0.15 * k)]})
    sh(B3(52), "voynich2", 3, 0, act="III", palette="blood", fx=[[0, 0.2], [0.7, 1.0], [1, 1.5]],
       text="[ OVERLOAD IN 3..2..1.. ]", hudcol=RED, probe={"at": (0.5, 0.6), "subject": (0.5, 0.4)})

    # ── IV. OVERLOAD (Final Battle of the Dark Wizards, 112.3 bpm): cuts accelerate 4 bars → 1/2 bar
    sh(B4(0), "judgment", 4, 1, act="IV", after="blackhole", fx=[[0, 0.4], [1, 1.2]],
       p={"uHoleR": [[0, 0.02], [1, 0.16]]}, probe={"enter": "near", "at": (0.66, 0.6), "subject": (0.5, 0.5)})
    ti("IV  ·  OVERLOAD   过 载", B4(0) + 0.4, B4(0) + 3.4, y=0.88, size=0.03, font=SERIF, idx=2, fade=0.3, tracking=0.3,
       color=(255, 200, 120))
    sh(B4(4), "wrath", 2, 0, act="IV", fx=[[0, 0.3], [1, 1.2]])
    sh(B4(6), "wave", 2, 3, act="IV", tr="match", fx=[[0, 0.2], [1, 1.3]])
    quad = [[0.015, 0.02, 0.495, 0.49], [0.505, 0.02, 0.985, 0.49], [0.015, 0.51, 0.495, 0.98], [0.505, 0.51, 0.985, 0.98]]
    sh(B4(8), None, act="IV", tr="whip", text="[ STORM CELLS: 4 ]", hudcol=GOLD,
       panels=[dict(painting=pid, rect=quad[k], alpha=step(k, 16), mode=2, var=v, fx=[[0, 0.2], [1, 1.0]])
               for k, (pid, v) in enumerate((("snowstorm", 3), ("starry", 0), ("ninthwave", 0), ("crows", 3)))],
       probe={"enter": "right", "at": (0.5, 0.5), "subject": (0.25, 0.25),
              "path": [(0.3, 0.5, 0.5), (0.6, 0.5, 0.5), (0.9, 0.5, 0.5, 1.4)]})
    sh(B4(12), "empyrean", 1, 0, act="IV", tr="portal", world="mandelbulb", reveal=[[0, 0], [0.3, 0], [0.9, 1.0]],
       style=IRIS, hud=[9], hudcol=GOLD, portal="center")
    sh(B4(14), "ascent", 0, 3, act="IV", tr="portal", fx=[[0, 0.5], [1, 1.0]], portal="center")
    sh(B4(16), "kiss", 1, 0, act="IV", tr="portal", fx=[[0, 0.2], [1, 1.0]], hud=[1], hudcol=GOLD)
    seq = [("liberty", 1, 0), ("damned", 2, 5), ("comp8", 0, 0), ("rebels", 3, 2), ("starry", 0, 3), ("flammarion", 0, 0)]
    for k, (pid, m, v) in enumerate(seq):
        sh(B4(18 + k), pid, m, v, act="IV", fx=[[0, 0.4], [1, 1.2]], probe={"at": (0.5, 0.55)})
    ins(B4(19) + 1.05, "pearl", frames=4, frame=ECU("pearl_eye", 5.0))       # memories of Act I flash back
    ins(B4(21) + 1.05, "adam", frames=4, frame=ECU("fingers", 5.0))
    ins(B4(23) + 1.05, "narcissus", frames=4, frame=ECU("narcissus", 2.0))
    seq = [("crows", 4, 3), ("empyrean", 1, 0), ("snowstorm", 2, 3), ("ninthwave", 2, 0), ("wrath", 2, 0),
           ("kiss", 1, 0), ("ascent", 0, 3), ("judgment", 4, 1)]
    for k, (pid, m, v) in enumerate(seq):
        sh(B4(24 + k * 0.5), pid, m, v, act="IV", fx=[[0, 0.7], [1, 1.4]], probe={"at": (0.5, 0.55)})
    sh(B4(28), "adam", 4, 4, act="IV", portal="center", fx=[[0, 0.0], [0.8, 0.85], [1, 1.0]],
       p={"uPalPaint": 0.0}, text="[ VRAM: 99.9% CRITICAL ]", hudcol=RED,
       probe={"at": (0.5, 0.62), "subject": (0.5, 0.5), "exit": "portal"})
    sh(246.7, "cmb", 4, 5, act="IV", tr="crossfade", portal="center", micro=0.0, after="blackhole",
       fx=[[0, 0.3], [1, 1.0]], p={"uHoleR": [[0, 0.05], [1, 0.3]]}, probe={"enter": "hide"})

    # ── V. AWAKENING (Dreams Become Real): long takes and dissolves; it comes home to the gap between the fingers
    sh(251.3, "lilies", 2, 1, act="V", fx=[[0, 0.0], [1, 0.4]], micro=0.4, dust=True,
       probe={"enter": "spark", "spark_t": 1.2, "at": (0.6, 0.55), "subject": (0.5, 0.65), "look": "camera"})
    ti("V  ·  AWAKENING   醒 来", 252.4, 256.4, y=0.88, size=0.03, font=SERIF, idx=2, fade=0.6, tracking=0.3,
       color=(255, 225, 190))
    sh(258.5, "ophelia", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.25]], micro=0.3,
       panels=[dict(painting="etoiles", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.5, 0.25], [1, 0.35]],
                    mode=0, var=0, fx=0.0, relief=0.0)],
       probe={"path": [(0.3, 0.4, 0.4), (0.9, 0.55, 0.35)]})
    sh(265.5, "almond", 0, 0, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.3]], relief=[[0, 0.2], [1, 1.0]], micro=0.4,
       probe={"look": "camera"})
    sh(272.5, "sunrise", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.4]], micro=0.3, dust=True)
    sh(279.5, "sistine", 0, 0, act="V", tr="dissolve", fx=0.0, relief=[[0, 0.6], [1, 0.0]], micro=0.2,
       probe={"path": [(0.2, 0.5, 0.7), (0.95, 0.5, 0.3)]})
    sh(286.5, "adam", 0, 0, act="V", tr="dissolve", frame=ECU("fingers", 1.0, 3.0), fx=0.0, relief=0.0, micro=0.0,
       kb=0.0, probe={"at": (0.62, 0.38)})
    sh(293.5, "adam", 0, 0, act="V", frame=ECU("fingers", 3.0, 7.0), fx=0.0, relief=0.0, micro=0.0, kb=0.0,
       post={k: [[0, ACT["V"]["post"].get(k, v)], [1, ACT["P"]["post"].get(k, v)]]
             for k, v in (("bloom", 0.12), ("sat", 1.35), ("teal", 0.0), ("grain", 0.4), ("vignette", 0.35))},
       probe={"at": (0.58, 0.44), "subject": (0.5, 0.5), "exit": "spark", "gap": (0.5, 0.5), "state": SPARK,
              "look": "camera"})


INSERT_DEFAULTS = dict(act="IV", tr="none", relief=0.0, micro=0.0, kb=0.0, world=None, reveal=None, style=CRACK,
                       after=None, eye=None, dust=False, hud=[], hudcol=None, text=None, space=None, spacemix=0.0,
                       panels=None, p={}, post={}, portal="focus", probe={}, palette="gold")


def build():
    tl = json.loads((HERE / "timeline.json").read_text())
    D = Director()
    storyboard(D)
    D.shots.sort(key=lambda s: s["t"])
    chapters = []
    for i, s in enumerate(D.shots):
        end = D.shots[i + 1]["t"] if i + 1 < len(D.shots) else 300.0
        chapters.append(chapter(s, s["t"], end, f"{i + 1:02d}_{s['act']}_{s['painting'] or 'black'}"))
    chapters[0]["transition"] = {"type": "none"}
    inserts = [chapter(dict(INSERT_DEFAULTS, painting=s["painting"], mode=s["mode"], var=s["var"], frame=s["frame"],
                            fx=s["fx"]), s["t"], s["end"], f"insert{k}_{s['painting']}")
               for k, s in enumerate(D.inserts)]
    titles = list(D.titles)
    for c, s in zip(chapters, D.shots):           # per-shot HUD read-outs
        if s["text"]:
            dur = c["end"] - c["start"]
            alarm = any(w in s["text"] for w in ("CRITICAL", "OVERLOAD", "FAILED", "CONTAMINATED", "WATCHING"))
            titles.append({"text": s["text"], "start": round(c["start"] + 0.2 * dur, 3), "end": round(c["start"] + 0.8 * dur, 3),
                           "x": 0.06, "y": 0.12, "size": 0.022, "box": True, "fade": 0.06,
                           "blink": 2.0 if any(w in s["text"] for w in ("CRITICAL", "OVERLOAD")) else 0,
                           "font": MONO, "tracking": 0.04, "color": [int(255 * v) for v in (RED if alarm else s["hudcol"] or CYAN)]})
    tl.update(chapters=chapters, inserts=inserts, titles=titles, palettes=PALETTES)
    tl["probe"] = plan_probe(D, chapters)
    tl["glitches"] = [{"start": 125.0, "dur": 0.5, "freeze": True, "tear": 1.0}]
    tl["master"] = [[0, 1.0], [14.9, 1.0], [14.95, 0.0], [15.0, 1.0], [63.6, 1.0], [64.7, 0.0], [64.99, 0.0], [65.0, 1.0],
                    [179.4, 1.0], [180.2, 0.05], [180.29, 0.05], [180.3, 1.0], [248.6, 1.0], [249.8, 0.0], [251.3, 0.0],
                    [252.6, 1.0], [300, 1.0]]
    tl["intensity"] = [[0, 0.8], [14.9, 0.9], [15.0, 0.25], [64.0, 0.4], [65.0, 0.7], [124, 0.9], [125.5, 0.55],
                       [180.0, 0.6], [180.3, 0.85], [246, 1.0], [250, 0.2], [300, 0.3]]
    tl["speed"] = [[0, 0.3], [5, 2.0], [14.5, 6.0], [15.0, 0.4], [64.5, 0.6], [65.0, 1.0], [124, 3.8], [125, 0.0],
                   [125.5, 0.8], [180.3, 1.2], [246, 3.5], [249, 0.2], [300, 0.2]]
    (HERE / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    lens = np.diff([c["start"] for c in chapters] + [300.0])
    print(f"{len(chapters)} shots + {len(inserts)} inserts, median {np.median(lens):.2f}s, "
          f"longest {lens.max():.2f}s, shortest {lens.min():.2f}s, probe keys {len(tl['probe']['pos'])}")
    missing = sorted({c["painting"] for c in chapters + inserts if c["painting"] and c["painting"] not in CAT})
    if missing:
        print("paintings not in catalog:", ", ".join(missing))


if __name__ == "__main__":
    build()
