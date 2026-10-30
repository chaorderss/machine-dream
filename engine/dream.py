"""v13: the inside of the machine's dream — real 3D space behind the 2D chapter pipeline.

A "dream:<event>" scene renders into its own HDR target with a depth buffer and is then a normal chapter layer
(transitions, mosaic, bloom, grade and titles all still apply). Three layers, sharing one camera:

  Layer 01 Artwork      GridMesh: a painting as displaced geometry (neural depth in its alpha, SAM masks as layers)
  Layer 02 Geometry     Field: millions of instanced tiles / boxes / dots; each one's place in the world is a pure
                        function of time in GLSL (shaders/dream/field_*.glsl), so any frame can be rendered on its own
  Layer 03 Perception   engine/perception.py, drawn after the grade

The six abilities of the film are modules here and in shaders/dream/, reused from shot to shot:
  recursive reality (Ladder), painting deconstruction (GridMesh layers), latent mutation (Morph), impossible geometry
  (tower), perceptual breakdown (perception.py, faces), emergent consciousness (gathering Fields).
"""
import json
import math
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHADERS = ROOT / "shaders" / "dream"
ANALYSIS = ROOT / "assets" / "analysis"
FOV = math.radians(40.0)
D0 = 0.5 / math.tan(FOV / 2)              # camera distance at which a unit-height plane exactly fills the frame


def rd(name):
    return (SHADERS / name).read_text()


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def keys(t, ks):
    """Smoothstep-eased keyframes [(t, value or vector), ...] in absolute film seconds."""
    if t <= ks[0][0]:
        return np.asarray(ks[0][1], float)
    for (t0, a), (t1, b) in zip(ks, ks[1:]):
        if t < t1:
            return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * ease((t - t0) / max(t1 - t0, 1e-6))
    return np.asarray(ks[-1][1], float)


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(fovy / 2)
    return np.array([[f / aspect, 0, 0, 0], [0, f, 0, 0],
                     [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)], [0, 0, -1, 0]], np.float32)


def look_at(eye, target, up=(0.0, 1.0, 0.0)):
    eye, target, up = (np.asarray(v, np.float32) for v in (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


class Camera:
    def __init__(self, eng, near=0.01, far=200.0, fov=FOV):
        self.aspect, self.near, self.far, self.fov = eng.w / eng.h, near, far, fov

    def set(self, eye, target, up=(0.0, 1.0, 0.0)):
        self.eye = tuple(float(v) for v in eye)
        self.vp = perspective(self.fov, self.aspect, self.near, self.far) @ look_at(eye, target, up)
        return self

    def project(self, p):
        """World point → top-down screen uv."""
        q = self.vp @ np.array([*p, 1.0], np.float32)
        return 0.5 + 0.5 * q[0] / q[3], 0.5 - 0.5 * q[1] / q[3]

    def uniforms(self):
        return {"uVP": self.vp.T.tobytes(), "uCamPos": self.eye}


def plane_frame(pa, c, z, aspect):
    """Camera (eye, target) framing painting point c (uv, top-down) at zoom z over cover-fit, plane height 1."""
    cx, cy = (c[0] - 0.5) * pa, 0.5 - c[1]
    vis_h = min(1.0, pa / aspect) / max(z, 1e-3)
    return (cx, cy, vis_h * D0), (cx, cy, 0.0)


def set_u(prog, u):
    for k, v in u.items():
        m = prog.get(k, None)
        if isinstance(m, moderngl.Uniform):
            if isinstance(v, bytes):
                m.write(v)
            else:
                m.value = v


class Sheet:
    """Every painting on one 8192 px texture (fitted into 1024 px cells, alpha = neural depth), for the tile fields."""
    CELL, GRID = 1024, 8

    def __init__(self, paint):
        f, meta = ANALYSIS / "sheet.npy", ANALYSIS / "sheet.json"
        ids = [k for k in paint.cat if (paint.dir / f"{k}.png").exists()]
        if not f.exists():
            S = self.CELL * self.GRID
            A = np.zeros((S, S, 4), np.uint8)
            rects = {}
            for n, pid in enumerate(ids):
                im = Image.open(paint.dir / f"{pid}.png").convert("RGBA")
                s = self.CELL / max(im.size)
                w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
                im = im.resize((w, h), Image.LANCZOS)
                a = np.array(im)
                dp = ANALYSIS / "depth" / f"{pid}.png"
                if dp.exists():
                    a[..., 3] = np.array(Image.open(dp).resize((w, h), Image.BILINEAR), np.float32) / 257.0
                x0, y0 = (n % self.GRID) * self.CELL + (self.CELL - w) // 2, (n // self.GRID) * self.CELL + (self.CELL - h) // 2
                A[y0:y0 + h, x0:x0 + w] = a[::-1]            # bottom-up, like every texture here
                rects[pid] = [x0 / S, y0 / S, (x0 + w) / S, (y0 + h) / S]
            np.save(f, A)
            meta.write_text(json.dumps(rects))
        self.rects = json.loads(meta.read_text())
        self.ids = list(self.rects)
        A = np.load(f)
        self.tex = paint.ctx.texture(A.shape[1::-1], 4, data=A.tobytes())
        self.tex.build_mipmaps()
        self.tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        self.tex.anisotropy = 4.0
        self.art = [k for k in self.ids if not k.startswith("space_") and k != "cmb"]


BOX = np.array([(c, n) for n, faces in (
    ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
    ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)]),
    ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, -1, -1), (-1, 1, 1), (-1, 1, -1)]),
    ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
    ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, -1), (1, -1, 1), (-1, -1, 1)])) for c in faces],
    np.float32).reshape(-1, 6)
