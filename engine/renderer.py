"""ModernGL render engine: scenes → chapter layers → transition composite → bloom → post.

Every frame is a pure function of (time, previous frame, scene state), rendered sequentially,
so a render is reproducible frame-for-frame at any resolution.
"""
import json
import math
from collections import OrderedDict
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .dream import DreamScene, Sheet

ROOT = Path(__file__).resolve().parent.parent
SHADERS = ROOT / "shaders"

FS_VERT = """#version 430
void main() {
    vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""
FRAG_MAIN = """
out vec4 fragColor;
void main() {
    vec3 c = render(gl_FragCoord.xy);
    if (any(isnan(c)) || any(isinf(c))) c = vec3(0.0);
    fragColor = vec4(max(c, 0.0), 1.0);
}
"""
UNITS = {"uSpectrum": 0, "uPrev": 1, "uRD": 2, "uA": 3, "uB": 4, "uSrc": 5, "uHDR": 6,
         "uBloom": 7, "uState": 8, "uInput": 9, "uTitle": 10, "uPaint": 11, "uPalTex": 12, "uAtlas": 13,
         "uSpace": 14, "uTitle2": 15, "uSheet": 16, "uTexA": 17, "uTexB": 18, "uTexC": 19, "uData": 20, "uFlow": 21,
         "uOverlay": 22}
SCENE_FILES = {"cathedral": "cathedral.glsl", "dive": "dive.glsl", "mercury": "mercury.glsl",
               "mandelbox": "mandelbox.glsl", "eye": "eye.glsl", "blackhole": "blackhole.glsl",
               "kaleido": "kaleido.glsl", "julia": "julia.glsl", "hyperbolic": "hyperbolic.glsl",
               "mandelbulb": "mandelbulb.glsl", "warp": "warp.glsl", "voronoi": "voronoi.glsl",
               "truchet": "truchet.glsl", "tunnel2d": "tunnel2d.glsl", "kifs": "kifs.glsl",
               "painting": "painting.glsl"}
STATEFUL = {"organic", "particles"}
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def src(name):
    return (SHADERS / name).read_text()


def bind_units(prog):
    for name, unit in UNITS.items():
        m = prog.get(name, None)
        if isinstance(m, moderngl.Uniform):
            m.value = unit


def set_uniforms(prog, u):
    for k, v in u.items():
        m = prog.get(k, None)
        if isinstance(m, moderngl.Uniform):
            m.value = v


def perspective(fovy, aspect, near, far):
    f = 1.0 / math.tan(fovy / 2)
    return np.array([[f / aspect, 0, 0, 0], [0, f, 0, 0],
                     [0, 0, (far + near) / (near - far), 2 * far * near / (near - far)], [0, 0, -1, 0]], np.float32)


def look_at(eye, target, up=(0.0, 1.0, 0.0)):
    eye, target, up = map(lambda v: np.asarray(v, np.float32), (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4, dtype=np.float32)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


class ShaderScene:
    def __init__(self, eng, file):
        self.eng = eng
        self.prog = eng.program(file)
        self.tex, self.fbo = eng.target()
        self.last_frame, self.last_key = -10, None

    def render(self, u, frame, extra=(), key=None):
        if (self.last_frame, self.last_key) != (frame, key):
            self.eng.draw(self.prog, self.fbo, u, extra)
            self.last_frame, self.last_key = frame, key
        return self.tex


class OrganicScene(ShaderScene):
    """Gray-Scott sim seeded from the previous frame's edges, displayed as lit membrane."""

    def __init__(self, eng):
        super().__init__(eng, "organic.glsl")
        long_side = 1024
        if eng.w >= eng.h:
            self.sim = (long_side, max(8, round(long_side * eng.h / eng.w)))
        else:
            self.sim = (max(8, round(long_side * eng.w / eng.h)), long_side)
        self.state = [eng.target(self.sim, dtype="f4", repeat=True) for _ in range(2)]
        self.step_prog = eng.program("rd_step.glsl")
        self.seed_prog = eng.program("rd_seed.glsl")
        self.cur, self.acc, self.notes = 0, 0.0, 0.0

    def steps(self, su, n, drop=None):
        set_uniforms(self.step_prog, su)
        vao = self.eng.vao(self.step_prog)
        for i in range(n):
            self.step_prog["uDrop"].value = drop if (i == 0 and drop) else (0.0, 0.0, 0.0)
            self.state[self.cur][0].use(location=UNITS["uState"])
            self.state[1 - self.cur][1].use()
            vao.render(moderngl.TRIANGLES, vertices=3)
            self.cur = 1 - self.cur

    def render(self, u, frame, extra=(), key=None):
        if self.last_frame == frame:
            return self.tex
        su = dict(u, uRes=tuple(map(float, self.sim)))
        if self.last_frame != frame - 1:     # (re)activated: grow out of whatever is on screen
            self.eng.draw(self.seed_prog, self.state[self.cur][1], su)
            self.acc, self.notes = 0.0, u["uNoteCount"]
            self.steps(su, int(u.get("rd_warm", 0)))
        self.acc += u["uDt"] * u.get("rd_rate", 1500.0)
        n = int(self.acc)
        self.acc -= n
        drop = None
        if u["uNoteCount"] > self.notes:   # each note plants a new seed of life
            self.notes = u["uNoteCount"]
            r = np.random.default_rng(int(self.notes) * 7919 + 3)
            drop = (float(r.uniform(0.1, 0.9)), float(r.uniform(0.1, 0.9)), 0.006 + 0.01 * u["uHit"])
        self.steps(su, n, drop)
        self.eng.draw(self.prog, self.fbo, u, [("uRD", self.state[self.cur][0])])
        self.last_frame = frame
        return self.tex


