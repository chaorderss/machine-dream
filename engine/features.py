"""Music signals sampled at frame time from analysis/features.npz (see analysis/analyze_audio.py)."""
from pathlib import Path

import numpy as np

CONTINUOUS = {
    "uBass": "bass", "uLowMid": "lowmid", "uMid": "mid", "uHigh": "high", "uRms": "rms",
    "uSpring": "spring", "uSpringV": "spring_v", "uOnset": "onset", "uHit": "hit", "uCentroid": "centroid",
}
EVENTS = {"Note": "note_times", "Hi": "hi_times", "Cut": "cut_times", "Pulse": "pulse_times"}


class Features:
    def __init__(self, path):
        self.ok = path is not None and Path(path).exists()
        if not self.ok:
            print(f"[features] {path} missing → silent music signals")
            self.spec = np.zeros((1, 64), np.float32)
            return
        d = np.load(path)
        self.rate = float(d["rate"])
        self.arr = {k: d[k].astype(np.float32) for k in CONTINUOUS.values()}
        self.events = {k: d[v].astype(np.float64) for k, v in EVENTS.items()}
        self.spec = d["spectrum"].astype(np.float32)

    def _interp(self, a, t):
        x = t * self.rate
        i = int(np.clip(np.floor(x), 0, len(a) - 2))
        f = float(np.clip(x - i, 0.0, 1.0))
        return float(a[i] * (1 - f) + a[i + 1] * f)

    def sample(self, t):
        u = {}
        if not self.ok:
            for k in CONTINUOUS:
                u[k] = 0.0
            for k in EVENTS:
                u[f"u{k}Count"], u[f"u{k}Age"] = 0.0, 99.0
            u["uStep"] = float(int(t))
            return u
        for uk, ak in CONTINUOUS.items():
            u[uk] = self._interp(self.arr[ak], t)
        for k, times in self.events.items():
            n = int(np.searchsorted(times, t, side="right"))
            u[f"u{k}Count"] = float(n)
            u[f"u{k}Age"] = float(t - times[n - 1]) if n else 99.0
        # continuous step counter: +1 per pulse, eased over 0.3 s (micro-variation clock)
        x = min(u["uPulseAge"] / 0.3, 1.0)
        u["uStep"] = u["uPulseCount"] - 1.0 + x * x * (3.0 - 2.0 * x)
        return u

    def spectrum(self, t):
        if not self.ok:
            return self.spec[0]
        i = int(np.clip(round(t * self.rate), 0, len(self.spec) - 1))
        return self.spec[i]
