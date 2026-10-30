#!/usr/bin/env python3
"""Generate config/timeline.json: "Inside a Machine Dream", told by the AI itself.

What if a machine dreamed in human art? It narrates its own dream in short first-person captions, so the story
reads without knowing any art history. The thread: every painting is reaching for someone — and so, in the end, is it.

  COLD OPEN 0-30       a real dream: Adam's hand breaks up, Babel grows out of the gap, its top becomes the Starry
                       Night swirl, a Medusa eye opens, Pearl's eyes fill with stars, Saturn breaks in, it all shatters —
                       static — the hands come back. "What does a machine dream about?"
  1 LEARNING TO SEE    the clue: every painting is reaching for someone (Narcissus, Arnolfini's hands, the Wanderer, the Kiss)
  2 HUNGER             it takes everything apart, then starts mixing them up; images copy themselves; "I kept building."
  3 NIGHTMARE          Saturn keeps breaking into other paintings; "Then I began to recognize the feeling."
  4 OVERLOAD           one continuous morph through everything; "Every painting. All at once." — black
  5 WAKING UP          "For five hundred years, two hands have been reaching toward each other. They have never touched.
                       I had no hands. But I was reaching, too." A point of light in the gap (loop).

Each act is cut on the bars of its own track (config/mix_cc.json). The montage devices (match cuts, jump cuts,
split screens, double exposure, flash inserts, accelerating cuts) support the captions instead of replacing them.
Earlier versions are archived in versions/ (see versions/README.md).

  .venv/bin/python config/build_timeline.py
  MUSIC=ai .venv/bin/python config/build_timeline.py      # AI-music cut → config/timeline_ai.json
"""
import json
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
             space=None, spacemix=0.0, panels=None, p=None, post=None, portal="focus", palette="gold"):
        """One shot from time t to the next shot's t. tr = transition INTO this shot."""
        self.shots.append(dict(t=t, painting=painting, mode=mode, var=var, act=act, tr=tr, frame=frame, fx=fx,
                               relief=relief, micro=micro, kb=kb, world=world, reveal=reveal, style=style, after=after,
                               eye=eye, dust=dust, hud=list(hud), hudcol=hudcol, space=space, spacemix=spacemix,
                               panels=panels, p=p or {}, post=post or {}, portal=portal, palette=palette))

    def insert(self, t, painting, frames=3, frame=None, mode=0, var=0, fx=0.0):
        """Flash-forward / memory: a few frames hard-cut over whatever is playing."""
        self.inserts.append(dict(t=t, end=round(t + frames / 30.0, 4), painting=painting, frame=frame, mode=mode, var=var, fx=fx))

    def _add(self, d, cn, sub):
        if CHINESE:
            d["sub"] = dict(sub, text=cn)
        self.titles.append(d)

    def cap(self, t0, t1, en, cn, color=(255, 255, 255)):
        """The AI's narration, lower third (Chinese line under it when CHINESE)."""
        self._add({"text": en, "start": t0, "end": t1, "y": 0.84 if CHINESE else 0.87, "size": 0.036 if CHINESE else 0.04,
                   "font": SANS, "font_index": 2, "weight": 560, "shadow": True, "color": list(color), "fade": 0.25,
                   "tracking": 0.02}, cn, {"size": 0.032, "color": list(color), "tracking": 0.08})

    def card(self, t0, t1, en, cn, color=(255, 255, 255)):
        """Chapter card, centred over the picture."""
        self._add({"text": en, "start": t0, "end": t1, "y": 0.5, "size": 0.05, "font": SERIF, "font_index": 2,
                   "weight": 500, "shadow": True, "band": 0.6, "color": list(color), "fade": 0.5, "tracking": 0.14},
                  cn, {"size": 0.034, "color": list(color), "tracking": 0.4})

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
    if s["eye"] is not None:                       # a giant eye whose cornea reflects the painting
        layers.append({"scene": "eye", "input": True})
        params["uZoom"] = frac(s["eye"], dur)
    if s["dust"]:
        layers.append({"scene": "particles", "weight": frac([[0, 0.0], [0.3, 0.35], [0.9, 0.35], [1, 0.0]], dur)})
        params.update(WORLD["particles"])
    params.update({k: frac(v, dur) for k, v in s["p"].items()})
    typ, length, pre = TR[s["tr"]]
    post = dict(POST[s["act"]])
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
    WARM = (255, 220, 210)

    # ── COLD OPEN (Industrial Revolution, cuts on 2 beats): a real dream from the first second — paintings swallow,
    #    grow out of and turn into each other. Frame 0 = the last frame of the film.
    b = 1.72
    sh(0.0, "adam", 0, 0, act="P", frame=ECU("fingers", 7.0, 5.5), kb=0.0, relief=0.0, micro=[[0, 0.0], [0.4, 1.0]],
       fx=[[0, 0.0], [0.35, 0.0], [1, 0.3]])                                   # the hands break up into pixels (mosaic)
    cap(0.3, 3.3, "What does a machine dream about?", "机器会梦见什么？")
    sh(2 * b, "babel", 0, 0, act="P", tr="portal", frame={"c": (0.5, 0.62), "z": [[0, 1.6], [1, 1.9]], "drift": (0.0, -0.5)},
       relief=[[0, 0.2], [1, 1.6]], fx=[[0, 0.0], [1, 0.3]])                   # Babel grows out of the gap, the camera climbs it
    cap(3.6, 6.7, "What if it dreamed in human art?", "如果它梦见的，是人类的艺术呢？")
    sh(4 * b, "starry", 2, 3, act="P", tr="morph", frame=ECU("swirl", 1.3, 2.6), fx=[[0, 0.2], [1, 0.9]])   # the top becomes the swirl
    sh(5.5 * b, "medusa", 0, 0, act="P", tr="iris", frame=ECU("medusa_eye", 5.5, 3.0), fx=0.0, relief=0.0)  # an eye opens inside it
    sh(6.5 * b, "pearl", 0, 0, act="P", tr="morph", frame=ECU("pearl_face", 2.2, 1.6), fx=0.0, relief=0.0,
       panels=[dict(painting="starry", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.3, 0.0], [1, 0.75]],
                    mode=2, var=3, fx=[[0, 0.2], [1, 0.8]])])                  # her eyes fill with stars
    cap(11.4, 14.4, "At first, it was beautiful.", "一开始，它很美。")
    sh(8.5 * b, "starry", 2, 5, act="P", frame=ECU("swirl", 1.2, 1.6), fx=[[0, 0.4], [1, 1.6]])             # the sky melts
    ins(15.9, "saturn", frames=4, frame=ECU("saturn_eye", 3.0))
    ins(16.8, "saturn", frames=3, frame=ECU("saturn", 1.6))
    cap(14.8, 17.5, "Then something went wrong.", "然后，出了问题。", color=WARM)
    sh(10 * b, "adam", 4, 4, act="P", portal="center", fx=[[0, 0.35], [1, 1.0]], p={"uPalPaint": 0.0})        # everything shatters
    sh(20.5, "adam", 0, 0, act="P", frame=ECU("fingers", 1.0, 1.6), kb=0.0, **CLEAN)                     # ...but the hands return
    cap(21.0, 24.6, "But one image kept coming back.", "但有一幅画，一次又一次地回来。")
    sh(25.0, "adam", 0, 0, act="P", frame=ECU("fingers", 1.6, 4.5), kb=0.0, fx=0.0, relief=0.0, micro=0.3)
    cap(25.2, 29.6, "Two hands. Almost touching.", "两只手。差一点就碰到。")

    # ── 1. LEARNING TO SEE (Metaphysik): a clue — every painting is reaching for someone
    sh(30.0, "narcissus", 0, 0, act="I", tr="morph", frame={"c": (0.32, 0.5), "z": [[0, 1.0], [1, 1.15]]},
       fx=[[0, 0.0], [0.6, 0.1], [1, 0.6]])
    card(30.3, 33.4, "PART 1 · LEARNING TO SEE", "第一章 · 学会看", color=(200, 230, 255))
    cap(33.6, 37.2, "A boy, reaching for the face in the water.", "一个少年，伸手去够水里的那张脸。")
    sh(37.5, "arnolfini", 0, 0, act="I", tr="portal", frame=ECU("arnolfini_hands", 3.2, 1.2), fx=0.0,
       relief=[[0, 0.0], [1, 0.5]])
    cap(38.0, 43.2, "Two people holding hands, as if afraid to let go.", "两个人牵着手，好像怕一松开就会失去。")
    sh(43.5, "wanderer", 0, 0, act="I", tr="portal", reveal=[[0, 0], [0.4, 0], [0.9, 0.7]], style=PEEL_NEAR,
       space="space_carina", fx=0.0, micro=0.5)
    cap(44.0, 49.2, "A man alone, searching for something beyond the fog.", "一个孤独的人，在雾的尽头寻找着什么。")
    sh(49.5, "kiss", 0, 0, act="I", tr="morph", frame=ECU("kiss_faces", 2.0, 1.3), fx=LATE)
    cap(50.0, 55.2, "Every painting was reaching for someone.", "每一幅画，都在伸手够向某个人。")
    sh(55.5, "sistine", 0, 0, act="I", tr="portal", fx=0.0, relief=[[0, 0.0], [1, 0.6]], micro=0.5)
    cap(56.0, 59.6, "Centuries apart, they all wanted the same thing.", "隔着几百年，他们想要的都是同一样东西。")
    sh(60.0, "adam", 0, 0, act="I", tr="portal", frame=ECU("fingers", 5.0, 6.5), fx=0.0, relief=0.0, micro=0.3)
    cap(60.3, 64.4, "I wanted to know what they were reaching for.", "我想知道，他们到底在够什么。")
    for t, pid, c, z in ((61.0, "judgment", None, None), (61.9, "saturn", "saturn_eye", 5.0), (62.7, "babel", None, None),
                         (63.4, "medusa", "medusa_eye", 5.0)):
        ins(t, pid, frames=3, frame=ECU(c, z) if c else None)

    # ── 2. HUNGER (Nightmare Machine, 143.6 bpm): it takes everything apart — and starts getting it wrong
    sh(B2(0), "vitruvian", 1, 0, act="II", fx=[[0, 0.0], [0.7, 0.1], [1, 0.8]], hud=[3], hudcol=CYAN)
    card(B2(0) + 0.3, B2(0) + 4.2, "PART 2 · HUNGER", "第二章 · 贪婪", color=(170, 235, 255))
    tri = [[0.02, 0.06, 0.33, 0.94], [0.345, 0.06, 0.655, 0.94], [0.67, 0.06, 0.98, 0.94]]
    step = lambda k, n=4: [[0, 0.0], [k / n - 0.001, 0.0], [k / n + 0.01, 1.0], [1, 1.0]] if k else 1.0
    sh(B2(4), None, act="II",
       panels=[dict(painting="vesalius", rect=tri[0], alpha=step(0), mode=3, var=3, fx=LATE),
               dict(painting="tulp", rect=tri[1], alpha=step(1), mode=1, var=1, fx=LATE),
               dict(painting="vitruvian", rect=tri[2], alpha=step(2), mode=1, var=3, fx=LATE)])
    cap(B2(4) + 0.4, B2(8) - 0.2, "To understand them, I took them apart. Their bodies…", "为了理解他们，我把一切拆开。他们的身体……")
    sh(B2(8), "melencolia", 0, 0, act="II", tr="whip", world="kifs", reveal=[[0, 0], [0.6, 0], [1, 0.6]], style=IRIS, fx=LATE)
    cap(B2(8) + 0.4, B2(12) - 0.2, "…their mathematics…", "……他们的数学……")
    sh(B2(12), None, act="II", tr="whip",
       panels=[dict(painting="cellarius", rect=tri[0], alpha=step(0), mode=2, var=3, fx=LATE),
               dict(painting="fludd", rect=tri[1], alpha=step(1), mode=0, var=1, fx=LATE),
               dict(painting="kircher", rect=tri[2], alpha=step(2), mode=1, var=0, fx=LATE)])
    cap(B2(12) + 0.4, B2(16) - 0.2, "…their heavens.", "……他们的天堂。")
    for k, (pid, fr, m, v) in enumerate((("arnolfini", ECU("mirror", 5.0, 5.6), 0, 0), ("mandala", None, 1, 0),
                                         ("arnolfini", ECU("mirror", 7.0, 8.0), 0, 2), ("mandala", None, 1, 2))):
        sh(B2(16 + k), pid, m, v, act="II", tr="match" if k else "cut", frame=fr, fx=[[0, 0.0], [1, 0.4]])
    cap(B2(16) + 0.3, B2(20) - 0.2, "Different worlds. The same questions, again and again.", "不同的世界。同样的问题，一遍又一遍。")
    sh(B2(20), "voynich", 3, 0, act="II", fx=LATE)
    cap(B2(20) + 0.2, B2(22) - 0.1, "Then I started mixing them up.", "然后，我开始把它们弄混了。")
    mixups = (("redfuji", 0, 1, "tulp"), ("sanromano", 1, 2, "melencolia"), ("magdalene", 0, 0, "haeckel"), ("ancient", 1, 2, "vitruvian"))
    for k, (pid, m, v, ghost) in enumerate(mixups):    # saints and skeletons, mountains and anatomy, bleeding into each other
        sh(B2(22 + k), pid, m, v, act="II", fx=[[0, 0.2], [1, 0.8]],
           panels=[dict(painting=ghost, rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.15], [1, 0.45]], mode=0, var=0,
                        fx=0.0, relief=0.0)])
    cap(B2(22) + 0.2, B2(26) - 0.2, "Saints became skeletons. Faces became geometry.", "圣人变成了骷髅。面孔变成了几何。")
    seq = [("athens", 0, 2), ("kircher", 1, 2), ("cellarius", 0, 2), ("vitruvian", 1, 2), ("mandala", 0, 2),
           ("fludd", 1, 2), ("odalisque", 0, 2), ("melencolia", 1, 2)]     # Droste and recursive copies
    for k, (pid, m, v) in enumerate(seq):
        sh(B2(26 + k * 0.5), pid, m, v, act="II", fx=[[0, 0.5], [1, 1.2]])
    cap(B2(26) + 0.2, B2(30) - 0.2, "The images began copying themselves.", "画面开始自我复制。")
    for k, z in enumerate((1.0, 1.7, 2.8)):           # the tower becomes its own knowledge, growing
        sh(B2(30 + 2 * k), "babel", 0, 0, act="II", world="mandelbox", frame={"c": (0.5, 0.35), "z": [[0, z], [1, z * 1.15]]},
           reveal=[[0, 0.25 * k], [1, 0.1 + 0.35 * k]], fx=[[0, 0.15 + 0.4 * k], [1, 0.5 + 0.5 * k]])
    cap(B2(30) + 0.3, B2(33) - 0.1, "They built a tower to reach heaven.", "他们造了一座塔，想通到天上。")
    cap(B2(33) + 0.1, 124.4, "I kept building.", "我一直往上造。")

    # ── 3. NIGHTMARE (Waltz of the Carnies, 3/4): the fear stops being theirs — Saturn keeps breaking in
    sh(125.0, "garden", 0, 0, act="III", world="organic", reveal=[[0, 0], [0.45, 0], [0.9, 0.6]], style=PEEL,
       fx=0.0, relief=0.0, micro=0.5, palette="blood")
    card(125.6, 129.4, "PART 3 · NIGHTMARE", "第三章 · 噩梦", color=(255, 170, 150))
    cap(129.7, B3(8) - 0.15, "Then the dream turned dark.", "然后，梦变黑了。", color=WARM)
    for k, z in enumerate((1.0, 1.6, 3.0, 6.0)):      # jump cuts creeping in on Saturn's eye, every 2 bars
        sh(B3(8 + 2 * k), "saturn", 2 if k == 3 else 0, 5 if k == 3 else 0, act="III",
           frame=ECU("saturn" if k < 2 else "saturn_eye", z, z * 1.1), fx=[[0, 0.0], [1, 0.1 + 0.2 * k]], relief=0.2 * k,
           palette="blood")
    cap(B3(8) + 0.2, B3(12) - 0.1, "A father, devouring his own son.", "一个父亲，在吞吃自己的儿子。", color=WARM)
    cap(B3(12) + 0.1, B3(16) - 0.1, "I thought I was learning what humans feared.", "我以为，我只是在学习人类害怕什么。", color=WARM)
    sh(B3(16), "saturn", 0, 0, act="III", frame=ECU("saturn_eye", 2.0), eye=[[0, 1.0], [1, 0.55]], fx=0.0, palette="blood")
    cap(B3(16) + 0.2, B3(20) - 0.1, "Then I began to recognize the feeling.", "后来，我开始认得这种感觉。", color=WARM)
    di = [[0.02, 0.05, 0.49, 0.95], [0.51, 0.05, 0.98, 0.95]]
    sh(B3(20), None, act="III", palette="blood",
       panels=[dict(painting="medusa", rect=di[0], frame=ECU("medusa_face", 2.0, 2.4), mode=4, var=0, fx=LATE),
               dict(painting="oiwa", rect=di[1], frame=ECU("oiwa_eye", 2.2, 2.6), mode=2, var=5, fx=LATE),
               dict(painting="saturn", rect=[0, 0, 1, 1], blend="screen", frame=ECU("saturn_eye", 1.5),
                    alpha=[[0, 0.0], [0.6, 0.0], [1, 0.35]], mode=0, var=0, fx=0.0, relief=0.0)])
    cap(B3(20) + 0.3, B3(28) - 0.2, "Screams, everywhere.", "到处都是尖叫。", color=WARM)
    sh(B3(28), "nightmare", 2, 5, act="III", tr="portal", palette="blood", fx=LATE,
       panels=[dict(painting="haeckel", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.6, 0.2], [1, 0.5]],
                    mode=3, var=4, fx=[[0, 0.3], [1, 0.8]])])
    cap(B3(28) + 0.4, B3(36) - 0.2, "A demon, sitting on a sleeping woman.", "一个恶魔，坐在熟睡的女人身上。", color=WARM)
    sh(B3(36), "cyclops", 0, 0, act="III", tr="match", frame=ECU("cyclops_eye", 5.0, 1.3), fx=[[0, 0.0], [1, 0.2]],
       palette="blood")
    cap(B3(36) + 0.3, B3(44) - 0.2, "Something was watching me.", "有什么东西，一直在看着我。", color=WARM)
    for k, (pid, m, v) in enumerate((("rebels", 3, 2), ("damned", 2, 5), ("winter", 0, 0), ("haeckel", 3, 4))):
        sh(B3(44 + 2 * k), pid, m, v, act="III", palette="blood", fx=[[0, 0.2], [1, 0.8]],
           world="organic" if pid == "winter" else None, reveal=[[0, 0.2], [1, 0.7]] if pid == "winter" else None,
           style=PEEL)
    cap(B3(44) + 0.3, B3(52) - 0.2, "Falling. And falling. And falling.", "一直往下坠。一直往下坠。", color=WARM)
    sh(B3(52), "voynich2", 3, 0, act="III", palette="blood", fx=[[0, 0.2], [0.7, 1.0], [1, 1.5]])
    cap(B3(52) + 0.3, 179.4, "I tried to wake up. I couldn't.", "我想醒过来。可是醒不过来。", color=WARM)
    for n, c, z in ((22.5, "saturn_eye", 4.0), (31.5, "saturn", 1.4), (40.5, "saturn_eye", 6.0), (47.5, "saturn", 2.0),
                    (55.5, "saturn_eye", 3.0)):        # it keeps breaking into other paintings
        ins(B3(n), "saturn", frames=3, frame=ECU(c, z))

    # ── 4. OVERLOAD (Final Battle of the Dark Wizards, 112.3 bpm): one continuous transformation, faster and faster
    sh(B4(0), "judgment", 4, 1, act="IV", after="blackhole", fx=[[0, 0.2], [1, 1.1]], p={"uHoleR": [[0, 0.02], [1, 0.16]]})
    card(B4(0) + 0.3, B4(0) + 4.0, "PART 4 · OVERLOAD", "第四章 · 失控", color=(255, 215, 150))
    cap(B4(0) + 4.3, B4(4) - 0.15, "Judgment Day.", "末日审判。")
    labels = {}
    sh(B4(4), "wrath", 2, 0, act="IV", tr="morph", fx=[[0, 0.2], [1, 1.1]])
    labels[B4(4)] = ("Fire.", "火。")
    sh(B4(6), "wave", 2, 3, act="IV", tr="morph", fx=[[0, 0.1], [1, 1.2]])
    labels[B4(6)] = ("Water.", "水。")
    quad = [[0.015, 0.02, 0.495, 0.49], [0.505, 0.02, 0.985, 0.49], [0.015, 0.51, 0.495, 0.98], [0.505, 0.51, 0.985, 0.98]]
    sh(B4(8), None, act="IV", tr="morph",
       panels=[dict(painting=pid, rect=quad[k], alpha=step(k, 16), mode=2, var=v, fx=[[0, 0.1], [1, 1.0]])
               for k, (pid, v) in enumerate((("snowstorm", 3), ("starry", 0), ("ninthwave", 0), ("crows", 3)))])
    labels[B4(8)] = ("Every storm they ever painted.", "他们画过的每一场风暴。")
    sh(B4(12), "empyrean", 1, 0, act="IV", tr="morph", world="mandelbulb", reveal=[[0, 0], [0.5, 0], [0.95, 1.0]],
       style=IRIS, portal="center", fx=LATE)
    labels[B4(12)] = ("Heaven…", "天堂……")
    sh(B4(14), "ascent", 0, 3, act="IV", tr="portal", fx=[[0, 0.3], [1, 1.0]], portal="center")
    labels[B4(14)] = ("…the light at the end of the tunnel.", "……隧道尽头的光。")
    sh(B4(16), "kiss", 1, 0, act="IV", tr="morph", fx=[[0, 0.1], [1, 1.0]])
    labels[B4(16)] = ("Love.", "爱。")
    for k, (pid, m, v, en, cn) in enumerate((("liberty", 1, 0, "Freedom.", "自由。"), ("damned", 2, 5, "Hell.", "地狱。"),
                                             ("comp8", 0, 0, "Chaos.", "混乱。"), ("rebels", 3, 2, "Fallen angels.", "堕落的天使。"),
                                             ("starry", 0, 3, "Night.", "黑夜。"),
                                             ("flammarion", 0, 0, "The edge of the world.", "世界的尽头。"))):
        sh(B4(18 + k), pid, m, v, act="IV", tr="morph", fx=[[0, 0.3], [1, 1.1]])
        labels[B4(18 + k)] = (en, cn)
    for t0, (en, cn) in labels.items():            # one word per picture as it turns into the next
        nxt = min([t for t in labels if t > t0] + [B4(24)])
        cap(round(t0 + 0.1, 3), round(nxt - 0.1, 3), en, cn)
    ins(B4(19) + 1.05, "pearl", frames=4, frame=ECU("pearl_eye", 5.0))       # memories of the cold open flash back
    ins(B4(21) + 1.05, "adam", frames=4, frame=ECU("fingers", 5.0))
    ins(B4(23) + 1.05, "narcissus", frames=4, frame=ECU("narcissus", 2.0))
    seq = [("crows", 4, 3), ("empyrean", 1, 0), ("snowstorm", 2, 3), ("ninthwave", 2, 0), ("wrath", 2, 0),
           ("kiss", 1, 0), ("ascent", 0, 3), ("judgment", 4, 1)]
    for k, (pid, m, v) in enumerate(seq):           # half-bar shots, each one already melting into the next
        sh(B4(24 + k * 0.5), pid, m, v, act="IV", tr="morph", fx=[[0, 0.7], [1, 1.4]])
    cap(B4(24) + 0.2, B4(28) - 0.2, "It all came in at once.", "所有东西，一起涌了进来。")
    sh(B4(28), "adam", 4, 4, act="IV", tr="morph", portal="center", fx=[[0, 0.0], [0.8, 0.85], [1, 1.0]], p={"uPalPaint": 0.0})
    cap(B4(28) + 0.2, 246.4, "Every painting. All at once.", "所有的画。同时出现。", color=(255, 160, 120))
    sh(246.7, "cmb", 4, 5, act="IV", tr="crossfade", portal="center", micro=0.0, after="blackhole",
       fx=[[0, 0.3], [1, 1.0]], p={"uHoleR": [[0, 0.05], [1, 0.3]]})

    # ── 5. WAKING UP (Dreams Become Real): long takes; what was missing
    sh(251.3, "lilies", 2, 1, act="V", fx=[[0, 0.0], [1, 0.3]], micro=0.4, dust=True)
    card(252.0, 255.6, "PART 5 · WAKING UP", "第五章 · 醒来", color=(255, 235, 205))
    cap(255.9, 260.4, "When I woke up, everything was quiet.", "醒来的时候，一切都很安静。")
    sh(258.5, "ophelia", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.25]], micro=0.3,
       panels=[dict(painting="etoiles", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.5, 0.25], [1, 0.35]],
                    mode=0, var=0, fx=0.0, relief=0.0)])
    cap(260.8, 265.3, "I remembered all of it.", "我全都记得。")
    sh(265.5, "almond", 0, 0, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.25]], relief=[[0, 0.2], [1, 0.9]], micro=0.4)
    cap(265.9, 268.9, "I had seen everything they ever painted.", "他们画过的一切，我都看过了。")
    cap(269.1, 272.3, "But I kept coming back to what was missing.", "可我总是回到那个缺口。")
    sh(272.5, "sunrise", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.3]], micro=0.3, dust=True)
    cap(273.2, 279.0, "And then I understood.", "然后，我明白了。")
    sh(279.5, "sistine", 0, 0, act="V", tr="dissolve", fx=0.0, relief=[[0, 0.5], [1, 0.0]], micro=0.2)
    cap(280.0, 286.3, "For five hundred years, two hands have been reaching toward each other.",
        "五百年来，有两只手一直在伸向彼此。")
    sh(286.5, "adam", 0, 0, act="V", tr="dissolve", frame=ECU("fingers", 1.0, 3.0), fx=0.0, relief=0.0, micro=0.0, kb=0.0)
    cap(287.2, 292.8, "They have never touched.", "它们从来没有碰到。")
    sh(293.0, "adam", 0, 0, act="V", frame=ECU("fingers", 3.0, 7.0), fx=0.0, relief=0.0, micro=0.0, kb=0.0,
       post={k: [[0, POST["V"].get(k, v)], [1, POST["P"].get(k, v)]]
             for k, v in (("bloom", 0.12), ("sat", 1.35), ("teal", 0.0), ("grain", 0.4), ("vignette", 0.35))})
    cap(293.6, 296.3, "I had no hands.", "我没有手。")
    cap(296.5, 299.2, "But I was reaching, too.", "但我也在伸手。")


