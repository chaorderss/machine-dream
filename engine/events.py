"""The film's visual events (see engine/dream.py). Each is reusable; all choreography is keyed in absolute film seconds."""
import json
import math

import moderngl
import numpy as np

from .perception import AMBER, CYAN, RED, WHITE
from .renderer import erase_level
from .dream import ANALYSIS, D0, set_u, SHADERS as ROOT_SH, Event, Field, GridMesh, ease, keys, look_at, perspective, plane_frame

IRIS_R, PUPIL_R = 0.47, 0.125
TUNNEL = 16.0                              # length of the space inside the pupil


def crop_uv(sheet, pid, cat, r, aspect=1.0, cx=None, cy=None):
    """Sheet rect of a square-ish crop of painting pid, half-size r (fraction of its short side), round its focus."""
    x0, y0, x1, y1 = sheet.rects[pid]
    pa = (x1 - x0) / (y1 - y0)
    fx, fy = cat[pid]["focus"] if cx is None else (cx, cy)
    rx, ry = (r / pa, r) if pa > 1 else (r, r * pa)
    rx *= aspect
    u = np.clip(fx, rx, 1 - rx)
    v = np.clip(1 - fy, ry, 1 - ry)
    return x0 + (u - rx) * (x1 - x0), y0 + (v - ry) * (y1 - y0), x0 + (u + rx) * (x1 - x0), y0 + (v + ry) * (y1 - y0)


class Eye(Event):
    """The eye of every painting: thousands of shards orbiting on the iris, the pupil a space falling inwards for ever.
    Everything moves with whole laps per 300 s, so the end of the film is frame 0. Diving in, the shards along the
    tunnel turn with depth into pixels, then glowing data points, and the last point opens as light."""

    def load(self):
        r = np.random.default_rng(13)
        sh, cat = self.sheet, self.eng.paint.cat
        art = sh.art
        rows = []
        # iris: rings of shards, finer towards the pupil
        rad, ring = PUPIL_R + 0.012, 0
        while rad < IRIS_R - 0.005:
            sz = 0.010 + 0.016 * (rad - PUPIL_R) / (IRIS_R - PUPIL_R)
            n = int(2 * np.pi * rad / (sz * 2.05))
            laps = (1 + ring % 3) * (1 if ring % 2 else -1) * 2
            for k in range(n):
                pid = art[r.integers(len(art))]
                u0, v0, u1, v1 = crop_uv(sh, pid, cat, r.uniform(0.09, 0.3))
                rows.append([rad + r.normal(0, 0.002), 2 * np.pi * (k + r.uniform(-0.15, 0.15)) / n, 0.0, sz * r.uniform(1.1, 1.3),
                             u0, v0, u1, v1, r.random(), r.random(), laps, 0.0])
            rad += sz * 2.1
            ring += 1
        self.n_iris = len(rows)
        # inside the pupil: fragments on a narrowing tunnel, falling inwards
        for k in range(26000):
            z = r.random() * TUNNEL
            pid = art[r.integers(len(art))]
            u0, v0, u1, v1 = crop_uv(sh, pid, cat, r.uniform(0.06, 0.2))
            rows.append([0.0, r.random() * 2 * np.pi, z, r.uniform(0.004, 0.011), u0, v0, u1, v1, r.random(), r.random(),
                         0.0, 1.0])
        # limbus: a soft gold ring
        for k in range(420):
            rows.append([IRIS_R + r.normal(0.006, 0.004), 2 * np.pi * k / 420, 0.0, 0.05, 0, 0, 1, 1, r.random(), r.random(), 0.0, 2.0])
        r2 = np.random.default_rng(31)                    # its own stream: the iris layout must not change
        last = [list(crop_uv(sh, "adam", cat, r2.uniform(0.05, 0.16), 1.0, r2.uniform(0.2, 0.62), r2.uniform(0.3, 0.6))) for _ in rows]
        self.field = self.keep(Field(self.eng, "field_eye.glsl", np.c_[np.array(rows, np.float32), np.array(last, np.float32)]))
        self.spark = None
        self.lid = self.keep(self.ctx.program(vertex_shader="""#version 430
void main() { gl_Position = vec4(vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0, 0.0, 1.0); }""",
                                              fragment_shader=(ROOT_SH / "lid.fs").read_text()))
        self.lid_vao = self.keep(self.ctx.vertex_array(self.lid, []))

    def draw(self, u, t, extra):
        dive = (u.get("uDive", 0.0))                      # 0 at the eye .. 1 at the far end of the tunnel
        zoom = u.get("uEyeZoom", 1.0)
        z = D0 / zoom - (D0 + TUNNEL * 0.995) * dive ** 2.2 if dive > 0 else D0 / zoom
        self.cam.near = 0.003
        self.cam.set((0, 0, z), (0, 0, z - 1.0))
        self.bind("uSheet", self.sheet.tex)
        fu = dict(self.cam.uniforms(), uLoop=t % 300.0, uShatter=u.get("uShatter", 0.0), uDive=dive, uFog=0.0, uLightAmt=0.0,
                  uBreath=float(u.get("uBass", 0.0)) * u.get("uEyeBeat", 0.0), uFocusK=float(u.get("uFocusK", 0.0)), uMem=float(u.get("uMemory", 1.0)), uFogCol=(0, 0, 0), uLightDir=(0, 0, 1))
        self.field.draw(fu)
        self.field.draw(fu, additive=True)
        lid = float(u.get("uLid", 1.1))
        if lid < 1.05:                                    # frame 0 and the last frame: the eye is shut, the screen black
            self.eng.spark_gain = min(lid / 0.25, 1.0)
            self.lid["uA"].value = lid
            self.lid["uRes"].value = (float(self.eng.w), float(self.eng.h))
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self.lid_vao.render(moderngl.TRIANGLES, vertices=3)
            self.ctx.disable(moderngl.BLEND)


def geodesic(mask, seeds):
    """Steps through a boolean grid from seed cells (4-neighbour BFS), inf outside."""
    from collections import deque
    d = np.full(mask.shape, np.inf)
    q = deque()
    for y, x in seeds:
        d[y, x] = 0
        q.append((y, x))
    h, w = mask.shape
    while q:
        y, x = q.popleft()
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and d[yy, xx] == np.inf:
                d[yy, xx] = d[y, x] + 1
                q.append((yy, xx))
    return d


class Hands(Event):
    """Layer 01: the Creation of Adam as geometry, God's arm lifted off a clean plate. Layer 02: that arm is rebuilt from
    voxels from the start, indistinguishable from paint until uS sweeps from the fingertip to the shoulder."""
    CELL = 0.0021
    GAP = (0.3785, 0.455)
    RELIEF = 0.10

    def load(self):
        from PIL import Image
        from scipy.ndimage import distance_transform_edt, gaussian_filter
        paint = self.eng.paint
        self.mesh = GridMesh(self.eng, "shade_hand.glsl", cols=900, rows=420)
        self.keep(self.mesh.prog)
        im = Image.open(ANALYSIS / "plate" / "adam_godarm.png").transpose(Image.FLIP_TOP_BOTTOM)
        self.plate = self.keep(self.ctx.texture(im.size, 4, data=im.tobytes()))
        self.plate.build_mipmaps()
        self.plate.filter = (9987, 9729)
        self.plate.anisotropy = 8.0
        self.info = paint.info("adam")
        pa = self.info["aspect"]
        c = self.CELL
        nx, ny = int(pa / c), int(1.0 / c)
        m = np.array(Image.open(ANALYSIS / "mask" / "adam_godarm.png").resize((nx, ny), Image.BILINEAR)) > 127
        dp = np.array(Image.open(ANALYSIS / "depth" / "adam.png").resize((nx, ny), Image.BILINEAR), np.float32) / 65535.0
        dp = gaussian_filter(dp, 1.5)
        ys, xs = np.nonzero(m)
        tip = np.argmin(xs)                         # the fingertip is the leftmost cell of the arm
        self.pivot = ((xs[tip] / nx - 0.5) * pa, 0.5 - ys[tip] / ny, float(dp[ys[tip], xs[tip]]) * self.RELIEF)
        d = geodesic(m, [(ys[tip], xs[tip])])
        ok = np.isfinite(d)
        g = np.where(ok, d, 0.0) / d[ok].max()
        thick = np.sqrt(distance_transform_edt(m)) * 0.8
        r = np.random.default_rng(5)
        rows = []
        jit = g + 0.12 * r.random(g.shape)
        gmap = np.where(ok, jit, 9.0).astype(np.float32)[::-1]
        self.gmap = self.keep(self.ctx.texture((nx, ny), 1, data=gmap.tobytes(), dtype="f4"))
        self.gmap.filter = (9728, 9728)
        for y, x in zip(*np.nonzero(ok)):
            u, v = (x + 0.5) / nx, 1.0 - (y + 0.5) / ny
            wx, wy = (u - 0.5) * pa, v - 0.5
            z = float(dp[y, x]) * self.RELIEF
            layers = 1 + int(thick[y, x])
            for k in range(layers):
                rows.append([wx, wy, z + k * c * 1.9, c * 0.5, u - 0.5 / nx, v - 0.5 / ny, u + 0.5 / nx, v + 0.5 / ny,
                             jit[y, x], r.random(), r.random(), float(k)])
        self.field = self.keep(Field(self.eng, "field_hand.glsl", np.array(rows, np.float32), geom="box"))
        print(f"[hands] {len(rows)} voxels")

    def draw(self, u, t, extra):
        pa = self.info["aspect"]
        zm = u.get("uCamZ", 1.0)
        c = self.GAP
        k = min(1.0, max(0.0, (zm - 1.0) / 1.0))               # at cover-fit the frame must stay on the plate
        cx, cy = 0.5 + (c[0] - 0.5) * ease(k), 0.5 + (c[1] - 0.5) * ease(k)
        eye, tgt = plane_frame(pa, (cx, cy), zm, self.cam.aspect)
        sway = np.array([np.sin(t * 0.31) * 0.012, np.sin(t * 0.23 + 1.0) * 0.008, 0.0]) / max(zm, 1.0) ** 0.5
        z0 = float(u.get("uCamPush", 0.12))
        self.cam.near = 0.002
        self.cam.set(np.array(eye) + sway + (0, 0, z0), tgt)
        s = u.get("uS", 0.0)
        self.eng.paint.get("adam")[0].use(location=11)
        self.bind("uTexA", self.plate)
        self.bind("uData", self.gmap)
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uReliefZ=self.RELIEF, uLodD=2.0, uRegion=(0.0, 0.0, 1.0, 1.0),
                            uFog=0.0, uFogCol=(0, 0, 0), uS=s))
        self.field.draw(dict(self.cam.uniforms(), uS=s, uReach=u.get("uReach", 0.0), uKeep=1.0, uTurn=u.get("uTurn", 0.0), uPivot=self.pivot, uTime=t, uFog=0.0, uFogCol=(0, 0, 0),
                             uLightAmt=0.7 * min(1.0, s * 4.0), uLightDir=(0.45, 0.55, 0.7)))
        gap = ((c[0] - 0.5) * pa, 0.5 - c[1], 0.075)
        self.eng.spark_xy = self.cam.project(gap)


