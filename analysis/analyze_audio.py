"""Audio → music signals for the shaders (analysis/features.npz), sampled at 200 Hz.

Beyond plain band energies this extracts what makes visuals feel directed rather than twitchy:
  * EMA envelopes (fast attack, slow release) instead of raw energy
  * a damped spring driven by loudness: visuals get weight and keep rippling after the music stops
  * note onsets (spectral flux peaks) → discrete events: Chladni modes, fold steps, seeds
  * high-band onsets (violin/flute register) → tendril twitches
  * tutti events (sudden loudness jumps, rate-limited) → automatic camera cuts
  * spectral centroid → cold/warm colour grade
"""
import numpy as np

RATE = 200
SR = 48000


def norm(x, pct=98.0):
    ref = np.percentile(x[x > 1e-9], pct) if np.any(x > 1e-9) else 1.0
    return np.clip(x / (ref + 1e-9), 0.0, 1.5)


def ema(x, attack, release, rate=RATE):
    a_att, a_rel = np.exp(-1.0 / (attack * rate)), np.exp(-1.0 / (release * rate))
    y = np.empty_like(x)
    s = 0.0
    for i, v in enumerate(x):
        c = a_att if v > s else a_rel
        s = c * s + (1.0 - c) * v
        y[i] = s
    return y


def spring(target, freq=1.4, zeta=0.28, rate=RATE):
    """Underdamped spring following `target`: overshoots and keeps ringing ~2 s after silence."""
    w = 2 * np.pi * freq
    dt = 1.0 / rate
    x = v = 0.0
    xs, vs = np.empty_like(target), np.empty_like(target)
    for i, tgt in enumerate(target):
        v += (w * w * (tgt - x) - 2.0 * zeta * w * v) * dt
        x += v * dt
        xs[i], vs[i] = x, v / w
    return xs, vs


def peaks(env, delta, wait_s, rate=RATE):
    import librosa
    idx = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=int(0.1 * rate), post_avg=int(0.1 * rate),
                                 delta=delta, wait=int(wait_s * rate))
    return np.asarray(idx, int)


def analyze(audio_path, out_path):
    import librosa
    y, sr = librosa.load(str(audio_path), sr=SR, mono=True)
    hop = SR // RATE
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop)).astype(np.float32)
    T = S.shape[1]
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    def band(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        return np.sqrt((S[m] ** 2).mean(0))

    bands = {k: norm(band(lo, hi)) for k, (lo, hi) in
             dict(bass=(25, 150), lowmid=(150, 500), mid=(500, 2500), high=(2500, 12000)).items()}
    out = {k: ema(v, 0.02, 0.25) for k, v in bands.items()}
    rms = norm(librosa.feature.rms(S=S, frame_length=2048)[0][:T])
    out["rms"] = ema(rms, 0.03, 0.4)
    out["spring"], out["spring_v"] = spring(ema(rms, 0.05, 0.6))

    Sdb = librosa.amplitude_to_db(S, ref=np.max)
    onset = librosa.onset.onset_strength(S=Sdb, sr=sr, hop_length=hop)[:T]
    onset_n = norm(onset, 99.5)
    out["onset"] = ema(onset_n, 0.01, 0.15)
    note_idx = peaks(onset_n, 0.07, 0.09)
    hit = np.zeros(T, np.float32)
    hit[note_idx] = np.clip(onset_n[note_idx], 0.0, 1.0)
    out["hit"] = ema(hit, 0.005, 0.35) * 2.5

    hi_m = (freqs >= 2000) & (freqs < 9000)
    hi_on = norm(librosa.onset.onset_strength(S=Sdb[hi_m], sr=sr, hop_length=hop)[:T], 99.5)
    hi_idx = peaks(hi_on, 0.12, 0.12)

    # tutti: loudness jumps well above the recent past, at most one per 2 s
    ldb = 20 * np.log10(librosa.feature.rms(S=S, frame_length=2048)[0][:T] + 1e-6)
    past = np.array([np.median(ldb[max(0, i - RATE):i + 1]) for i in range(T)])
    jump = np.clip((ldb - past - 6.0) / 10.0, 0.0, 1.0)
    cut_idx = peaks(jump, 0.25, 2.0)

    cen = librosa.feature.spectral_centroid(S=S, sr=sr)[0][:T]
    cen = np.clip((np.log(cen + 1.0) - np.log(400.0)) / (np.log(5000.0) - np.log(400.0)), 0.0, 1.0)
    loud = rms > 0.05
    held = cen.copy()
    for i in range(1, T):                       # hold the colour through silences
        if not loud[i]:
            held[i] = held[i - 1]
    out["centroid"] = ema(held, 0.4, 0.8)

    mel = librosa.feature.melspectrogram(S=S ** 2, sr=sr, n_mels=64, fmin=30, fmax=16000)
    spec = np.clip((librosa.power_to_db(mel, ref=np.max) + 70.0) / 70.0, 0.0, 1.0).T
    spec = np.stack([ema(spec[:, b], 0.01, 0.2) for b in range(64)], axis=1)

    # pulses (~1 per second): tracked beats thinned to >=0.7 s apart, gaps >1.4 s filled on a grid.
    # Every scene makes a small change on each pulse.
    _, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop)
    bt = np.asarray(beats, float) / RATE
    pulses, last = [], -10.0
    for b in list(bt) + [len(y) / sr + 10.0]:
        while b - last > 1.4:
            last += 1.0
            pulses.append(last)
        if b - last >= 0.7 and b < len(y) / sr:
            pulses.append(b)
            last = b
    pulse_times = np.array([p for p in pulses if 0.0 <= p < len(y) / sr])

    t_of = lambda idx: idx.astype(np.float64) / RATE  # noqa: E731
    np.savez_compressed(
        out_path, rate=RATE, duration=len(y) / sr, spectrum=spec.astype(np.float16),
        note_times=t_of(note_idx), pulse_times=pulse_times, hi_times=t_of(hi_idx), cut_times=t_of(cut_idx),
        **{k: v.astype(np.float32) for k, v in out.items()})
    print(f"[analyze] {len(y) / sr:.1f}s  pulses={len(pulse_times)}  notes={len(note_idx)}  hi={len(hi_idx)}  cuts={len(cut_idx)}  → {out_path}")
