#!/usr/bin/env python3
"""Download the public-domain paintings used as visual anchors → assets/paintings/<id>.png + catalog.json.

Each painting is the lead image of its Wikipedia article (or a Commons search hit), fetched from Wikimedia
Commons at <=3840 px and only kept when Commons tags it public domain (deep-space images may be CC BY;
the catalog marks those as needing attribution). Per painting we also store:
  * alpha channel = depth, computed with plain image math (multi-scale luminance + vertical perspective prior),
    no neural depth model, so the visuals stay "no AI"
  * palette: 16 dominant colours ordered round the hue circle (cyclic, so pal(fract(t)) never jumps)
  * focus: the most detailed point near the centre, used as the portal the camera dives into

    .venv/bin/python assets/fetch_paintings.py            # fetch missing ones
    .venv/bin/python assets/fetch_paintings.py --sheet    # contact sheet → output/stills/paintings.png
"""
import colorsys
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
OUT = HERE / "paintings"
UA = {"User-Agent": "machine-dream-renderer/1.0 (offline art video; https://github.com/chaorderss/machine-dream)"}
MAX_SIDE = 3840

# id: (Wikipedia article | "search:<Commons query>" | "File:<Commons file>", manual focus (x, y) uv with y down | None, crop box | None)
# Order follows the director blueprint S01–S60; "space" entries are deep-sky backgrounds for overlays.
PAINTINGS = {
    "adam":        ("The Creation of Adam", (0.53, 0.40), None),                                   # S01 S60
    "carceri":     ("search:Piranesi Carceri plate VII drawbridge", None, None),                   # S02
    "athens":      ("The School of Athens", (0.50, 0.42), None),                                   # S03
    "pearl":       ("Girl with a Pearl Earring", (0.47, 0.60), None),                              # S04
    "narcissus":   ("Narcissus (Caravaggio)", None, None),                                         # S05
    "kircher":     ("search:Kircher Mundus Subterraneus systema ideale pyrophylaciorum", None, None),  # S06
    "magdalene":   ("search:Georges de La Tour Magdalene with the Smoking Flame Google Art Project", None, None),                               # S07
    "drapery":     ("search:Leonardo drapery study", None, None),  # S08
    "wanderer":    ("Wanderer above the Sea of Fog", (0.50, 0.30), None),                          # S09
    "ancient":     ("The Ancient of Days", None, None),                                            # S10
    "jatte":       ("A Sunday Afternoon on the Island of La Grande Jatte", None, None),            # S11
    "voynich":     ("search:Voynich Manuscript 78 Beinecke", None, None),                                  # S12
    "ambassadors": ("The Ambassadors (Holbein)", (0.48, 0.85), None),                              # S13
    "babel":       ("The Tower of Babel (Bruegel)", (0.55, 0.15), None),                           # S14
    "vitruvian":   ("Vitruvian Man", None, None),                                                  # S15
    "tulp":        ("The Anatomy Lesson of Dr. Nicolaes Tulp", None, None),                        # S16
    "cellarius":   ("search:Cellarius Harmonia Macrocosmica planisphaerium Ptolemaicum", (0.5, 0.5), None),  # S17
    "melencolia":  ("Melencolia I", None, None),                                                   # S18
    "sanromano":   ("The Battle of San Romano", None, None),                                       # S19
    "mandala":     ("Mandala", (0.5, 0.5), None),       # S20
    "arnolfini":   ("Arnolfini Portrait", (0.50, 0.36), None),                                     # S21
    "fludd":       ("search:Fludd monochord", None, None),                  # S22
    "redfuji":     ("Fine Wind, Clear Morning", (0.50, 0.35), None),                               # S23
    "odalisque":   ("Grande Odalisque", None, None),                                               # S24
    "vesalius":    ("File:Vesalius 606c.png", (0.45, 0.35), None),                       # S25
    "garden":      ("The Garden of Earthly Delights", None, (0.665, 0.0, 1.0, 1.0)),               # S26 hell wing
    "haeckel":     ("search:Haeckel Kunstformen der Natur Discomedusae", (0.5, 0.5), None),        # S27
    "winter":      ("search:Arcimboldo Winter 1563 Kunsthistorisches", None, None),                # S28
    "saturn":      ("Saturn Devouring His Son", None, None),                                       # S29
    "medusa":      ("Medusa (Caravaggio)", (0.5, 0.5), None),                                      # S30
    "rebels":      ("search:Pieter Bruegel the Elder The Fall of the Rebel Angels Google Art Project", None, None),                         # S31
    "nightmare":   ("The Nightmare", None, None),                                                  # S32
    "cyclops":     ("search:Odilon Redon The Cyclops Kroller-Muller", None, None),                 # S33
    "oiwa":        ("File:Katsushika Hokusai - The Lantern Ghost, Iwa - Google Art Project.jpg", None, None),                   # S34
    "damned":      ("search:Rubens Fall of the Damned Google Art Project", None, None),               # S35
    "voynich2":    ("search:Voynich manuscript 86v", (0.5, 0.5), None),               # S36
    "judgment":    ("The Last Judgment (Michelangelo)", (0.50, 0.30), None),                       # S37
    "wrath":       ("The Great Day of His Wrath", None, None),                                     # S38
    "snowstorm":   ("Snow Storm: Steam-Boat off a Harbour's Mouth", (0.5, 0.5), None),            # S39
    "starry":      ("The Starry Night", (0.83, 0.18), None),                                       # S40
    "empyrean":    ("Paradiso (Dante)", (0.5, 0.45), None),     # S41
    "wave":        ("The Great Wave off Kanagawa", None, None),                                    # S42
    "ascent":      ("search:Bosch Ascent of the Blessed", None, None),                      # S43
    "kiss":        ("The Kiss (Klimt)", None, None),                                               # S44
    "ninthwave":   ("The Ninth Wave", None, None),                                                 # S45
    "comp8":       ("search:Kandinsky Composition VIII 1923", (0.17, 0.25), None),                                       # S46
    "liberty":     ("Liberty Leading the People", None, None),                                     # S47
    "crows":       ("Wheatfield with Crows", None, None),                                          # S48
    "flammarion":  ("Flammarion engraving", None, None),                                           # S49
    "cmb":         ("search:WMAP 2012 cosmic microwave background all-sky map", (0.5, 0.5), None), # S51
    "lilies":      ("File:Claude Monet - The Water Lilies - Setting Sun - Google Art Project.jpg", None, None),  # S52
    "dnieper":     ("Moonlit Night on the Dnieper", None, None),                                   # S53
    "ophelia":     ("search:Millais Ophelia Tate", None, None),                                             # S54
    "serpents":    ("search:Klimt Water Serpents I", None, None),                                  # S55
    "almond":      ("Almond Blossoms", None, None),                                                # S56
    "etoiles":     ("search:Bouguereau Dante and Virgil in Hell", None, None),                     # S57
    "sunrise":     ("Impression, Sunrise", None, None),                                            # S58
    "sistine":     ("File:'Sistine Chapel ceiling' by Michelangelo JBU21.JPG", None, None),  # S59 (CC BY 3.0 photo, credited)
    # deep-space backgrounds (NASA public domain or ESA/Webb CC BY — credit kept in catalog)
    "space_carina":  ("search:Cosmic Cliffs Carina Nebula NIRCam Webb", None, None),
    "space_udf":     ("Hubble Ultra-Deep Field", None, None),
    "space_orion":   ("search:Orion Nebula Hubble mosaic 2006", None, None),
    "space_pillars": ("search:Pillars of Creation Webb NIRCam", None, None),
}