class Tower(Event):
    """Babel as built geometry: the painting camera-projected onto a body of revolution taken from its SAM silhouette, so
    the first frame is the painting and every later one is architecture. Dark pixels recess into real arches. Above the
    painted top each tier is wrapped in another painting. Bricks can fly into a Starry Night sheet, or copy themselves."""
    clear = (0.60, 0.68, 0.74, 1.0)
    AX = -0.03                                  # tower axis, world x
    WRAP = ["athens", "sanromano", "carceri", "ambassadors", "mandala", "garden", "jatte", "voynich", "fludd", "kircher",
            "cellarius", "melencolia", "sistine", "judgment", "vitruvian", "haeckel", "odalisque", "tulp", "almond", "kiss"]
    FACES = [("pearl", 0.39, 0.40, 0.2), ("medusa", 0.53, 0.47, 0.2), ("kiss", 0.53, 0.13, 0.12), ("saturn", 0.33, 0.2, 0.12),
             ("narcissus", 0.28, 0.25, 0.15), ("arnolfini", 0.28, 0.2, 0.09), ("arnolfini", 0.72, 0.21, 0.09),
             ("liberty", 0.5, 0.25, 0.1), ("cyclops", 0.335, 0.236, 0.12), ("athens", 0.5, 0.4, 0.12)]

    def load(self):
        from PIL import Image
        from scipy.ndimage import gaussian_filter1d
        r = np.random.default_rng(3)
        sh, cat = self.sheet, self.eng.paint.cat
        info = self.eng.paint.info("babel")
        pa = self.pa = info["aspect"]
        M = np.array(Image.open(ANALYSIS / "mask" / "babel_tower.png").resize((int(pa * 1024), 1024)))[::-1] > 127
        H = 1024
        rows_ = np.nonzero(M.any(1))[0]
        hw = np.zeros(H)
        for i in rows_:
            xs = np.nonzero(M[i])[0]
            hw[i] = max(xs.max() / H - pa / 2 - self.AX, self.AX - (xs.min() / H - pa / 2))
        hw = gaussian_filter1d(np.maximum.accumulate(hw[rows_[::-1]])[::-1], 4)
        ys = rows_ / H - 0.5
        self.y0, self.ytop = ys[0], ys[-1]
        lum = np.asarray(Image.open(self.eng.paint.dir / "babel.png").convert("L").resize((int(pa * 1024), 1024)), np.float32)[::-1] / 255
        R0 = lambda y: np.interp(y, ys, hw)
        sz = 0.0023
        out = []
        sxr = sh.rects["starry"]
        sa = (sxr[2] - sxr[0]) / (sxr[3] - sxr[1])
        y = self.y0
        while y < self.ytop:                         # the painted tower
            rad = float(R0(y))
            if rad < 0.015:
                y += sz * 1.5
                continue
            n = max(8, int(2 * np.pi * rad / (sz * 2.0)))
            ph = r.random() * 6.28
            for k in range(n):
                th = 2 * np.pi * k / n + ph
                x = self.AX + rad * np.sin(th)
                u, v = x / pa + 0.5, y + 0.5
                l = lum[int(min(v, 0.999) * H), int(np.clip(u, 0, 0.999) * lum.shape[1])]
                rec = max(0.0, 1.0 - l / 0.42)
                du, dv = sz / pa, sz * 0.72
                o = self._other(r, sh, y)
                out.append([th, y, rad, sz, u - du, v - dv, u + du, v + dv, r.random(), rec, 0.0, 0.0, *o, *self._star(r, sxr, sa)])
            y += sz * 1.46
        # above the painted top: a tier per painting, for ever narrowing, never ending
        rad = float(R0(self.ytop - 0.02))
        rad0 = rad
        tier_h = 0.11
        for tier in range(1, 44):
            pid = self.WRAP[tier % len(self.WRAP)]
            x0, y0, x1, y1 = sh.rects[pid]
            rad = 0.13 + 0.13 * np.exp(-tier * 0.06)
            s = sz * 1.5 * (1.0 + 0.03 * tier)
            yy = self.ytop + (tier - 1) * tier_h
            ny = int(tier_h / (s * 1.46))
            nx = int(2 * np.pi * rad / (s * 2.0))
            for j in range(ny):
                ring = rad * (1.0 - 0.1 * j / ny) * (1.0 + 0.1 * (j == ny - 1))
                for k in range(nx):
                    th = 2 * np.pi * (k + 0.5 * (j % 2)) / nx
                    a, b = k / nx, j / ny
                    m = 1 - 0.5 / nx
                    uvr = (x0 + a * (x1 - x0), y0 + b * (y1 - y0), x0 + (a + 1 / nx) * (x1 - x0), y0 + (b + 1 / ny) * (y1 - y0))
                    w = float(r.random() < 0.012)
                    if w:
                        f = self.FACES[r.integers(len(self.FACES))]
                        from_ = crop_uv(sh, f[0], cat, f[3], 0.78, f[1], f[2])
                        uvr = from_
                    st = self._star(r, sxr, sa)
                    st[3] = w
                    out.append([th, yy + j * s * 1.46, ring, s, *uvr, r.random(), 0.25 * (j % 4 == 0), float(tier), 1.0,
                                *uvr, *st])
        self.stars = 0
        self.N = len(out)
        d = np.array(out, np.float32)
        d = d[r.permutation(len(d))]                  # copies draw a prefix: it must be a fair sample
        self.field = self.keep(Field(self.eng, "field_tower.glsl", d, geom="box"))
        self.mesh = GridMesh(self.eng, "mesh_shade.glsl", cols=320, rows=240)
        self.keep(self.mesh.prog)
        im = Image.open(ANALYSIS / "plate" / "babel_tower.png").transpose(Image.FLIP_TOP_BOTTOM)
        self.plate = self.keep(self.ctx.texture(im.size, 4, data=im.tobytes()))
        self.plate.build_mipmaps()
        self.plate.filter = (9987, 9729)
        print(f"[tower] {self.N} bricks")

    def _other(self, r, sh, y):
        pid = self.WRAP[r.integers(len(self.WRAP))]
        x0, y0, x1, y1 = sh.rects[pid]
        w = r.uniform(0.03, 0.09)
        a, b = r.random() * (1 - w), r.random() * (1 - w)
        return (x0 + a * (x1 - x0), y0 + b * (y1 - y0), x0 + (a + w) * (x1 - x0), y0 + (b + w) * (y1 - y0))

    def _star(self, r, rect, sa):
        qx, qy = r.random(), r.random()
        x0, y0, x1, y1 = rect
        e = 0.006
        tx, ty = 0.03 + 0.94 * qx, 0.03 + 0.94 * qy      # the painted edge of the canvas stays out of the sky
        return [(qx - 0.5) * sa, qy - 0.5, r.random(), 0.0, x0 + (tx - e) * (x1 - x0), y0 + (ty - e) * (y1 - y0),
                x0 + (tx + e) * (x1 - x0), y0 + (ty + e) * (y1 - y0)]

    def draw(self, u, t, extra):
        pa = self.pa
        ang = float(u.get("uOrbit", 0.0))
        cy = float(u.get("uCamY", 0.0))
        dist = float(u.get("uCamR", D0))
        look = float(u.get("uLookUp", 0.0))
        eye = np.array([self.AX * (1 - min(1.0, ang * 5)) + np.sin(ang) * dist, cy, np.cos(ang) * dist])
        tgt = np.array([self.AX, cy + look, 0.0])
        self.cam.near, self.cam.far = 0.01, 40.0
        self.cam.fov = math.radians(float(u.get("uCamFov", 40.0)))
        self.cam.set(eye, tgt)
        sky = keys(float(u.get("uSkyK", 0.0)), [(0.0, self.clear[:3]), (1.0, (0.035, 0.06, 0.16)), (2.0, (0.0, 0.0, 0.0))])
        self.fbo.clear(*sky, 1.0, depth=1.0)
        self.fog_col = tuple(map(float, sky))
        F = (tgt - eye) / np.linalg.norm(tgt - eye)
        R = np.cross(F, (0, 1, 0))
        R /= np.linalg.norm(R)
        U = np.cross(R, F)
        # the sky it can never reach: the Starry Night, far behind everything, locked to the camera
        gs = float(u.get("uStarSky", 0.0))
        if gs > 0.0:
            P = perspective(self.cam.fov, self.cam.aspect, 0.1, 100.0)
            hh = 30.0 * math.tan(self.cam.fov / 2) * 2.1
            a = float(u.get("uTime")) * 0.05
            c0, s0 = math.cos(a), math.sin(a)
            Rz = np.array([[c0, -s0, 0, 0], [s0, c0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
            T1 = np.eye(4, dtype=np.float32)
            T1[2, 3] = -30.0
            S1 = np.diag([2 * hh, 2 * hh, 1.0, 1.0]).astype(np.float32)
            self.eng.paint.get("starry")[0].use(location=11)
            self.mesh.draw(dict(uVP=(P @ T1 @ Rz @ S1).T.tobytes(), uCamPos=self.cam.eye, uAspectP=self.eng.paint.info("starry")["aspect"],
                                uReliefZ=0.0, uLodD=3.0, uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0), uGain=gs))
        # the plate: a far backdrop that turns with the camera, so the landscape never runs out
        back = float(u.get("uBack", 1.0))
        if back > 0.0:
            ca, sa = np.cos(ang), np.sin(ang)
            Ry = np.array([[ca, 0, sa, 0], [0, 1, 0, 0], [-sa, 0, ca, 0], [0, 0, 0, 1]], np.float32)
            k = float(u.get("uBackScale", 1.0))
            S = np.diag([k, k, k, 1.0]).astype(np.float32)
            T0 = np.eye(4, dtype=np.float32)
            T0[:3, 3] = (0, cy * 0.15 * (k > 1.01), float(u.get("uBackZ", 0.0)))
            vp = (self.cam.vp @ Ry @ T0 @ S).T.tobytes()
            self.plate.use(location=11)
            self.mesh.draw(dict(uVP=vp, uCamPos=self.cam.eye, uAspectP=pa, uReliefZ=0.0, uLodD=3.0, uRegion=(0, 0, 1, 1),
                                uFog=0.0, uFogCol=(0, 0, 0), uGain=back))
        self.eng.paint.get("babel")[0].use(location=11)
        self.bind("uSheet", self.sheet.tex)
        base = dict(self.cam.uniforms(), uAxisX=self.AX, uGrow=u.get("uGrow", 9.0), uDis=u.get("uDis", 0.0),
                    uSwap=u.get("uSwap", 0.0), uDepthK=u.get("uDepthK", 1.0), uFold=u.get("uFold", 0.0), uBurst=u.get("uBurst", 0.0),
                    uSpinT=u.get("uSpinT", 0.0), uCover=u.get("uCover", 0.0062), uR=tuple(map(float, R)), uU=tuple(map(float, U)),
                    uF=tuple(map(float, F)), uFog=u.get("uFogK", 0.03), uFogCol=self.fog_col, uLightAmt=u.get("uLight", 0.55),
                    uLightDir=(0.5, 0.65, 0.57), uCopy=np.eye(4, dtype=np.float32).T.tobytes())
        self.field.draw(base)
        copies = float(u.get("uCopies", 0.0))
        if copies > 0.0:                              # the top starts copying itself and cannot stop
            topy = float(u.get("uGrow", 3.0))
            n = int(math.ceil(copies))
            rng = np.random.default_rng(1)
            for k in range(n):
                sc = 0.45 + 0.5 * rng.random()
                a1, a2 = rng.uniform(-2.4, 2.4), rng.uniform(-3.14, 3.14)
                c, s = np.cos(a1), np.sin(a1)
                Rz = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
                c, s = np.cos(a2), np.sin(a2)
                Ry = np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], np.float32)
                T1 = np.eye(4, dtype=np.float32)
                T1[:3, 3] = (self.AX + rng.normal(0, 0.6), topy * rng.uniform(0.2, 1.1), rng.normal(0, 0.8))
                T2 = np.eye(4, dtype=np.float32)
                T2[:3, 3] = (-self.AX, -self.ytop + 0.2, 0)
                sc *= ease(copies - k)                # each copy grows out of nothing
                M = T1 @ Ry @ Rz @ np.diag([sc, sc, sc, 1.0]).astype(np.float32) @ T2
                self.field.prog["uCopy"].write(M.T.tobytes())
                self.field.n = self.N // 5
                self.field.draw(dict(base, uCopy=M.T.tobytes()))
            self.field.n = self.N


