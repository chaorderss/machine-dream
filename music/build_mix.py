"""Hybrid Classical Glitch mix: assemble recording excerpts per config/mix.json and modernise them.

  * sub-bass reinforcement: a sine on the piece's tonic, gated by the recording's own low end
  * Paulstretch pads: a tail frozen and stretched 8-20x into a cosmic bed under transitions
  * granular stutters, risers, heartbeat, impacts, hard silences
  * master: 25 Hz high-pass, peak limiter, loudness to ~-14 LUFS-ish (YouTube's normalisation target)
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import maximum_filter1d

SR = 48000
ROOT = Path(__file__).resolve().parent.parent
rng = np.random.default_rng(565)
MOTIF = [659.26, 493.88, 587.33]        # E5 B4 D5: the bell signature that returns between acts


def db(x):
    return 10 ** (x / 20.0)


def load(path):
    x, sr = sf.read(str(ROOT / path), always_2d=True, dtype="float32")
    x = x.T
    if x.shape[0] == 1:
        x = np.repeat(x, 2, axis=0)
    if sr != SR:
        import soxr
        x = soxr.resample(x.T, sr, SR).T
    return x[:2]


def ramp(n, fin, fout):
    e = np.ones(n, np.float32)
    a, b = int(fin * SR), int(fout * SR)
    if a > 0:
        e[:a] *= np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if b > 0:
        e[n - b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return e


def place(bus, t, x, gain=1.0):
    i = int(round(t * SR))
    n = min(x.shape[1], bus.shape[1] - i)
    if n > 0:
        bus[:, i:i + n] += x[:, :n] * gain


def lowpass(x, hz, order=4):
    return signal.sosfiltfilt(signal.butter(order, hz, "lowpass", fs=SR, output="sos"), x, axis=-1)


def envelope(x, release=0.25):
    a = np.exp(-1.0 / (release * SR))
    return signal.lfilter([1 - a], [1, -a], np.abs(x))


# ------------------------------------------------------------------ sound design
def sub_bass(seg, hz, gain_db):
    """Sine on the tonic (plus a quiet octave), following the recording's own low-frequency energy."""
    low = lowpass(seg.mean(0), 180.0)
    env = envelope(low, 0.3)
    env = env / (np.percentile(env, 99) + 1e-9)
    env = np.clip(env, 0, 1.2) ** 1.5
    t = np.arange(seg.shape[1]) / SR
    s = np.sin(2 * np.pi * hz * t) + 0.25 * np.sin(4 * np.pi * hz * t)
    s = np.tanh(1.5 * s * env) * db(gain_db)
    return np.stack([s, s]).astype(np.float32)


def paulstretch(x, stretch, win_s=0.3):
    n = int(win_s * SR) // 2 * 2
    win = (1 - np.linspace(-1, 1, n) ** 2) ** 1.25
    hop_out = n // 2
    hop_in = hop_out / stretch
    out_len = int(x.shape[1] * stretch) + n
    out = np.zeros((2, out_len), np.float32)
    for c in range(2):
        pos, o = 0.0, 0
        while o + n <= out_len:
            i = int(pos)
            seg = x[c, i:i + n]
            if len(seg) < n:
                seg = np.pad(seg, (0, n - len(seg)))
            mag = np.abs(np.fft.rfft(seg * win))
            ph = rng.uniform(0, 2 * np.pi, len(mag))
            out[c, o:o + n] += np.fft.irfft(mag * np.exp(1j * ph), n) * win
            o += hop_out
            pos += hop_in
    return out / (np.abs(out).max() + 1e-9)


