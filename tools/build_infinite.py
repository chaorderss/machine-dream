#!/usr/bin/env python3
"""The Infinite Painting: every painting cut into ~1.6 million cells, each with three places in the world.

  wall    where it is in its own painting, all paintings hung side by side
  sim     a map of visual similarity: cells travel in blocks (still-legible fragments of a painting); DINOv2 features of the
          blocks (analysis data) are laid out with t-SNE and rectified to a grid, so what looks alike ends up side by side
  eye     a cell of the frame-0 eye: assignment by colour rank, so the chaos was always going to be that eye

  .venv/bin/python tools/build_infinite.py        → assets/analysis/infinite.npy
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.cluster import MiniBatchKMeans
from sklearn.manifold import TSNE

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "assets" / "analysis"
W, H = 1690, 950                 # the eye grid
PLANE_H = 40.0                   # world height of the eye plane
COLS, ROWS = 8, 8
BLOCK = 26                       # cells per side of a travelling block


def main():
    rects = json.loads((A / "sheet.json").read_text())
    ids = [k for k in rects if not k.startswith("space_") and k != "cmb"]
    per = (W * H) / len(ids) * 1.04
    rows = []
    feats = []
    cell_w, cell_h = PLANE_H * W / H / COLS, PLANE_H / ROWS
    pal, blocks = [], []
    for n, pid in enumerate(ids):
        x0, y0, x1, y1 = rects[pid]
        pa = (x1 - x0) / (y1 - y0)
        ny = max(8, int(np.sqrt(per / pa)))
        nx = max(8, int(per / ny))
        im = Image.open(ROOT / "assets" / "paintings" / f"{pid}.png").convert("RGB").resize((nx, ny), Image.BOX)
        c = np.array(im, np.float32)[::-1] / 255.0
        d = np.load(A / "dino" / f"{pid}.npy").astype(np.float32)
        gx, gy = np.meshgrid(np.arange(nx), np.arange(ny))
        u, v = (gx + 0.5) / nx, (gy + 0.5) / ny
        # the painting fits its wall cell
        s = min(cell_w / pa, cell_h) * 0.94
        cx = ((n % COLS) + 0.5) * cell_w - PLANE_H * W / H / 2
        cy = PLANE_H / 2 - ((n // COLS) + 0.5) * cell_h
        wx, wy = cx + (u - 0.5) * s * pa, cy + (v - 0.5) * s
        fy, fx = ((1 - v) * 36.99).astype(int), (u * 36.99).astype(int)
        rows.append(np.stack([wx, wy, np.full_like(wx, s / ny * 0.5), x0 + (u - 0.5 / nx) * (x1 - x0), y0 + (v - 0.5 / ny) * (y1 - y0),
                              np.full_like(wx, (x1 - x0) / nx), np.full_like(wx, (y1 - y0) / ny), n * np.ones_like(wx)], -1).reshape(-1, 8))
        pal.append(c.reshape(-1, 3))
        feats.append(d[fy, fx].reshape(-1, 32)[:, :12])
        blocks.append((n * 4096 + (gy // BLOCK) * 64 + gx // BLOCK).ravel())
        print(pid, nx, ny, flush=True)
    R = np.concatenate(rows)
    C = np.concatenate(pal) ** 2.2
    F = np.concatenate(feats)
    B = np.concatenate(blocks)
    r = np.random.default_rng(0)
    # block ids, compact; block means
    ub, inv = np.unique(B, return_inverse=True)
    n = len(ub)
    cnt = np.bincount(inv, minlength=n)[:, None]
    bf = np.stack([np.bincount(inv, F[:, k], n) for k in range(F.shape[1])], 1) / cnt
    bc = np.stack([np.bincount(inv, C[:, k], n) for k in range(3)], 1) / cnt
    bw = np.stack([np.bincount(inv, R[:, k], n) for k in range(2)], 1) / cnt
    X = np.concatenate([(bf - bf.mean(0)) / (bf.std(0) + 1e-6), (bc - bc.mean(0)) / (bc.std(0) + 1e-6) * 2.0], 1)
    xy = TSNE(n_components=2, perplexity=30, init="pca", random_state=0).fit_transform(X)
    # rectify onto a grid of blocks that fills the plane
    gw = PLANE_H * W / H
    nc = int(round(np.sqrt(n * gw / PLANE_H)))
    nr = int(np.ceil(n / nc))
    o = np.argsort(xy[:, 0])
    bsim = np.zeros((n, 2), np.float32)
    for j, col in enumerate(np.array_split(o, nc)):
        col = col[np.argsort(xy[col, 1])]
        bsim[col, 0] = ((j + 0.5) / nc - 0.5) * gw
        bsim[col, 1] = ((np.arange(len(col)) + 0.5) / len(col) - 0.5) * PLANE_H
    print("blocks", n, nc, nr, flush=True)
    keep = np.sort(r.permutation(len(R))[:W * H])
    R, C, inv = R[keep], C[keep], inv[keep]
    N = len(R)
    bseed = r.random(n)
    # eye: rank match in L, then a, then b
    T = np.array(Image.open(A / "eye_target.png").convert("RGB").resize((W, H), Image.BOX), np.float32)[::-1] / 255.0
    T = T.reshape(-1, 3) ** 2.2
    gx, gy = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    grid = np.stack([(gx.ravel() - 0.5) * gw, (gy.ravel() - 0.5) * PLANE_H], 1)

    def opp(c):
        return np.stack([c @ (0.3, 0.6, 0.1), c[:, 0] - c[:, 1], (c[:, 0] + c[:, 1]) / 2 - c[:, 2]], 1)

    def order(c):
        a = opp(c)
        o1 = np.argsort(a[:, 0], kind="stable")
        out = []
        for ch in np.array_split(o1, 180):
            o2 = ch[np.argsort(a[ch, 1], kind="stable")]
            for ch2 in np.array_split(o2, 40):
                out.append(ch2[np.argsort(a[ch2, 2], kind="stable")])
        return np.concatenate(out)
    so, to = order(C), order(T)
    eye = np.zeros((N, 2), np.float32)
    tgt = np.zeros((N, 3), np.float32)
    eye[so] = grid[to]
    tgt[so] = T[to]
    # iA block centre on the wall, block centre on the map; iB eye x, y, offset in block x, y
    # iC uv rect origin, size; iD eye colour, painting; iE half size, cell seed, block seed, block scale on the map
    out = np.zeros((N, 20), np.float32)
    out[:, 0:2] = bw[inv]
    out[:, 2:4] = bsim[inv]
    out[:, 4:6] = eye
    out[:, 6:8] = R[:, :2] - bw[inv]
    out[:, 8:12] = R[:, 3:7]
    out[:, 12:15] = tgt
    out[:, 15] = R[:, 7] / len(ids)
    out[:, 16] = R[:, 2]
    out[:, 17] = r.random(N)
    out[:, 18] = bseed[inv]
    out[:, 19] = (gw / nc) / np.maximum(np.sqrt(np.bincount(inv, minlength=n)[inv] * 1.0) * R[:, 2] * 2, 1e-6)
    np.save(A / "infinite.npy", out[r.permutation(N)])
    print("cells", N)


if __name__ == "__main__":
    main()