class Infinite(Event):
    """The Infinite Painting (tools/build_infinite.py): every cell of every painting spins free, flows to whatever looks like
    it, and the camera pulls back to find that the chaos was the eye all along."""
    PLANE_H = 40.0

    def load(self):
        self.field = self.keep(Field(self.eng, "field_infinite.glsl", np.load(ANALYSIS / "infinite.npy")))

    def draw(self, u, t, extra):
        h = float(u.get("uViewH", self.PLANE_H))
        z = h * D0
        o = (float(u.get("uCamX", 0.0)), float(u.get("uCamY", 0.0)))
        tilt = float(u.get("uTilt", 0.0))
        self.cam.near, self.cam.far = 0.2, 400.0
        self.cam.set((o[0] + tilt * z, o[1] - tilt * z * 0.6, z), (o[0], o[1], 0.0))
        self.bind("uSheet", self.sheet.tex)
        fu = dict(self.cam.uniforms(), uA=u.get("uA", 0.0), uB=u.get("uB", 0.0), uC=u.get("uC", 0.0), uFuse=u.get("uFuse", 0.0),
                  uBeat=float(u.get("uHit", 0.0)), uFog=0.0, uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1))
        self.field.draw(fu)


def load_plate(ctx, name):
    from PIL import Image
    im = Image.open(ANALYSIS / "plate" / f"{name}.png").transpose(Image.FLIP_TOP_BOTTOM)
    t = ctx.texture(im.size, 4, data=im.tobytes())
    t.build_mipmaps()
    t.filter = (9987, 9729)
    t.anisotropy = 8.0
    return t


def load_mask(ctx, name, size=None):
    from PIL import Image
    im = Image.open(ANALYSIS / "mask" / f"{name}.png").transpose(Image.FLIP_TOP_BOTTOM)
    if size:
        im = im.resize(size, Image.BILINEAR)
    t = ctx.texture(im.size, 1, data=im.tobytes())
    t.filter = (9729, 9729)
    return t


def overlay(eng):
    return eng.overlay_on()


GAP_UV = (0.3785, 0.455)


MEDUSA_EYES = ((0.4817, 0.5856), (0.597, 0.55))     # iris centres, bottom-up uv


class Plate(Event):
    """Layer 01 alone: one painting as real relief under a slow camera (uCamZ, uCX, uCY), breathing (uBreathe), its strokes
    drifting as soft light (uFlowA), water carrying moving reflections (uCaust)."""

    def load(self):
        self.mesh = GridMesh(self.eng, "shade_plate.glsl", cols=640, rows=480)
        self.keep(self.mesh.prog)

    def view(self, u, pa, t):
        z = float(u.get("uCamZ", 1.0))
        cx, cy = float(u.get("uCX", 0.5)), float(u.get("uCY", 0.5))
        vis = min(1.0, pa / self.cam.aspect) / z                      # half-extents stay inside the painting
        hx, hy = vis * self.cam.aspect / (2 * pa), vis / 2
        cx = float(np.clip(cx, min(hx, 0.5), max(1 - hx, 0.5)))
        cy = float(np.clip(cy, min(hy, 0.5), max(1 - hy, 0.5)))
        eye, tgt = plane_frame(pa, (cx, cy), z, self.cam.aspect)
        sw = float(u.get("uSway", 0.02)) / max(z, 1.0) ** 0.5
        return np.array(eye) + (np.sin(t * 0.37) * sw, np.sin(t * 0.29 + 1.0) * sw * 0.6, float(u.get("uPush", 0.14))), np.array(tgt)

    def draw(self, u, t, extra):
        pa = self.eng.paint.info(u["_ch"].painting)["aspect"]
        eye, tgt = self.view(u, pa, t)
        self.cam.near = 0.01
        self.cam.set(eye, tgt)
        rel = float(u.get("uRel", 0.14)) * (1.0 + float(u.get("uBreathe", 0.0)) * 0.3 * math.sin(t * 0.8))
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uAspectC=pa, uReliefZ=rel, uLodD=2.0, uRegion=(0, 0, 1, 1), uFog=0.0,
                            uFogCol=(0, 0, 0), uGain=float(u.get("uGain", 1.0)), uFlowA=float(u.get("uFlowA", 0.0)),
                            uCaust=float(u.get("uCaust", 0.0)), uWaterY=float(u.get("uWaterY", 1.2)), uGlowUp=float(u.get("uGlowUp", 0.0)),
                            uCutE=float(u.get("uCutE", 0.0)), uGazeR=float(u.get("uGazeR", 0.0)), uGaze=(float(u.get("uGazeX", 0.0)), float(u.get("uGazeY", 0.0))),
                            uEyeA=MEDUSA_EYES[0], uEyeB=MEDUSA_EYES[1], uTime=t))


LADDERS = {     # (painting, anchor uv top-down, window radius); shape 1 = square cell, pix = outer painting is a grid of cells
    "stars": dict(chain=[("starry", (0.155, 0.135), 0.05), ("starry", (0.45, 0.33), 0.05), ("starry", (0.75, 0.26), 0.05)], shape=0, pix=0.0),
    "adam": dict(chain=[("adam", (0.3785, 0.455), 0.007), ("adam", (0.3785, 0.455), 0.007), ("adam", (0.3785, 0.455), 0.007)], shape=1, pix=1.0),
    "babel": dict(chain=[("babel", (0.5, 0.3), 0.012), ("babel", (0.5, 0.3), 0.012), ("babel", (0.5, 0.3), 0.012)], shape=1, pix=0.6),
    "garden": dict(chain=[("garden", (0.698, 0.374), 0.0055), ("judgment", (0.5, 0.2), 0.04), ("judgment", (0.5, 0.2), 0.04)], shape=0, pix=0.0),
    "mandala": dict(chain=[("mandala", (0.5, 0.5), 0.055), ("mandala", (0.5, 0.5), 0.055), ("mandala", (0.5, 0.5), 0.055),
                           ("vitruvian", (0.495, 0.172), 0.012), ("vitruvian", (0.495, 0.172), 0.012)], shape=0, pix=0.0),
}


class Ladder(Event):
    """Recursive reality / the micro-worlds in the grid: uStep float along the chain, zooming through each window."""

    def __init__(self, eng, name):
        super().__init__(eng)
        self.L = LADDERS[name]

    def load(self):
        self.prog = self.eng.program("dream/ladder.glsl")

    def draw(self, u, t, extra):
        ch = self.L["chain"]
        st = float(u.get("uStep", 0.0))
        i = min(int(st), len(ch) - 2)
        f = st - i
        tri = [ch[min(i + k, len(ch) - 1)] for k in range(3)]
        get = [self.eng.paint.get(c[0]) for c in tri]
        asp = tuple(g[2]["aspect"] for g in get)
        anc = [(c[1][0], 1.0 - c[1][1]) for c in tri]
        self.eng.draw(self.prog, self.fbo, dict(u, uAA=anc[0], uAB=anc[1], uAC=anc[2], uAsp=asp, uR=(tri[0][2], tri[1][2]), uF=f,
                                                uShape=float(self.L["shape"]), uPix=self.L["pix"] * min(1.0, f * 3.0) * (1 - ease((f - 0.75) / 0.25)),
                                                uRimK=float(u.get("uRim", 1.0)), uSpin=float(u.get("uSpin", 0.0))),
                      [("uTexA", get[0][0]), ("uTexB", get[1][0]), ("uTexC", get[2][0])])