def download(url):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return r.read()
        except Exception as e:
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(3 + 5 * attempt)
    raise RuntimeError(f"download failed: {url}")


def api(base, **params):
    params.update(format="json", formatversion=2)
    url = base + "?" + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(2 + 3 * attempt)
    raise RuntimeError(f"API failed: {url}")


def commons_file(src):
    if src.startswith("File:"):
        return src
    if src.startswith("search:"):
        for attempt in range(4):
            d = api("https://commons.wikimedia.org/w/api.php", action="query", list="search", srnamespace=6,
                    srsearch=src[7:] + " filetype:bitmap", srlimit=1)
            if "query" in d:
                hits = d["query"]["search"]
                return hits[0]["title"] if hits else None
            time.sleep(15 + 15 * attempt)                     # "search is too busy": back off
        raise RuntimeError(f"search error: {d.get('error', d)}")
    d = api("https://en.wikipedia.org/w/api.php", action="query", prop="pageimages", piprop="name",
            titles=src, redirects=1)
    page = d["query"]["pages"][0]
    return "File:" + page["pageimage"] if "pageimage" in page else None


def file_info(title):
    d = api("https://commons.wikimedia.org/w/api.php", action="query", prop="imageinfo", titles=title,
            iiprop="url|extmetadata|size", iiurlwidth=MAX_SIDE)
    page = d["query"]["pages"][0]
    if "imageinfo" not in page:             # en-wiki local file (non-free) → not on Commons
        return None
    ii = page["imageinfo"][0]
    md = ii.get("extmetadata", {})
    strip = lambda k: re.sub("<[^>]+>", "", md.get(k, {}).get("value", "")).strip()  # noqa: E731
    url = ii["thumburl"] if ii["width"] > MAX_SIDE else ii["url"]
    return dict(file=title, url=url, page=ii.get("descriptionurl"), license=strip("LicenseShortName"),
                artist=strip("Artist")[:120], date=strip("DateTimeOriginal")[:40], title=strip("ObjectName")[:120])


