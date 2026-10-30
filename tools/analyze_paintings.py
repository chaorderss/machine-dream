#!/usr/bin/env python3
"""Machine-vision analysis of every painting → assets/analysis/ (AI as measurement only: nothing here draws a pixel
that reaches the film; the results are data that drive shaders and geometry).

  depth/<id>.png      16-bit Depth Anything V2 small (1 = near), long side 1024
  seg/<id>.png        16-bit SAM 2.1 base-plus label map (0 = none, 1.. = segments, largest first), long side 1024
  seg/<id>.json       per segment: bbox (uv, top-down), area, score, centroid
  dino/<id>.npy       DINOv2 large patch tokens, PCA to 32 dims (float16), grid 37 x 37 over the square-resized image

Results are cached: a file that exists is never recomputed.   VRAM is capped (the GPU is shared).

  .venv-music/bin/python tools/analyze_paintings.py depth dino seg
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import os
import torch
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PAINT = ROOT / "assets" / "paintings"
OUT = ROOT / "assets" / "analysis"
MODELS = Path(os.environ.get("MODELS_DIR", ROOT / "models"))
HF = MODELS / "huggingface" / "hub"
DEPTH_MODEL = str(MODELS / "depth-anything-v2-small")
DINO_MODEL = str(MODELS / "dinov2-large")
SAM_MODEL = next((HF / "models--facebook--sam2.1-hiera-base-plus" / "snapshots").iterdir())
LONG = 1024
DEV = "cuda" if torch.cuda.is_available() else "cpu"
if DEV == "cuda":
    torch.cuda.set_per_process_memory_fraction(3.8 / (torch.cuda.get_device_properties(0).total_memory / 2**30))


def ids():
    cat = json.loads((PAINT / "catalog.json").read_text())
    return [k for k in cat if (PAINT / f"{k}.png").exists()]


def load(pid):
    im = Image.open(PAINT / f"{pid}.png").convert("RGB")
    s = LONG / max(im.size)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def run_depth():
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    (OUT / "depth").mkdir(parents=True, exist_ok=True)
    proc = AutoImageProcessor.from_pretrained(DEPTH_MODEL)
    model = AutoModelForDepthEstimation.from_pretrained(DEPTH_MODEL).to(DEV).eval()
    for pid in ids():
        f = OUT / "depth" / f"{pid}.png"
        if f.exists():
            continue
        im = load(pid)
        inp = proc(images=im, return_tensors="pt", size={"height": 770, "width": 770}, do_resize=True).to(DEV)
        with torch.no_grad():
            d = model(**inp).predicted_depth
        d = torch.nn.functional.interpolate(d[None], size=im.size[::-1], mode="bicubic", align_corners=False)[0, 0]
        d = d.cpu().numpy().astype(np.float32)
        lo, hi = np.percentile(d, 0.5), np.percentile(d, 99.5)
        d = np.clip((d - lo) / max(hi - lo, 1e-6), 0, 1)
        Image.fromarray((d * 65535).astype(np.uint16)).save(f)
        print("depth", pid, flush=True)


def run_dino():
    from transformers import AutoImageProcessor, AutoModel
    (OUT / "dino").mkdir(parents=True, exist_ok=True)
    proc = AutoImageProcessor.from_pretrained(DINO_MODEL)
    model = AutoModel.from_pretrained(DINO_MODEL).to(DEV).eval()
    all_ids = ids()
    feats = {}
    for pid in all_ids:
        im = load(pid).resize((518, 518), Image.BICUBIC)
        inp = proc(images=im, return_tensors="pt", do_resize=False, do_center_crop=False).to(DEV)
        with torch.no_grad():
            t = model(**inp).last_hidden_state[0, 1:].cpu().numpy()
        feats[pid] = t.astype(np.float32)
        print("dino", pid, flush=True)
    X = np.concatenate([feats[p] for p in all_ids])
    mean = X.mean(0)
    idx = np.random.default_rng(0).choice(len(X), min(30000, len(X)), replace=False)
    _, _, vt = np.linalg.svd(X[idx] - mean, full_matrices=False)
    comp = vt[:32]
    for pid in all_ids:
        np.save(OUT / "dino" / f"{pid}.npy", ((feats[pid] - mean) @ comp.T).astype(np.float16).reshape(37, 37, 32))
    np.savez(OUT / "dino" / "_pca.npz", mean=mean, comp=comp)


class Sam:
    """SAM 2.1 used directly: one image embedding, then batches of point prompts on the low-res mask decoder."""

    def __init__(self):
        from transformers import Sam2Model, Sam2Processor
        self.proc = Sam2Processor.from_pretrained(str(SAM_MODEL))
        self.model = Sam2Model.from_pretrained(str(SAM_MODEL)).to(DEV).eval()

    def embed(self, im):
        self.im = im
        inp = self.proc(images=im, return_tensors="pt").to(DEV)
        with torch.no_grad():
            self.emb = self.model.get_image_embeddings(inp["pixel_values"])

    def points(self, pts, labels=None, multimask=True):
        """pts: list of objects, each a list of [x, y] px → (masks n, k, 256, 256 logits, iou n, k)."""
        lab = labels or [[1] * len(p) for p in pts]
        inp = self.proc(images=self.im, input_points=[pts], input_labels=[lab], return_tensors="pt").to(DEV)
        with torch.no_grad():
            out = self.model(image_embeddings=self.emb, input_points=inp["input_points"], input_labels=inp["input_labels"],
                             multimask_output=multimask)
        return out.pred_masks[0], out.iou_scores[0]


def run_seg(side=32, batch=12):
    (OUT / "seg").mkdir(parents=True, exist_ok=True)
    sam = Sam()
    for pid in ids():
        f = OUT / "seg" / f"{pid}.png"
        if f.exists() or pid.startswith("space_") or pid == "cmb":
            continue
        im = load(pid)
        w, h = im.size
        sam.embed(im)
        gx, gy = np.meshgrid((np.arange(side) + 0.5) / side * w, (np.arange(side) + 0.5) / side * h)
        pts = np.stack([gx.ravel(), gy.ravel()], 1).tolist()
        cand = []
        for i in range(0, len(pts), batch):
            while True:                            # the GPU is shared: wait out a full card instead of dying
                try:
                    masks, iou = sam.points([[p] for p in pts[i:i + batch]])
                    break
                except torch.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    time.sleep(20)
            hard, soft0, soft1 = masks > 0, masks > 1, masks > -1
            stab = soft0.flatten(2).sum(2).float() / soft1.flatten(2).sum(2).float().clamp(min=1)
            good = (iou > 0.72) & (stab > 0.86)
            for n, k in good.nonzero().tolist():
                cand.append((float(iou[n, k]), hard[n, k].cpu().numpy()))
        cand.sort(key=lambda c: -c[0])
        kept, areas = [], []                      # greedy mask NMS at 256 x 256
        for sc, m in cand:
            a = int(m.sum())
            if a < 12:
                continue
            if any((m & k).sum() / max(1, (m | k).sum()) > 0.7 for _, k in kept):
                continue
            kept.append((sc, m))
        kept.sort(key=lambda c: -int(c[1].sum()))
        lab = np.zeros((h, w), np.uint16)
        meta = []
        for sc, m in kept:                         # largest first, smaller segments paint over them
            mk = np.array(Image.fromarray(m.astype(np.uint8) * 255).resize((w, h), Image.BILINEAR)) > 127
            lab[mk] = len(meta) + 1
            meta.append({"score": sc})
        out = []
        for i, m in enumerate(meta):
            ys, xs = np.nonzero(lab == i + 1)
            out.append(None if len(xs) < 30 else
                       dict(m, area=float(len(xs)) / (w * h), bbox=[float(xs.min()) / w, float(ys.min()) / h,
                                                                     float(xs.max() + 1) / w, float(ys.max() + 1) / h],
                            c=[float(xs.mean()) / w, float(ys.mean()) / h]))
        Image.fromarray(lab).save(f)
        (OUT / "seg" / f"{pid}.json").write_text(json.dumps(out))
        print("seg", pid, len(meta), flush=True)
        torch.cuda.empty_cache()


if __name__ == "__main__":
    for step in sys.argv[1:] or ("depth", "dino", "seg"):
        {"depth": run_depth, "dino": run_dino, "seg": run_seg}[step]()