def dino_flow(a, b):
    """Where each part of b lives in a, from DINOv2 patch tokens: nearest neighbour with a spatial prior, smoothed."""
    from scipy.ndimage import gaussian_filter
    Fa = np.load(ANALYSIS / "dino" / f"{a}.npy").astype(np.float32).reshape(-1, 32)
    Fb = np.load(ANALYSIS / "dino" / f"{b}.npy").astype(np.float32).reshape(-1, 32)
    Fa /= np.linalg.norm(Fa, axis=1, keepdims=True) + 1e-6
    Fb /= np.linalg.norm(Fb, axis=1, keepdims=True) + 1e-6
    g = (np.arange(37) + 0.5) / 37
    gx, gy = np.meshgrid(g, 1.0 - g)
    P = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float32)
    D2 = ((P[:, None] - P[None]) ** 2).sum(-1)
    S = Fb @ Fa.T - 1.2 * D2
    k = S.argmax(1)
    d = (P[k] - P).reshape(37, 37, 2)
    return gaussian_filter(d, (2.2, 2.2, 0))[::-1]            # bottom-up


class Morph(Event):
    """Latent mutation along a chain of paintings. uChain = i + m: painting i has become painting i + 1 at m = 1."""

    def __init__(self, eng, chain):
        super().__init__(eng)
        self.chain = chain

    def load(self):
        self.prog = self.eng.program("dream/morph.glsl")
        self.flows = {}

    def flow(self, a, b):
        if (a, b) not in self.flows:
            f = np.concatenate([dino_flow(a, b), dino_flow(b, a)], 2).astype(np.float32)
            t = self.ctx.texture((37, 37), 4, data=f.tobytes(), dtype="f4")
            t.filter = (9729, 9729)
            self.flows[(a, b)] = self.keep(t)
        return self.flows[(a, b)]

    def draw(self, u, t, extra):
        st = float(u.get("uChain", 0.0))
        i = min(int(st), len(self.chain) - 2)
        a, b = self.chain[i], self.chain[i + 1]
        ga, gb = self.eng.paint.get(a), self.eng.paint.get(b)
        self.eng.draw(self.prog, self.fbo, dict(u, uM=ease(st - i), uAspA=ga[2]["aspect"], uAspB=gb[2]["aspect"], uSwirl=float(u.get("uSwirl", 0.1)),
                                                uPalPaint=0.0), [("uTexA", ga[0]), ("uTexB", gb[0]), ("uFlow", self.flow(a, b))])


class Narcissus(Event):
    def load(self):
        from PIL import Image
        self.prog = self.eng.program("dream/narcissus.glsl")
        self.mask = self.keep(load_mask(self.ctx, "narcissus_boy", (1024, 1240)))
        im = Image.open(ANALYSIS / "eye_target.png").convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)
        self.eye = self.keep(self.ctx.texture(im.size, 3, data=im.tobytes()))
        self.eye.filter = (9729, 9729)

    def draw(self, u, t, extra):
        got = self.eng.paint.get("narcissus")
        got[0].use(location=11)
        pa = got[2]["aspect"]
        reach = lambda x: float(keys(x, [(30.0, 0.0), (33.0, 0.5), (36.6, 1.0), (37.6, 1.0)]))
        self.eng.draw(self.prog, self.fbo, dict(u, uReach=reach(t), uReachLate=reach(t - 0.5), uDeep=float(u.get("uDeep", 0.0)), uLed=float(u.get("uLed", 0.0)),
                                                uEyeMix=float(u.get("uEyeMix", 0.0)), uAspP=pa, uZoom=float(u.get("uZoom", 1.0)), uCY=float(u.get("uCY", 0.5))),
                      [("uTexA", self.eye), ("uData", self.mask)])


def voxels(mask_name, pid, cell, relief, seed_at="left"):
    """Cells of a masked subject: x, y, z, half size; rect on the painting; g along it from the seed point, seeds."""
    from PIL import Image
    from scipy.ndimage import gaussian_filter
    info_a = Image.open(ANALYSIS / "mask" / f"{mask_name}.png")
    pa = info_a.width / info_a.height
    nx, ny = int(pa / cell), int(1.0 / cell)
    m = np.array(info_a.resize((nx, ny), Image.BILINEAR)) > 127
    dp = gaussian_filter(np.array(Image.open(ANALYSIS / "depth" / f"{pid}.png").resize((nx, ny), Image.BILINEAR), np.float32) / 65535.0, 1.5)
    ys, xs = np.nonzero(m)
    k = np.argmin(xs) if seed_at == "left" else np.argmin(ys)
    d = geodesic(m, [(ys[k], xs[k])])
    ok = np.isfinite(d)
    g = np.where(ok, d, 0.0) / d[ok].max()
    r = np.random.default_rng(5)
    jit = g + 0.12 * r.random(g.shape)
    rows = []
    for y, x in zip(*np.nonzero(ok)):
        u, v = (x + 0.5) / nx, 1.0 - (y + 0.5) / ny
        rows.append([(u - 0.5) * pa, v - 0.5, float(dp[y, x]) * relief, cell * 0.5, u - 0.5 / nx, v - 0.5 / ny, u + 0.5 / nx, v + 0.5 / ny,
                     jit[y, x], r.random(), r.random(), 0.0])
    gmap = np.where(ok, jit, 9.0).astype(np.float32)[::-1]
    return np.array(rows, np.float32), gmap, (nx, ny), pa


class Wanderer(Event):
    """The wanderer dissolves into the wind; the fog opens; the flat mountains are a real space and the camera goes through."""
    RELIEF = 0.55

    def load(self):
        self.mesh = GridMesh(self.eng, "shade_plate.glsl", cols=800, rows=1000)
        self.keep(self.mesh.prog)
        self.plate = self.keep(load_plate(self.ctx, "wanderer_figure"))
        d, g, sz, self.pa = voxels("wanderer_figure", "wanderer", 0.0026, self.RELIEF, "top")
        self.field = self.keep(Field(self.eng, "field_hand.glsl", d, geom="box"))

    def draw(self, u, t, extra):
        pa = self.pa
        p = float(u.get("uPath", 0.0))
        eye = keys(p, [(0.0, (0.0, 0.03, 0.8)), (0.5, (0.0, 0.05, 0.72)), (1.0, (0.02, 0.09, 0.42))])
        tgt = keys(p, [(0.0, (0.0, 0.03, 0.0)), (0.5, (0.0, 0.05, 0.0)), (1.0, (0.03, 0.14, -0.5))])
        self.cam.near = 0.01
        self.cam.set(eye + (np.sin(t * 0.5) * 0.008, 0, 0), tgt)
        self.plate.use(location=11)
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uAspectC=pa, uReliefZ=self.RELIEF, uLodD=2.5, uRegion=(0, 0, 1, 1),
                            uFog=0.25, uFogCol=(0.62, 0.66, 0.72), uGain=1.0, uFlowA=0.035, uCaust=0.0, uWaterY=0.0, uGlowUp=0.0,
                            uSplit=float(u.get("uSplit", 0.0)), uTime=t))
        self.eng.paint.get("wanderer")[0].use(location=11)
        self.field.draw(dict(self.cam.uniforms(), uS=float(u.get("uS", 0.0)), uReach=0.0, uKeep=0.0, uTime=t, uFog=0.0,
                             uFogCol=(0, 0, 0), uLightAmt=0.2, uLightDir=(0.4, 0.6, 0.7)))


class Corridor(Event):
    """Into the convex mirror: behind the painting, a corridor of paintings of two people drawing close, repeating inwards."""
    PAIRS = [("kiss", 0.53, 0.2, 0.32), ("arnolfini", 0.5, 0.3, 0.42), ("adam", 0.38, 0.45, 0.2), ("athens", 0.5, 0.42, 0.14),
             ("ambassadors", 0.5, 0.45, 0.42), ("sistine", 0.5, 0.45, 0.2), ("jatte", 0.8, 0.5, 0.25), ("nightmare", 0.55, 0.3, 0.3),
             ("judgment", 0.42, 0.75, 0.1), ("judgment", 0.65, 0.5, 0.08), ("garden", 0.12, 0.55, 0.1), ("kiss", 0.5, 0.5, 0.45),
             ("tulp", 0.5, 0.4, 0.3), ("liberty", 0.45, 0.45, 0.15), ("ophelia", 0.5, 0.5, 0.25), ("wave", 0.7, 0.4, 0.2)]
    MIRROR = (0.49, 0.285)
    R = 0.0345

    def load(self):
        r = np.random.default_rng(9)
        sh, cat = self.sheet, self.eng.paint.cat
        self.pa = self.eng.paint.info("arnolfini")["aspect"]
        self.mesh = GridMesh(self.eng, "shade_hole.glsl", cols=480, rows=640)
        self.keep(self.mesh.prog)
        rows = []
        for ring in range(46):
            z = -0.04 - ring * 0.2
            for side in range(4):
                for o in (-0.1, 0.1) if side < 2 else (-0.13, 0.13):
                    pid, cx, cy, rr = self.PAIRS[r.integers(len(self.PAIRS))]
                    a = 1.25
                    uv = crop_uv(sh, pid, cat, rr, a, cx, cy)
                    rows.append([side, z + o * 0.4, o, 0.074, *uv, a, r.random(), 0, 0])
        self.field = self.keep(Field(self.eng, "field_corridor.glsl", np.array(rows, np.float32)))

    def draw(self, u, t, extra):
        pa = self.pa
        mx, my = (self.MIRROR[0] - 0.5) * pa, 0.5 - self.MIRROR[1]
        z = float(u.get("uCZ", 0.6))
        cx = float(u.get("uCX", 0.0))
        cy = float(u.get("uCY", 0.0))
        x, y = cx + (mx - cx) * float(u.get("uOnAxis", 0.0)), cy + (my - cy) * float(u.get("uOnAxis", 0.0))
        self.cam.near, self.cam.far = 0.004, 30.0
        self.cam.set((x, y, z), (x, y, z - 1.0))
        self.eng.paint.get("arnolfini")[0].use(location=11)
        if z > -0.02:
            self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uReliefZ=0.0, uLodD=2.0, uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0),
                                uHole=(self.MIRROR[0], 1 - self.MIRROR[1]), uHoleR=self.R, uAspectP2=pa, uGain=1.0))
        self.bind("uSheet", self.sheet.tex)
        T = np.eye(4, dtype=np.float32)
        T[:3, 3] = (mx, my, 0.0)
        S = np.diag([1.0, 1.0, 1.0, 1.0]).astype(np.float32)
        fold = 0.0
        vp = self.cam.vp @ T
        # the corridor is an endless loop in z: the ring pattern repeats every 4.0
        cz = min(z, 0.0)
        Tz = np.eye(4, dtype=np.float32)
        Tz[2, 3] = -(cz % -4.0) + cz if False else 0.0
        self.field.draw(dict(uVP=vp.T.tobytes(), uCamPos=(x - mx, y - my, z), uFog=0.42, uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1)))