class ParticleScene:
    """Transform-feedback particles rendered as depth-of-field bokeh over a faint nebula."""
    N = 1 << 19

    def __init__(self, eng):
        self.eng = eng
        ctx = eng.ctx
        head = "#version 430\n" + eng.common
        self.upd = ctx.program(vertex_shader=head + src("particles_update.glsl"), varyings=["out_pos", "out_vel"])
        self.drw = ctx.program(vertex_shader=head + src("particles_draw_vs.glsl"),
                               fragment_shader="#version 430\n" + src("particles_draw_fs.glsl"))
        bind_units(self.upd)
        bind_units(self.drw)
        self.bufs = [ctx.buffer(reserve=self.N * 32) for _ in range(2)]
        self.vao_u = [ctx.vertex_array(self.upd, [(b, "4f 4f", "in_pos", "in_vel")]) for b in self.bufs]
        self.vao_d = [ctx.vertex_array(self.drw, [(b, "4f 16x", "in_pos")]) for b in self.bufs]
        self.bg = eng.program("nebula.glsl")
        self.tex, self.fbo = eng.target()
        self.cur, self.last_frame, self.last_key = 0, -10, None

    def spawn(self, u):
        r = np.random.default_rng(7)
        n = self.N
        d = r.normal(size=(n, 3)).astype(np.float32)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        pos = d * (0.03 * r.random(n) ** (1 / 3))[:, None]
        speed = r.gamma(2.0, 1.0, n) * u.get("burst", 1.5)
        vel = d * speed[:, None]
        vel[:, 1] *= 0.6
        data = np.zeros((n, 8), np.float32)
        data[:, :3], data[:, 3], data[:, 4:7] = pos, r.random(n) * 1000.0, vel
        self.bufs[self.cur].write(data.tobytes())

    def render(self, u, frame, extra=(), key=None):
        if self.last_frame == frame:
            return self.tex
        eng, ctx = self.eng, self.eng.ctx
        if self.last_frame != frame - 1:
            self.spawn(u)
        set_uniforms(self.upd, u)
        self.vao_u[self.cur].transform(self.bufs[1 - self.cur], mode=moderngl.POINTS, vertices=self.N)
        self.cur = 1 - self.cur

        eng.draw(self.bg, self.fbo, u)
        dist = u.get("uCamDist", 4.0)
        a = 0.04 * u["uTime"]
        eye = (math.sin(a) * dist, 0.15 * dist, math.cos(a) * dist)
        vp = perspective(math.radians(50), eng.w / eng.h, 0.05, 100.0) @ look_at(eye, (0, 0, 0))
        self.drw["uViewProj"].write(vp.T.copy().tobytes())
        set_uniforms(self.drw, dict(u, uCamPos=eye, uFocus=dist * u.get("focus", 1.0),
                                    uPxScale=eng.h / 1080.0))
        self.fbo.use()
        ctx.enable(moderngl.BLEND | moderngl.PROGRAM_POINT_SIZE)
        ctx.blend_func = moderngl.ONE, moderngl.ONE
        self.vao_d[self.cur].render(mode=moderngl.POINTS, vertices=self.N)
        ctx.disable(moderngl.BLEND)
        self.last_frame = frame
        return self.tex


# erase level that blacks out a given fraction of the screen: the cell pattern (engine/perception.py) is not uniform
_r = np.random.default_rng(0).random((3, 200000))
ERASE_CDF = np.sort(0.5 * _r[0] + 0.32 * _r[1] + 0.18 * _r[2])


def erase_level(fraction):
    return float(np.interp(fraction, np.linspace(0.0, 1.0, len(ERASE_CDF)), ERASE_CDF)) if fraction > 0.0 else 0.0


