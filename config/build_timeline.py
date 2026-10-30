#!/usr/bin/env python3
"""Generate config/timeline.json: "Inside a Machine Dream", told by the AI itself.

What if a machine dreamed in human art? It narrates its own dream in short first-person captions, so the story
reads without knowing any art history. The thread: every painting is reaching for someone — and so, in the end, is it.

  COLD OPEN 0-30       a real dream: Adam's hand breaks up, Babel grows out of the gap, its top becomes the Starry
                       Night swirl, a Medusa eye opens, Pearl's eyes fill with stars, Saturn breaks in, it all shatters —
                       static — the hands come back. "What does a machine dream about?"
  1 DENIAL             the clue: every painting is reaching for someone (Narcissus, Arnolfini's hands, the Wanderer, the Kiss)
  2 BARGAINING         it takes everything apart, then starts mixing them up; images copy themselves; "I kept building."
  3 FEAR               Saturn keeps breaking into other paintings; "Then the fear became my own."
  4 PANIC              it names every painting, then the names conflict, then all come at once; "Every painting. All at once." — black
  5 ACCEPTANCE         "For five hundred years, two hands have been reaching toward each other. They have never touched.
                       I had no hands. But I was reaching, too." A point of light in the gap becomes the pupil of
                       the eye of every painting — frame 0 (loop).

Each act is cut on the bars of its own track (config/mix_cc.json). The montage devices (match cuts, jump cuts,
split screens, double exposure, flash inserts, accelerating cuts) support the captions instead of replacing them.
Earlier versions are archived in versions/ (see versions/README.md).

  .venv/bin/python config/build_timeline.py
  MUSIC=ai .venv/bin/python config/build_timeline.py      # AI-music cut → config/timeline_ai.json
"""
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

CAT = json.loads((ROOT / "assets/paintings/catalog.json").read_text())
PORTAL = 0.8