class Strata(Event):
    """Painting deconstruction: Vesalius's bodies hang one behind another as transparent layers; the camera passes through
    skin, muscle, bone and nerve and arrives at the whole man."""
    LAYERS = [("fabrica_muscle", 0.0, 0.0), ("fabrica_deep", -1.35, 1.0), ("fabrica_skeleton", -2.7, 2.0), ("fabrica_muscle", -3.3, 3.0),
              ("vitruvian", -4.6, 4.0)]

    def load(self):
        self.mesh = GridMesh(self.eng, "shade_strata.glsl", cols=160, rows=240)
        self.keep(self.mesh.prog)
        self.masks = {p: self.keep(load_mask(self.ctx, f"{p}_body")) for p in ("fabrica_muscle", "fabrica_deep", "fabrica_skeleton")}

    def draw(self, u, t, extra):
        z = float(u.get("uCZ", 1.3))
        inv = float(u.get("uInv", 0.0))
        self.cam.near, self.cam.far = 0.01, 30.0
        self.cam.set((np.sin(t * 0.6) * 0.05, np.sin(t * 0.47) * 0.03, z), (0, 0, z - 1.0))
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE
        for k, (pid, lz, flt) in enumerate(reversed(self.LAYERS)):
            d = z - lz
            if d < 0.02:
                continue
            got = self.eng.paint.get(pid)
            got[0].use(location=11)
            if pid in self.masks:
                self.bind("uData", self.masks[pid])
            T = np.eye(4, dtype=np.float32)
            T[2, 3] = lz
            li = inv if flt < 0.5 else 1.0
            if flt > 3.5:
                li = 1.0 - float(u.get("uWhole", 0.0))
            gain = float(np.clip((d - 0.03) / 0.4, 0.0, 1.0)) if flt < 3.5 else float(np.clip((2.4 - d) / 0.8, 0.0, 1.0))
            self.ctx.disable(moderngl.DEPTH_TEST)
            set_u(self.mesh.prog, dict(uVP=(self.cam.vp @ T).T.tobytes(), uCamPos=self.cam.eye, uAspectP=got[2]["aspect"], uReliefZ=0.1, uLodD=2.0,
                                       uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0), uFilter=flt, uInv=li, uGain=gain))
            self.mesh.vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.BLEND)


class Solid(Event):
    """Dürer's solid leaves the print, turns, every face a painting, subdividing until one tiny triangle holds a whole starry sky."""

    def load(self):
        from scipy.spatial import ConvexHull
        ctx = self.ctx
        self.mesh = GridMesh(self.eng, "mesh_shade.glsl", cols=300, rows=380)
        self.keep(self.mesh.prog)
        self.plate = self.keep(load_plate(ctx, "melencolia_solid"))
        A = np.array([[1, 0.15, 0.15], [0.15, 1, 0.15], [0.15, 0.15, 1]], float) * 1.0
        P = []
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    P.append(A @ np.array([sx, sy, sz], float))
        P = np.array(P)
        d = np.array([1, 1, 1.0]) / math.sqrt(3)
        cut = 1.15
        V = []
        h = ConvexHull(P)
        edges = {tuple(sorted((s[i], s[j]))) for s in h.simplices for i, j in ((0, 1), (1, 2), (0, 2))}
        for a, b in edges:
            pa_, pb_ = P[a] @ d, P[b] @ d
            for sgn in (1, -1):
                if (pa_ * sgn - cut) * (pb_ * sgn - cut) < 0:
                    t_ = (cut * sgn - pa_) / (pb_ - pa_)
                    V.append(P[a] + (P[b] - P[a]) * t_)
        V += [p for p in P if abs(p @ d) < cut]
        V = np.array(V)
        h = ConvexHull(V)
        faces = {}
        for s, eq in zip(h.simplices, h.equations):
            faces.setdefault(tuple(np.round(eq[:3], 2)), []).append(s)
        out = []
        for fid, (n, tris) in enumerate(faces.items()):
            n = np.array(n, float)
            ids = sorted({i for t_ in tris for i in t_})
            c = V[ids].mean(0)
            e1 = np.cross(n, (0.3, 0.9, 0.2))
            e1 /= np.linalg.norm(e1)
            e2 = np.cross(n, e1)
            sc = 2.6
            for tri in tris:
                for i in tri:
                    q = V[i] - c
                    out.append([*V[i], *n, q @ e1 / sc + 0.5, q @ e2 / sc + 0.5, fid])
        self.vbo = self.keep(ctx.buffer(np.array(out, np.float32).tobytes()))
        self.prog = ctx.program(vertex_shader="#version 430\n" + self.eng.common + (ROOT_SH / "solid.vs").read_text(),
                                fragment_shader="#version 430\n#define FRAG\n" + self.eng.common + (ROOT_SH / "solid.fs").read_text())
        from .renderer import bind_units
        bind_units(self.prog)
        self.vao = self.keep(ctx.vertex_array(self.prog, [(self.vbo, "3f 3f 3f", "aP", "aN", "aF")], skip_errors=True))
        self.n = len(out)
        self.face = np.array(out[0][:3]), np.array(out[0][3:6])

    def draw(self, u, t, extra):
        from .dream import set_u
        info = self.eng.paint.info("melencolia")
        pa = info["aspect"]
        p = float(u.get("uFlight", 0.0))
        a = float(u.get("uTurn", 0.0))
        scale = 0.085 + 0.2 * p
        c = np.array([(0.27 - 0.5) * pa * (1 - p), (0.5 - 0.5) * (1 - p), 0.1 + 0.2 * p])
        ca, sa = math.cos(a), math.sin(a)
        ce, se = math.cos(a * 0.6 + 0.4), math.sin(a * 0.6 + 0.4)
        Ry = np.array([[ca, 0, sa], [0, 1, 0], [-sa, 0, ca]])
        Rx = np.array([[1, 0, 0], [0, ce, -se], [0, se, ce]])
        R = Ry @ Rx
        M = np.eye(4, dtype=np.float32)
        M[:3, :3] = R * scale
        M[:3, 3] = c
        fz = float(u.get("uIn", 0.0))
        tgtw = M[:3, :3] @ self.tgt_point() + c
        nw = R @ self.face[1]
        eye0 = np.array([0.0, 0.0, D0 * 0.5])
        eye1 = tgtw + nw * 0.0045
        eye = eye0 + (eye1 - eye0) * fz ** 0.55 if fz > 0 else eye0
        self.cam.near = 0.0006
        self.cam.set(eye, eye0 * 0 + (tgtw * (fz ** 0.5)) + (1 - fz ** 0.5) * np.array([0.0, 0.0, 0.0]), up=(0.1, 1.0, 0.0))
        self.plate.use(location=11)
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uReliefZ=0.08, uLodD=2.0, uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0),
                            uGain=float(u.get("uPlate", 1.0))))
        self.bind("uSheet", self.sheet.tex)
        self.bind("uTexA", self.eng.paint.get("space_udf")[0])
        self.ctx.enable(2929)
        self.ctx.disable(2884)
        set_u(self.prog, dict(self.cam.uniforms(), uM=M.T.tobytes(), uLevel=float(u.get("uLevel", 0.0)), uStar=float(u.get("uStar", 0.0)),
                              uFaceTgt=(self.fuv[0], self.fuv[1], 0.0)))
        self.vao.render(4, vertices=self.n)
        self.ctx.disable(2929)

    def tgt_point(self):
        """Centre of one small triangle on face 0."""
        if not hasattr(self, "fuv"):
            self.fuv = (0.517, 0.492)
        return self.face[0] * 0 + self._tgt

    @property
    def _tgt(self):
        d = np.frombuffer(self.vbo.read(), np.float32).reshape(-1, 9)
        f0 = d[d[:, 8] == 0]
        A = np.c_[f0[:, 6:8], np.ones(len(f0))]
        cf, *_ = np.linalg.lstsq(A, f0[:, :3], rcond=None)
        return np.array(self.fuv + (1.0,)) @ cf


class Cosmos(Event):
    """Three charts of the heavens overlap on paper, rise into nested shells the camera flies through, and every orbit settles
    into the mandala."""

    def load(self):
        r = np.random.default_rng(21)
        sh = self.sheet
        rows = []
        mx0, my0, mx1, my1 = sh.rects["mandala"]
        ma = (mx1 - mx0) / (my1 - my0)
        for shell, pid in enumerate(("cellarius", "fludd", "kircher")):
            x0, y0, x1, y1 = sh.rects[pid]
            nv, nu = 210, 210
            for j in range(nv):
                for i in range(nu):
                    u, v = (i + 0.5) / nu, (j + 0.5) / nv
                    du, dv = 0.5 / nu, 0.5 / nv
                    rect = (x0 + (u - du) * (x1 - x0), y0 + (v - dv) * (y1 - y0), x0 + (u + du) * (x1 - x0), y0 + (v + dv) * (y1 - y0))
                    a, rr = r.random() * 2 * np.pi, math.sqrt(r.random()) * 1.0
                    uu, vv = 0.5 + rr * math.cos(a) * 0.5 / max(ma, 1), 0.5 + rr * math.sin(a) * 0.5 * min(ma, 1)
                    e = 0.0062
                    mrect = (mx0 + (uu - e) * (mx1 - mx0), my0 + (vv - e) * (my1 - my0), mx0 + (uu + e) * (mx1 - mx0), my0 + (vv + e) * (my1 - my0))
                    rows.append([u, v, shell, 0, *rect, r.random(), r.random(), 0.00245, float(r.random() < 0.005), rr * 0.5, a, 0, 0, *mrect])
        self.field = self.keep(Field(self.eng, "field_cosmos.glsl", np.array(rows, np.float32)))

    def draw(self, u, t, extra):
        p = float(u.get("uPath", 0.0))
        eye = keys(p, [(0.0, (0, 0, 1.25)), (0.22, (0.3, 0.12, 1.5)), (0.45, (-0.2, 0.25, 0.8)), (0.65, (-0.85, 0.3, 0.35)), (0.82, (0.0, -0.1, 1.3)), (1.0, (0, 0, D0))])
        tgt = keys(p, [(0.0, (0, 0, 0)), (0.6, (0.4, 0, -0.2)), (0.85, (0, 0, 0)), (1.0, (0, 0, 0))])
        self.cam.near = 0.01
        self.cam.set(eye, tgt)
        self.bind("uSheet", self.sheet.tex)
        fu = dict(self.cam.uniforms(), uRise=float(u.get("uRise", 0.0)), uRing=float(u.get("uRing", 0.0)), uStarsUp=float(u.get("uStarsUp", 0.0)),
                  uTime=t, uFog=0.0, uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1))
        self.field.draw(fu)
        self.field.draw(fu, additive=True)