class Paintings:
    """Painting textures (rgb + depth alpha) and their cyclic palettes, loaded lazily, LRU-cached on the GPU."""
    CACHE = 16                                       # split screens + transitions can hold ~10 at once

    def __init__(self, ctx):
        self.ctx = ctx
        self.dir = ROOT / "assets" / "paintings"
        cat = self.dir / "catalog.json"
        self.cat = json.loads(cat.read_text()) if cat.exists() else {}
        self.cache = OrderedDict()
        self._atlas = None
        self._sheet = None
        self.black = ctx.texture((1, 1), 4, data=bytes([0, 0, 0, 128]))
        self.grey_pal = ctx.texture((1, 1), 3, data=np.full(3, 0.5, np.float32).tobytes(), dtype="f4")

    def info(self, pid):
        return self.cat.get(pid)

    def get(self, pid):
        """→ (texture, palette texture, catalog entry) or None when the painting is not on disk."""
        if pid in self.cache:
            self.cache.move_to_end(pid)
            return self.cache[pid]
        path = self.dir / f"{pid}.png"
        if pid not in self.cat or not path.exists():
            print(f"[paintings] missing {pid}")
            self.cache[pid] = None
            return None
        img = Image.open(path).convert("RGBA")
        dp = self.dir.parent / "analysis" / "depth" / f"{pid}.png"
        if dp.exists():                              # v13: neural depth (analysis data) replaces the math-only alpha
            d = np.array(Image.open(dp).resize(img.size, Image.BILINEAR), np.float32) / 257.0
            img.putalpha(Image.fromarray(d.astype(np.uint8)))
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        tex = self.ctx.texture(img.size, 4, data=img.tobytes())
        tex.build_mipmaps()
        tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        tex.anisotropy = 8.0
        cols = np.array(self.cat[pid]["palette"], np.float32) ** 2.2 * 1.25      # sRGB → linear, a bit hot
        x = np.linspace(0, len(cols), 256, endpoint=False)
        i0 = np.floor(x).astype(int) % len(cols)
        f = (x - np.floor(x))[:, None]
        f = f * f * (3 - 2 * f)
        ramp = cols[i0] * (1 - f) + cols[(i0 + 1) % len(cols)] * f               # cyclic: no seam at fract()
        pal = self.ctx.texture((256, 1), 3, data=ramp.astype(np.float32).tobytes(), dtype="f4")
        pal.repeat_x = True
        pal.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.cache[pid] = (tex, pal, self.cat[pid])
        while len(self.cache) > self.CACHE:
            old = self.cache.popitem(last=False)[1]
            if old:
                old[0].release()
                old[1].release()
        return self.cache[pid]

    def sheet(self):
        if self._sheet is None:
            self._sheet = Sheet(self)
        return self._sheet

    def atlas(self):
        """All paintings as an 8x8 grid of 512 px squares (cropped round their focus) for the hyper-montage."""
        if self._atlas is None:
            path = self.dir / "atlas.png"
            ids = [k for k in self.cat if not k.startswith("space_")][:64]
            if not path.exists():
                A = Image.new("RGB", (4096, 4096))
                for n, pid in enumerate(ids):
                    im = Image.open(self.dir / f"{pid}.png").convert("RGB")
                    w, h = im.size
                    sq = min(w, h)
                    fx, fy = self.cat[pid]["focus"]
                    x0 = int(np.clip(fx * w - sq / 2, 0, w - sq))
                    y0 = int(np.clip(fy * h - sq / 2, 0, h - sq))
                    A.paste(im.crop((x0, y0, x0 + sq, y0 + sq)).resize((512, 512), Image.LANCZOS),
                            ((n % 8) * 512, (n // 8) * 512))
                A.save(path)
            img = Image.open(path).convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM)
            self._atlas = self.ctx.texture(img.size, 4, data=img.tobytes())
            self._atlas.build_mipmaps()
            self._atlas.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.atlas_n = len(ids)
        return self._atlas


def painting_view(info, kb, prog, aspect, focus_pull=1.0, frame=None, lt=0.0):
    """Ken-Burns framing of a painting on screen → (uView vec4, focus in screen uv).
    Screen point p (y in [-0.5, 0.5], x scaled by aspect) maps to uv = c + (p.x / pa, p.y) * s.
    frame = {"c", "z", "drift"} pins the shot instead: a close-up of painting point c at zoom z (1 = cover-fit)."""
    pa = info["aspect"]
    s0 = min(1.0, pa / aspect)                       # cover-fit
    e = prog * prog * (3 - 2 * prog)
    if frame is not None:
        s = s0 / max(frame["z"](lt), 1e-3)
        f = np.array([frame["c"][0] + frame["drift"][0] * e, 1.0 - frame["c"][1] - frame["drift"][1] * e])
        hx, hy = aspect / (2 * pa) * s, 0.5 * s
        c = np.array([np.clip(f[0], min(hx, 0.5), max(1 - hx, 0.5)), np.clip(f[1], min(hy, 0.5), max(1 - hy, 0.5))])
        fs = ((f[0] - c[0]) * pa / s / aspect + 0.5, (f[1] - c[1]) / s + 0.5)
        return (float(c[0]), float(c[1]), float(s), float(pa)), tuple(map(float, fs))
    s = s0 / (1.0 + 0.6 * kb * e)
    fx, fy = info["focus"]
    f = np.array([fx, 1.0 - fy])                     # catalog y is top-down
    hx, hy = aspect / (2 * pa) * s, 0.5 * s
    tgt = np.array([np.clip(f[0], hx, 1 - hx), np.clip(f[1], hy, 1 - hy)])
    c = np.array([0.5, 0.5]) + (tgt - 0.5) * e * min(kb, 1.0) * focus_pull
    fs = ((f[0] - c[0]) * pa / s / aspect + 0.5, (f[1] - c[1]) / s + 0.5)
    return (float(c[0]), float(c[1]), float(s), float(pa)), tuple(map(float, fs))


class Engine:
    BLOOM_LEVELS = 6

    def __init__(self, timeline, features, size, fps):
        self.tl, self.feats = timeline, features
        self.w, self.h = size
        self.fps = fps
        self.ctx = moderngl.create_context(standalone=True, backend="egl", require=430)
        self.common = src("common.glsl")
        self._vaos = {}
        self.spec_tex = self.ctx.texture((64, 1), 1, dtype="f4")
        self.prev, self.prev_fbo = self.target()
        self.chap = {0: self.target(), 1: self.target()}   # per-slot layer accumulators (panels add more lazily)
        self.pp = {}                                       # per-slot ping-pong targets for split-screen panels
        self.comp, self.comp_fbo = self.target()
        self.down, self.up = [], []
        for i in range(self.BLOOM_LEVELS):
            s = (max(1, self.w >> (i + 1)), max(1, self.h >> (i + 1)))
            self.down.append(self.target(s) + (s,))
            self.up.append(self.target(s) + (s,))
        self.out_tex = self.ctx.texture(size, 4)
        self.out_fbo = self.ctx.framebuffer(color_attachments=[self.out_tex])
        self.p_comp = self.program("composite.glsl")
        self.p_panel = self.program("panel.glsl")
        self.p_probe = self.program("probe.glsl")
        self.probe_tex, self.probe_fbo = self.target()
        self.p_mosaic = self.program("mosaic.glsl")
        self.mos_tex, self.mos_fbo = self.target()
        self.p_blit = self.program("blit.glsl")
        self.p_down = self.program("bloom_down.glsl")
        self.p_up = self.program("bloom_up.glsl")
        self.p_post = self.program("hud.glsl", "post.glsl")
        self.overlay = None
        self.readout_on = True
        self.spark_gain = 1.0
        self.paint = Paintings(self.ctx)
        self.scenes = {}
        self.titles = [self._title_texture(t) for t in self.tl.titles]
        self.no_title = self.ctx.texture((1, 1), 4, data=bytes(4))
        self.reset()

    # ---------------------------------------------------------------- GL helpers
    def target(self, size=None, dtype="f2", repeat=False):
        tex = self.ctx.texture(size or (self.w, self.h), 4, dtype=dtype)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        tex.repeat_x = tex.repeat_y = repeat
        return tex, self.ctx.framebuffer(color_attachments=[tex])

    def program(self, *files):
        fs = "#version 430\n#define FRAG\n" + self.common + "\n".join(src(f) for f in files) + FRAG_MAIN
        p = self.ctx.program(vertex_shader=FS_VERT, fragment_shader=fs)
        bind_units(p)
        return p

    def vao(self, prog):
        if id(prog) not in self._vaos:
            self._vaos[id(prog)] = self.ctx.vertex_array(prog, [])
        return self._vaos[id(prog)]

    def draw(self, prog, fbo, u, textures=()):
        self.spec_tex.use(location=UNITS["uSpectrum"])
        self.prev.use(location=UNITS["uPrev"])
        for name, tex in textures:
            tex.use(location=UNITS[name])
        fbo.use()
        set_uniforms(prog, u)
        self.vao(prog).render(moderngl.TRIANGLES, vertices=3)

    def scene(self, name, key=None):
        """Scene instance; when it already rendered this frame for another chapter, use a twin instance."""
        if name not in self.scenes:
            base = name.split("@")[0]
            if base.startswith("dream:"):
                self.scenes[name] = DreamScene(self, base[6:])
            elif base == "organic":
                self.scenes[name] = OrganicScene(self)
            elif base == "particles":
                self.scenes[name] = ParticleScene(self)
            else:
                self.scenes[name] = ShaderScene(self, SCENE_FILES[base])
        sc = self.scenes[name]
        if key is not None and sc.last_frame == self.frame and sc.last_key != key:
            base, _, k = name.partition("@")
            return self.scene(f"{base}@{int(k or 0) + 1}", key)    # twin instance per extra user this frame
        return sc

    def _line_image(self, text, px, fontpath, idx, color, tracking, weight=None, shadow=False):
        try:
            font = ImageFont.truetype(fontpath, px, index=idx)
            if weight:
                font.set_variation_by_axes([weight])
        except (OSError, ValueError):
            font = ImageFont.load_default()
        probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        track = tracking * px
        widths = [probe.textlength(ch, font=font) for ch in text]
        total = sum(widths) + track * (len(text) - 1)
        pad = px // 3 if shadow else 0
        img = Image.new("RGBA", (max(1, int(math.ceil(total)) + 2 + 2 * pad), px * 2), (0, 0, 0, 0))
        layers = [((0, 0, 0), True), (tuple(color), False)] if shadow else [(tuple(color), False)]
        for col, blur in layers:                       # soft dark halo first, so captions read on any painting
            lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(lay)
            x = float(pad)
            for ch, wd in zip(text, widths):
                dr.text((x, px * 0.5), ch, font=font, fill=col + (255,))
                x += wd + track
            if blur:
                lay = lay.filter(ImageFilter.GaussianBlur(px / 6))
                lay.putalpha(lay.getchannel("A").point(lambda a: min(255, int(a * 2.2))))
            img.alpha_composite(lay)
        return img

    def _title_texture(self, t):
        px = max(8, int(t.get("size", 0.035) * self.h))
        fontpath = t.get("font", "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-ExtraLight.ttf")
        color = tuple(t.get("color", [255, 255, 255]))
        wt, sh = t.get("weight"), t.get("shadow", False)
        lines = [self._line_image(ln, px, fontpath, t.get("font_index", 0), color, t.get("tracking", 0.15), wt, sh)
                 for ln in t["text"].split("\n")]
        img = lines[0]
        if len(lines) > 1:                             # several lines (HUD readouts), left-aligned or centred
            lh = int(px * t.get("leading", 1.35))
            img = Image.new("RGBA", (max(l.width for l in lines), lh * (len(lines) - 1) + lines[-1].height), (0, 0, 0, 0))
            for k, l in enumerate(lines):
                img.alpha_composite(l, (0 if t.get("align") == "left" else (img.width - l.width) // 2, k * lh))
        if t.get("sub"):                               # subtitle line, centred under the title
            sb = t["sub"]
            spx = max(8, int(sb["size"] * self.h))
            sub = self._line_image(sb["text"], spx, sb.get("font", fontpath), sb.get("font_index", t.get("font_index", 0)),
                                   sb.get("color", color), sb["tracking"], wt if "font" not in sb else None, sh)
            both = Image.new("RGBA", (max(img.width, sub.width), img.height + sub.height), (0, 0, 0, 0))
            both.alpha_composite(img, ((both.width - img.width) // 2, 0))
            both.alpha_composite(sub, ((both.width - sub.width) // 2, img.height))
            img = both
        x0 = t["x"] * self.w if "x" in t else (self.w - img.width) / 2
        if t.get("band"):                              # chapter card: full-width soft dark band behind the text
            bh = int(img.height * t.get("band_h", 2.0))
            yy = np.linspace(-1.0, 1.0, bh)
            a = (np.exp(-(yy * 1.6) ** 2) * 255 * t["band"]).astype(np.uint8)
            band = Image.new("RGBA", (self.w, bh), (0, 0, 0, 0))
            band.putalpha(Image.fromarray(np.repeat(a[:, None], self.w, 1)))
            off = (bh - img.height) // 2
            band.alpha_composite(img, (int(x0), off))
            img, x0 = band, 0.0
            t = dict(t, y=t.get("y", 0.5) - off / self.h)     # keep the text where it was; the band grows around it
        if t.get("plate"):                             # HUD readout: faint dark plate so it reads over bright frames
            pad = px // 2
            b = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, int(255 * t["plate"])))
            b.alpha_composite(img, (pad, pad))
            img, x0 = b, x0 - pad
            t = dict(t, y=t.get("y", 0.5) - pad / self.h)
        if t.get("box"):                               # HUD style: bracketed box around the label
            b = Image.new("RGBA", (img.width + px, img.height), (0, 0, 0, 0))
            bd = ImageDraw.Draw(b)
            bd.rectangle([1, int(px * 0.3), b.width - 2, int(px * 1.75)], fill=(0, 0, 0, 110),
                         outline=color + (220,), width=max(1, px // 14))
            b.alpha_composite(img, (px // 2, 0))
            img, x0 = b, x0 - px / 2
        # placement rect in top-down screen uv: (x0, y0, x1, y1)
        y0 = t.get("y", 0.5) * self.h - px
        rect = (x0 / self.w, y0 / self.h, (x0 + img.width) / self.w, (y0 + img.height) / self.h)
        tex = self.ctx.texture(img.size, 4, data=img.tobytes())
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        return dict(t, rect=rect), tex

    # ---------------------------------------------------------------- frame
    def reset(self):
        for s in self.scenes.values():
            s.last_frame = -10
        self.prev_fbo.clear(0, 0, 0, 1)
        self.comp_fbo.clear(0, 0, 0, 1)
        self.slow_lum = None
        self.lum_log = []
        self.portals = {0: (0.5, 0.5), 1: (0.5, 0.5)}
        self.frame = 0

    def bind_painting(self, ch, lt, u):
        """Bind the chapter's painting / palette / deep-space textures; returns the portal point (screen uv)."""
        got = self.paint.get(ch.painting) if ch.painting else None
        portal = (0.5, 0.5)
        if got:
            tex, pal, info = got
            prog = min(max(lt / max(ch.end - ch.start, 1e-6), 0.0), 1.0)
            view, fs = painting_view(info, u.get("uKB", 1.0), prog, self.w / self.h, frame=ch.frame, lt=lt)
            fx, fy = ch.frame["c"] if ch.frame else info["focus"]
            u.update(uView=view, uFocusS=fs, uFocus=(fx, 1.0 - fy), uPalPaint=u.get("uPalPaint", 0.75))
            tex.use(location=UNITS["uPaint"])
            pal.use(location=UNITS["uPalTex"])
            if ch.portal == "focus":
                portal = fs
        else:
            u.update(uView=(0.5, 0.5, 1.0, self.w / self.h), uFocusS=(0.5, 0.5), uFocus=(0.5, 0.5), uPalPaint=0.0)
            self.paint.black.use(location=UNITS["uPaint"])
            self.paint.grey_pal.use(location=UNITS["uPalTex"])
        sp = self.paint.get(ch.space) if ch.space else None
        (sp[0] if sp else self.paint.black).use(location=UNITS["uSpace"])
        if ch.atlas:
            self.paint.atlas().use(location=UNITS["uAtlas"])
            u["uAtlasN"] = float(self.paint.atlas_n)
        if isinstance(ch.portal, (list, tuple)):
            portal = tuple(ch.portal)
        return portal

    def render_chapter(self, ch, t, base, slot):
        u = dict(base)
        u.update(ch.uniforms(t))
        lt = t - ch.start
        self.portals[slot] = self.bind_painting(ch, lt, u)
        items = []
        n = len(ch.layers)
        for i, L in enumerate(ch.layers):
            w = L.weight(lt)
            feeds_next = i + 1 < n and ch.layers[i + 1].input
            if w <= 1e-3 and not feeds_next:
                continue
            extra = []
            if L.input and items:
                extra = [("uInput", items.pop()[0])]
            lu = dict(u, uHasInput=float(bool(extra)), _ch=ch)
            tex = self.scene(L.scene, ch.index).render(lu, self.frame, extra, key=ch.index)
            items.append((tex, w))
        if len(items) == 1 and abs(items[0][1] - 1.0) < 1e-6:
            return self.render_panels(ch, t, base, slot, items[0][0])
        if slot not in self.chap:
            self.chap[slot] = self.target()
        acc_tex, acc_fbo = self.chap[slot]
        acc_fbo.clear(0, 0, 0, 1)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.ONE, moderngl.ONE
        for tex, w in items:
            self.draw(self.p_blit, acc_fbo, {"uRes": (float(self.w), float(self.h)), "uWeight": w}, [("uSrc", tex)])
        self.ctx.disable(moderngl.BLEND)
        return self.render_panels(ch, t, base, slot, acc_tex)

    def render_panels(self, ch, t, base, slot, cur):
        """Split screen / polyptych / double exposure: each panel is a sub-chapter drawn into its rect over cur."""
        if not ch.panels:
            return cur
        if slot not in self.pp:
            self.pp[slot] = [self.target(), self.target()]
        k = 0
        for i, sub in enumerate(ch.panels):
            a = sub.alpha(t - ch.start)
            if a <= 1e-3:
                continue
            tex = self.render_chapter(sub, t, base, f"{slot}.{i}")
            x0, y0, x1, y1 = sub.rect
            dst_tex, dst_fbo = self.pp[slot][k % 2]
            self.draw(self.p_panel, dst_fbo, {"uRes": (float(self.w), float(self.h)), "uRect": (x0, 1.0 - y1, x1, 1.0 - y0),
                                              "uAlpha": a, "uBlend": sub.blend, "uBorder": sub.border},
                      [("uA", cur), ("uB", tex)])
            cur, k = dst_tex, k + 1
        return cur

    def probe_state(self, t):
        pr = self.tl.probe
        x, y, r, a = pr["pos"](t)
        bob = r * 0.08
        x += bob * math.sin(t * 2.1) / (self.w / self.h)
        y += bob * math.sin(t * 1.7 + 1.0)
        return x, y, r, a

    def overlay_on(self):
        if self.overlay is None:
            from .perception import Overlay
            self.overlay = Overlay(self)
        return self.overlay

    def erase_at(self, ch, t, m):
        """Fraction of the screen lost: the memory curve, plus this painting being deleted as its shot ends."""
        f = (1.0 - m) ** 2.2
        if ch.end - ch.start >= 2.5:
            k = max(0.0, min(1.0, (t - (ch.end - 1.2)) / 1.4))
            f += 0.32 * k * k * (3.0 - 2.0 * k)
        return erase_level(min(f, 0.97) * ch.erase)

    def draw_probe(self, t, base):
        """IRIS-01 over the composite (HDR, before bloom so its lens glows)."""
        x, y, r, a = self.probe_state(t)
        a *= self.spark_gain
        if self.spark_xy:                            # a dream scene knows where the point of light really is
            x, y = self.spark_xy
        if a <= 1e-3 or r <= 1e-4:
            return
        pr = self.tl.probe
        st = pr["state"](t)
        trail = []
        for k in range(1, 9):
            tx, ty, tr, _ = self.probe_state(t - 0.035 * k)
            trail.append((tx, 1.0 - ty, tr))
        u = dict(base, uProbe=(x, 1.0 - y, r, a), uLook=pr["look"](t), uIris=tuple(st[:3]), uGlow=st[3],
                 uCrack=st[4], uVein=st[5], uRingA=0.25 * math.sin(t * 0.37), uTrail=trail,
                 uSpark=1.0 if pr["spark"] else 0.0)
        self.draw(self.p_probe, self.probe_fbo, u, [("uA", self.comp)])
        self.ctx.copy_framebuffer(self.comp_fbo, self.probe_fbo)

    def bloom(self, src_tex=None):
        src_tex = src_tex or self.comp
        for i, (tex, fbo, s) in enumerate(self.down):
            th = 0.8 if i == 0 else 0.0
            self.draw(self.p_down, fbo, {"uRes": tuple(map(float, s)), "uThreshold": th}, [("uSrc", src_tex)])
            src_tex = tex
        cur = self.down[-1][0]
        for i in reversed(range(self.BLOOM_LEVELS - 1)):
            tex, fbo, s = self.up[i]
            self.draw(self.p_up, fbo, {"uRes": tuple(map(float, s))}, [("uSrc", cur), ("uB", self.down[i][0])])
            cur = tex
        return cur

    def limiter(self, exposure, dt):
        """Photosensitivity guard (WCAG/Harding: a flash = a pair of opposing swings of >=0.1 relative luminance).
        v13: a single big bloom of light is allowed (+0.34 over the 0.35 s average); the hard floor is the rate. Once
        the last second already holds 4 swings, or the frame is saturated red, the old +0.06 ceiling comes back."""
        lv = max(0, int(math.log2(max(self.w, self.h))) - 5)        # ~32 px wide mip of the composite
        self.comp.build_mipmaps(0, lv)
        data = np.frombuffer(self.comp.read(level=lv), np.float16).reshape(-1, 4)[:, :3].astype(np.float32)
        self.comp.filter = (moderngl.LINEAR, moderngl.LINEAR)
        lum = max(float((data @ LUMA).mean()) * exposure, 1e-6)
        disp = lum / (1.0 + lum)
        if self.slow_lum is None:
            self.slow_lum = disp
        red = data[:, 0] / np.maximum(data.sum(1), 1e-6) >= 0.8        # WCAG saturated red
        strict = self._recent_swings() >= 4 or float(red.mean()) > 0.25
        limit = min(self.slow_lum + (0.06 if strict else 0.34), 0.95)
        factor = 1.0
        if disp > limit:
            factor = (limit / (1.0 - limit)) / lum
            disp = limit
        self.slow_lum += (disp - self.slow_lum) * (1.0 - math.exp(-dt / 0.35))
        self.lum_log.append(disp)
        return factor

    def _recent_swings(self):
        """Swings of >=0.1 between luminance extrema in the last second of the log."""
        x = np.asarray(self.lum_log[-int(self.fps) - 1:])
        if len(x) < 3:
            return 0
        d = np.diff(x)
        ext = [0] + [i + 1 for i in range(len(d) - 1) if d[i] * d[i + 1] < 0] + [len(x) - 1]
        return int((np.abs(np.diff(x[ext])) >= 0.1).sum())

    def render_frame(self, t, dt, output=True):
        tl = self.tl
        for sc in self.scenes.values():
            if isinstance(sc, DreamScene):
                sc.idle(self.frame)
        self.spark_xy = None
        self.spark_gain = 1.0
        if self.overlay is not None:
            self.overlay.begin()
        A, B, mix, ttype = tl.state(t)
        freeze, tear = tl.glitch_at(t)
        base = {"uRes": (float(self.w), float(self.h)), "uTime": t, "uDt": dt,
                "uIntensity": tl.intensity(t), "uTravel": tl.travel(t)}
        base.update(self.feats.sample(t))
        base["uMemory"] = tl.memory(t) if tl.memory else 1.0
        self.spec_tex.write(self.feats.spectrum(t).astype(np.float32).tobytes())
        if not freeze:
            tex_b = self.render_chapter(B, t, base, 1)
            tex_a = self.render_chapter(A, t, base, 0) if A else tex_b
            cu = dict(base, uMix=mix, uType=ttype, uMaster=tl.master(t), uPortal=self.portals[0], uPortalB=self.portals[1],
                      uVar=B.tr_var, uAng=B.tr_ang, uTrC=(B.tr_c[0], 1.0 - B.tr_c[1]))
            cu.update({k: v for k, v in B.uniforms(t).items() if k.startswith("uPal")})
            cu["uPalPaint"] = 0.0
            if ttype == 5:                           # portal shrinks B up to 10x: needs mips
                tex_b.build_mipmaps()
                tex_b.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.draw(self.p_comp, self.comp_fbo, cu, [("uA", tex_a), ("uB", tex_b)])
            tex_b.filter = (moderngl.LINEAR, moderngl.LINEAR)
            if tl.probe and not tl.in_insert(t):
                self.draw_probe(t, base)
            if tl.memory:
                eb = self.erase_at(B, t, base["uMemory"])
                e = eb if A is None else self.erase_at(A, t, base["uMemory"]) * (1.0 - mix) + eb * mix
                self.overlay_on().erase(self.comp_fbo, e)


        frame_bytes = None
        if output:
            post = B.post_values(t)
            if A:
                pa = A.post_values(t)
                post = {k: pa[k] + (post[k] - pa[k]) * mix for k in post}
            hdr = self.comp
            if tl.memory:
                ov = self.overlay_on()
                if self.readout_on:
                    ov.readout(t, base["uMemory"])
                ov.flush()
            if tl.mosaic:                            # machine vision: re-sample the frame into cells (titles stay sharp)
                mo = {k: c(t) for k, c in tl.mosaic.items()}
                x0, y0, x1, y1 = mo["mask"]               # top-down rect → bottom-up
                if mo["amt"] > 1e-3:
                    self.draw(self.p_mosaic, self.mos_fbo,
                              dict(base, uAmt=mo["amt"], uCell=mo["cell"], uShape=mo["shape"], uGap=mo["gap"],
                                   uQuant=mo["quant"], uFovea=mo["fovea"], uFocus=self.portals[1],
                                   uFlowL=mo["flowl"], uFlowC=mo["flowc"], uFlowS=mo["flows"], uFlowK=mo["flowk"],
                                   uMask=(x0, 1.0 - y1, x1, 1.0 - y0), uOutside=mo["outside"],
                                   uCrystal=mo["crystal"], uMaskCrystal=mo["maskcrystal"]), [("uA", self.comp)])
                    hdr = self.mos_tex
            bloom_tex = self.bloom(hdr)
            exposure = post["exposure"] * self.limiter(post["exposure"], dt)
            # two title layers: 0 = narration / cards, 1 = the machine's HUD readout (Part 4 classification)
            slots = [[self.no_title, 0.0, (0.0, 0.0, 1.0, 1.0), 1.0, 0.0] for _ in range(2)]
            for spec, tex in self.titles:
                if spec["start"] <= t < spec["end"]:
                    f = spec.get("fade", 0.25)
                    a = min(1.0, (t - spec["start"]) / f, (spec["end"] - t) / f)
                    decode, seed = 1.0, 0.0
                    if spec.get("decode"):           # machine text: cells switch on in random order, then off
                        din, dout = spec["decode"]
                        decode = max(0.0, min(1.0, (t - spec["start"]) / din, (spec["end"] - t) / dout))
                        a, seed = 1.0, float(spec["start"])
                    if spec.get("blink"):
                        a *= float((t * spec["blink"]) % 1.0 < 0.6)
                    slots[spec.get("layer", 0)] = [tex, a, spec["rect"], decode, seed]
            (title_tex, title_a, title_rect, decode, seed), (tex2, a2, rect2, decode2, seed2) = slots
            mo = {k: c(t) for k, c in tl.mosaic.items()} if tl.mosaic else None
            tcell = max(1.6 * self.h / 1080.0, 0.2 * mo["cell"] * self.h) if mo else 0.0   # titles: fine pixel matrix
            tflow = (mo["flowl"], mo["flowc"], mo["flows"], mo["flowk"]) if mo else (0.0, 0.0, 1.0, 2.0)
            hc = B if (A is None or mix >= 0.5) else A
            hud = hc.hud_values(t)
            hud_focus = self.portals[1] if hc is B else self.portals[0]
            pu = dict(base, uExposure=exposure, uBloomStr=post["bloom"] / self.BLOOM_LEVELS, uCA=post["ca"],
                      uGrain=post["grain"], uVignette=post["vignette"], uGrade=post["grade"], uTear=tear,
                      uTitleAlpha=title_a, uTitleRect=title_rect, uGradeHue=base["uCentroid"], uSat=post["sat"],
                      uHue=post["hue"], uTealGold=post["teal"], uHud0=hud[0], uHud1=hud[1],
                      uHudA=hud[2] * (1.0 - abs(2.0 * mix - 1.0) if A else 1.0), uHudCol=hud[3], uHudFocus=hud_focus,
                      # tutti → 2-frame-ish negative flash (cut events are already >=2 s apart)
                      uInvert=post["invert"] * float(base["uCutAge"] < 0.07),
                      uTCell=tcell, uTDecode=decode, uTSeed=seed, uTFlow=tflow,
                      uTitleAlpha2=a2, uTitleRect2=rect2, uTDecode2=decode2, uTSeed2=seed2)
            pt = [("uHDR", hdr), ("uBloom", bloom_tex), ("uTitle", title_tex), ("uTitle2", tex2)]
            on = self.overlay is not None and self.overlay.active
            pu["uOverlayOn"] = float(on)
            if on:
                pt.append(("uOverlay", self.overlay.tex))
            self.draw(self.p_post, self.out_fbo, pu, pt)
            frame_bytes = self.out_fbo.read(components=3, alignment=1)
        if not freeze:
            self.ctx.copy_framebuffer(self.prev_fbo, self.comp_fbo)
        self.frame += 1
        return frame_bytes

    def preroll(self, t0):
        start = self.tl.preroll_start(t0, STATEFUL)
        n = int(round((t0 - start) * self.fps))
        for i in range(n):
            self.render_frame(t0 - (n - i) / self.fps, 1.0 / self.fps, output=False)

    def flash_report(self):
        """Max flashes in any 1 s window: swings between luminance extrema of >=0.1, two per flash."""
        x = np.asarray(self.lum_log)
        if len(x) < 3:
            return 0.0
        ext = [0] + [i for i in range(1, len(x) - 1) if (x[i] - x[i - 1]) * (x[i + 1] - x[i]) < 0] + [len(x) - 1]
        chg = np.array([ext[k + 1] for k in range(len(ext) - 1) if abs(x[ext[k + 1]] - x[ext[k]]) >= 0.1])
        if len(chg) == 0:
            return 0.0
        return max(int(((chg >= i) & (chg < i + self.fps)).sum()) for i in chg) / 2.0
