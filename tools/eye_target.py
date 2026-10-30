#!/usr/bin/env python3
"""The open eye at 1080p → assets/analysis/eye_target.png: the eye that the Infinite Painting (tools/build_infinite.py) and the
mirrored eyes in Narcissus and Saturn have to match.

  .venv/bin/python tools/eye_target.py
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.features import Features                # noqa: E402
from engine.renderer import Engine                  # noqa: E402
from engine.timeline import Timeline                # noqa: E402

tl = Timeline(ROOT / "config" / "timeline.json")
e = Engine(tl, Features(ROOT / "analysis" / "features.npz"), (1920, 1080), 30)
Image.frombytes("RGB", (1920, 1080), e.render_frame(1.5, 1 / 30)).save(ROOT / "assets" / "analysis" / "eye_target.png")