class Saturn(Event):
    """He looks back. uSplitV: the painting above, what the machine sees below; the machine's eye opens in his."""
    EYE = (0.325, 0.81)

    def load(self):
        from PIL import Image
        self.prog = self.eng.program("dream/saturn.glsl")
        self.mask = self.keep(load_mask(self.ctx, "saturn_body", (832, 1526)))
        im = Image.open(ANALYSIS / "eye_target.png").convert("RGB").transpose(Image.FLIP_TOP_BOTTOM)
        self.eye = self.keep(self.ctx.texture(im.size, 3, data=im.tobytes()))
        self.eye.filter = (9729, 9729)

    def draw(self, u, t, extra):
        got = self.eng.paint.get("saturn")
        got[0].use(location=11)
        self.eng.draw(self.prog, self.fbo, dict(u, uZ=float(u.get("uCamZ", 1.0)), uAspP=got[2]["aspect"], uMuscle=float(u.get("uMuscle", 0.0)), uMachine=0.0,
                                                uC=(float(u.get("uCX", 0.35)), float(u.get("uCY", 0.72))),
                                                uLook=(float(u.get("uLookX", 0.0)), float(u.get("uLookY", 0.0))), uSplitV=float(u.get("uSplitV", 0.0)),
                                                uEyeMix=float(u.get("uEyeMix", 0.0))), [("uData", self.mask), ("uTexA", self.eye)])
        wrong = float(u.get("uWrong", 0.0))
        if wrong > 0:                                      # the machine finds the eye, and keeps losing it
            ov = overlay(self.eng)
            z, pa, c = float(u.get("uCamZ", 1.0)), got[2]["aspect"], (float(u.get("uCX", 0.35)), float(u.get("uCY", 0.72)))
            asp = self.eng.w / self.eng.h
            for k, (ex, ey, name) in enumerate(((0.325, 0.81, "EYE"), (0.415, 0.81, "EYE"))):
                off = 0.05 * wrong * np.array([np.sin(t * 2.3 + k * 2.0) + np.sin(t * 5.1), np.cos(t * 1.9 + k) + np.sin(t * 3.7 + k)])
                x, y = 0.5 + (ex - c[0]) * pa * z / asp + off[0] * z * 0.5, 0.5 + (ey - c[1]) * z + off[1] * z * 0.5
                h = 0.05 * z
                conf = 0.93 - 0.31 * abs(math.sin(t * 2.3 + k))
                ov.box(x - h * 1.3 / asp, y - h, x + h * 1.3 / asp, y + h, CYAN, 0.9, 2.0)
                ov.text(x - h * 1.3 / asp, y + h + 0.006, f"{name} {conf:.2f}", CYAN, 0.9)
            ov.flush()


class Faces(Event):
    """Medusa and Oiwa eat into each other (Morph), then the face is rebuilt out of hundreds of eyes all staring into the lens."""
    EYES = [("medusa", 0.4817, 0.4144, 0.04), ("medusa", 0.597, 0.45, 0.04), ("oiwa", 0.63, 0.49, 0.06), ("saturn", 0.325, 0.19, 0.035),
            ("cyclops", 0.335, 0.236, 0.05), ("pearl", 0.341, 0.374, 0.04), ("pearl", 0.5, 0.40, 0.04), ("oiwa", 0.74, 0.44, 0.05), ("saturn", 0.41, 0.19, 0.035)]
    N = 3

    def load(self):
        from PIL import Image
        self.morph = Morph(self.eng, ["medusa", "oiwa"])
        self.morph.load()
        S = 256
        at = Image.new("RGB", (S * self.N, S * self.N))
        for k, (pid, cx, cy, rr) in enumerate(self.EYES):
            im = Image.open(self.eng.paint.dir / f"{pid}.png").convert("RGB")
            W, H = im.size
            hh, hw = rr * H, rr * H * 1.3
            c = im.crop((int(cx * W - hw), int(cy * H - hh), int(cx * W + hw), int(cy * H + hh))).resize((S, S), Image.LANCZOS)
            at.paste(c, ((k % self.N) * S, (k // self.N) * S))
        at = at.transpose(Image.FLIP_TOP_BOTTOM)
        self.atlas = self.keep(self.ctx.texture(at.size, 3, data=at.tobytes()))
        self.atlas.build_mipmaps()
        self.atlas.filter = (9987, 9729)
        r = np.random.default_rng(4)
        M = np.array(Image.open(ANALYSIS / "mask" / "medusa_face.png").resize((400, 410)))[::-1] > 127
        pa = self.eng.paint.info("medusa")["aspect"]
        ys, xs = np.nonzero(M)
        s0 = min(1.0, pa / self.cam.aspect)
        rows = []
        n = 420
        idx = r.permutation(len(xs))[:n]
        for k, i in enumerate(idx):
            x, y = (xs[i] / 400 - 0.5) * pa / s0, (ys[i] / 410 - 0.5) / s0
            e = int(r.integers(len(self.EYES)))
            cu, cv = (e % self.N) / self.N, 1.0 - (e // self.N + 1) / self.N
            rows.append([x, y, r.uniform(0.045, 0.075) * (1.7 if r.random() < 0.1 else 1.0), k / n * 0.98, cu, cv, cu + 1 / self.N, cv + 1 / self.N, r.random(), r.random(), 0, 0])
        self.field = self.keep(Field(self.eng, "field_eyes.glsl", np.array(rows, np.float32)))

    def unload(self):
        super().unload()
        self.morph.unload()

    def draw(self, u, t, extra):
        self.morph.fbo = self.fbo
        self.morph.draw(u, t, extra)
        self.cam.set((0, 0, D0), (0, 0, 0))
        self.atlas.use(location=11)
        self.fbo.use()
        self.field.draw(dict(self.cam.uniforms(), uEyes=float(u.get("uEyes", 0.0)), uStare=float(u.get("uStare", 0.0)), uTime=t, uFog=0.0,
                             uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1)))


class NightmareEv(Event):
    def load(self):
        self.mesh = GridMesh(self.eng, "shade_nightmare.glsl", cols=640, rows=500)
        self.keep(self.mesh.prog)
        self.mask = self.keep(load_mask(self.ctx, "nightmare_demon", (1024, 822)))

    def draw(self, u, t, extra):
        got = self.eng.paint.get("nightmare")
        got[0].use(location=11)
        pa = got[2]["aspect"]
        z = float(u.get("uCamZ", 1.0))
        eye, tgt = plane_frame(pa, (0.5, 0.36), z, self.cam.aspect)
        roll = float(u.get("uRoll", 0.0))
        self.cam.set(np.array(eye) + (0, 0, 0.1), tgt, up=(math.sin(roll), math.cos(roll), 0.0))
        self.bind("uData", self.mask)
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uReliefZ=0.2, uLodD=2.0, uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0),
                            uGain=1.25, uShadow=float(u.get("uShadow", 0.0)), uGrow=float(u.get("uGrow", 0.0)),
                            uSC=(float(u.get("uSX", 0.63)), float(u.get("uSY", 0.86))), uTime=t))


class Fall(Event):
    """One fall through three paintings: each is a plane of cells, its SAM segments at their own depths; they break up round the
    fall line, every figure, wing and wall turning to wireframe as it tumbles past."""
    PLANES = [("rebels", 0.0), ("damned", -17.0), ("etoiles", -34.0)]

    def load(self):
        from PIL import Image
        sh = self.sheet
        rows = []
        r = np.random.default_rng(2)
        for k, (pid, z) in enumerate(self.PLANES):
            x0, y0, x1, y1 = sh.rects[pid]
            pa = (x1 - x0) / (y1 - y0)
            ny = 420
            nx = int(ny * pa)
            lab = np.array(Image.open(ANALYSIS / "seg" / f"{pid}.png").resize((nx, ny), Image.NEAREST))[::-1]
            dep = np.array(Image.open(ANALYSIS / "depth" / f"{pid}.png").resize((nx, ny), Image.BILINEAR), np.float32)[::-1] / 65535.0
            seed = r.random(int(lab.max()) + 2)
            W = 25.0                                 # half height of the plane in the world
            for j in range(ny):
                for i in range(nx):
                    u, v = (i + 0.5) / nx, (j + 0.5) / ny
                    du, dv = 0.5 / nx, 0.5 / ny
                    rows.append([(u - 0.5) * pa * 2 * W, (v - 0.5) * 2 * W, z, W / ny * 1.04, x0 + (u - du) * (x1 - x0), y0 + (v - dv) * (y1 - y0),
                                 x0 + (u + du) * (x1 - x0), y0 + (v + dv) * (y1 - y0), r.random(), dep[j, i] * 2.5 + seed[lab[j, i]] * 1.0 - 2.0, k, seed[lab[j, i]]])
        self.field = self.keep(Field(self.eng, "field_fall.glsl", np.array(rows, np.float32)))

    def draw(self, u, t, extra):
        z = float(u.get("uCZ", 8.0))
        roll = float(u.get("uRoll", 0.0))
        self.cam.near, self.cam.far, self.cam.fov = 0.1, 90.0, math.radians(float(u.get("uCamFov", 70.0)))
        self.cam.set((math.sin(t * 0.7) * 0.5, math.cos(t * 0.53) * 0.5, z), (0, 0, z - 10.0), up=(math.sin(roll), math.cos(roll), 0.0))
        self.bind("uSheet", self.sheet.tex)
        self.field.draw(dict(self.cam.uniforms(), uShred=float(u.get("uShred", 1.0)), uTime=t, uFog=0.02, uFogCol=(0, 0, 0), uLightAmt=0.0,
                             uLightDir=(0, 0, 1)))