def depth_map(rgb):
    """Pseudo depth from image math only: bright, detailed and low regions come forward."""
    g = Image.fromarray(rgb).convert("L")
    w, h = g.size
    lum = lambda r: np.asarray(g.filter(ImageFilter.GaussianBlur(r)), np.float32) / 255.0  # noqa: E731
    fine, mid, coarse = lum(max(1, w // 400)), lum(w // 60), lum(w // 12)
    detail = np.abs(np.asarray(g, np.float32) / 255.0 - fine)
    detail = np.asarray(Image.fromarray((np.clip(detail * 4, 0, 1) * 255).astype(np.uint8))
                        .filter(ImageFilter.GaussianBlur(w // 50)), np.float32) / 255.0
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    d = 0.35 * fine + 0.25 * mid + 0.15 * coarse + 0.15 * detail / (detail.max() + 1e-6) + 0.10 * y
    d = (d - np.percentile(d, 1)) / (np.percentile(d, 99) - np.percentile(d, 1) + 1e-6)
    return np.clip(d, 0, 1)


def palette(rgb, k=16):
    """k-means colours, saturation pushed, ordered round the hue circle so the gradient is cyclic."""
    px = np.asarray(Image.fromarray(rgb).resize((96, 96)), np.float32).reshape(-1, 3) / 255.0
    rng = np.random.default_rng(0)
    c = px[rng.choice(len(px), k, replace=False)]
    for _ in range(20):
        lab = np.argmin(((px[:, None] - c[None]) ** 2).sum(-1), 1)
        c = np.array([px[lab == i].mean(0) if np.any(lab == i) else c[i] for i in range(k)])
    out = []
    for r, g, b in c:
        hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
        out.append((hh, colorsys.hls_to_rgb(hh, 0.12 + 0.76 * ll, min(1.0, ss * 1.5 + 0.08))))
    out.sort(key=lambda x: x[0])
    return [[round(float(v), 4) for v in col] for _, col in out]


def focus_point(rgb, manual):
    if manual:
        return list(manual)
    g = Image.fromarray(rgb).convert("L").resize((160, 90))
    a = np.asarray(g, np.float32) / 255.0
    det = np.abs(a - np.asarray(g.filter(ImageFilter.GaussianBlur(3)), np.float32) / 255.0)
    det = np.asarray(Image.fromarray((det / (det.max() + 1e-6) * 255).astype(np.uint8))
                     .filter(ImageFilter.GaussianBlur(6)), np.float32)
    yy, xx = np.mgrid[0:90, 0:160]
    w = det * np.exp(-(((xx / 160 - 0.5) / 0.22) ** 2 + ((yy / 90 - 0.45) / 0.22) ** 2))
    y, x = np.unravel_index(np.argmax(w), w.shape)
    return [round(x / 160, 3), round(y / 90, 3)]


def fetch(only=None):
    OUT.mkdir(parents=True, exist_ok=True)
    cat_path = OUT / "catalog.json"
    cat = json.loads(cat_path.read_text()) if cat_path.exists() else {}
    for pid, (src, manual, crop) in PAINTINGS.items():
        if only and pid not in only:
            continue
        if pid in cat and (OUT / f"{pid}.png").exists():
            continue
        try:
            title = commons_file(src)
            info = file_info(title) if title else None
        except RuntimeError as e:
            print(f"[fail] {pid}: {e}")
            continue
        if not info:
            print(f"[miss] {pid}: no Commons file for {src!r}")
            continue
        vetted = pid.startswith("space_") or pid == "cmb" or src.startswith("File:")   # hand-picked: CC BY ok, credited
        ok = r"public domain|PD|CC0" + (r"|CC BY(?!-SA)" if vetted else "")
        if not re.search(ok, info["license"], re.I):
            print(f"[skip] {pid}: license {info['license']!r} ({info['file']})")
            continue
        try:
            img = Image.open(io.BytesIO(download(info["url"]))).convert("RGB")
        except RuntimeError as e:
            print(f"[fail] {pid}: {e}")
            continue
        if crop:
            W, H = img.size
            img = img.crop((int(crop[0] * W), int(crop[1] * H), int(crop[2] * W), int(crop[3] * H)))
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        rgb = np.asarray(img)
        d = depth_map(rgb)
        rgba = np.dstack([rgb, (d * 255).astype(np.uint8)])
        Image.fromarray(rgba, "RGBA").save(OUT / f"{pid}.png", optimize=False, compress_level=3)
        cat[pid] = dict(info, source=src, attribution=not re.search(r"public domain|PD|CC0", info["license"], re.I), size=list(img.size), aspect=round(img.size[0] / img.size[1], 4),
                        palette=palette(rgb), focus=focus_point(rgb, manual))
        cat_path.write_text(json.dumps(cat, indent=1, ensure_ascii=False))
        print(f"[ok] {pid:12s} {img.size[0]}x{img.size[1]}  {info['license']:<14s} {info['file'][:70]}")
        time.sleep(1.5)


def sheet():
    cat = json.loads((OUT / "catalog.json").read_text())
    tw, th = 320, 200
    cols = 8
    rows = (len(cat) + cols - 1) // cols
    S = Image.new("RGB", (cols * tw, rows * th), (20, 20, 20))
    dr = ImageDraw.Draw(S)
    for i, (pid, c) in enumerate(cat.items()):
        im = Image.open(OUT / f"{pid}.png")
        rgb, dep = im.convert("RGB"), im.getchannel("A").convert("RGB")
        rgb.thumbnail((tw // 2 * 2, th - 34))
        dep.thumbnail((tw // 2 * 2, th - 34))
        x, y = (i % cols) * tw, (i // cols) * th
        half = tw // 2
        S.paste(rgb.resize((half - 4, th - 34)), (x + 2, y + 2))
        S.paste(dep.resize((half - 4, th - 34)), (x + half + 2, y + 2))
        fx, fy = c["focus"]
        dr.ellipse([x + 2 + fx * (half - 4) - 4, y + 2 + fy * (th - 34) - 4,
                    x + 2 + fx * (half - 4) + 4, y + 2 + fy * (th - 34) + 4], outline=(255, 0, 0), width=2)
        for j, col in enumerate(c["palette"]):
            dr.rectangle([x + 2 + j * (tw - 4) / 16, y + th - 32, x + 2 + (j + 1) * (tw - 4) / 16, y + th - 20],
                         fill=tuple(int(v * 255) for v in col))
        dr.text((x + 4, y + th - 18), f"{pid}  {c['license'][:12]}", fill=(230, 230, 230))
    dst = HERE.parent / "output/stills/paintings.png"
    dst.parent.mkdir(parents=True, exist_ok=True)
    S.save(dst)
    print(dst)


if __name__ == "__main__":
    if "--sheet" in sys.argv:
        sheet()
    else:
        fetch([a for a in sys.argv[1:] if not a.startswith("-")] or None)
