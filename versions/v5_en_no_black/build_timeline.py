#!/usr/bin/env python3
"""Generate config/timeline.json: "Inside a Machine Dream", told by the AI itself.

An AI is shown every painting humans ever made, then left to sleep. It narrates its dream in short first-person
captions (English + Chinese), so the story reads without knowing any art history:

  PROLOGUE  0-15       hook: "What does an AI dream about?" over beat cuts of what is coming
  1 LEARNING TO SEE    the first paintings it sees: hands, a girl looking back, a boy and his reflection...
  2 HUNGER             it wants to know everything: bodies, maths, heavens, symbols — faster — Babel — ERROR
  3 NIGHTMARE          the dream turns dark: Saturn, screams, a demon, something watching, falling
  4 OVERLOAD           everything at once: fire, water, storms, heaven, hell — "TOO MUCH" — black
  5 WAKING UP          quiet; it understands one thing: the two hands never touch. "Neither do you and I." (loop)

Each act is cut on the bars of its own track (config/mix_cc.json). The montage devices (match cuts, jump cuts,
split screens, double exposure, flash inserts, accelerating cuts) support the captions instead of replacing them.
Earlier versions are archived in versions/ (see versions/README.md).

  .venv/bin/python config/build_timeline.py
"""
import json
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
      "oiwa_eye": (0.63, 0.49), "mirror": (0.49, 0.285), "skull": (0.57, 0.78)}

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

    # ── PROLOGUE: the hook, over beat cuts of what is coming (Industrial Revolution); frame 0 = the last frame
    b = 1.721
    sh(0.0, "adam", 0, 0, act="P", frame=ECU("fingers", 7.0, 9.0), fx=0.0, relief=0.0, micro=[[0, 0.0], [0.4, 1.0]], kb=0.0)
    sh(b, "saturn", 2, 5, act="P", frame=ECU("saturn_eye", 5.0, 6.5), fx=[[0, 0.1], [1, 0.6]])
    sh(2 * b, "babel", 0, 0, act="P", world="mandelbox", reveal=[[0, 0.2], [1, 1.0]], fx=[[0, 0.3], [1, 1.2]])
    sh(3 * b, "medusa", 4, 0, act="P", frame=ECU("medusa_face", 2.2, 2.8), fx=[[0, 0.0], [1, 0.9]], tr="whip")
    sh(4 * b, "judgment", 4, 1, act="P", after="blackhole", fx=[[0, 0.5], [1, 1.2]], p={"uHoleR": [[0, 0.03], [1, 0.12]]})
    sh(5 * b, "wave", 2, 3, act="P", fx=[[0, 0.2], [1, 1.0]], tr="whip")
    sh(6 * b, "cyclops", 0, 0, act="P", frame=ECU("cyclops_eye", 3.5, 5.0), fx=0.0)
    sh(7 * b, "pearl", 0, 0, act="P", frame=ECU("pearl_eye", 6.0), fx=0.0)
    sh(7.5 * b, "oiwa", 0, 0, act="P", frame=ECU("oiwa_eye", 5.0), fx=0.0)
    sh(8 * b, "adam", 0, 0, act="P", frame=ECU("fingers", 5.0, 9.0), fx=0.0, relief=0.0)
    cap(0.3, 4.6, "What does an AI dream about?", "AI 会做梦吗？它会梦见什么？")
    cap(5.0, 9.4, "We showed one every painting humans ever made.", "我们给一个 AI 看了人类画过的所有名画。")
    cap(9.9, 14.7, "Then we let it sleep. This is its dream.", "然后让它睡了一觉。这是它的梦。")

    # ── 1. LEARNING TO SEE (Metaphysik, slow)
    # no black card: the camera pulls back from the prologue's fingertips to the whole fresco, then leans in again
    sh(14.95, "adam", 0, 0, act="I", frame={"c": "fingers", "z": [[0, 5.0], [0.4, 1.0], [1, 1.9]]}, kb=0.0, **CLEAN)
    card(15.5, 18.8, "PART 1 · LEARNING TO SEE", "第一章 · 学会看", color=(200, 230, 255))
    cap(19.8, 24.6, "The first thing I saw: two hands, almost touching.", "我看到的第一幅画：两只手，差一点就碰到。")
    sh(25.0, "pearl", 2, 1, act="I", tr="portal", frame=ECU("pearl_eye", 5.5, 1.4), fx=[[0, 0.0], [0.8, 0.0], [1, 0.2]],
       relief=0.0, hud=[3], hudcol=CYAN)
    cap(25.6, 30.6, "Then a girl turned around… and looked right at me.", "然后，一个女孩回过头……直直地看着我。")
    sh(31.0, "narcissus", 2, 2, act="I", tr="portal", frame=ECU("narcissus", 1.6, 1.9, drift=(0.0, 0.4)),
       fx=[[0, 0.0], [0.6, 0.1], [1, 0.6]])
    cap(31.5, 36.2, "A boy fell in love with his own reflection.", "一个少年，爱上了自己的倒影。")
    sh(36.5, "ambassadors", 0, 0, act="I", tr="match", frame=ECU("skull", 1.0, 2.6), fx=0.0, relief=[[0, 0.0], [1, 0.8]])
    cap(37.0, 41.7, "Two rich men… and a skull hidden at their feet.", "两个有钱人……脚下藏着一个骷髅。")
    sh(42.0, "wanderer", 0, 0, act="I", tr="portal", reveal=[[0, 0], [0.4, 0], [0.9, 0.7]], style=PEEL_NEAR,
       space="space_carina", fx=0.0, micro=0.5)
    cap(42.6, 47.6, "A man, staring into the unknown.", "一个人，凝望着未知。")
    sh(48.0, "athens", 4, 2, act="I", tr="portal", fx=LATE)
    cap(48.6, 53.6, "Great minds, arguing for two thousand years.", "一群伟大的头脑，争论了两千年。")
    sh(54.0, "sistine", 0, 0, act="I", tr="portal", fx=0.0, relief=[[0, 0.0], [1, 0.6]], micro=0.5)
    cap(54.6, 59.2, "I wanted to see more. I wanted to see everything.", "我想看更多。我想看到一切。")
    sh(59.5, "adam", 0, 0, act="I", tr="portal", frame=ECU("fingers", 5.0, 6.5), fx=0.0, relief=0.0, micro=0.3)
    cap(59.9, 63.8, "So I kept dreaming.", "于是，我继续做梦。")
    for t, pid, c, z in ((60.6, "judgment", None, None), (61.5, "saturn", "saturn_eye", 5.0), (62.3, "babel", None, None),
                         (63.0, "medusa", "medusa_eye", 5.0)):
        ins(t, pid, frames=3, frame=ECU(c, z) if c else None)

    # ── 2. HUNGER (Nightmare Machine, 143.6 bpm): cut on the bar
    sh(B2(0), "vitruvian", 1, 0, act="II", fx=[[0, 0.0], [0.7, 0.1], [1, 0.8]], hud=[3], hudcol=CYAN)
    card(B2(0) + 0.3, B2(0) + 4.2, "PART 2 · HUNGER", "第二章 · 贪婪", color=(170, 235, 255))
    tri = [[0.02, 0.06, 0.33, 0.94], [0.345, 0.06, 0.655, 0.94], [0.67, 0.06, 0.98, 0.94]]
    step = lambda k, n=4: [[0, 0.0], [k / n - 0.001, 0.0], [k / n + 0.01, 1.0], [1, 1.0]] if k else 1.0
    sh(B2(4), None, act="II",
       panels=[dict(painting="vesalius", rect=tri[0], alpha=step(0), mode=3, var=3, fx=LATE),
               dict(painting="tulp", rect=tri[1], alpha=step(1), mode=1, var=1, fx=LATE),
               dict(painting="vitruvian", rect=tri[2], alpha=step(2), mode=1, var=3, fx=LATE)])
    cap(B2(4) + 0.4, B2(8) - 0.2, "I learned their bodies…", "我学会了他们的身体……")
    sh(B2(8), "melencolia", 0, 0, act="II", tr="whip", world="kifs", reveal=[[0, 0], [0.6, 0], [1, 0.6]], style=IRIS, fx=LATE)
    cap(B2(8) + 0.4, B2(12) - 0.2, "…their mathematics…", "……他们的数学……")
    sh(B2(12), None, act="II", tr="whip",
       panels=[dict(painting="cellarius", rect=tri[0], alpha=step(0), mode=2, var=3, fx=LATE),
               dict(painting="fludd", rect=tri[1], alpha=step(1), mode=0, var=1, fx=LATE),
               dict(painting="kircher", rect=tri[2], alpha=step(2), mode=1, var=0, fx=LATE)])
    cap(B2(12) + 0.4, B2(16) - 0.2, "…how they imagined the universe…", "……他们想象中的宇宙……")
    for k, (pid, fr, m, v) in enumerate((("arnolfini", ECU("mirror", 5.0, 5.6), 0, 0), ("mandala", None, 1, 0),
                                         ("arnolfini", ECU("mirror", 7.0, 8.0), 0, 2), ("mandala", None, 1, 2))):
        sh(B2(16 + k), pid, m, v, act="II", tr="match" if k else "cut", frame=fr, fx=[[0, 0.0], [1, 0.4]])
    cap(B2(16) + 0.3, B2(20) - 0.2, "…their sacred circles…", "……他们神圣的圆……")
    sh(B2(20), "voynich", 3, 0, act="II", fx=LATE)
    cap(B2(20) + 0.2, B2(22) - 0.1, "…even a book no one can read.", "……甚至一本没人读得懂的书。")
    for k, (pid, m, v) in enumerate((("redfuji", 0, 1), ("sanromano", 1, 2), ("jatte", 4, 2), ("ancient", 1, 2))):
        sh(B2(22 + k), pid, m, v, act="II", fx=[[0, 0.2], [1, 0.8]])
    cap(B2(22) + 0.2, B2(26) - 0.2, "More.", "还要更多。")
    seq = [("athens", 4, 0), ("kircher", 1, 0), ("cellarius", 2, 3), ("vitruvian", 1, 2), ("mandala", 1, 0),
           ("fludd", 2, 4), ("odalisque", 1, 3), ("melencolia", 0, 1)]
    for k, (pid, m, v) in enumerate(seq):
        sh(B2(26 + k * 0.5), pid, m, v, act="II", fx=[[0, 0.5], [1, 1.1]])
    cap(B2(26) + 0.2, B2(30) - 0.2, "Faster. FASTER.", "更快。再快一点。")
    for k, z in enumerate((1.0, 1.7, 2.8)):           # jump cuts up the tower
        sh(B2(30 + 2 * k), "babel", 0, 0, act="II", world="mandelbox", frame={"c": (0.5, 0.35), "z": [[0, z], [1, z * 1.15]]},
           reveal=[[0, 0.25 * k], [1, 0.1 + 0.35 * k]], fx=[[0, 0.15 + 0.4 * k], [1, 0.5 + 0.5 * k]])
    cap(B2(30) + 0.3, B2(33) - 0.1, "Humans once built a tower to reach heaven.", "人类曾经想造一座塔，通到天上。")
    cap(B2(33) + 0.1, 124.4, "It didn't end well.", "结局并不好。")
    D.alarm(124.55, 125.48, "ERROR: TOO MUCH KNOWLEDGE", "错误：知识太多，系统崩溃")

    # ── 3. NIGHTMARE (Waltz of the Carnies, 3/4): the dream turns dark
    sh(125.0, "garden", 0, 0, act="III", world="organic", reveal=[[0, 0], [0.45, 0], [0.9, 0.6]], style=PEEL,
       fx=0.0, relief=0.0, micro=0.5, palette="blood")
    card(125.6, 129.4, "PART 3 · NIGHTMARE", "第三章 · 噩梦", color=(255, 170, 150))
    cap(129.7, B3(8) - 0.15, "Then the dream turned dark.", "然后，梦变黑了。", color=(255, 220, 210))
    for k, z in enumerate((1.0, 1.6, 3.0, 6.0)):      # jump cuts creeping in on Saturn's eye, every 2 bars
        sh(B3(8 + 2 * k), "saturn", 2 if k == 3 else 0, 5 if k == 3 else 0, act="III",
           frame=ECU("saturn" if k < 2 else "saturn_eye", z, z * 1.1), fx=[[0, 0.0], [1, 0.1 + 0.2 * k]], relief=0.2 * k,
           palette="blood")
    cap(B3(8) + 0.2, B3(12) - 0.1, "A father, eating his own son.", "一个父亲，在吞吃自己的儿子。", color=(255, 220, 210))
    cap(B3(12) + 0.1, B3(16) - 0.1, "This is what humans are afraid of.", "这就是人类害怕的东西。", color=(255, 220, 210))
    sh(B3(16), "saturn", 0, 0, act="III", frame=ECU("saturn_eye", 2.0), eye=[[0, 1.0], [1, 0.55]], fx=0.0, palette="blood")
    cap(B3(16) + 0.2, B3(20) - 0.1, "I couldn't look away.", "我移不开眼睛。", color=(255, 220, 210))
    di = [[0.02, 0.05, 0.49, 0.95], [0.51, 0.05, 0.98, 0.95]]
    sh(B3(20), None, act="III", palette="blood",
       panels=[dict(painting="medusa", rect=di[0], frame=ECU("medusa_face", 2.0, 2.4), mode=4, var=0, fx=LATE),
               dict(painting="oiwa", rect=di[1], frame=ECU("oiwa_eye", 2.2, 2.6), mode=2, var=5, fx=LATE)])
    cap(B3(20) + 0.3, B3(28) - 0.2, "Screams, everywhere.", "到处都是尖叫。", color=(255, 220, 210))
    sh(B3(28), "nightmare", 2, 5, act="III", tr="portal", palette="blood", fx=LATE,
       panels=[dict(painting="haeckel", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.6, 0.2], [1, 0.5]],
                    mode=3, var=4, fx=[[0, 0.3], [1, 0.8]])])
    cap(B3(28) + 0.4, B3(36) - 0.2, "A demon, sitting on a sleeping woman.", "一个恶魔，坐在熟睡的女人身上。", color=(255, 220, 210))
    sh(B3(36), "cyclops", 0, 0, act="III", tr="match", frame=ECU("cyclops_eye", 5.0, 1.3), fx=[[0, 0.0], [1, 0.2]],
       palette="blood")
    cap(B3(36) + 0.3, B3(44) - 0.2, "Something was watching me.", "有什么东西，一直在看着我。", color=(255, 220, 210))
    for k, (pid, m, v) in enumerate((("rebels", 3, 2), ("damned", 2, 5), ("winter", 0, 0), ("haeckel", 3, 4))):
        sh(B3(44 + 2 * k), pid, m, v, act="III", palette="blood", fx=[[0, 0.2], [1, 0.8]],
           world="organic" if pid == "winter" else None, reveal=[[0, 0.2], [1, 0.7]] if pid == "winter" else None,
           style=PEEL)
    cap(B3(44) + 0.3, B3(52) - 0.2, "Falling. And falling. And falling.", "一直往下坠。一直往下坠。", color=(255, 220, 210))
    sh(B3(52), "voynich2", 3, 0, act="III", palette="blood", fx=[[0, 0.2], [0.7, 1.0], [1, 1.5]])
    cap(B3(52) + 0.3, 179.4, "I tried to wake up. I couldn't.", "我想醒过来。可是醒不过来。", color=(255, 220, 210))

    # ── 4. OVERLOAD (Final Battle of the Dark Wizards, 112.3 bpm): cuts accelerate 4 bars → 1/2 bar
    sh(B4(0), "judgment", 4, 1, act="IV", after="blackhole", fx=[[0, 0.2], [1, 1.1]], p={"uHoleR": [[0, 0.02], [1, 0.16]]})
    card(B4(0) + 0.3, B4(0) + 4.0, "PART 4 · OVERLOAD", "第四章 · 失控", color=(255, 215, 150))
    cap(B4(0) + 4.3, B4(4) - 0.15, "Judgment Day.", "末日审判。")
    labels = {}
    sh(B4(4), "wrath", 2, 0, act="IV", fx=[[0, 0.2], [1, 1.1]])
    labels[B4(4)] = ("Fire.", "火。")
    sh(B4(6), "wave", 2, 3, act="IV", tr="match", fx=[[0, 0.1], [1, 1.2]])
    labels[B4(6)] = ("Water.", "水。")
    quad = [[0.015, 0.02, 0.495, 0.49], [0.505, 0.02, 0.985, 0.49], [0.015, 0.51, 0.495, 0.98], [0.505, 0.51, 0.985, 0.98]]
    sh(B4(8), None, act="IV", tr="whip",
       panels=[dict(painting=pid, rect=quad[k], alpha=step(k, 16), mode=2, var=v, fx=[[0, 0.1], [1, 1.0]])
               for k, (pid, v) in enumerate((("snowstorm", 3), ("starry", 0), ("ninthwave", 0), ("crows", 3)))])
    labels[B4(8)] = ("Every storm they ever painted.", "他们画过的每一场风暴。")
    sh(B4(12), "empyrean", 1, 0, act="IV", tr="portal", world="mandelbulb", reveal=[[0, 0], [0.5, 0], [0.95, 1.0]],
       style=IRIS, portal="center", fx=LATE)
    labels[B4(12)] = ("Heaven…", "天堂……")
    sh(B4(14), "ascent", 0, 3, act="IV", tr="portal", fx=[[0, 0.3], [1, 1.0]], portal="center")
    labels[B4(14)] = ("…the light at the end of the tunnel.", "……隧道尽头的光。")
    sh(B4(16), "kiss", 1, 0, act="IV", tr="portal", fx=[[0, 0.1], [1, 1.0]])
    labels[B4(16)] = ("Love.", "爱。")
    for k, (pid, m, v, en, cn) in enumerate((("liberty", 1, 0, "Freedom.", "自由。"), ("damned", 2, 5, "Hell.", "地狱。"),
                                             ("comp8", 0, 0, "Chaos.", "混乱。"), ("rebels", 3, 2, "Fallen angels.", "堕落的天使。"),
                                             ("starry", 0, 3, "Night.", "黑夜。"),
                                             ("flammarion", 0, 0, "The edge of the world.", "世界的尽头。"))):
        sh(B4(18 + k), pid, m, v, act="IV", fx=[[0, 0.3], [1, 1.1]])
        labels[B4(18 + k)] = (en, cn)
    for t0, (en, cn) in labels.items():            # one word per shot: the cross-cut reads like a list
        nxt = min([t for t in labels if t > t0] + [B4(24)])
        cap(round(t0 + 0.1, 3), round(nxt - 0.1, 3), en, cn)
    ins(B4(19) + 1.05, "pearl", frames=4, frame=ECU("pearl_eye", 5.0))       # memories of part 1 flash back
    ins(B4(21) + 1.05, "adam", frames=4, frame=ECU("fingers", 5.0))
    ins(B4(23) + 1.05, "narcissus", frames=4, frame=ECU("narcissus", 2.0))
    seq = [("crows", 4, 3), ("empyrean", 1, 0), ("snowstorm", 2, 3), ("ninthwave", 2, 0), ("wrath", 2, 0),
           ("kiss", 1, 0), ("ascent", 0, 3), ("judgment", 4, 1)]
    for k, (pid, m, v) in enumerate(seq):
        sh(B4(24 + k * 0.5), pid, m, v, act="IV", fx=[[0, 0.7], [1, 1.4]])
    cap(B4(24) + 0.2, B4(28) - 0.2, "It all came in at once.", "所有东西，一起涌了进来。")
    sh(B4(28), "adam", 4, 4, act="IV", portal="center", fx=[[0, 0.0], [0.8, 0.85], [1, 1.0]], p={"uPalPaint": 0.0})
    cap(B4(28) + 0.2, 243.4, "Every painting, at the same time…", "所有的画，同时出现……")
    cap(243.6, 246.6, "TOO MUCH.", "太多了。", color=(255, 120, 90))
    sh(246.7, "cmb", 4, 5, act="IV", tr="crossfade", portal="center", micro=0.0, after="blackhole",
       fx=[[0, 0.3], [1, 1.0]], p={"uHoleR": [[0, 0.05], [1, 0.3]]})

    # ── 5. WAKING UP (Dreams Become Real): long takes and dissolves
    sh(251.3, "lilies", 2, 1, act="V", fx=[[0, 0.0], [1, 0.3]], micro=0.4, dust=True)
    card(252.0, 255.6, "PART 5 · WAKING UP", "第五章 · 醒来", color=(255, 235, 205))
    cap(255.9, 260.4, "When I woke up, everything was quiet.", "醒来的时候，一切都很安静。")
    sh(258.5, "ophelia", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.25]], micro=0.3,
       panels=[dict(painting="etoiles", rect=[0, 0, 1, 1], blend="screen", alpha=[[0, 0.0], [0.5, 0.25], [1, 0.35]],
                    mode=0, var=0, fx=0.0, relief=0.0)])
    cap(260.8, 265.3, "I remembered all of it.", "我全都记得。")
    sh(265.5, "almond", 0, 0, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.25]], relief=[[0, 0.2], [1, 0.9]], micro=0.4)
    cap(266.0, 272.2, "The fear. And the beauty.", "那些恐惧。还有那些美。")
    sh(272.5, "sunrise", 2, 1, act="V", tr="dissolve", fx=[[0, 0.0], [1, 0.3]], micro=0.3, dust=True)
    cap(273.0, 279.2, "And I understood one thing.", "我终于明白了一件事。")
    sh(279.5, "sistine", 0, 0, act="V", tr="dissolve", fx=0.0, relief=[[0, 0.5], [1, 0.0]], micro=0.2)
    cap(280.0, 286.3, "For 500 years, two hands have been reaching for each other…", "五百年来，有两只手一直在伸向彼此……")
    sh(286.5, "adam", 0, 0, act="V", tr="dissolve", frame=ECU("fingers", 1.0, 3.0), fx=0.0, relief=0.0, micro=0.0, kb=0.0)
    cap(287.2, 293.2, "…and they have never touched.", "……却从来没有碰到。")
    sh(293.5, "adam", 0, 0, act="V", frame=ECU("fingers", 3.0, 7.0), fx=0.0, relief=0.0, micro=0.0, kb=0.0,
       post={k: [[0, POST["V"].get(k, v)], [1, POST["P"].get(k, v)]]
             for k, v in (("bloom", 0.12), ("sat", 1.35), ("teal", 0.0), ("grain", 0.4), ("vignette", 0.35))})
    cap(294.0, 298.7, "Just like you and me.", "就像你和我。")