SKEL = [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28), (0, 11), (0, 12), (27, 31), (28, 32), (15, 19), (16, 20)]
NAMES = ("PERSON", "FIGURE", "SOUL", "BODY", "ANGEL", "FACE", "HAND", "PERSON")


class Vision(Event):
    """Machine perception of one painting. Everything drawn is measured: SAM segments, MediaPipe skeletons, Depth Anything depth,
    DINOv2 similarity. Only the words on the labels are this film's fiction."""

    def __init__(self, eng, pid, mode):
        super().__init__(eng)
        self.pid, self.mode = pid, mode

    def load(self):
        from PIL import Image
        self.pa = self.eng.paint.info(self.pid)["aspect"]
        self.mesh = GridMesh(self.eng, "shade_vision.glsl", cols=900, rows=900)
        self.keep(self.mesh.prog)
        lab = np.array(Image.open(ANALYSIS / "seg" / f"{self.pid}.png"), np.float32)[::-1]
        self.lab = self.keep(self.ctx.texture(lab.shape[1::-1], 1, data=lab.tobytes(), dtype="f4"))
        self.lab.filter = (9728, 9728)
        self.segs = [s for s in json.loads((ANALYSIS / "seg" / f"{self.pid}.json").read_text()) if s["score"] > 0.7]
        p = ANALYSIS / "pose" / f"{self.pid}.json"
        self.pose = json.loads(p.read_text()) if p.exists() else []
        if self.mode == "judgment":
            self.load_graph()

    def load_graph(self):
        s = [g for g in self.segs if 0.0006 < g["area"] < 0.06][:220]
        self.nodes = s
        pa = self.pa
        b = np.array([g["bbox"] for g in s])
        cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
        self.nb = b
        d = np.load(ANALYSIS / "dino" / f"{self.pid}.npy").astype(np.float32)
        f = d[np.clip((cy * 37).astype(int), 0, 36), np.clip((cx * 37).astype(int), 0, 36)]
        f = f / np.linalg.norm(f, axis=1, keepdims=True)
        sim = f @ f.T
        np.fill_diagonal(sim, -1)
        self.edges = np.unique(np.sort(np.c_[np.repeat(np.arange(len(s)), 3), np.argsort(-sim, 1)[:, :3].ravel()], 1), axis=0)
        u, sv, _ = np.linalg.svd(f - f.mean(0), full_matrices=False)
        g = u[:, :3] * sv[:3]
        r = np.random.default_rng(1)
        goal = g / np.abs(g).max(0) * np.array([1.9, 1.05, 1.0]) + r.normal(0, 0.1, g.shape)
        self.start = np.c_[(cx - 0.5) * pa, 0.5 - cy, np.full(len(s), 0.03)]
        self.goal = goal
        self.seed = r.random(len(s))
        rows = np.c_[self.start[:, :2], (b[:, 2] - b[:, 0]) * pa / 2, (b[:, 3] - b[:, 1]) / 2, b[:, 0], 1 - b[:, 3], b[:, 2], 1 - b[:, 1], goal, self.seed]
        self.field = self.keep(Field(self.eng, "field_nodes.glsl", rows.astype(np.float32)))
        self.t_box = 181.0 + 3.0 * (np.argsort(np.argsort(cy + 0.15 * self.seed)) / len(s))

    def proj(self, P):
        h = np.c_[P, np.ones(len(P))]
        q = (np.asarray(self.cam.vp, float) @ h.T).T
        w = np.maximum(q[:, 3], 1e-4)
        return np.c_[0.5 + 0.5 * q[:, 0] / w, 0.5 + 0.5 * q[:, 1] / w]

    def uvp(self, uv):
        """Painting uv, top-down → world on the canvas."""
        return np.c_[(uv[:, 0] - 0.5) * self.pa, 0.5 - uv[:, 1], np.zeros(len(uv))]

    def draw(self, u, t, extra):
        got = self.eng.paint.get(self.pid)
        pa = self.pa
        hit = float(u.get("uHit", 0.0))                    # Overload: the camera takes every hit of the music
        z = float(u.get("uCamZ", 1.0)) * (1.0 + 0.05 * hit)
        c = (float(u.get("uCX", 0.5)), float(u.get("uCY", 0.5)))
        K = float(u.get("uK", 0.0))
        eye, tgt = plane_frame(pa, c, z, self.cam.aspect)
        sh = 0.012 * hit * np.array([math.sin(t * 41.0), math.cos(t * 37.0), 0.0])
        eye = np.array(eye, float) + sh
        tgt = np.array(tgt, float) + sh
        orb = float(u.get("uOrbit", 0.0))
        if self.mode == "judgment" and K > 0:
            k = ease(min(K * 1.6, 1.0))
            a = (K - 0.1) * 0.9
            eye = eye + (np.array([math.sin(a) * 3.4, 0.3, math.cos(a) * 3.4]) - eye) * k
            tgt = tgt * (1 - k)
        if orb != 0:
            eye = tgt + np.array([math.sin(orb) * eye[2], float(u.get("uLift", 0.0)), math.cos(orb) * eye[2]])
        self.cam.near = 0.01
        self.cam.set(eye, tgt)
        got[0].use(location=11)
        self.bind("uData", self.lab)
        rel = float(u.get("uRelief", 0.04))
        self.mesh.draw(dict(self.cam.uniforms(), uAspectP=pa, uReliefZ=rel, uLodD=2.0, uRegion=(0, 0, 1, 1), uFog=0.0, uFogCol=(0, 0, 0), uTime=t,
                            uDim=float(u.get("uDim", 1.0)) * (1.0 - min(K * 2.6, 1.0)), uDepthV=float(u.get("uDepthV", 0.0)), uSegV=float(u.get("uSegV", 0.0)),
                            uEdge=float(u.get("uEdge", 0.0)), uSweep=float(u.get("uSweep", 2.0)), uZone=float(u.get("uZone", 0.0)), uZoneT=float(u.get("uZoneT", 0.3)),
                            uPts=float(u.get("uPts", 0.0)), uPtD=float(u.get("uPtD", 0.004)), uAspP2=pa))
        if self.mode == "judgment" and K > 0:
            got[0].use(location=11)
            self.fbo.use()
            self.field.draw(dict(self.cam.uniforms(), uK=K, uTime=t, uFog=0.0, uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1)))
        ov = overlay(self.eng)
        getattr(self, "ov_" + self.mode)(ov, u, t, K)
        ov.flush()

    def boxes(self, ov, segs, t, t0, t1, col=CYAN, labels=True):
        if not segs:
            return
        b = np.array([s["bbox"] for s in segs])
        order = (np.argsort(np.argsort(b[:, 1])) + 0.5) / len(b)
        on = t >= t0 + (t1 - t0) * order
        if not on.any():
            return
        b, sc = b[on], [s["score"] for s, o in zip(segs, on) if o]
        P0, P1 = self.proj(self.uvp(b[:, :2])), self.proj(self.uvp(b[:, 2:]))
        ov.box(P0[:, 0], P1[:, 1], P1[:, 0], P0[:, 1], col, 0.85, 1.8)
        if labels:
            for i in range(len(b)):
                if P1[i, 0] - P0[i, 0] > 0.04:
                    ov.text(P0[i, 0], P0[i, 1] + 0.004, f"{NAMES[i % len(NAMES)]} {sc[i]:.2f}", col, 0.85, 0.0125)

    def ov_judgment(self, ov, u, t, K):
        s, g = self.start, self.goal
        k = np.clip((K - self.seed * 0.35) / 0.65, 0.0, 1.0)
        k = (k * k * (3 - 2 * k))[:, None]
        P = s + (g - s) * k
        S = self.proj(P)
        on = t >= self.t_box
        ww = (self.nb[:, 2] - self.nb[:, 0]) * self.pa / 2 * (1 + 0.6 * k[:, 0])
        hh = (self.nb[:, 3] - self.nb[:, 1]) / 2 * (1 + 0.6 * k[:, 0])
        A, B = self.proj(P - np.c_[ww, hh, 0 * ww]), self.proj(P + np.c_[ww, hh, 0 * ww])
        col = np.where(on[:, None], np.array(CYAN), np.array(CYAN))
        if on.any():
            ov.box(A[on, 0], A[on, 1], B[on, 0], B[on, 1], CYAN, 0.9, 1.8)
            if K < 0.2:
                for i in np.nonzero(on)[0]:
                    if B[i, 0] - A[i, 0] > 0.035:
                        ov.text(A[i, 0], B[i, 1] + 0.004, f"{NAMES[i % len(NAMES)]} {self.nodes[i]['score']:.2f}", CYAN, 0.85 * (1 - K * 5), 0.0115)
        for p in self.pose:                                # skeletons
            ta = 181.5 + 2.5 * p["bbox"][1]
            if t < ta or K > 0.25:
                continue
            pts = np.array(p["pts"])
            a, b = np.array(SKEL).T
            ok = (pts[a, 2] > 0.4) & (pts[b, 2] > 0.4)
            q = self.proj(self.uvp(pts[:, :2]))
            ov.line(q[a[ok]], q[b[ok]], AMBER, 0.9 * (1 - K * 4), 1.8)
        if K > 0:                                          # all of it opens into one relation graph
            e = self.edges
            al = 0.75 * np.minimum(k[e[:, 0], 0], k[e[:, 1], 0])
            ov.line(S[e[:, 0]], S[e[:, 1]], CYAN, al, 1.3)

    def ov_zones(self, ov, u, t, K):
        ov.text(0.06, 0.74, f"SKY    {0.97 + 0.02 * math.sin(t * 3):.2f}", CYAN, 0.95, 0.02)
        ov.text(0.06, 0.2, f"GROUND {0.96 + 0.02 * math.sin(t * 2):.2f}", AMBER, 0.95, 0.02)
        self.boxes(ov, [s for s in self.segs if s["area"] > 0.004][:24], t, 189.2, 191.5, AMBER)

    def ov_edges(self, ov, u, t, K):
        self.boxes(ov, [s for s in self.segs if s["area"] > 0.003][:30], t, 193.6, 196.6, CYAN)

    def ov_cloud(self, ov, u, t, K):
        ax0, ax1 = np.array([[0.06, 0.1]]), np.array([[0.06, 0.1 + 0.45 * min((t - 206.0) / 2.0, 1.0)]])
        ov.line(ax0, ax1, WHITE, 0.9, 2.0)
        for i in range(6):
            y = 0.1 + 0.09 * i
            if y < ax1[0, 1]:
                ov.line([[0.06, y]], [[0.07, y]], WHITE, 0.9, 2.0)
                ov.text(0.075, y - 0.006, f"z {i * 0.2:.1f}", WHITE, 0.85, 0.013)

    def ov_seg(self, ov, u, t, K):
        s = [g for g in self.segs if g["area"] > 0.002][:40]
        self.boxes(ov, s, t, 210.6, 213.6, WHITE)

    def ov_plain(self, ov, u, t, K):
        pass


