#!/usr/bin/env python3
"""Find a beat-aligned edit that fits a track into an act of fixed length while keeping its real opening AND
its real ending: head = [start, a), tail = [b, end).  a and b are beats the same number of bars apart in phase,
picked so the music on both sides of the cut sounds alike (chroma + loudness), and (a - start) + (end - b) ≈ length.

  .venv/bin/python music/find_splice.py audio/sources/cc/Waltz_of_the_Carnies.wav --start 0 --length 55 --meter 3
"""
import argparse

import librosa
import numpy as np


def natural_end(y, sr, floor_db=-50.0):
    """Last moment the track is above floor_db (relative to its peak RMS): where its ending has rung out."""
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    db = 20 * np.log10(rms / rms.max() + 1e-9)
    idx = np.nonzero(db > floor_db)[0]
    return float(librosa.frames_to_time(idx[-1], sr=sr, hop_length=512))


def find(path, start, length, meter=4, bpm=None, head_min=0.45, head_max=0.85, end=None):
    y, sr = librosa.load(path, sr=22050, mono=True)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=bpm or 120, units="time")
    end = end or natural_end(y, sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    fr = lambda t: int(librosa.time_to_frames(t, sr=sr, hop_length=512))

    def sig(t, span=2.0):
        a, b = fr(t), fr(t + span)
        c = chroma[:, a:b].mean(1)
        return c / (np.linalg.norm(c) + 1e-9), 20 * np.log10(rms[a:b].mean() + 1e-9)

    best = None
    for i, a in enumerate(beats):
        h = a - start
        if not head_min * length <= h <= head_max * length:
            continue
        want_b = end - (length - h)
        for j, b in enumerate(beats):
            if b <= a or abs(b - want_b) > 0.6 or (j - i) % meter:
                continue
            ca, la = sig(a)
            cb, lb = sig(b)
            score = float(ca @ cb) - 0.04 * abs(la - lb) - 0.5 * abs(b - want_b)
            if best is None or score > best[0]:
                best = (score, a, b)
    if best is None:
        raise SystemExit("no splice found; widen head range")
    score, a, b = best
    return dict(start=start, cut_at=round(float(a), 3), resume=round(float(b), 3), end=round(end, 3),
                total=round(float(a - start + end - b), 3), score=round(score, 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--length", type=float, required=True)
    ap.add_argument("--meter", type=int, default=4)
    ap.add_argument("--bpm", type=float)
    ap.add_argument("--end", type=float)
    args = ap.parse_args()
    print(find(args.path, args.start, args.length, args.meter, args.bpm, end=args.end))