INSERT_DEFAULTS = dict(act="IV", tr="none", relief=0.0, micro=0.0, kb=0.0, world=None, reveal=None, style=CRACK,
                       after=None, eye=None, dust=False, hud=[], hudcol=None, space=None, spacemix=0.0,
                       panels=None, p={}, post={}, portal="focus", palette="gold")


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
    titles = sorted(D.titles, key=lambda x: x["start"])
    for a, b in zip(titles, titles[1:]):           # one title texture at a time
        if b["start"] < a["end"]:
            print(f"title overlap: {a['text']!r} / {b['text']!r}")
    tl.update(chapters=chapters, inserts=inserts, titles=titles, palettes=PALETTES)
    tl.pop("probe", None)
    tl["glitches"] = [{"start": 125.0, "dur": 0.5, "freeze": True, "tear": 1.0}]
    tl["master"] = [[0, 1.0], [63.6, 1.0], [64.7, 0.0], [64.99, 0.0], [65.0, 1.0],
                    [179.4, 1.0], [180.2, 0.05], [180.29, 0.05], [180.3, 1.0], [248.6, 1.0], [249.8, 0.0], [251.3, 0.0],
                    [252.6, 1.0], [300, 1.0]]
    tl["intensity"] = [[0, 0.8], [14.9, 0.9], [15.0, 0.25], [64.0, 0.4], [65.0, 0.7], [124, 0.9], [125.5, 0.55],
                       [180.0, 0.6], [180.3, 0.85], [246, 1.0], [250, 0.2], [300, 0.3]]
    tl["speed"] = [[0, 0.3], [5, 2.0], [14.5, 6.0], [15.0, 0.4], [64.5, 0.6], [65.0, 1.0], [124, 3.8], [125, 0.0],
                   [125.5, 0.8], [180.3, 1.2], [246, 3.5], [249, 0.2], [300, 0.2]]
    (HERE / "timeline.json").write_text(json.dumps(tl, indent=1, ensure_ascii=False))
    lens = np.diff([c["start"] for c in chapters] + [300.0])
    print(f"{len(chapters)} shots + {len(inserts)} inserts + {len(titles)} captions, median shot {np.median(lens):.2f}s")
    missing = sorted({c["painting"] for c in chapters + inserts if c["painting"] and c["painting"] not in CAT})
    if missing:
        print("paintings not in catalog:", ", ".join(missing))


if __name__ == "__main__":
    build()