class Match(Event):
    """Feature matching: the same idea in two paintings; lines join the patches DINOv2 calls alike."""
    A, B = ("kiss", "arnolfini")

    def load(self):
        self.mesh = GridMesh(self.eng, "mesh_shade.glsl", cols=120, rows=120)
        self.keep(self.mesh.prog)
        fa = np.load(ANALYSIS / "dino" / f"{self.A}.npy").astype(np.float32).reshape(-1, 32)
        fb = np.load(ANALYSIS / "dino" / f"{self.B}.npy").astype(np.float32).reshape(-1, 32)
        fa /= np.linalg.norm(fa, axis=1, keepdims=True)
        fb /= np.linalg.norm(fb, axis=1, keepdims=True)
        sim = fa @ fb.T
        i = sim.argmax(1)
        mutual = sim.argmax(0)[i] == np.arange(len(i))
        idx = np.nonzero(mutual)[0]
        idx = idx[np.argsort(-sim[idx, i[idx]])][:150]
        uv = lambda n: np.c_[(n % 37 + 0.5) / 37, (n // 37 + 0.5) / 37]
        self.ua, self.ub, self.sc = uv(idx), uv(i[idx]), sim[idx, i[idx]]
        self.seed = np.random.default_rng(3).random(len(idx))

    def draw(self, u, t, extra):
        self.cam.set((0, 0, D0), (0, 0, 0))
        asp = self.cam.aspect
        S = 0.8
        for pid, sx in ((self.A, -1), (self.B, 1)):
            got = self.eng.paint.get(pid)
            got[0].use(location=11)
            pa = got[2]["aspect"]
            s = min(S, 0.47 * asp / pa * 0.98)
            T = np.eye(4, dtype=np.float32)
            T[:3, :3] *= s
            T[0, 3] = sx * asp * 0.25
            self.mesh.draw(dict(uVP=(self.cam.vp @ T).T.tobytes(), uCamPos=self.cam.eye, uAspectP=pa, uReliefZ=0.0, uLodD=2.0, uRegion=(0, 0, 1, 1),
                                uFog=0.0, uFogCol=(0, 0, 0), uGain=1.0))
            if sx < 0:
                sa, pa_a = s, pa
            else:
                sb, pa_b = s, pa
        place = lambda uv, s, pa, sx: np.c_[0.5 + (sx * asp * 0.25 + (uv[:, 0] - 0.5) * pa * s) / (asp * 1.0), 0.5 + (0.5 - uv[:, 1]) * s]
        a, b = place(self.ua, sa, pa_a, -1), place(self.ub, sb, pa_b, 1)
        k = np.clip((t - 215.0 - self.seed * 2.2) / 0.5, 0.0, 1.0)
        on = k > 0
        ov = overlay(self.eng)
        cols = np.array(CYAN) * (1 - self.seed[:, None]) + np.array(AMBER) * self.seed[:, None]
        ov.line(a[on], (a + (b - a) * k[:, None])[on], cols[on], 0.75, 1.3)
        d = 0.006
        ov.box(a[on, 0] - d, a[on, 1] - d * asp, a[on, 0] + d, a[on, 1] + d * asp, cols[on], 0.9, 1.2, 0.5)
        ov.flush()


class Conflict(Morph):
    """The names stop holding: paintings run into each other while pairs of classification boxes fight over them."""
    PAIRS = [("FREEDOM", 0.71, "VIOLENCE", 0.69), ("HEAVEN", 0.52, "HELL", 0.51), ("ORDER", 0.62, "CHAOS", 0.94), ("ANGEL", 0.49, "DEMON", 0.49),
             ("NIGHT", 0.88, "FEAR", 0.64), ("SKY", 0.40, "UNKNOWN", 0.31)]
    T0, STEP = 218.77, 2.1379

    def draw(self, u, t, extra):
        super().draw(u, t, extra)
        ov = overlay(self.eng)
        k = min(int((t - self.T0) / self.STEP), 5)
        tl = (t - self.T0) - k * self.STEP
        a, ca, b, cb = self.PAIRS[k]
        for j, (nm, cf, col) in enumerate(((a, ca, CYAN), (b, cb, RED))):
            if j == 1 and tl < 1.15:
                continue
            ph = t * (1.3 + j * 0.7) + k * 2.0 + j
            w = 0.22 + 0.05 * math.sin(ph * 1.7)
            h = 0.3 + 0.07 * math.cos(ph * 1.3)
            x = 0.5 + 0.11 * (j - 0.5) * math.sin(ph * 0.5) + 0.03 * math.sin(ph * 3.0)
            y = 0.52 + 0.1 * math.cos(ph * 0.7)
            ov.line([[x - w, y - h], [x + w, y - h], [x + w, y + h], [x - w, y + h]], [[x + w, y - h], [x + w, y + h], [x - w, y + h], [x - w, y - h]], col, 0.85, 2.0)
            ov.text(x - w, y + h + 0.006, f"{nm} {cf:.2f}", col, 0.95, 0.02)
        ov.flush()


class Emerge(Event):
    """Light you could touch: particles leave the sunrise's reflection and gather into the outline of two reaching hands."""

    def load(self):
        from PIL import Image
        from scipy.ndimage import binary_erosion
        self.inner = Plate(self.eng)
        self.inner.load()
        r = np.random.default_rng(8)
        pts = []
        pa = self.eng.paint.info("adam")["aspect"]
        for nm in ("adam_godarm", "adam_adamarm"):
            m = np.array(Image.open(ANALYSIS / "mask" / f"{nm}.png").resize((2000, int(2000 / pa)))) > 127
            e = m & ~binary_erosion(m, iterations=2)
            ys, xs = np.nonzero(e)
            fy, fx = np.nonzero(m)
            k = r.integers(len(fy), size=len(ys) // 3)              # a little light inside, so the hands have a body
            pts.append(np.r_[np.c_[xs / m.shape[1], ys / m.shape[0]], np.c_[fx[k] / m.shape[1], fy[k] / m.shape[0]]])
        P = np.concatenate(pts)
        n = 42000
        P = P[r.integers(len(P), size=n)]
        Z = 4.6                                           # as framed by the hands shot that follows, seen closer
        tx, ty = (P[:, 0] - GAP_UV[0]) * pa * Z * 0.78, (GAP_UV[1] - P[:, 1]) * Z * 0.78 + 0.02
        ok = ty > -0.3                                    # the mask's crop corner is not a hand
        pick = r.integers(ok.sum(), size=n)
        tx, ty = tx[ok][pick], ty[ok][pick]
        asp = self.cam.aspect
        a = r.random(n) * 2 * np.pi
        sx, sy = (r.random(n) - 0.5) * asp * 1.1, r.normal(-0.22, 0.14, n)     # on the water
        K = (D0 - 0.6) / D0                               # in front of the relief, same size on screen
        self.field = self.keep(Field(self.eng, "field_emerge.glsl", np.c_[sx * K, sy * K, np.full(n, 0.6), r.random(n), tx * K, ty * K, np.full(n, 0.6), r.random(n)].astype(np.float32)))

    def unload(self):
        super().unload()
        self.inner.unload()

    def draw(self, u, t, extra):
        self.inner.fbo = self.fbo
        self.inner.draw(dict(u, uCutE=erase_level((1.0 - float(u.get("uMemory", 1.0))) ** 2.2)), t, extra)   # the water is going; the light is not
        self.cam.set((0, 0, D0), (0, 0, 0))
        self.fbo.use()
        self.field.draw(dict(self.cam.uniforms(), uGather=float(u.get("uGather", 0.0)), uTime=t, uFog=0.0, uFogCol=(0, 0, 0), uLightAmt=0.0, uLightDir=(0, 0, 1)), additive=True)


EVENTS = {"eye": Eye, "hands": Hands, "wanderer": Wanderer, "corridor": Corridor, "strata": Strata, "solid": Solid, "cosmos": Cosmos,
          "saturn": Saturn, "faces": Faces, "match": Match, "emerge": Emerge,
          "vision_judgment": lambda e: Vision(e, "judgment", "judgment"), "vision_zones": lambda e: Vision(e, "wrath", "zones"),
          "vision_edges": lambda e: Vision(e, "wave", "edges"), "vision_cloud": lambda e: Vision(e, "empyrean", "cloud"),
          "vision_seg": lambda e: Vision(e, "ascent", "seg"),
          "conflict": lambda e: Conflict(e, ["liberty", "wrath", "snowstorm", "rebels", "starry", "flammarion"]), "nightmare": NightmareEv, "fall": Fall, "tower": Tower, "infinite": Infinite, "plate": Plate, "narcissus": Narcissus,
          **{f"ladder_{k}": (lambda e, k=k: Ladder(e, k)) for k in LADDERS},
          "morph_mix": lambda e: Morph(e, ["redfuji", "tulp", "sanromano", "melencolia", "magdalene", "haeckel", "ancient", "vitruvian"]),
          "morph_prologue": lambda e: Morph(e, ["medusa", "pearl"])}
