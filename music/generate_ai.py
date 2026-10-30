"""Generate the soundtrack sections locally with ACE-Step 1.5 (MIT) → audio/gen/.

Runs inside .venv-music (see README). Checkpoints live in models/checkpoints/ (big weights are symlinks into
~/models/ace_step_1.5). The DiT runs on the GPU with CPU offload; the 4B planner LM runs on the CPU so this
never needs more than ~5 GB of VRAM next to other GPU jobs.

    .venv-music/bin/python music/generate_ai.py                  # every section, every seed
    .venv-music/bin/python music/generate_ai.py s1_coldopen      # one section
    .venv-music/bin/python music/generate_ai.py s1_coldopen --one   # first seed only (quick test)
    .venv-music/bin/python music/generate_ai.py --pick           # score takes → audio/gen/<section>.wav

Everything that decides the music (captions, structure, key, tempo, length, seeds) is in SECTIONS, so a take is
reproducible from this file alone. All sections share the D minor tonal centre so the crossfades in
config/mix.json land on related harmony; the coda resolves to F major (relative major).
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ACE-Step-1.5"
CKPT = ROOT / "models" / "checkpoints"
OUT = ROOT / "audio" / "gen"
LM = "acestep-5Hz-lm-4B"
MIN_FREE_VRAM_MB = 5000

COMMON = "instrumental, no vocals, cinematic, high fidelity, wide stereo, rich reverb"

# dur = what the mix needs + ~4 s for crossfades. curve = expected loudness shape used by --pick.
SECTIONS = {
    "s1_coldopen": dict(
        dur=19, bpm=72, key="D minor", ts="4", seeds=[11, 23, 37], curve="hit_then_build",
        caption="monumental baroque pipe organ, massive D minor chords, cathedral reverb, deep sub-bass boom on the "
                "first chord, then glitchy electronic stutters, heartbeat kick and a rising tension riser, dark, epic",
        lyrics="[Intro - huge organ chord with sub boom]\n[Instrumental - glitch stutters, heartbeat]\n"
               "[Build - riser]"),
    "s2_satie": dict(
        dur=54, bpm=60, key="D minor", ts="4", seeds=[11, 23, 37], curve="flat_quiet",
        caption="slow mysterious solo piano in the style of Erik Satie, D dorian, sparse melody, gentle bass notes, "
                "long hall reverb, subtle granular glitch textures, minimal, hypnotic, intimate",
        lyrics="[Intro - solo piano]\n[Instrumental - sparse piano melody]\n[Instrumental - granular shimmer]\n"
               "[Outro - piano]"),
    "s3_fugue": dict(
        dur=64, bpm=120, key="D minor", ts="4", seeds=[11, 23, 37], curve="build",
        caption="baroque pipe organ fugue in D minor, counterpoint, toccata, driving electronic pulse, deep sub bass, "
                "modern cinematic hybrid, intensity rising, machine-like precision, abrupt ending",
        lyrics="[Intro - organ fugue subject]\n[Instrumental - counterpoint, electronic pulse enters]\n"
               "[Build - sub bass, faster]\n[Climax]\n[Outro - abrupt stop]"),
    "s4_macabre": dict(
        dur=59, bpm=150, key="D minor", ts="3", seeds=[11, 23, 37], curve="build",
        caption="dark macabre waltz in 3/4, solo violin with tritones, pizzicato strings, xylophone skeleton rattles, "
                "glitch percussion, deep sub bass, orchestral, playful and sinister, Saint-Saens inspired",
        lyrics="[Intro - solo violin tritone]\n[Verse - pizzicato waltz, xylophone]\n"
               "[Instrumental - full orchestra waltz, glitch percussion]\n[Climax - frenzied]"),
    "s5_overload": dict(
        dur=79, bpm=120, key="D minor", ts="4", seeds=[11, 23, 37], curve="build",
        caption="dark epic hybrid orchestral trailer music, brass stabs, thundering timpani, wordless choir, "
                "trailer sub booms, distorted synth bass, relentless build to a massive climax, apocalyptic",
        lyrics="[Intro - low brass and timpani]\n[Build - choir enters]\n[Build - distorted synth, faster]\n"
               "[Climax - full orchestra and choir]\n[Climax]"),
    "s6_reverie": dict(
        dur=52, bpm=66, key="F major", ts="4", seeds=[11, 23, 37], curve="fade",
        caption="dreamy impressionist solo piano in the style of Debussy, F major, soft string pads, arpeggios, "
                "warm, floating, peaceful, gentle, ending very quietly",
        lyrics="[Intro - soft piano]\n[Instrumental - piano arpeggios, string pads]\n[Outro - very quiet, fade out]"),
}


def take_path(name, seed):
    return OUT / f"{name}_seed{seed}.wav"


def free_vram_mb():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"])
        return int(out.decode().split()[0])
    except Exception:
        return None


def generate(names, one=False):
    free = free_vram_mb()
    if free is not None and free < MIN_FREE_VRAM_MB:
        sys.exit(f"only {free} MiB VRAM free (need {MIN_FREE_VRAM_MB}); not starting")
    sys.path.insert(0, str(VENDOR))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")            # all weights are local; never auto-download
    os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
    import acestep.model_downloader as md
    md.MAIN_MODEL_COMPONENTS.remove("acestep-5Hz-lm-1.7B")  # we use the local 4B LM instead
    import soundfile as sf
    from acestep.handler import AceStepHandler
    from acestep.inference import GenerationConfig, GenerationParams, generate_music
    from acestep.llm_inference import LLMHandler

    dit, lm = AceStepHandler(), LLMHandler()
    msg, ok = dit.initialize_service(project_root=str(ROOT / "models"), config_path="acestep-v15-turbo",
                                     device="cuda", offload_to_cpu=True, offload_dit_to_cpu=True,
                                     quantization="int8_weight_only")
    print("[dit]", msg)
    if not ok:
        sys.exit(1)
    msg, ok = lm.initialize(checkpoint_dir=str(CKPT), lm_model_path=LM, backend="pt", device="cpu")
    print("[lm]", msg)
    if not ok:
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    # seed-major order: one take of every section first, so a full mix exists early
    jobs = [(name, seed) for k in range(1 if one else 3) for name in names
            for seed in SECTIONS[name]["seeds"][k:k + 1]]
    for name, seed in jobs:
        s = SECTIONS[name]
        dst = take_path(name, seed)
        if dst.exists():
            print(f"[skip] {dst.name}")
            continue
        params = GenerationParams(
            caption=f"{s['caption']}, {COMMON}", lyrics=s["lyrics"], instrumental=True,
            bpm=s["bpm"], keyscale=s["key"], timesignature=s["ts"], duration=float(s["dur"]), seed=seed, inference_steps=8, shift=3.0,
            thinking=True, use_cot_caption=False, use_cot_metas=False, use_cot_language=False)
        config = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[seed], audio_format="wav")
        res = generate_music(dit, lm, params, config, save_dir=str(OUT / "_raw"))
        if not res.success:
            print(f"[fail] {name} seed {seed}: {res.error}")
            continue
        a = res.audios[0]
        sf.write(dst, a["tensor"].numpy().T, a["sample_rate"], subtype="PCM_24")
        print(f"[ok] {dst.name}  {a['tensor'].shape[-1] / a['sample_rate']:.1f}s")
    shutil.rmtree(OUT / "_raw", ignore_errors=True)


def score(path, curve):
    """Objective take check: clipping, dropouts, loudness and how well the loudness follows the intended shape."""
    import soundfile as sf
    y, sr = sf.read(path, always_2d=True)
    mono = y.mean(1)
    peak = float(np.abs(y).max())
    clip = float((np.abs(y) > 0.999).mean())
    hop = sr // 2
    rms = np.array([np.sqrt(np.mean(mono[i:i + hop] ** 2) + 1e-12) for i in range(0, len(mono) - hop, hop)])
    db = 20 * np.log10(rms)
    loud = float(np.percentile(db, 90))
    dropouts = int(np.sum(db[2:-4] < loud - 35))           # half-seconds of near silence mid-section
    x = np.linspace(0, 1, len(db))
    target = {"build": x, "hit_then_build": np.where(x < 0.12, 1.0, x), "fade": 1 - x,
              "flat_quiet": np.zeros_like(x)}[curve]
    shape = 0.0 if curve == "flat_quiet" else float(np.corrcoef(db, target)[0, 1])
    steady = -float(np.std(np.diff(db)))                    # penalise erratic level jumps
    total = shape * 2.0 + steady * 0.15 - dropouts * 0.3 - clip * 200
    return dict(peak=round(peak, 3), clip=round(clip, 5), loud_db=round(loud, 1), dropouts=dropouts,
                shape=round(shape, 2), total=round(total, 3), dur=round(len(mono) / sr, 1))


def pick():
    report = {}
    for name, s in SECTIONS.items():
        takes = {seed: score(take_path(name, seed), s["curve"]) for seed in s["seeds"] if take_path(name, seed).exists()}
        if not takes:
            continue
        best = max(takes, key=lambda k: takes[k]["total"])
        shutil.copyfile(take_path(name, best), OUT / f"{name}.wav")
        report[name] = dict(best=best, takes=takes)
        print(f"{name:13s} best seed {best}  " + "  ".join(f"{k}:{v['total']:+.2f}" for k, v in takes.items()))
    (OUT / "picks.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--pick" in args:
        pick()
    else:
        generate([a for a in args if a in SECTIONS] or list(SECTIONS), one="--one" in args)