TRI = np.array([(x, y, 0, 0, 0, 1) for x, y in ((-1, -1), (1, -1), (-1, 1))], np.float32)
QUAD = np.array([(x, y, 0, 0, 0, 1) for x, y in ((-1, -1), (1, -1), (1, 1), (-1, -1), (1, 1), (-1, 1))], np.float32)


class Field:
    """Instanced quads or boxes. data: N x 4K floats → instance vec4s iA, iB, ...; `glsl` defines place(inout Tile)."""

    def __init__(self, eng, glsl, data, geom="quad"):
        self.eng = eng
        ctx = eng.ctx
        self.n, k = data.shape[0], data.shape[1] // 4
        names = ["iA", "iB", "iC", "iD", "iE", "iF"][:k]
        head = "#version 430\n" + eng.common
        self.prog = ctx.program(vertex_shader=head + rd("field_head.vs") + rd(glsl) + rd("field_main.vs"),
                                fragment_shader="#version 430\n#define FRAG\n" + eng.common + rd("field.fs"))
        from .renderer import bind_units
        bind_units(self.prog)
        geo = BOX if geom == "box" else QUAD
        self.nv = len(geo)
        self.vbo = ctx.buffer(geo.tobytes())
        self.ibo = ctx.buffer(np.asarray(data, np.float32).tobytes())
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "3f 3f", "aC", "aN"),
                                                (self.ibo, " ".join(["4f"] * k) + "/i", *names)], skip_errors=True)

    def draw(self, u, additive=False):
        ctx = self.eng.ctx
        set_u(self.prog, dict(u, uPass=1.0 if additive else 0.0))
        if additive:
            ctx.enable(moderngl.BLEND | moderngl.DEPTH_TEST)
            ctx.fbo.depth_mask = False
            ctx.blend_func = moderngl.ONE, moderngl.ONE
        else:
            ctx.enable(moderngl.DEPTH_TEST)
            ctx.disable(moderngl.BLEND)
            ctx.fbo.depth_mask = True
        self.vao.render(moderngl.TRIANGLES, vertices=self.nv, instances=self.n)
        ctx.fbo.depth_mask = True
        ctx.disable(moderngl.BLEND | moderngl.DEPTH_TEST)

    def release(self):
        for o in (self.vao, self.ibo, self.vbo, self.prog):
            o.release()


