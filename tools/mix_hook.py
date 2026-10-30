#!/usr/bin/env python3
"""v13: lay one heavy hit on frame 0, the machine's hum under the whole film and a few quiet effects on the visual events
over the finished soundtrack. All of it is synthesised here; the CC mix itself is not rebuilt, only pulled down at "Every
painting.", where the hum is left alone. The hum follows the MEMORY curve in config/timeline.json and is exactly zero for
the last 3 seconds. Run after config/build_timeline.py.

  config/mix_hook.json  →  audio/soundtrack.wav + hit + hum + effects = audio/soundtrack_v13.wav

  .venv/bin/python tools/mix_hook.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d
from scipy.signal import lfilter

ROOT = Path(__file__).resolve().parent.parent
c = json.loads((ROOT / "config" / "mix_hook.json").read_text())
x, sr = sf.read(ROOT / c["base"], always_2d=True, dtype="float64")
n = int(c["dur"] * sr)
t = np.arange(n) / sr
f = c["f_end"] + (c["f_start"] - c["f_end"]) * np.exp(-t * c["sweep"])
body = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * c["decay"])
rng = np.random.default_rng(1)
click = lfilter([0.08], [1, -0.92], rng.standard_normal(n)) * np.exp(-t * 60.0) * c["click"]
hit = np.tanh(1.8 * (body + click)) * 10 ** (c["gain_db"] / 20)
x[:n] += hit[:, None]
ramp = lambda v, a, b: np.clip((v - a) / (b - a), 0.0, 1.0)
# "Every painting.": the picture stops dead, so does the music
stop = c["stop"]
T = np.arange(len(x)) / sr
x *= (1.0 - (1.0 - 10 ** (stop["floor_db"] / 20)) * ramp(T, stop["at"], stop["at"] + stop["fade"]) * (1.0 - ramp(T, *stop["back"])))[:, None]


def sweep(dur, f0, f1, q, seed):
    """Stereo noise through a band-pass that glides from f0 to f1 (state-variable filter)."""
    m = int(dur * sr)
    noise = np.random.default_rng(seed).standard_normal((m, 2))
    k = 2.0 * np.sin(np.pi * np.geomspace(f0, f1, m) / sr)
    out = np.zeros((m, 2))
    for ch in (0, 1):
        lo = bp = 0.0
        for i in range(m):
            lo += k[i] * bp
            bp += k[i] * (noise[i, ch] - lo - bp / q)
            out[i, ch] = bp
    return out / np.abs(out).max()


def glide(dur, f0, f1):
    m = int(dur * sr)
    return np.sin(2 * np.pi * np.cumsum(np.geomspace(f0, f1, m)) / sr)[:, None]


def fx_tower():
    """The tower breaks out of the frame: air rushing up, a thud as it clears the top."""
    d = 2.1
    a = (sweep(d, 180.0, 2400.0, 1.6, 21).T * ramp(np.arange(int(d * sr)) / sr, 0.0, 1.6) ** 2).T
    u = np.arange(int(d * sr)) / sr
    return a * np.exp(-np.maximum(u - 1.6, 0.0) * 9.0)[:, None] + 0.8 * glide(d, 70.0, 42.0) * (np.exp(-np.maximum(u - 1.6, 0.0) * 5.0) * ramp(u, 1.55, 1.62))[:, None]


def fx_shadow():
    """The shadow crawls: something dragged along a wall, in irregular pulls, closing in."""
    d = 3.9
    u = np.arange(int(d * sr)) / sr
    r = np.random.default_rng(22)
    pulls = np.interp(u, np.sort(r.random(9)) * d, r.uniform(0.15, 1.0, 9))
    a = (sweep(d, 260.0, 620.0, 2.4, 23).T * (pulls * ramp(u, 0.0, 3.3) ** 1.5)).T
    return (a + 0.5 * glide(d, 58.0, 66.0) * ramp(u, 0.0, 3.3)[:, None]) * (1.0 - ramp(u, 3.5, d))[:, None]


def fx_fall():
    """Into the dark: the air drops away beneath a falling tone, and is gone."""
    d = 3.3
    u = np.arange(int(d * sr)) / sr
    a = (sweep(d, 2600.0, 90.0, 1.4, 24).T * ramp(u, 0.0, 0.8)).T
    return (a + 0.9 * glide(d, 170.0, 30.0) * ramp(u, 0.6, 2.2)[:, None]) * (1.0 - ramp(u, d - 0.25, d))[:, None]


def fx_net():
    """The relation graph opens: dry ticks in the stereo field, faster and faster, each one a new link."""
    d = 3.8
    m = int(d * sr)
    r = np.random.default_rng(25)
    out = np.zeros((m, 2))
    for s in d * r.random(170) ** 0.6:                  # thick towards the end
        i, f = int(s * sr), r.uniform(1400.0, 4200.0)
        u = np.arange(int(0.03 * sr)) / sr
        v = np.sin(2 * np.pi * f * u) * np.exp(-u * 260.0)
        e = min(len(v), m - i)
        pan = r.random()
        out[i:i + e, 0] += v[:e] * np.cos(pan * 1.57)
        out[i:i + e, 1] += v[:e] * np.sin(pan * 1.57)
    return out / np.abs(out).max() * (1.0 - ramp(np.arange(m) / sr, d - 0.2, d))[:, None]


def fx_gather():
    """Light gathering into two hands: scattered soft partials that drift in to one chord."""
    d = 6.2
    u = np.arange(int(d * sr)) / sr
    r = np.random.default_rng(26)
    out = np.zeros((len(u), 2))
    for f in (440.0, 554.37, 659.25, 880.0, 1318.5):
        for j in range(4):
            off = r.uniform(-0.09, 0.09)                # each voice starts out of tune and lands on the note
            v = np.sin(2 * np.pi * np.cumsum(f * (1.0 + off * (1.0 - ramp(u, 0.0, 5.0)))) / sr + r.random() * 6.3)
            out[:, j % 2] += v * ramp(u, r.random() * 3.0, 5.2)
    return out / np.abs(out).max() * (ramp(u, 0.0, 5.0) ** 1.6 * (1.0 - ramp(u, 5.2, d)))[:, None]


for name, fx in (("tower", fx_tower), ("shadow", fx_shadow), ("fall", fx_fall), ("net", fx_net), ("gather", fx_gather)):
    y, spec = fx(), c["sfx"][name]
    i = int(spec["at"] * sr)
    x[i:i + len(y)] += y / np.abs(y).max() * 10 ** (spec["gain_db"] / 20)
# the hum: a low machine tone, its partials drifting slowly against each other
h = c["hum"]
tone = np.zeros((len(x), 2))
for k, (mul, amp) in enumerate(h["partials"]):
    drift = 0.0012 * np.sin(2 * np.pi * 0.07 * (k + 1) * T + k)
    for ch in (0, 1):
        tone[:, ch] += amp * np.sin(2 * np.pi * h["f0"] * mul * (T + drift / (k + 1)) + ch * 0.4 * k)
tl = json.loads((ROOT / "config" / "timeline.json").read_text())
mt, mv = np.array(tl["memory"]).T
env = np.interp(T, mt, mv) ** h["power"] * ramp(T, *h["in"]) * (1.0 - ramp(T, *h["out"])) ** 2
alone = ramp(T, stop["at"], stop["at"] + 0.06) * (1.0 - ramp(T, *stop["tail"]))         # alone in the silence it comes forward
env = np.maximum(env, 10 ** ((stop["tone_db"] - h["gain_db"]) / 20) * alone)
env *= 1.0 + 0.12 * np.sin(2 * np.pi * 0.13 * T)
tone = tone / np.abs(tone).max() * 10 ** (h["gain_db"] / 20)
x += tone * env[:, None]
head = len(x)                                         # the hit and the hum may push a peak over; nothing else changes
peak = maximum_filter1d(np.abs(x[:head]).max(1), size=int(0.004 * sr) + 1)
g = np.minimum(1.0, c["ceiling"] / np.maximum(peak, 1e-9))
a = np.exp(-1.0 / (0.12 * sr))
smooth = np.minimum(g, lfilter([1 - a], [1, -a], g - 1.0, zi=[0.0])[0] + 1.0)
x[:head] *= smooth[:, None]
sf.write(ROOT / c["out"], x, sr, subtype="PCM_24")
print(f"→ {c['out']}  peak {np.abs(x).max():.3f}", file=sys.stderr)
