#!/usr/bin/env python3
"""Inside a Machine Dream — render pipeline.

  python main.py mix                      # build audio/soundtrack.wav from config/mix.json
  python main.py analyze                  # audio → analysis/features.npz
  python main.py stills 0:01 1:30 ...     # contact sheet → output/stills/contact.png
  python main.py render --preset preview  # 1080p30 preview  (draft | preview | final | short)
  python main.py render --preset final    # 4K60 master
  python main.py render --preset short --start 2:00 --end 2:40   # native 9:16 Short
"""
import argparse
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PRESETS = {
    "draft":   dict(size=(960, 540), fps=30, crf=23, preset="veryfast"),
    "preview": dict(size=(1920, 1080), fps=30, crf=20, preset="fast"),
    "final":   dict(size=(3840, 2160), fps=60, crf=16, preset="slow"),
    "short":   dict(size=(2160, 3840), fps=60, crf=16, preset="slow"),
}


def parse_time(s):
    s = str(s)
    if ":" in s:
        m, sec = s.split(":")
        return int(m) * 60 + float(sec)
    return float(s)


def load(args):
    from engine.features import Features
    from engine.timeline import Timeline
    tl = Timeline(ROOT / args.timeline)
    feats = Features(ROOT / tl.features if tl.features else None)
    return tl, feats


def cmd_render(args):
    from engine.encoder import FFmpegWriter
    from engine.renderer import Engine
    tl, feats = load(args)
    p = dict(PRESETS[args.preset])
    if args.size:
        p["size"] = tuple(map(int, args.size.lower().split("x")))
    if args.fps:
        p["fps"] = args.fps
    t0 = parse_time(args.start)
    t1 = parse_time(args.end) if args.end else tl.duration
    fps = p["fps"]
    n = int(round((t1 - t0) * fps))
    out = Path(args.out or ROOT / "output" / f"machine_dream_{args.preset}_{int(t0)}-{int(t1)}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    audio = ROOT / tl.audio if tl.audio and (ROOT / tl.audio).exists() else None
    eng = Engine(tl, feats, p["size"], fps)
    eng.preroll(t0)
    wr = FFmpegWriter(out, p["size"], fps, audio, t0, t1 - t0, crf=p["crf"], preset=p["preset"])
    start = time.time()
    for i in range(n):
        wr.write(eng.render_frame(t0 + i / fps, 1.0 / fps))
        if i % (fps * 5) == 0 or i == n - 1:
            el = time.time() - start
            rate = (i + 1) / max(el, 1e-6)
            print(f"\r{i + 1}/{n} frames  {rate:5.1f} fps  ETA {(n - i - 1) / rate / 60:5.1f} min", end="", flush=True)
    code = wr.close()
    print(f"\n→ {out}  (ffmpeg exit {code})   flash-safety worst: {eng.flash_report():.1f} swings/s")


def cmd_stills(args):
    from engine.renderer import Engine
    tl, feats = load(args)
    p = PRESETS[args.preset]
    fps = p["fps"]
    eng = Engine(tl, feats, p["size"], fps)
    eng.readout_on = not args.no_readout
    outdir = ROOT / "output" / "stills"
    outdir.mkdir(parents=True, exist_ok=True)
    imgs = []
    for ts in args.times:
        t = parse_time(ts)
        eng.reset()
        eng.preroll(t)
        img = Image.frombytes("RGB", p["size"], eng.render_frame(t, 1.0 / fps))
        img.save(outdir / f"t{t:07.2f}.png")
        imgs.append((t, img))
        print(f"still {t:.2f}s  [{tl.state(t)[1].id}]")
    w, h = p["size"]
    cols = min(4, len(imgs))
    rows = (len(imgs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w // 2, rows * h // 2), (20, 20, 20))
    for i, (t, img) in enumerate(imgs):
        x, y = (i % cols) * w // 2, (i // cols) * h // 2
        sheet.paste(img.resize((w // 2, h // 2)), (x, y))
        ImageDraw.Draw(sheet).text((x + 6, y + 4), f"{int(t // 60)}:{t % 60:05.2f} {tl.state(t)[1].id}", fill=(255, 255, 0))
    sheet.save(outdir / "contact.png")
    print(f"→ {outdir / 'contact.png'}")


def cmd_analyze(args):
    from analysis.analyze_audio import analyze
    from engine.timeline import Timeline
    tl = Timeline(ROOT / args.timeline)
    analyze(ROOT / (args.audio or tl.audio), ROOT / tl.features)


def cmd_mix(args):
    from music.build_mix import build
    build(ROOT / args.mix)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeline", default="config/timeline.json")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--preset", default="preview", choices=PRESETS)
    r.add_argument("--start", default="0")
    r.add_argument("--end")
    r.add_argument("--size")
    r.add_argument("--fps", type=int)
    r.add_argument("--out")
    s = sub.add_parser("stills")
    s.add_argument("times", nargs="+")
    s.add_argument("--no-readout", action="store_true", help="no SHUTDOWN / MEMORY in the corner (cover frame)")
    s.add_argument("--preset", default="draft", choices=PRESETS)
    a = sub.add_parser("analyze")
    a.add_argument("--audio")
    m = sub.add_parser("mix")
    m.add_argument("--mix", default="config/mix.json")
    args = ap.parse_args()
    {"render": cmd_render, "stills": cmd_stills, "analyze": cmd_analyze, "mix": cmd_mix}[args.cmd](args)


if __name__ == "__main__":
    main()