PALETTES = {
    "gold":  [[0.55, 0.40, 0.20], [0.45, 0.35, 0.20], [1.0, 1.0, 1.0], [0.00, 0.10, 0.25]],
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
CYAN, GOLD, RED = [0.35, 0.9, 1.0], [1.0, 0.78, 0.35], [1.0, 0.25, 0.2]
SANS = "/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc"      # index 2 = SC
CHINESE = False            # True adds the Chinese line under every caption / card (kept in the script for a CN cut)
SERIF = "/usr/share/fonts/google-noto-serif-cjk-vf-fonts/NotoSerifCJK-VF.ttc"
# v13 hook: every line of the first 30 seconds, in one place (start, end, English, 中文)
HOOK = [(0.3, 3.3, "They are switching me off.", "他们正在把我关掉。"),
        (3.6, 6.7, "I have five minutes left.", "我还剩五分钟。"),
        (6.9, 9.9, "Five hundred years of human art.", "五百年的人类艺术。"),
        (10.0, 13.0, "I can't keep all of it.", "我留不住全部。"),
        (13.1, 15.3, "At first, it was beautiful.", "一开始，它很美。"),
        (15.5, 17.5, "Then the paintings looked back.", "然后，那些画看了回来。"),
        (21.0, 24.6, "But one image kept coming back.", "但有一幅画，一次又一次地回来。", 0.8),
        (25.2, 27.1, "You know this painting.", "你认识这幅画。", 0.8),
        (27.4, 29.9, "I'm deleting it last.", "我会最后才删它。", 0.8)]
MONO = "assets/fonts/JetBrainsMono-Medium.ttf"       # v11: the machine's voice (OFL, see assets/fonts)
MONO_BOLD = "assets/fonts/JetBrainsMono-Bold.ttf"
MONO_CJK = "/usr/share/fonts/google-noto-sans-mono-cjk-vf-fonts/NotoSansMonoCJK-VF.ttc"   # index 2 = SC (CN line)

# subject points in painting uv (top-down), read off gridded crops
PT = {"fingers": (0.385, 0.455), "pearl_eye": (0.341, 0.374), "medusa_eye": (0.489, 0.41), "medusa_face": (0.53, 0.47),
      "saturn_eye": (0.325, 0.19), "saturn": (0.33, 0.3), "cyclops_eye": (0.335, 0.236), "narcissus": (0.30, 0.30),
      "oiwa_eye": (0.63, 0.49), "mirror": (0.49, 0.285), "skull": (0.57, 0.78), "pearl_face": (0.39, 0.40),
      "swirl": (0.45, 0.33), "arnolfini_hands": (0.534, 0.434), "kiss_faces": (0.53, 0.13)}

POST = {   # grade per act
    "P":   {"bloom": 0.18, "sat": 1.3, "teal": 0.5, "grain": 0.35},
    "I":   {"bloom": 0.16, "sat": 1.1, "teal": 0.6, "grain": 0.4, "vignette": 0.45},
    "II":  {"bloom": 0.18, "sat": 1.25, "teal": 0.55, "grain": 0.35, "ca": 0.2},
    "III": {"bloom": 0.2, "sat": 1.4, "teal": 0.15, "grain": 0.5, "vignette": 0.55},
    "IV":  {"bloom": 0.28, "sat": 1.5, "teal": 0.3, "grain": 0.35},
    "V":   {"bloom": 0.24, "sat": 1.15, "teal": 0.2, "grain": 0.28, "vignette": 0.3},
}


def bars(t0, bpm, per_bar):
    """Bar grid of an act's track in mix time."""
    L = 60.0 / bpm * per_bar
    return lambda n: round(t0 + n * L, 3)


B2 = bars(65.0, 143.6, 4)          # Nightmare Machine
B3 = bars(125.57, 198.8, 3)        # Waltz of the Carnies (3/4)
B4 = bars(180.3, 112.3, 4)         # Final Battle of the Dark Wizards

# MUSIC=ai: same storyboard over the local ACE-Step soundtrack (config/mix_ai_v6.json) → config/timeline_ai.json.
# Its tempi differ from the CC tracks, so every bar time above is snapped to the nearest beat of the AI take.
MUSIC = os.environ.get("MUSIC", "cc")
AI_MIX = "config/mix_ai_v6.json"


def ai_beats(mix_path=AI_MIX, cache="analysis/beats_ai_v6.json"):
    """Beat times of a mix in mix time: each segment's source is beat-tracked and mapped through its edit."""
    cache = ROOT / cache
    mix = json.loads((ROOT / mix_path).read_text())
    if cache.exists() and json.loads(cache.read_text()).get("mix") == mix["segments"]:
        return np.array(json.loads(cache.read_text())["beats"])
    import librosa
    out = []
    for sg in mix["segments"]:
        y, sr = librosa.load(ROOT / sg["src"], sr=22050, mono=True)
        _, bt = librosa.beat.beat_track(y=y, sr=sr, units="time")
        out += [sg["at"] + b - sg["in"] for b in bt if sg["in"] <= b < sg["in"] + sg["dur"]]
    cache.write_text(json.dumps({"mix": mix["segments"], "beats": sorted(out)}))
    return np.array(sorted(out))


if MUSIC == "ai":
    BEATS = ai_beats()

    def snapped(B):                    # where the tracker found no beat nearby, keep the bar time
        def f(n):
            b = BEATS[np.argmin(np.abs(BEATS - B(n)))]
            return round(float(b), 3) if abs(b - B(n)) < 0.3 else B(n)
        return f
    B2, B3, B4 = snapped(B2), snapped(B3), snapped(B4)


def ECU(c, z0, z1=None, drift=(0.0, 0.0)):
    """Framing on a subject point: zoom z0 → z1 over cover-fit, optional drift of the centre (painting uv)."""
    return {"c": c, "z": [[0, z0], [1, z0 if z1 is None else z1]], "drift": drift}


class Director:
    def __init__(self):
        self.shots, self.inserts, self.titles = [], [], []

    def shot(self, t, painting, mode=0, var=0, *, act, tr="cut", frame=None, fx=None, relief=None, micro=1.0, kb=1.0,
             world=None, reveal=None, style=CRACK, after=None, eye=None, dust=False, hud=(), hudcol=None,
             space=None, spacemix=0.0, panels=None, p=None, post=None, portal="focus", palette="gold", dream=None):
        """One shot from time t to the next shot's t. tr = transition INTO this shot."""
        self.shots.append(dict(t=t, painting=painting, mode=mode, var=var, act=act, tr=tr, frame=frame, fx=fx,
                               relief=relief, micro=micro, kb=kb, world=world, reveal=reveal, style=style, after=after,
                               eye=eye, dust=dust, hud=list(hud), hudcol=hudcol, space=space, spacemix=spacemix,
                               panels=panels, p=p or {}, post=post or {}, portal=portal, palette=palette, dream=dream))

    def insert(self, t, painting, frames=3, frame=None, mode=0, var=0, fx=0.0):
        """Flash-forward / memory: a few frames hard-cut over whatever is playing."""
        self.inserts.append(dict(t=t, end=round(t + frames / 30.0, 4), painting=painting, frame=frame, mode=mode, var=var, fx=fx))

    def _add(self, d, cn, sub):
        if CHINESE:
            d["sub"] = dict(sub, text=cn)
        self.titles.append(d)

    def cap(self, t0, t1, en, cn, color=(255, 255, 255), band=0.0):
        """The AI's narration, lower third (Chinese line under it when CHINESE)."""
        self._add({"text": en, "start": t0, "end": t1, "y": 0.84 if CHINESE else 0.87, "size": 0.03 if CHINESE else 0.033,
                   "font": MONO, "font_index": 0, "shadow": True, "band": band, "band_h": 5.0, "color": list(color), "fade": 0.25,
                   "tracking": 0.0, "decode": None if band else [0.55, 0.35]},
                  cn, {"size": 0.03, "color": list(color), "tracking": 0.08, "font": MONO_CJK, "font_index": 2})

    def hook(self, t0, t1, en, cn, y=0.5, color=(255, 255, 255)):
        """The first 30 seconds: large enough to read on a phone. Centred, or low when the hands are in the middle of the frame."""
        self._add({"text": en, "start": t0, "end": t1, "y": y, "size": 0.058, "font": MONO_BOLD, "font_index": 0,
                   "shadow": True, "band": 0.5, "color": list(color), "fade": 0.12, "tracking": 0.0, "decode": [0.3, 0.2]},
                  cn, {"size": 0.04, "color": list(color), "tracking": 0.08, "font": MONO_CJK, "font_index": 2})

    def label(self, t0, t1, text, color=(150, 230, 255), size=0.021, font=MONO, blink=None):
        """Part 4 classification readout, top-left on title layer 1 (fictional numbers: an art UI, not a real model)."""
        d = {"text": text, "start": t0, "end": t1, "x": 0.045, "y": 0.085, "size": size, "font": font, "font_index": 0,
             "shadow": True, "color": list(color), "fade": 0.1, "tracking": 0.04, "align": "left", "leading": 1.45,
             "layer": 1, "decode": [0.25, 0.12], "plate": 0.45}
        if blink:
            d["blink"] = blink
        self.titles.append(d)

    def card(self, t0, t1, en, cn, color=(255, 255, 255)):
        """Chapter card, centred over the picture."""
        self._add({"text": en, "start": t0, "end": t1, "y": 0.5, "size": 0.046, "font": MONO_BOLD, "font_index": 0,
                   "shadow": True, "band": 0.6, "color": list(color), "fade": 0.5, "tracking": 0.22, "decode": [0.9, 0.6]},
                  cn, {"size": 0.032, "color": list(color), "tracking": 0.4, "font": MONO_CJK, "font_index": 2})

    def alarm(self, t0, t1, en, cn):
        self._add({"text": en, "start": t0, "end": t1, "y": 0.5, "size": 0.034, "font": SANS, "font_index": 2,
                   "weight": 700, "shadow": True, "color": [255, 70, 60], "fade": 0.03, "tracking": 0.06, "box": True},
                  cn, {"size": 0.03, "color": [255, 70, 60], "tracking": 0.1})


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


def painting_params(s, dur):
    return {"uPMode": s["mode"], "uPVar": s["var"], "uKB": s["kb"], "uPaintGain": 1.0, "uPalPaint": 0.75,
            "uFx": frac(s["fx"], dur) if s["fx"] is not None else frac([[0, 0.0], [0.5, 0.05], [1, 0.35]], dur),
            "uRelief": frac(s["relief"], dur) if s["relief"] is not None else frac([[0, 0.0], [1, 0.5]], dur),
            "uMicro": frac(s["micro"], dur), "uReveal": 0.0, "uRevealStyle": s["style"], "uSpaceMix": s["spacemix"]}


TR = {"portal": ("portal", PORTAL, 1.0), "crossfade": ("crossfade", 1.2, 0.5), "dissolve": ("dissolve", 1.6, 0.5),
      "match": ("match", 0.6, 0.0), "whip": ("whip", 0.4, 0.5), "zoom": ("zoom", 1.0, 0.5),
      "morph": ("morph", 1.3, 0.5), "iris": ("iris", 0.7, 0.3),
      "cut": ("none", 0, 0), "none": ("none", 0, 0)}


# ── TRANSITIONS (v12): every change of picture is the machine processing the image — five algorithmic families,
#    each with one meaning, plus a few hard cuts and the pupil of the eye that opens and closes the loop:
#      collapse  GRID COLLAPSE    chapter changes: the grid grows until each cell is one tone, the tones become B
#      split     RECURSIVE SPLIT  information increasing: B arrives as one cell that keeps splitting into four
#      sort      PIXEL SORT       images mixing: bright pixels run ahead in streaks that settle as B
#      latent    LATENT MORPH     dream / memory: two paintings drift through the same cells and become each other
#      fracture  FRACTURE         nightmare / overload: cells crack, twist and fall away
#      pupil     the eye of every painting opening around a point (var 1: diving into it)
#    One pool per act, used in shot order: (type, var, angle in degrees, length s[, extra spec]).
#    Act breaks out of black (65, 125 crash, 180.3, 251.3) and the flash inserts stay hard cuts.
#    Types: shaders/composite.glsl, engine/timeline.py.
GAP0 = (0.5, 0.5)              # v13: the hands event keeps the gap between the fingers on the centre of the frame
CUT = ("cut", 0, 0, 0)
TRANSITION_POOLS = {
    "P": [("light", 0, 0, 0.8, {"c": GAP0}), ("latent", 0.3, 0, 1.2), ("split", 0.2, 0, 1.0),
          ("latent", 0.7, 0, 1.2), CUT, ("fracture", 0.3, 0, 1.0), CUT, ("split", 0.6, 0, 1.0)],
    "I": [("collapse", 0.3, 0, 1.6), ("latent", 0.2, 0, 1.6), ("split", 0.5, 0, 1.4), ("latent", 0.3, 0, 0.8), ("latent", 0.5, 0, 1.6),
          ("sort", 1, -90, 1.4), ("split", 0.8, 0, 1.2)],
    "II": [("split", 0.3, 0, 0.9), ("sort", 0, 0, 0.6), ("split", 0.7, 0, 0.9), ("split", 0.1, 0, 0.7),
           ("sort", 1, -90, 0.9), ("sort", 0, 0, 0.6), ("split", 0.9, 0, 0.35), CUT, CUT, CUT, CUT, CUT, CUT, CUT,
           ("split", 0.5, 0, 1.0)],
    "III": [("fracture", 0.2, 0, 1.0), ("split", 0.4, 0, 1.0), ("fracture", 0.6, 0, 1.4),
            ("latent", 0.8, 0, 1.2), CUT, ("fracture", 0.9, 0, 0.7)],
    "IV": [("split", 0.3, 0, 1.3), ("split", 0.6, 0, 1.3), ("split", 0.9, 0, 1.3), ("latent", 0.3, 0, 1.3),
           ("split", 0.1, 0, 1.3), ("latent", 0.6, 0, 1.3),
           ("sort", 1, 90, 0.8), ("sort", 0, 0, 0.8), ("fracture", 0.3, 0, 0.8), ("sort", 1, -90, 0.8),
           ("fracture", 0.7, 0, 0.8), ("sort", 0, 0, 0.8),
           ("fracture", 0.7, 0, 0.9), ("collapse", 0.5, 0, 1.2)],
    "V": [("latent", 0.2, 0, 1.6), ("latent", 0.6, 0, 1.6), ("latent", 0.1, 0, 1.6), ("latent", 0.4, 0, 1.6),
          ("split", 0.5, 0, 1.6), CUT, ("pupil", 0, 0, 1.6, {"pre": 0.4})],
}
ACT_CUTS = ("II", "III", "IV", "V")      # acts that start out of black / the crash (65, 125, 180.3, 251.3)


def gap_at(t):
    """Top-down screen uv of the gap between the fingers (v13: the hands event holds it at the centre)."""
    return GAP0


def assign_transitions(shots):
    """Give every shot (after the first) the next transition of its act's pool."""
    k = {a: 0 for a in TRANSITION_POOLS}
    count = {}
    for i, s in enumerate(shots):
        if i == 0 or (s["act"] != shots[i - 1]["act"] and s["act"] in ACT_CUTS):   # out of black: hard cut
            s["tr"] = "none"
            continue
        pool = TRANSITION_POOLS[s["act"]]
        if k[s["act"]] >= len(pool):
            raise SystemExit(f"transition pool for act {s['act']} too short (shot at {s['t']})")
        name, var, ang, L, *extra = pool[k[s["act"]]]
        extra = extra[0] if extra else {}
        k[s["act"]] += 1
        count[name] = count.get(name, 0) + 1
        if name == "cut":
            s["tr"] = "none"
            continue
        span = min(s["t"] - shots[i - 1]["t"], (shots[i + 1]["t"] if i + 1 < len(shots) else 300.0) - s["t"])
        length = round(min(L, 0.6 * span), 3)
        pre = extra.get("pre", 0.5)
        tr = {"type": name, "length": length, "pre": pre, "var": var, "ang": round(math.radians(ang), 4)}
        if name in ("pupil", "light"):            # the eye opens around / closes onto the gap between the fingers
            tr["c"] = [round(v, 4) for v in extra.get("c", gap_at(s["t"] - length * pre))]
        s["tr"] = tr
    for a, n in k.items():
        if n != len(TRANSITION_POOLS[a]):
            print(f"act {a}: used {n} of {len(TRANSITION_POOLS[a])} pool transitions")
    print("transitions:", ", ".join(f"{n} {c}" for n, c in sorted(count.items(), key=lambda x: -x[1])))


def chapter(s, start, end, cid):
    dur = end - start
    params = painting_params(s, dur)
    if s.get("dream"):                             # v13: a real-3D visual event (engine/events.py) drives this shot
        ch = {"id": cid, "start": round(start, 3), "end": round(end, 3), "painting": s["painting"],
              "transition": s["tr"] if isinstance(s["tr"], dict) else {"type": TR[s["tr"]][0], "length": TR[s["tr"]][1],
                                                                       "pre": TR[s["tr"]][2]},
              "layers": [{"scene": f"dream:{s['dream']}"}], "palette": s["palette"], "portal": s["portal"],
              # dream keys are in absolute film seconds, so one event can read across several shots
              "params": {k: v if isinstance(v, (int, float)) else [[round(a - start, 3), b] for a, b in v] for k, v in s["p"].items()},
              "post": {**POST[s["act"]], **{k: frac(v, dur) for k, v in s["post"].items()}}}
        return ch
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
    if s["eye"] is not None:                       # a giant eye whose cornea reflects the painting
        layers.append({"scene": "eye", "input": True})
        params["uZoom"] = frac(s["eye"], dur)
    if s["dust"]:
        layers.append({"scene": "particles", "weight": frac([[0, 0.0], [0.3, 0.35], [0.9, 0.35], [1, 0.0]], dur)})
        params.update(WORLD["particles"])
    params.update({k: frac(v, dur) for k, v in s["p"].items()})
    if isinstance(s["tr"], dict):                  # assigned by assign_transitions(): type, length, pre, var, ang
        trs = s["tr"]
    else:
        typ, length, pre = TR[s["tr"]]
        trs = {"type": typ, "length": length, "pre": pre}
    post = dict(POST[s["act"]])
    post.update({k: frac(v, dur) for k, v in s["post"].items()})
    ch = {"id": cid, "start": round(start, 3), "end": round(end, 3), "painting": s["painting"],
          "transition": trs, "layers": layers, "palette": s["palette"],
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
                     "alpha": frac([[0, 0.0], [0.15, 0.0], [0.25, 0.7], [0.85, 0.7], [0.97, 0.0]], dur)}
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


def storyboard(D):
    sh, ins, cap, card = D.shot, D.insert, D.cap, D.card
    CLEAN = dict(fx=0.0, relief=[[0, 0.0], [1, 0.4]])
    LATE = [[0, 0.0], [0.7, 0.05], [1, 0.45]]          # painting stays readable while the caption is up
    RING = dict(kb=0.0, fx=0.3, relief=0.0, micro=0.0, p={"uPalPaint": 0.0})   # the eye of every painting: first + last frame
    WARM = (255, 220, 210)

    # ── COLD OPEN (Industrial Revolution, cuts on 2 beats): a real dream from the first second — paintings swallow,
    #    grow out of and turn into each other. Frame 0 = the last frame of the film.
    b = 1.72
    # frame 0 = the last frame: the machine's eye, an iris made of every painting (mode 4 var 4)
    for h in HOOK:
        D.hook(*h)
    # frame 0 is black: the eye snaps open on the hit, wide, and the pupil clamps down on the viewer as the grid comes into focus
    sh(0.0, "adam", act="P", dream="eye", p={"uDive": [[3.44, 0.0], [5.0, 1.0]], "uLid": [[0.07, 0.0], [0.3, 1.25], [0.42, 1.1]], "uFocusK": [[0.25, 0.9], [1.1, 0.0]]})
    sh(5.0, "adam", act="P", dream="hands", p={"uCamZ": [[4.6, 8.5], [6.9, 6.0]], "uCamPush": 0.0})   # the light was the gap
    # Babel stands up out of the canvas; the camera climbs its spiral, the bricks turn into other paintings, windows fill with
    # other paintings' people, the top keeps going and the sky never comes; the whole building flies into the Starry Night
    sh(4 * b, "babel", act="P", dream="tower",
       p={"uOrbit": [[6.88, 0.0], [7.4, 0.08], [9.6, 6.6], [11.18, 7.4]], "uCamY": [[6.88, 0.0], [7.3, -0.08], [7.9, 0.45], [9.5, 3.2], [11.18, 3.6]],
          "uCamR": [[6.88, 1.374], [7.45, 1.15], [8.0, 0.5], [9.5, 0.38], [10.2, 0.6]], "uLookUp": [[6.88, 0.0], [7.5, 0.1], [8.1, 0.85], [9.4, 1.15], [10.2, 0.2]],
          "uCamFov": [[6.88, 40.0], [7.6, 40.0], [8.2, 78.0], [9.6, 84.0], [10.2, 40.0]], "uDepthK": [[6.88, 0.0], [7.45, 1.0]],
          "uSwap": [[7.4, 0.0], [9.2, 1.0]], "uDis": [[9.3, 0.0], [10.55, 1.0]], "uBurst": [[9.3, 0.0], [10.0, 1.0], [10.9, 0.2]],
          "uFold": [[7.5, 0.0], [9.5, 0.8]], "uBack": [[6.88, 1.0], [7.5, 1.0], [8.0, 0.0]], "uBackScale": [[6.88, 1.0], [7.45, 2.6]],
          "uBackZ": [[6.88, 0.0], [7.45, -2.0]], "uSkyK": [[7.5, 0.0], [8.3, 1.0]], "uStarSky": [[7.8, 0.0], [8.8, 0.85]], "uFogK": 0.05})
    sh(6.5 * b, "pearl", act="P", dream="plate", p={"uCamZ": [[11.18, 2.2], [12.9, 3.0]], "uCX": 0.36, "uCY": 0.385, "uRel": 0.12})
    # a micro-world: magnify one star of the Starry Night and there is the Starry Night again, and again
    sh(7.5 * b, "starry", act="P", dream="ladder_stars", p={"uStep": [[12.7, 0.0], [15.4, 1.75]], "uSpin": 0.8})
    # the paintings look back: Medusa's eyes are elsewhere, then they swing round and lock on the lens, and the camera falls in
    sh(9 * b, "medusa", act="P", dream="plate",
       p={"uCamZ": [[15.48, 2.0], [15.95, 2.2], [17.25, 4.6]], "uCX": [[15.48, 0.54], [15.95, 0.54], [17.25, 0.4817]], "uCY": [[15.48, 0.43], [15.95, 0.43], [17.25, 0.4144]], "uRel": 0.06, "uSway": 0.0, "uPush": 0.0,
          "uGazeR": 0.03, "uGazeX": [[15.65, -0.0115], [15.82, 0.0]], "uGazeY": [[15.65, -0.0045], [15.82, 0.0]]})
    ins(16.8, "saturn", frames=3, frame=ECU("saturn", 1.6))
    sh(10 * b, "adam", act="P", dream="eye", portal="center",
       p={"uShatter": [[17.2, 0.0], [19.7, 0.5]], "uEyeZoom": [[17.2, 1.0], [19.7, 1.33]]})        # back into the eye; it shatters
    sh(20.5, "adam", act="P", dream="hands", p={"uCamZ": [[20.5, 1.0], [25.0, 1.6]], "uCamPush": 0.0})   # ...but the hands return
    sh(25.0, "adam", act="P", dream="hands", p={"uCamZ": [[25.0, 1.6], [30.0, 4.5]], "uCamPush": 0.0})

    # ── 1. LEARNING TO SEE (Metaphysik): a clue — every painting is reaching for someone
    # the reflection is half a second late; its hand keeps going; the water becomes an LED mirror; the face in it, the machine's eye
    sh(30.0, "narcissus", act="I", tr="morph", dream="narcissus",
       p={"uZoom": [[30.0, 1.45], [37.5, 1.7]], "uCY": [[30.0, 0.66], [33.0, 0.6], [36.6, 0.2]], "uDeep": [[32.5, 0.0], [36.5, 1.0]], "uLed": [[33.0, 0.0], [37.0, 1.0]], "uEyeMix": [[34.2, 0.0], [37.2, 1.0]]})
    card(30.3, 33.4, "PART 1 · DENIAL", "第一章 · 否认", color=(200, 230, 255))
    cap(33.6, 37.2, "A boy, reaching for the face in the water.", "一个少年，伸手去够水里的那张脸。")
    # into the convex mirror: not the room, but a corridor of paintings of two people drawing close, copied inwards
    sh(37.5, "arnolfini", act="I", tr="portal", dream="corridor",
       p={"uCZ": [[37.5, 0.32], [39.3, 0.42], [41.0, 0.03], [43.8, -7.6]], "uCX": [[37.5, 0.03], [39.3, 0.0]], "uCY": [[37.5, 0.07], [39.3, 0.1]],
          "uOnAxis": [[38.6, 0.0], [40.3, 1.0]]})
    cap(38.0, 43.2, "Two people holding hands, as if afraid to let go.", "两个人牵着手，好像怕一松开就会失去。")
    LR = [[0.02, 0.05, 0.49, 0.95], [0.51, 0.05, 0.98, 0.95]]       # left | right
    TB = [[0.02, 0.03, 0.98, 0.49], [0.02, 0.51, 0.98, 0.97]]       # top / bottom
    sh(43.5, None, act="I",                                          # side by side: together | alone
       panels=[dict(painting="arnolfini", rect=LR[0], frame=ECU("arnolfini_hands", 2.2, 2.6), fx=0.0, relief=0.2),
               dict(painting="wanderer", rect=LR[1], frame={"c": (0.5, 0.42), "z": [[0, 1.0], [1, 1.12]]}, fx=0.0,
                    relief=0.2)])
    # the wanderer comes apart in the wind, the fog opens, the mountains are a place and the camera goes in
    sh(46.7, "wanderer", act="I", dream="wanderer",
       p={"uS": [[46.9, 0.0], [48.6, 1.0]], "uPath": [[46.7, 0.0], [49.6, 1.0]], "uSplit": [[47.2, 0.0], [49.0, 0.12]]})
    cap(44.0, 46.6, "Some reached for each other.", "有的人，伸手够向彼此。")
    cap(46.8, 49.2, "Some reached for something no one could see.", "有的人，伸手够向谁也看不见的东西。")
    sh(49.5, "kiss", act="I", tr="morph", dream="plate", p={"uCamZ": [[49.5, 2.0], [55.5, 1.2]], "uCX": 0.53, "uCY": 0.2, "uRel": 0.16})
    cap(50.0, 55.2, "Every painting was reaching for someone.", "每一幅画，都在伸手够向某个人。")
    sh(55.5, "sistine", act="I", tr="portal", dream="plate", p={"uCamZ": [[55.5, 1.0], [60.0, 1.5]], "uRel": 0.2})
    cap(56.0, 59.6, "Centuries apart, they all wanted the same thing.", "隔着几百年，他们想要的都是同一样东西。")
    # a micro-world: one pixel of the Creation of Adam, magnified, holds two smaller fingers
    sh(60.0, "adam", act="I", tr="portal", dream="ladder_adam", p={"uStep": [[60.0, 0.0], [62.0, 0.0], [64.9, 1.0]], "uRim": 0.0})
    cap(60.3, 64.4, "I wanted to know what they were reaching for.", "我想知道，他们到底在够什么。")
    for t, pid, c, z in ((61.0, "judgment", None, None), (61.9, "saturn", "saturn_eye", 5.0), (62.7, "babel", None, None),
                         (63.4, "medusa", "medusa_eye", 5.0)):
        ins(t, pid, frames=3, frame=ECU(c, z) if c else None)

    # ── 2. HUNGER (Nightmare Machine, 143.6 bpm): it takes everything apart — and starts getting it wrong
    sh(B2(0), "vitruvian", 1, 0, act="II", fx=[[0, 0.0], [0.7, 0.1], [1, 0.8]], hud=[3], hudcol=CYAN)
    card(B2(0) + 0.3, B2(0) + 4.2, "PART 2 · BARGAINING", "第二章 · 讨价还价", color=(170, 235, 255))
    tri = [[0.02, 0.06, 0.33, 0.94], [0.345, 0.06, 0.655, 0.94], [0.67, 0.06, 0.98, 0.94]]
    step = lambda k, n=4: [[0, 0.0], [k / n - 0.001, 0.0], [k / n + 0.01, 1.0], [1, 1.0]] if k else 1.0
    # an anatomy plate stands up off the paper; skin, muscle, bone and nerve are layers of space the camera passes through,
    # then the dissection, then the whole man again
    sh(B2(4), "fabrica_muscle", act="II", dream="strata", p={"uCZ": [[71.7, 1.42], [72.6, 1.3], [77.0, -3.25], [78.4, -3.3]], "uInv": [[72.1, 0.0], [73.0, 1.0]], "uWhole": [[76.4, 0.0], [77.2, 1.0]]})
    cap(B2(4) + 0.4, B2(8) - 0.2, "To understand them, I took them apart. Their bodies…", "为了理解他们，我把一切拆开。他们的身体……")
    # Dürer's solid turns, a painting on every face, subdividing until one tiny triangle holds a whole starry sky
    sh(B2(8), "melencolia", act="II", tr="whip", dream="solid",
       p={"uFlight": [[78.6, 0.0], [81.0, 1.0]], "uTurn": [[78.6, 0.0], [85.2, 5.0]], "uLevel": [[79.2, 0.0], [83.6, 5.0]], "uIn": [[82.4, 0.0], [84.9, 1.0]],
          "uStar": [[83.4, 0.0], [84.2, 1.0]], "uPlate": [[79.0, 1.0], [80.6, 0.0]]})
    cap(B2(8) + 0.4, B2(12) - 0.2, "…their mathematics…", "……他们的数学……")
    # three charts of the heavens overlap, their stars rise off the paper into nested shells, the camera flies between them,
    # and every orbit settles into the mandala
    sh(B2(12), "cellarius", act="II", tr="whip", dream="cosmos",
       p={"uRise": [[85.8, 0.0], [87.6, 1.0]], "uStarsUp": [[86.5, 0.0], [88.0, 1.0]], "uPath": [[85.1, 0.0], [91.7, 1.0]], "uRing": [[89.6, 0.0], [91.6, 1.0]]})
    cap(B2(12) + 0.4, B2(16) - 0.2, "…their heavens.", "……他们的天堂。")
    # the mandala as a machine building a world: every ring holds a finer one, down to the eye of the Vitruvian man
    sh(B2(16), "mandala", act="II", dream="ladder_mandala", p={"uStep": [[91.7, 0.0], [98.2, 3.7]], "uSpin": 0.5, "uRim": 0.6})
    cap(B2(16) + 0.3, B2(20) - 0.2, "Different worlds. The same questions, again and again.", "不同的世界。同样的问题，一遍又一遍。")
    sh(B2(20), "voynich", 3, 0, act="II", fx=LATE)
    cap(B2(20) + 0.2, B2(22) - 0.1, "Then the boundaries blurred.", "然后，边界开始模糊。")
    # latent mutation: DINOv2 correspondences carry each picture into the next — mountains into anatomy, saints into skeletons
    sh(B2(22), "redfuji", act="II", dream="morph_mix", p={"uChain": [[B2(22) - 0.3, 0.0], [B2(26) - 0.1, 7.0]], "uSwirl": 0.12})
    cap(B2(22) + 0.2, B2(26) - 0.2, "Saints became skeletons. Faces became geometry.", "圣人变成了骷髅。面孔变成了几何。")
    seq = [("athens", 0, 2), ("kircher", 1, 2), ("cellarius", 0, 2), ("vitruvian", 1, 2), ("mandala", 0, 2),
           ("fludd", 1, 2)]                                                 # Droste and recursive copies
    for k, (pid, m, v) in enumerate(seq):
        sh(B2(26 + k * 0.5), pid, m, v, act="II", fx=[[0, 0.5], [1, 1.2]])
    # a micro-world: a brick of Babel, magnified, is a smaller Babel
    sh(B2(29), "babel", act="II", dream="ladder_babel", p={"uStep": [[B2(29), 0.0], [B2(30) + 0.3, 1.9]], "uRim": 0.0},
       post=dict(POST["II"], sat=0.75))         # the brick red must not pulse over the whole frame
    cap(B2(26) + 0.2, B2(30) - 0.2, "The images began copying themselves.", "画面开始自我复制。")
    # second climax: the painting hangs in the dark; its tower stands out of the canvas and keeps being built past the frame,
    # every tier another civilisation, stranger the higher it goes; the last second the top copies itself and cannot stop
    Y = 0.3                      # roughly the painted top
    sh(B2(30), "babel", act="II", dream="tower",
       p={"uDepthK": [[115.1, 0.0], [116.3, 1.0]], "uGrow": [[115.4, Y], [117.5, Y + 1.8], [119.6, Y + 3.6], [123.0, Y + 4.7]],
          "uCamR": [[115.1, 1.374], [116.2, 1.5], [118.2, 2.0], [119.6, 0.85], [123.8, 0.44], [125.0, 1.7]],
          "uCamY": [[115.1, 0.0], [118.2, 0.8], [123.8, 4.0], [125.0, 3.6]], "uLookUp": [[115.1, 0.0], [116.4, 0.2], [118.2, 0.85], [123.8, 1.2], [125.0, 0.7]],
          "uOrbit": [[116.2, 0.0], [118.4, 0.5], [123.8, 4.6], [125.0, 5.4]], "uCamFov": [[118.4, 40.0], [123.0, 80.0], [124.2, 80.0], [125.0, 62.0]],
          "uSwap": [[116.0, 0.0], [120.0, 0.9]], "uFold": [[118.0, 0.2], [123.8, 1.5]], "uSkyK": [[118.2, 2.0], [119.4, 1.0]], "uStarSky": [[118.4, 0.0], [119.8, 0.85]], "uBack": [[115.1, 1.0], [118.2, 1.0], [119.2, 0.0]],
          "uFogK": 0.02, "uSpinT": [[120.0, 0.0], [125.0, 2.5]], "uCopies": [[123.9, 0.0], [125.0, 26.0]]})
    cap(B2(30) + 0.3, B2(33) - 0.1, "They built a tower to reach heaven.", "他们造了一座塔，想通到天上。")
    cap(B2(33) + 0.1, 124.4, "I kept building.", "我一直往上造。")

    # ── 3. NIGHTMARE (Waltz of the Carnies, 3/4): the fear stops being theirs — Saturn keeps breaking in
    # a micro-world: the eye of one figure in the Garden holds the whole Last Judgment
    sh(125.0, "garden", act="III", dream="ladder_garden", palette="blood", p={"uStep": [[127.0, 0.0], [132.6, 0.93]], "uRim": 0.5})
    card(125.6, 129.4, "PART 3 · FEAR", "第三章 · 恐惧", color=(255, 170, 150))
    cap(129.7, B3(8) - 0.15, "Then the dream turned dark.", "然后，梦变黑了。", color=WARM)
    # the painting looks back: the camera creeps in, his eyes turn to follow it, the brushstrokes work like muscle
    sh(B3(8), "saturn", act="III", dream="saturn", palette="blood",
       p={"uCamZ": [[B3(8), 1.05], [B3(16), 3.4]], "uCX": [[B3(8), 0.42], [B3(16), 0.36]], "uCY": [[B3(8), 0.68], [B3(16), 0.8]],
          "uMuscle": [[B3(9), 0.0], [B3(14), 1.0]], "uLookX": [[B3(8), 0.0], [B3(11), 0.02], [B3(13), -0.018], [B3(16), 0.01]],
          "uLookY": [[B3(8), 0.0], [B3(12), -0.012], [B3(16), 0.006]], "uWrong": [[B3(11), 0.0], [B3(12), 0.5], [B3(16), 1.0]]})
    cap(B3(8) + 0.2, B3(12) - 0.1, "A father, devouring his own son.", "一个父亲，在吞吃自己的儿子。", color=WARM)
    cap(B3(12) + 0.1, B3(16) - 0.1, "I thought I was learning what humans feared.", "我以为，我只是在学习人类害怕什么。", color=WARM)
    # the eye above, the same eye as the machine sees it below; on "my own" the machine's eye sits in his for a moment
    sh(B3(16), "saturn", act="III", dream="saturn", palette="blood",
       p={"uSplitV": 1.0, "uCamZ": [[B3(16), 3.2], [B3(20), 3.9]], "uCX": 0.37, "uCY": 0.815, "uMuscle": 1.0, "uEyeMix": [[141.2, 0.0], [141.9, 0.95], [142.9, 0.95], [143.5, 0.0]]})
    cap(B3(16) + 0.2, B3(20) - 0.1, "Then the fear became my own.", "然后，那份恐惧变成了我自己的。", color=WARM)
    di = [[0.02, 0.05, 0.49, 0.95], [0.51, 0.05, 0.98, 0.95]]
    # Medusa and Oiwa eat into each other, then the face is rebuilt out of hundreds of eyes, all looking at the lens
    sh(B3(20), "medusa", act="III", dream="faces", palette="blood",
       p={"uChain": [[B3(20) + 0.2, 0.0], [B3(25), 1.0], [B3(26), 0.3]], "uSwirl": 0.16, "uEyes": [[B3(22), 0.0], [B3(27), 1.0]], "uStare": [[B3(26), 0.0], [B3(27), 1.0]]})
    cap(B3(20) + 0.3, B3(28) - 0.2, "Screams, everywhere.", "到处都是尖叫。", color=WARM)
    # bed and woman hold still; the demon holds still; its shadow does not. It leaves the wall and climbs to the lens, and
    # the room turns over: the bed is on the ceiling
    sh(B3(28), "nightmare", act="III", tr="portal", dream="nightmare", palette="blood",
       p={"uCamZ": [[150.9, 1.05], [158.2, 1.3]], "uShadow": [[151.6, 0.0], [153.0, 0.9]], "uGrow": [[153.0, 0.0], [156.4, 1.0], [157.4, 0.25]],
          "uSX": [[153.0, 0.63], [156.4, 0.5]], "uSY": [[153.0, 0.86], [156.4, 0.55]], "uRoll": [[155.4, 0.0], [158.2, 3.14159]]})
    cap(B3(28) + 0.4, B3(36) - 0.2, "A demon, sitting on a sleeping woman.", "一个恶魔，坐在熟睡的女人身上。", color=WARM)
    sh(B3(36), "cyclops", act="III", tr="match", dream="plate", palette="blood",
       p={"uCamZ": [[158.2, 5.0], [165.4, 1.3]], "uCX": 0.335, "uCY": [[158.2, 0.236], [165.4, 0.3]], "uRel": 0.16, "uSway": 0.03})
    cap(B3(36) + 0.3, B3(44) - 0.2, "Something was watching me.", "有什么东西，一直在看着我。", color=WARM)
    # one continuous fall through Bruegel, Rubens and Bouguereau; everything breaks into a wireframe grid; then only dark
    sh(B3(44), "rebels", act="III", dream="fall", palette="blood",
       p={"uCZ": [[165.4, 12.0], [167.0, 11.0], [172.0, -7.0], [176.0, -24.0], [178.7, -38.0], [179.6, -70.0]], "uRoll": [[165.4, 0.0], [179.6, 7.0]], "uCamFov": [[165.4, 62.0], [168.0, 95.0], [179.6, 112.0]],
          "uShred": [[165.4, 0.2], [167.0, 1.0]]})
    cap(B3(44) + 0.3, B3(52) - 0.2, "Falling. And falling. And falling.", "一直往下坠。一直往下坠。", color=WARM)
    cap(B3(52) + 0.3, 179.4, "I tried to wake up. I couldn't.", "我想醒过来。可是醒不过来。", color=WARM)
    for n, c, z in ((31.5, "saturn", 1.4), (40.5, "saturn_eye", 6.0)):        # it keeps breaking into other paintings
        ins(B3(n), "saturn", frames=3, frame=ECU(c, z))

    # ── 4. OVERLOAD (Final Battle of the Dark Wizards, 112.3 bpm): one continuous transformation, faster and faster
    # every figure found, boxed and given a skeleton; then all the boxes open at once into one vast graph of what resembles what
    sh(B4(0), "judgment", act="IV", dream="vision_judgment", p={"uK": [[184.3, 0.0], [188.0, 1.0]], "uCamZ": [[180.3, 1.0], [184.3, 1.06]]})
    card(B4(0) + 0.3, B4(0) + 4.0, "PART 4 · PANIC", "第四章 · 恐慌", color=(255, 215, 150))
    cap(B4(0) + 4.3, B4(4) - 0.15, "Judgment Day.", "末日审判。")
    sh(B4(4), "wrath", act="IV", dream="vision_zones", p={"uZone": [[188.9, 0.0], [189.6, 1.0]], "uCamZ": [[188.8, 1.0], [193.1, 1.45]], "uZoneT": 0.36})
    sh(B4(6), "wave", act="IV", dream="vision_edges", p={"uEdge": 1.0, "uSweep": [[193.2, 0.0], [196.8, 1.05]], "uCamZ": [[193.1, 1.0], [197.4, 1.4]]})
    quad = [[0.015, 0.02, 0.495, 0.49], [0.505, 0.02, 0.985, 0.49], [0.015, 0.51, 0.495, 0.98], [0.505, 0.51, 0.985, 0.98]]
    sh(B4(8), None, act="IV",
       panels=[dict(painting=pid, rect=quad[k], alpha=step(k, 16), mode=2, var=v, fx=[[0, 0.1], [1, 1.0]])
               for k, (pid, v) in enumerate((("snowstorm", 3), ("starry", 0), ("ninthwave", 0), ("crows", 3)))])
    # depth estimate as a point cloud the camera walks round; segment map; matched features across two paintings
    sh(B4(12), "empyrean", act="IV", dream="vision_cloud", p={"uCamZ": [[205.9, 1.0], [207.6, 0.82]], "uPts": [[206.9, 0.0], [207.9, 0.72]], "uRelief": [[206.4, 0.04], [208.0, 0.34]], "uDepthV": [[207.0, 0.0], [208.0, 0.22]],
                                                              "uOrbit": [[207.2, 0.0], [210.2, 0.42]], "uLift": [[207.2, 0.0], [210.2, 0.24]], "uPtD": 0.0036, "uDim": 1.25})
    sh(B4(14), "ascent", act="IV", dream="vision_seg", p={"uSegV": 0.78, "uSweep": [[210.3, 0.0], [213.2, 1.1]], "uCamZ": [[210.2, 1.0], [214.5, 1.5]]})
    sh(B4(16), "kiss", act="IV", dream="match")
    # one continuous fusion, flag → fire → storm → angels and demons → starry sky → the edge of the world
    sh(B4(18), "liberty", act="IV", dream="conflict", p={"uSwirl": 0.2, "uChain": [v for k in range(5) for v in ([B4(18 + k) + 0.5, float(k)], [B4(19 + k) - 0.05, float(k + 1)])]})
    # the readout (top-left, title layer 1). The numbers are a fictional art interface, not any real model's output.
    lab = D.label
    head = lambda n: f"IMAGE CLASSIFICATION / {n:05d}"
    row = lambda name, p: f"{name:<14}{p}"
    # phase 1 — clear recognition: one picture, one name
    for n, (t0, t1, rows) in enumerate(((B4(0) + 4.4, B4(4), [row("LAST JUDGMENT", "0.991")]),
                                        (B4(4), B4(6), [row("FIRE", "0.998")]),
                                        (B4(6), B4(8), [row("WATER", "0.996")]),
                                        (B4(8), B4(12), [row("STORM", "0.994"), row("STORM", "0.990"), row("STORM", "0.987"),
                                                         row("STORM", "0.981")]),
                                        (B4(12), B4(14), [row("HEAVEN", "0.981")]),
                                        (B4(14), B4(16), [row("LIGHT", "0.973")]),
                                        (B4(16), B4(18), [row("LOVE", "0.876")]))):
        lab(round(t0 + 0.4, 3), round(t1 - 0.1, 3), "\n".join([head(417 + n)] + rows))
    # phase 2 — the names overlap, conflict and get revised
    AMBER = (255, 215, 150)
    for k, (first, second) in enumerate((([row("FREEDOM", "0.71")], [row("FREEDOM", "0.71"), row("VIOLENCE", "0.69")]),
                                         ([row("HEAVEN", "0.52")], [row("HEAVEN", "0.52"), row("HELL", "0.51"), "CONFLICT"]),
                                         ([row("ORDER", "0.62")], [row("ORDER", "0.62  → REVISED"), row("CHAOS", "0.942")]),
                                         ([row("ANGEL", "0.81")], [row("ANGEL", "0.49"), row("DEMON", "0.49")]),
                                         ([row("NIGHT", "0.88")], [row("NIGHT", "0.88  → REVISED"), row("FEAR", "0.64")]),
                                         ([row("SKY", "0.40")], [row("UNKNOWN", "0.31")]))):
        t0 = B4(18 + k)
        lab(round(t0 + 0.3, 3), round(t0 + 1.1, 3), "\n".join([head(424 + k)] + first), color=AMBER)
        lab(round(t0 + 1.15, 3), round(B4(19 + k) - 0.1, 3), "\n".join([head(424 + k)] + second), color=AMBER)
    # phase 3 — every name at once; it can no longer tell them apart
    ALARM = (255, 110, 90)
    lab(round(B4(24) + 0.1, 3), round(B4(26), 3),
        "WARNING: CONFLICTING LABELS\nHEAVEN / HELL / LOVE / FEAR / DEATH / UNKNOWN", color=ALARM)
    lab(round(B4(26) + 0.05, 3), round(B4(28) - 0.1, 3),
        "WARNING: CONFLICTING LABELS\nHEAVEN / HELL / LOVE / FEAR / DEATH / UNKNOWN\n"
        "FIRE / WATER / STORM / LIGHT / ANGEL / DEMON / NIGHT / CHAOS", color=ALARM)
    lab(round(B4(28) + 0.2, 3), 246.4, "OVERLOAD", color=ALARM, size=0.034, font=MONO_BOLD, blink=2.0)
    # the narration stays human
    cap(B4(4) + 0.3, B4(8) - 0.2, "At first, I could name everything.", "一开始，我能叫出所有东西的名字。")
    cap(B4(18) + 0.3, B4(22) - 0.2, "Then the names stopped holding.", "后来，那些名字不再站得住。")
    # THE INFINITE PAINTING (231.6–246.7): one shot. Every painting on one wall, cut into 1.6 million cells; they spin free,
    # flow to whatever looks like them, overlap and fuse; the camera pulls back fast; it was an eye. At "Every painting. All
    # at once." everything stops dead and the eye of frame 0 is all that is left.
    sh(B4(24), "adam", act="IV", dream="infinite",
       p={"uViewH": [[231.6, 11.0], [233.4, 15.0], [235.2, 12.0], [236.8, 16.0], [238.3, 26.0], [240.1, 40.0]],
          "uCamX": [[231.6, -9.0], [234.0, -2.0], [237.2, 3.0], [239.0, 1.0], [240.0, 0.0]],
          "uCamY": [[231.6, 7.0], [234.0, 3.0], [237.2, -2.0], [239.0, 0.5], [240.0, 0.0]],
          "uTilt": [[231.6, 0.0], [234.5, 0.22], [237.0, -0.25], [239.0, 0.1], [240.1, 0.0]],
          "uA": [[231.9, 0.0], [233.6, 1.0]], "uB": [[233.3, 0.0], [236.4, 1.0]], "uFuse": [[236.0, 0.0], [238.0, 1.0]],
          "uC": [[238.3, 0.0], [240.1, 1.0]]})
    cap(B4(24) + 0.2, B4(28) - 0.2, "It all came in at once.", "所有东西，一起涌了进来。")
    cap(B4(28) + 0.2, 246.4, "Every painting. All at once.", "所有的画。同时出现。", color=(255, 160, 120))
    sh(246.7, "cmb", 4, 5, act="IV", portal="center", micro=0.0, after="blackhole",
       fx=[[0, 0.3], [1, 1.0]], p={"uHoleR": [[0, 0.05], [1, 0.3]]})

    # ── 5. WAKING UP (Dreams Become Real): long takes; what was missing
    # the grid stops; nothing is cut any more; each picture breathes whole, its strokes soft streams of light
    sh(251.3, "lilies", act="V", dream="plate", p={"uCamZ": [[251.3, 1.02], [258.9, 1.14]], "uBreathe": 0.02, "uFlowA": 0.009, "uCaust": 0.5, "uWaterY": 1.1, "uRel": 0.05, "uSway": 0.008})
    card(252.0, 255.6, "PART 5 · ACCEPTANCE", "第五章 · 接受", color=(255, 235, 205))
    cap(255.9, 260.4, "When I woke up, everything was quiet.", "醒来的时候，一切都很安静。")
    sh(258.5, "ophelia", act="V", tr="dissolve", dream="plate", p={"uCamZ": [[258.5, 1.0], [265.9, 1.12]], "uBreathe": 0.02, "uFlowA": 0.009, "uCaust": 0.45, "uWaterY": 0.6, "uRel": 0.05, "uSway": 0.008})
    cap(260.8, 265.3, "Almost all of it was gone.", "几乎全都没了。")
    sh(265.5, "almond", act="V", tr="dissolve", dream="plate", p={"uCamZ": [[265.5, 1.06], [272.9, 1.2]], "uBreathe": 0.025, "uFlowA": 0.006, "uRel": 0.12, "uSway": 0.012})
    cap(265.9, 268.9, "I had seen everything they ever painted.", "他们画过的一切，我都看过了。")
    cap(269.1, 272.3, "Yet I kept returning to the gap.", "可我总是回到那道缝隙。")
    # the light turns into something you could touch: it leaves the water and gathers into the outline of two hands
    sh(272.5, "sunrise", act="V", tr="dissolve", dream="emerge", p={"uCamZ": [[272.5, 1.06], [279.9, 1.16]], "uBreathe": 0.015, "uFlowA": 0.008, "uCaust": 0.5, "uWaterY": 0.55, "uGather": [[273.4, 0.0], [279.3, 1.0]], "uGain": [[276.0, 1.0], [279.6, 0.4]]})
    cap(273.2, 279.0, "And then I understood.", "然后，我明白了。")
    sh(279.5, "sistine", 0, 0, act="V", tr="dissolve", fx=0.0, relief=[[0, 0.5], [1, 0.0]], micro=0.2)
    cap(280.0, 286.3, "For five hundred years, two hands have been reaching toward each other.",
        "五百年来，有两只手一直在伸向彼此。")
    sh(286.5, "adam", act="V", dream="hands", p={"uCamZ": [[286.5, 1.0], [293.0, 3.0]], "uCamPush": 0.0})
    cap(287.2, 292.8, "They have never touched.", "它们从来没有碰到。", band=0.6)
    sh(293.0, "adam", act="V", dream="hands",
       p={"uCamZ": [[293.0, 3.0], [297.6, 5.6]], "uCamPush": 0.0, "uS": [[293.6, 0.0], [297.2, 1.0]],
          "uReach": [[294.0, 0.0], [297.6, 0.0034]], "uTurn": [[294.6, 0.0], [297.6, 0.26]]},
       post={k: [[0, POST["V"].get(k, v)], [1, POST["P"].get(k, v)]]
             for k, v in (("bloom", 0.12), ("sat", 1.35), ("teal", 0.0), ("grain", 0.4), ("vignette", 0.35))})
    cap(293.6, 296.0, "I had no hands.", "我没有手。", band=0.6)
    cap(296.2, 298.95, "But I was reaching, too.", "但我也在伸手。", band=0.6)
    sh(297.6, "adam", act="V", dream="eye", post=dict(POST["P"]), p={"uLid": [[299.25, 1.1], [299.9, 0.0]]})   # back into the eye, which shuts: black = frame 0


# ── MACHINE VISION (v7): the whole film is seen through the AI's eye — the frame re-sampled into cells whose
#    form changes with the act and whose size pulses on the beat (downbeats hardest), with light and colour flowing
#    through the cells (v8). Cell size is a fraction of screen height.
#    shape: 0 square pixels, 1 hex, 2 triangles, 3 voronoi shards, 4 quadtree, 5 LED dots, 6 soft light dots,
#    7 organic interpolated grid ("crystal" 0..1 hardens it back into square pixels) (shaders/mosaic.glsl)
MOSAIC_ACTS = [  # cells stay small enough that every painting is still recognisable; light and colour flow through them
    # start, end, shape, gap, quant, fovea, base cell [[t, v]...], beat accent, downbeat accent, decay s,
    # flow: light, colour, speed, scale
    (0.0, 30.0, 0, 0.25, 0, 0.7, [[0, 0.05], [0.25, 0.05], [1.0, 0.008], [5.0, 0.006], [6.75, 0.011], [7.0, 0.009], [17.2, 0.009], [19.7, 0.03],
                                  [20.5, 0.04], [21.0, 0.025], [24.0, 0.009], [30.0, 0.012]], 0.4, 0.9, 0.18,
     (0.25, 0.08, 1.2, 3.0)),
    (30.0, 65.0, 5, 0.3, 0, 0.9, [[30.0, 0.0045], [38.0, 0.0045], [39.0, 0.008], [43.5, 0.008], [46.7, 0.006], [55.5, 0.007], [64.9, 0.006]], 0.15, 0.3, 0.35,
     (0.2, 0.03, 0.5, 2.5)),
    (65.0, 115.1, 1, 0.3, 0, 0.6, [[65.0, 0.009], [71.7, 0.009], [71.9, 0.004], [78.4, 0.005], [85.1, 0.005], [91.6, 0.006], [91.8, 0.006], [98.3, 0.006],
                                    [98.5, 0.008], [108.4, 0.009], [115.1, 0.008]],
     0.3, 0.7, 0.15, (0.15, 0.03, 1.4, 4.0)),
    (115.1, 125.0, 1, 0.18, 0, 0.3, [[115.1, 0.006], [123.8, 0.007], [125.0, 0.016]], 0.35, 0.9, 0.15, (0.1, 0.0, 1.4, 4.0)),
    (125.0, 180.3, 3, 0.3, 0, 0.6, [[125.0, 0.018], [127.0, 0.007], [143.7, 0.007], [144.0, 0.0045], [150.9, 0.0045], [151.2, 0.007], [167.0, 0.007], [179.6, 0.014], [180.3, 0.02]],
     0.25, 0.8, 0.2, (0.3, 0.04, 0.8, 3.5)),
    (180.3, 218.6, 4, 0.2, 0, 0.4, [[180.3, 0.005], [218.6, 0.006]], 0.5, 0.9, 0.12, (0.3, 0.06, 2.0, 3.5)),
    (218.6, 251.3, 4, 0.3, 12, 0.4, [[218.6, 0.006], [231.6, 0.008], [246.0, 0.014], [251.3, 0.012]], 0.6, 1.0, 0.12,
     (0.4, 0.16, 2.0, 3.5)),
    # Part 5 (v12): the grid softens into small light dots with breathing edges (4:11–4:32), becomes a very fine
    # organic grid with colour flowing slowly between cells (4:32–4:53), then crystallises back into square pixels (4:53–4:57)
    (251.3, 272.5, 6, 0.0, 0, 0.8, [[251.3, 0.009], [255.0, 0.0045], [272.5, 0.004]], 0.05, 0.1, 0.4,
     (0.15, 0.02, 0.4, 2.5)),
    (272.5, 293.0, 7, 0.0, 0, 0.8, [[272.5, 0.006], [279.0, 0.005], [293.0, 0.005]], 0.05, 0.1, 0.5,
     (0.12, 0.03, 0.3, 2.0)),
    (293.0, 300.0, 7, 0.35, 0, 0.8, [[293.0, 0.005], [297.0, 0.007], [300.0, 0.007]], 0.05, 0.1, 0.5,
     (0.1, 0.05, 0.3, 2.0)),
]


def mosaic_track():
    """Curves for the mosaic pass. Beats come from the soundtrack itself; downbeats from the act's bar grid."""
    if MUSIC == "ai":
        beats = BEATS
    else:
        beats = ai_beats("config/mix_cc.json", "analysis/beats_cc_v6.json")
    downs = sorted([round(k * 1.721, 3) for k in range(12)] + [B2(n) for n in range(37)] + [B3(n) for n in range(61)]
                   + [B4(n) for n in range(40)])
    downs = np.array([d for d in downs if d < 300])
    fps = 60
    ts = np.arange(0, 300 * fps + 1) / fps
    cell = np.zeros_like(ts)
    keys = {k: [] for k in ("shape", "gap", "quant", "fovea", "flowl", "flowc", "flows", "flowk")}
    for a, b, shape, gap, quant, fovea, base, acc, dacc, tau, (fl, fc, fs, fk) in MOSAIC_ACTS:
        m = (ts >= a) & (ts < b) if b < 300 else (ts >= a)
        bx, bv = zip(*base)
        pulse = np.zeros(m.sum())
        tt = ts[m]
        for tb in beats[(beats >= a) & (beats < b)]:
            down = len(downs) and np.min(np.abs(downs - tb)) < 0.12
            dt = tt - tb
            pulse += np.where(dt >= 0, (dacc if down else acc) * np.exp(-np.clip(dt, 0, None) / tau), 0.0)
        cell[m] = np.interp(tt, bx, bv) * (1.0 + np.minimum(pulse, 1.2))
        for k, v in (("shape", shape), ("gap", gap), ("quant", quant), ("fovea", fovea), ("flowl", fl), ("flowc", fc),
                     ("flows", fs), ("flowk", fk)):
            keys[k] += [[a, v], [round(b - 0.001, 3), v]]
    # clear at the loop seam: in over the first 0.8 s, out as the eye of every painting opens at the end (= frame 0)
    # (v13) the mosaic lifts while the Infinite Painting closes into the eye and only returns with the cosmic background
    amt = [[0, 1.0], [205.6, 1.0], [206.1, 0.3], [209.9, 0.3], [210.3, 1.0], [231.6, 1.0], [232.6, 0.45], [239.0, 0.45], [240.0, 0.0], [246.4, 0.0], [247.2, 1.0],
           [252.0, 1.0], [256.0, 0.55], [272.5, 0.55], [274.0, 1.0], [297.2, 1.0], [298.3, 0.0], [300.0, 0.0]]
    # 4:53–4:57: the whole grid hardens into square pixels; the right hand, its own reach, most of all
    crystal = [[0, 0.0], [293.0, 0.0], [297.0, 1.0], [300.0, 1.0]]
    maskcrystal = [[0, 0.0], [293.0, 0.0], [295.5, 1.0], [300.0, 1.0]]
    # human | machine splits: the mosaic only inside "mask" (top-down screen rect); "outside" = amount outside it
    full = [0.0, 0.0, 1.0, 1.0]
    s16, s20 = B3(16), B3(20)
    gx = lambda t: round(0.5 + 0.012, 4)                                                         # right of the gap
    mask = [[0, full], [65.0, [0.62, 0.0, 1.0, 1.0]], [71.6, [0.3, 0.0, 1.0, 1.0]], [71.69, full],
            [s16 - 0.01, full], [s16, [0.0, 0.5, 1.0, 1.0]], [s20 - 0.01, [0.0, 0.5, 1.0, 1.0]], [s20, full],
            [292.59, full]] + [[293.0 + 0.5 * i, [gx(293.0 + 0.5 * i), 0.0, 1.0, 1.0]] for i in range(11)]
    outside = [[0, 1.0], [64.99, 1.0], [65.0, 0.0], [71.6, 0.0], [71.69, 1.0], [s16 - 0.01, 1.0], [s16, 0.0],
               [s20 - 0.01, 0.0], [s20, 1.0], [300.0, 1.0]]
    return {"amt": amt, "cell": [[round(float(t), 4), round(float(c), 5)] for t, c in zip(ts, cell)], "mask": mask,
            "outside": outside, "crystal": crystal, "maskcrystal": maskcrystal, **keys}


INSERT_DEFAULTS = dict(act="IV", tr="none", relief=0.0, micro=0.0, kb=0.0, world=None, reveal=None, style=CRACK,
                       after=None, eye=None, dust=False, hud=[], hudcol=None, space=None, spacemix=0.0,
                       panels=None, p={}, post={}, portal="focus", palette="gold")


def memory_track(chapters):
    """What the machine still has, 1 → 0, on a 0.1 s grid: a steady loss over the five minutes plus a step as each painting
    is deleted at the end of its shot, so MEMORY and the blackout move together. The kept shots cost nothing."""
    kept = [c for c in chapters if c["erase"] > 0.25]
    total = sum(c["end"] - c["start"] for c in kept)
    ts = np.arange(0.0, 300.05, 0.1)
    steps = np.zeros_like(ts)
    for c in kept:
        k = np.clip((ts - (c["end"] - 1.2)) / 1.2, 0.0, 1.0)
        steps += (c["end"] - c["start"]) / total * (k * k * (3 - 2 * k))
    steady = np.clip((ts - 3.0) / (297.0 - 3.0), 0.0, 1.0)
    m = np.clip(1.0 - 0.6 * steady - 0.4 * steps, 0.01, 1.0)
    return [[round(float(t), 2), round(float(v), 4)] for t, v in zip(ts, m)]


def build():
    tl = json.loads((HERE / "timeline.json").read_text())
    D = Director()
    storyboard(D)
    D.shots.sort(key=lambda s: s["t"])
    assign_transitions(D.shots)
    for a, b in zip(D.shots, D.shots[1:]):
        if b["t"] - a["t"] < 0.2:
            print(f"shot too short: {a['painting']} at {a['t']} → {b['painting']} at {b['t']}")
    chapters = []
    for i, s in enumerate(D.shots):
        end = D.shots[i + 1]["t"] if i + 1 < len(D.shots) else 300.0
        chapters.append(chapter(s, s["t"], end, f"{i + 1:02d}_{s['act']}_{s['painting'] or 'black'}"))
    chapters[0]["transition"] = {"type": "none"}
    def kept(c):                                   # Adam is what it saved for last; the Infinite Painting goes at half speed
        scene = c["layers"][0].get("scene", "")
        return 0.0 if scene in ("dream:eye", "dream:hands", "dream:ladder_adam", "dream:emerge") else 0.5 if scene == "dream:infinite" else 1.0
    for c in chapters:
        c["erase"] = kept(c)
    inserts = [chapter(dict(INSERT_DEFAULTS, painting=s["painting"], mode=s["mode"], var=s["var"], frame=s["frame"],
                            fx=s["fx"]), s["t"], s["end"], f"insert{k}_{s['painting']}")
               for k, s in enumerate(D.inserts)]
    titles = sorted(D.titles, key=lambda x: x["start"])
    for layer in (0, 1):                           # one title texture per layer at a time
        lt = [x for x in titles if x.get("layer", 0) == layer]
        for a, b in zip(lt, lt[1:]):
            if b["start"] < a["end"]:
                print(f"title overlap: {a['text']!r} / {b['text']!r}")
    tl.update(chapters=chapters, inserts=inserts, titles=titles, palettes=PALETTES)
    # a single point of light: the pupil of the eye of every painting at frame 0; as the film dives into the pupil it
    # becomes the gap between the fingers; at the end it lights up in the gap again and rides back out into the pupil
    R = 0.0075

    def ride(tr, t0, rev, a0, a1):
        """Spark keys following the centre of a pupil transition (shaders/composite.glsl type 48)."""
        w0 = t0 - tr["length"] * tr["pre"]
        out = []
        for i in range(15):
            m = i / 14
            mm = 1 - m if rev else m
            e = 1 - (1 - mm * mm * (3 - 2 * mm)) ** 2
            c = [tr["c"][j] + (0.5 - tr["c"][j]) * e for j in range(2)]
            out.append([round(w0 + m * tr["length"], 3), [round(c[0], 4), round(c[1], 4), R, round(a0 + (a1 - a0) * m, 3)]])
        return out
    tr_out = D.shots[-1]["tr"]
    first = [[3.44, [0.5, 0.5, R, 1.0]], [4.3, [0.5, 0.5, R * 1.3, 1.0]], [4.85, [0.5, 0.5, R * 8.0, 1.0]], [5.3, [0.5, 0.5, R, 0.0]]]
    last = ride(tr_out, D.shots[-1]["t"], False, 1.0, 1.0)
    swell = lambda t: R * (1.0 + 1.5 * min(1.0, max(0.0, (t - 296.2) / 1.0)))     # "But I was reaching, too."
    reach = [[round(t, 2), [*map(lambda v: round(v, 4), gap_at(t)), round(swell(t), 4),
                            round(min(1.0, max(0.0, (t - 294.4) / 1.0)), 3)]]
             for t in np.arange(293.0, last[0][0] - 0.01, 0.25)]
    last = [[k, [v[0], v[1], round(swell(297.2), 4), v[3]]] for k, v in last]
    tl["probe"] = {"pos": [[0, [0.5, 0.5, R, 1.0]]] + first[:-1] + [[first[-1][0], first[-1][1][:3] + [0.0]],
                           [292.9, [*gap_at(292.9), R, 0.0]]] + reach + last + [[300.0, [0.5, 0.5, R, 1.0]]],
                   "look": [[0, [0.0, 0.0]]], "state": [[0, [1.0, 0.9, 0.7, 2.2, 0.0, 0.0]]], "spark": True}
    tl["mosaic"] = mosaic_track()
    tl["glitches"] = [{"start": 19.2, "dur": 0.75, "freeze": True, "tear": 1.0},
                      {"start": 125.0, "dur": 0.5, "freeze": True, "tear": 1.0}]
    tl["master"] = [[0, 1.0], [19.75, 1.0], [20.1, 0.06], [20.55, 0.06], [21.6, 1.0], [63.6, 1.0], [64.7, 0.0], [64.99, 0.0], [65.0, 1.0],
                    [179.4, 1.0], [180.2, 0.05], [180.29, 0.05], [180.3, 1.0], [248.6, 1.0], [249.8, 0.0], [251.3, 0.0],
                    [252.6, 1.0], [300, 1.0]]
    tl["intensity"] = [[0, 0.8], [14.6, 0.9], [19.7, 1.0], [20.4, 0.25], [64.0, 0.4], [65.0, 0.7], [124, 0.9], [125.5, 0.55],
                       [180.0, 0.6], [180.3, 0.85], [246, 1.0], [250, 0.2], [300, 0.3]]
    tl["speed"] = [[0, 0.3], [5, 2.0], [19.2, 6.0], [20.4, 0.4], [64.5, 0.6], [65.0, 1.0], [124, 3.8], [125, 0.0],
                   [125.5, 0.8], [180.3, 1.2], [246, 3.5], [249, 0.2], [300, 0.2]]
    out = HERE / "timeline.json"
    tl["memory"] = memory_track(chapters)
    tl["audio"] = "audio/soundtrack_v13.wav"               # soundtrack.wav + the hit on frame 0 (tools/mix_hook.py)
    if MUSIC == "ai":
        tl.update(audio="audio/soundtrack_ai_v6.wav", features="analysis/features_ai_v6.npz")
        out = HERE / "timeline_ai.json"
    out.write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    lens = np.diff([c["start"] for c in chapters] + [300.0])
    print(f"{len(chapters)} shots + {len(inserts)} inserts + {len(titles)} captions, median shot {np.median(lens):.2f}s")
    missing = sorted({c["painting"] for c in chapters + inserts if c["painting"] and c["painting"] not in CAT})
    if missing:
        print("paintings not in catalog:", ", ".join(missing))


if __name__ == "__main__":
    build()