class GridMesh:
    """A painting as a displaced sheet: plane height 1, width = aspect, relief along +z from the alpha depth."""

    def __init__(self, eng, shade=None, cols=720, rows=540):
        ctx = eng.ctx
        self.eng = eng
        u, v = np.meshgrid(np.linspace(0, 1, cols + 1, dtype=np.float32), np.linspace(0, 1, rows + 1, dtype=np.float32))
        self.vbo = ctx.buffer(np.stack([u.ravel(), v.ravel()], 1).tobytes())
        i = np.arange((cols + 1) * rows, dtype=np.uint32)
        i = i[(i + 1) % (cols + 1) != 0]
        self.ibo = ctx.buffer(np.stack([i, i + 1, i + cols + 2, i, i + cols + 2, i + cols + 1], 1).tobytes())
        self.prog = ctx.program(vertex_shader="#version 430\n" + eng.common + rd("mesh.vs"),
                                fragment_shader="#version 430\n#define FRAG\n" + eng.common + rd(shade or "mesh_shade.glsl")
                                + rd("mesh.fs"))
        from .renderer import bind_units
        bind_units(self.prog)
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "2f", "aUV")], self.ibo, skip_errors=True)

    def draw(self, u):
        ctx = self.eng.ctx
        set_u(self.prog, u)
        ctx.enable(moderngl.DEPTH_TEST)
        self.vao.render(moderngl.TRIANGLES)
        ctx.disable(moderngl.DEPTH_TEST)


def analysis_tex(ctx, path, mips=True):
    """16-bit analysis image (label maps excluded) → single-channel float texture, bottom-up."""
    a = np.array(Image.open(path), np.float32)[::-1] / 65535.0
    t = ctx.texture(a.shape[1::-1], 1, data=a.tobytes(), dtype="f4")
    t.filter = (moderngl.LINEAR, moderngl.LINEAR)
    return t


class Event:
    """One visual event: load() builds its geometry once, draw(u, t) renders it into the bound HDR target."""
    clear = (0.0, 0.0, 0.0, 1.0)

    def __init__(self, eng):
        self.eng, self.ctx = eng, eng.ctx
        self.cam = Camera(eng)
        self.owned = []

    def keep(self, o):
        self.owned.append(o)
        return o

    def unload(self):
        for o in self.owned:
            o.release()
        self.owned = []

    @property
    def sheet(self):
        return self.eng.paint.sheet()

    def bind(self, name, tex):
        from .renderer import UNITS
        tex.use(location=UNITS[name])


class DreamScene:
    """Adapter: a chapter layer backed by an Event (see EVENTS in engine/events.py)."""

    def __init__(self, eng, kind):
        from .events import EVENTS
        self.eng = eng
        self.tex, _ = eng.target()
        self.depth = eng.ctx.depth_renderbuffer((eng.w, eng.h))
        self.fbo = eng.ctx.framebuffer(color_attachments=[self.tex], depth_attachment=self.depth)
        self.ev = EVENTS[kind](eng)
        self.loaded = False
        self.last_frame, self.last_key = -10, None

    def render(self, u, frame, extra=(), key=None):
        if (self.last_frame, self.last_key) == (frame, key):
            return self.tex
        if not self.loaded:
            self.ev.load()
            self.loaded = True
        self.fbo.use()
        self.fbo.clear(*self.ev.clear, depth=1.0)
        self.ev.fbo = self.fbo
        self.eng.spec_tex.use(location=0)
        self.ev.fbo = self.fbo
        self.ev.draw(dict(u), float(u["uTime"]), dict(extra))
        self.last_frame, self.last_key = frame, key
        return self.tex

    def idle(self, frame):
        if self.loaded and frame - self.last_frame > 40 * self.eng.fps:
            self.ev.unload()
            self.loaded = False