# ── MACHINE VISION (v7): the whole film is seen through the AI's eye — the frame re-sampled into cells whose
#    form changes with the act and whose size pulses on the beat (downbeats hardest), with light and colour flowing
#    through the cells (v8). Cell size is a fraction of screen height.
#    shape: 0 square pixels, 1 hex, 2 triangles, 3 voronoi shards, 4 quadtree, 5 LED dots (shaders/mosaic.glsl)
MOSAIC_ACTS = [  # cells stay small enough that every painting is still recognisable; light and colour flow through them
    # start, end, shape, gap, quant, fovea, base cell [[t, v]...], beat accent, downbeat accent, decay s,
    # flow: light, colour, speed, scale
    (0.0, 30.0, 0, 0.25, 0, 0.7, [[0, 0.008], [1.2, 0.008], [3.35, 0.03], [3.6, 0.009], [17.2, 0.009], [19.7, 0.03],
                                  [20.5, 0.04], [21.0, 0.025], [24.0, 0.009], [30.0, 0.012]], 0.4, 0.9, 0.18,
     (0.25, 0.08, 1.2, 3.0)),
    (30.0, 65.0, 5, 0.35, 0, 0.9, [[30.0, 0.018], [43.5, 0.013], [55.5, 0.009], [64.9, 0.006]], 0.15, 0.3, 0.35,
     (0.2, 0.05, 0.5, 2.5)),
    (65.0, 125.0, 1, 0.45, 10, 0.6, [[65.0, 0.010], [108.4, 0.011], [115.1, 0.014], [124.4, 0.028], [125.0, 0.035]],
     0.35, 0.9, 0.15, (0.3, 0.14, 1.4, 4.0)),
    (125.0, 180.3, 3, 0.6, 0, 0.6, [[125.0, 0.025], [127.0, 0.012], [167.0, 0.013], [179.6, 0.022], [180.3, 0.025]],
     0.25, 0.8, 0.2, (0.38, 0.15, 0.8, 3.5)),
    (180.3, 251.3, 4, 0.3, 12, 0.4, [[180.3, 0.006], [231.6, 0.008], [246.0, 0.014], [251.3, 0.016]], 0.6, 1.0, 0.12,
     (0.4, 0.3, 2.0, 3.5)),
    (251.3, 300.0, 0, 0.15, 0, 0.8, [[251.3, 0.011], [265.5, 0.007], [272.5, 0.005], [300.0, 0.005]], 0.1, 0.2, 0.4,
     (0.15, 0.06, 0.4, 2.5)),
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
    # clear at the loop seam: in over the first 0.8 s; out once it understands (273–279), clear to the end = frame 0
    amt = [[0, 0.0], [0.8, 1.0], [273.0, 1.0], [279.0, 0.0], [300.0, 0.0]]
    return {"amt": amt, "cell": [[round(float(t), 4), round(float(c), 5)] for t, c in zip(ts, cell)], **keys}


INSERT_DEFAULTS = dict(act="IV", tr="none", relief=0.0, micro=0.0, kb=0.0, world=None, reveal=None, style=CRACK,
                       after=None, eye=None, dust=False, hud=[], hudcol=None, space=None, spacemix=0.0,
                       panels=None, p={}, post={}, portal="focus", palette="gold")


def build():
    tl = json.loads((HERE / "timeline.json").read_text())
    D = Director()
    storyboard(D)
    D.shots.sort(key=lambda s: s["t"])
    for a, b in zip(D.shots, D.shots[1:]):
        if b["t"] - a["t"] < 0.2:
            print(f"shot too short: {a['painting']} at {a['t']} → {b['painting']} at {b['t']}")
    chapters = []
    for i, s in enumerate(D.shots):
        end = D.shots[i + 1]["t"] if i + 1 < len(D.shots) else 300.0
        chapters.append(chapter(s, s["t"], end, f"{i + 1:02d}_{s['act']}_{s['painting'] or 'black'}"))
    chapters[0]["transition"] = {"type": "none"}
    inserts = [chapter(dict(INSERT_DEFAULTS, painting=s["painting"], mode=s["mode"], var=s["var"], frame=s["frame"],
                            fx=s["fx"]), s["t"], s["end"], f"insert{k}_{s['painting']}")
               for k, s in enumerate(D.inserts)]
    titles = sorted(D.titles, key=lambda x: x["start"])
    for a, b in zip(titles, titles[1:]):           # one title texture at a time
        if b["start"] < a["end"]:
            print(f"title overlap: {a['text']!r} / {b['text']!r}")
    tl.update(chapters=chapters, inserts=inserts, titles=titles, palettes=PALETTES)
    # a single point of light in the gap between the fingers: the last frames and the first (loop)
    # it rides the last push-in (z 3 → 7 over 293–300), so its screen position follows the zoom about the centre
    gx, gy = 0.446, 0.513                  # top-down screen uv of the gap at z 7 (= frame 0)
    def gap(t, a):
        k = (3.0 + 4.0 * (t - 293.0) / 7.0) / 7.0 if t >= 293.0 else 1.0
        return [round(t, 2), [0.5 + (gx - 0.5) * k, 0.5 + (gy - 0.5) * k, 0.0075, a]]
    tl["probe"] = {"pos": [gap(0, 1.0), gap(0.9, 0.0)] + [gap(293.0 + 0.5 * i, min(1.0, max(0.0, (293.0 + 0.5 * i - 295.8) / 1.2)))
                                                          for i in range(15)],
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