def riser(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    blk = 1024
    zi = np.zeros((2, 2))
    centers = np.geomspace(250, 9000, n // blk + 1)
    for k in range(0, n, blk):
        sos = signal.butter(2, [centers[k // blk] / 1.5, min(centers[k // blk] * 1.5, SR / 2.1)], "bandpass", fs=SR, output="sos")
        out[k:k + blk], zi = signal.sosfilt(sos, x[k:k + blk], zi=zi)
    f = np.geomspace(80, 900, n)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    y = (out / (np.abs(out).max() + 1e-9) + tone) * (t / dur) ** 2.5
    pan = np.sin(2 * np.pi * 0.4 * t * (t / dur))
    return np.stack([y * (1 - 0.4 * pan), y * (1 + 0.4 * pan)]).astype(np.float32)


def thump(f0=52.0, dur=0.45):
    t = np.arange(int(dur * SR)) / SR
    f = f0 * 0.7 + f0 * 0.7 * np.exp(-t * 25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9) * (1 - np.exp(-t * 400))
    return lowpass(x, 220.0)


def heartbeat(dur, bpm):
    n = int(dur * SR)
    out = np.zeros(n)
    period = 60.0 / bpm
    for k in range(int(dur / period) + 1):
        for off, f, g in ((0.0, 55.0, 1.0), (0.18, 46.0, 0.6)):
            i = int((k * period + off) * SR)
            s = thump(f) * g
            m = min(len(s), n - i)
            if m > 0:
                out[i:i + m] += s[:m]
    return np.stack([out, out]).astype(np.float32)


def impact(dur=3.0):
    t = np.arange(int(dur * SR)) / SR
    f = 30 + 55 * np.exp(-t * 6)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    nz = lowpass(rng.standard_normal(len(t)), 900.0) * np.exp(-t * 3.0) * 0.35
    x = np.tanh(1.6 * (body + nz))
    return np.stack([x, x]).astype(np.float32)


def whoosh(dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = signal.sosfilt(signal.butter(2, [400, 4000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    env = np.sin(np.pi * t / dur) ** 2
    return np.stack([x * env, np.roll(x, 300) * env]).astype(np.float32) * 0.5


def static(dur):
    """Broken-signal burst: crackle + band-limited hiss with dropouts."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    hiss = signal.sosfilt(signal.butter(2, [1500, 9000], "bandpass", fs=SR, output="sos"), rng.standard_normal(n))
    crackle = (rng.random(n) < 0.004) * rng.standard_normal(n) * 6.0
    gate = np.repeat(rng.random(int(dur * 40) + 1) > 0.25, SR // 40 + 1)[:n]
    x = (hiss * 0.5 + crackle) * gate * np.exp(-t / (dur * 0.8))
    return np.stack([x, np.roll(x, 120)]).astype(np.float32) * 0.6


def bell(f, dur=4.0):
    """Soft FM bell."""
    t = np.arange(int(dur * SR)) / SR
    idx = 2.5 * np.exp(-t * 3.0)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 1.41 * t)) * np.exp(-t * 1.3) * (1 - np.exp(-t * 300))
    return x


def motif(notes, step, dur=4.0):
    """The film's recurring signature: a few bell notes, slightly spread in stereo."""
    n = int((step * (len(notes) - 1) + dur) * SR) + int(len(notes)) + 1
    out = np.zeros((2, n))
    for k, f in enumerate(notes):
        b = bell(f, dur)
        i = int(k * step * SR)
        pan = 0.5 + 0.3 * (k - (len(notes) - 1) / 2) / max(1, len(notes) - 1)
        out[0, i:i + len(b)] += b * (1 - pan)
        out[1, i:i + len(b)] += b * pan
    return out.astype(np.float32)


def stutter(bus, at, slice_s, repeats, gain):
    i, n = int(at * SR), int(slice_s * SR)
    piece = bus[:, i:i + n].copy() * ramp(n, 0.003, 0.003)
    for k in range(1, repeats + 1):
        j = i + k * n
        if j + n <= bus.shape[1]:
            bus[:, j:j + n] = bus[:, j:j + n] * (1 - gain) + piece * gain


def limiter(x, ceiling=0.89, release=0.08):
    peak = maximum_filter1d(np.abs(x).max(0), size=int(0.004 * SR) + 1)
    g = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    a = np.exp(-1.0 / (release * SR))
    smooth = signal.lfilter([1 - a], [1, -a], g - 1.0) + 1.0
    return x * np.minimum(g, smooth)


# ------------------------------------------------------------------ build
def build(mix_path):
    cfg = json.loads(Path(mix_path).read_text())
    n = int(cfg["duration"] * SR)
    music = np.zeros((2, n), np.float32)
    fxbus = np.zeros((2, n), np.float32)
    cache = {}

    for s in cfg["segments"]:
        src = cache.setdefault(s["src"], load(s["src"]))
        a, b = int(s["in"] * SR), int((s["in"] + s["dur"]) * SR)
        seg = src[:, a:b].copy()
        if "rate" in s:    # gentle speed change (pitch follows, like tape)
            import soxr
            seg = soxr.resample(seg.T, SR, int(SR / s["rate"])).T.copy()
        seg *= ramp(seg.shape[1], s.get("fade_in", 0.02), s.get("fade_out", 0.3))
        seg *= db(s.get("gain_db", 0.0))
        if "sub" in s:
            seg += sub_bass(seg, s["sub"]["hz"], s["sub"].get("gain_db", -10.0))
        place(music, s["at"], seg)
        print(f"  {s['id']:<14} {s['at']:7.2f}s  {seg.shape[1] / SR:6.2f}s  from {Path(s['src']).name}@{s['in']}")

    for f in cfg.get("fx", []):
        typ, g = f["type"], db(f.get("gain_db", 0.0))
        if typ == "paulstretch":
            src = cache.setdefault(f["src"], load(f["src"]))
            a = int(f["in"] * SR)
            x = paulstretch(src[:, a:a + int(f["len"] * SR)], f["stretch"])[:, :int(f["dur"] * SR)]
            place(fxbus, f["at"], x * ramp(x.shape[1], f.get("fade_in", 0.5), f.get("fade_out", 1.0)), g)
        elif typ == "riser":
            place(fxbus, f["at"], riser(f["dur"]), g)
        elif typ == "heartbeat":
            hb = heartbeat(f["dur"], f.get("bpm", 70))
            place(fxbus, f["at"], hb * ramp(hb.shape[1], f.get("fade_in", 0.3), f.get("fade_out", 0.5)), g)
        elif typ == "impact":
            place(fxbus, f["at"], impact(f.get("dur", 3.0)), g)
        elif typ == "whoosh":
            place(fxbus, f["at"], whoosh(f["dur"]), g)
        elif typ == "static":
            place(fxbus, f["at"], static(f["dur"]), g)
        elif typ == "motif":
            place(fxbus, f["at"], motif(f.get("notes", MOTIF), f.get("step", 0.55), f.get("dur", 4.0)), g)

    mix = music + fxbus
    for f in cfg.get("fx", []):            # edits that act on the finished mix
        if f["type"] == "stutter":
            stutter(mix, f["at"], f["slice"], f["repeats"], f.get("mix", 1.0))
    for f in cfg.get("fx", []):
        if f["type"] == "silence":
            i, m = int(f["at"] * SR), int(f["dur"] * SR)
            mix[:, i:i + m] *= 1.0 - f.get("depth", 1.0) * ramp(m, 0.03, 0.03)

    mix = signal.sosfilt(signal.butter(2, 25, "highpass", fs=SR, output="sos"), mix, axis=-1)
    # loudness: aim the loud passages (95th pct short-term RMS) at about -14 dBFS RMS, then limit
    blk = int(0.4 * SR)
    st = np.sqrt((mix[:, : n // blk * blk].reshape(2, -1, blk) ** 2).mean((0, 2)))
    mix *= db(-13.0) / (np.percentile(st, 95) + 1e-9)
    mix = limiter(mix)
    mix *= ramp(n, 0.0, cfg.get("end_fade", 0.4))
    out = ROOT / cfg.get("out", "audio/soundtrack.wav")
    sf.write(str(out), mix.T, SR, subtype="PCM_24")
    print(f"[mix] peak {20 * np.log10(np.abs(mix).max() + 1e-9):.1f} dBFS → {out}")
