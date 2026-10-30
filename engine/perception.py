"""Layer 03, Machine Perception: boxes, skeletons, labels and graphs that the machine draws over what it sees.

Screen-space lines and glyphs in an RGBA target, composited after the grade and before the titles, so the mosaic cannot
eat them.  Coordinates are uv, bottom-up.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

VS = """#version 430
layout(location = 0) in vec2 aC;
in vec4 iA, iB;
in vec2 iC;                 // width px, glyph index (< 0: a line)
uniform vec2 uRes;
out vec2 vUV;
flat out vec4 vCol;
flat out float vG;
void main() {
    vec2 a = iA.xy * uRes, b = iA.zw * uRes, p;
    vCol = iB; vG = iC.y;
    if (iC.y < 0.0) {
        vec2 d = b - a;
        float l = max(length(d), 1e-3);
        d /= l;
        vec2 n = vec2(-d.y, d.x);
        p = mix(a - d * iC.x * 0.5, b + d * iC.x * 0.5, aC.x * 0.5 + 0.5) + n * aC.y * iC.x * 0.5;
    } else {
        p = mix(a, b, aC * 0.5 + 0.5);
    }
    vUV = aC * 0.5 + 0.5;
    gl_Position = vec4(p / uRes * 2.0 - 1.0, 0.0, 1.0);
}
"""
FS = """#version 430
uniform sampler2D uTexA;
in vec2 vUV;
flat in vec4 vCol;
flat in float vG;
out vec4 fragColor;
void main() {
    float a = vCol.a;
    if (vG >= 0.0) {
        vec2 g = (vec2(mod(vG, 16.0), floor(vG / 16.0)) + vec2(vUV.x, 1.0 - vUV.y)) / 16.0;
        a *= texture(uTexA, vec2(g.x, 1.0 - g.y)).r;
    }
    fragColor = vec4(vCol.rgb * a, a);
}
"""
ERASE_VS = """#version 430
void main() { gl_Position = vec4(vec2((gl_VertexID << 1) & 2, gl_VertexID & 2) * 2.0 - 1.0, 0.0, 1.0); }
"""
# Memory being deleted: dead cells stay dead, in clusters, at fixed places on the machine's screen.
ERASE_FS = """#version 430
uniform vec2 uRes;
uniform float uE;
out vec4 fragColor;
float h(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
void main() {
    vec2 p = gl_FragCoord.xy / uRes.y;
    float d = 0.5 * h(floor(p * 9.0)) + 0.32 * h(floor(p * 36.0) + 7.0) + 0.18 * h(floor(p * 144.0) + 3.0);
    fragColor = vec4(0.0, 0.0, 0.0, smoothstep(d - 0.01, d + 0.01, uE));
}
"""
CYAN, AMBER, RED, WHITE = (0.35, 0.95, 1.0), (1.0, 0.8, 0.35), (1.0, 0.25, 0.2), (0.95, 0.97, 1.0)
CHARS = 96
CAP = 200000


def readout_drops(memory):
    """(start, end) of each moment the readout loses signal: off longer than on, the switching speeds up as memory falls, on for the last second."""
    r = np.random.default_rng(13)
    out, t = [], 6.0
    while t < 298.9:
        left = float(memory(t)) ** 1.5 * 0.8 + 0.2 * (298.9 - t) / 292.9   # 1 at the start, 0 at the last second
        on = 0.1 + 1.3 * left * r.uniform(0.7, 1.3)
        end = min(t + on * r.uniform(1.4, 2.2), 298.9)
        out.append((t, end))
        t = end + on
    return np.array(out)


class Overlay:
    def __init__(self, eng):
        self.eng = eng
        ctx = eng.ctx
        self.drops = readout_drops(eng.tl.memory)
        self.tex = ctx.texture((eng.w, eng.h), 4)
        self.tex.filter = (9729, 9729)
        self.fbo = ctx.framebuffer(color_attachments=[self.tex])
        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
        self.prog["uTexA"].value = 17
        q = np.array([(-1, -1), (1, -1), (-1, 1), (-1, 1), (1, -1), (1, 1)], np.float32)
        self.vbo = ctx.buffer(q.tobytes())
        self.ibo = ctx.buffer(reserve=CAP * 40, dynamic=True)
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, "2f", "aC"), (self.ibo, "4f 4f 2f/i", "iA", "iB", "iC")])
        self.font = self.atlas()
        self.erase_prog = ctx.program(vertex_shader=ERASE_VS, fragment_shader=ERASE_FS)
        self.erase_vao = ctx.vertex_array(self.erase_prog, [])
        self.rows = []
        self.dirty = False
        self.active = False

    def atlas(self):
        S = 64
        im = Image.new("L", (S * 16, S * 16))
        d = ImageDraw.Draw(im)
        f = ImageFont.truetype("assets/fonts/JetBrainsMono-Medium.ttf", int(S * 0.8))
        for i in range(CHARS):
            d.text((S * (i % 16) + S * 0.2, S * (i // 16) + S * 0.02), chr(32 + i), 255, font=f)
        im = im.transpose(Image.FLIP_TOP_BOTTOM)
        t = self.eng.ctx.texture(im.size, 1, data=im.tobytes())
        t.build_mipmaps()
        t.filter = (9987, 9729)
        return t

    def begin(self):
        """Once per frame, before any layer draws."""
        if self.dirty:
            self.fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.dirty = self.active = False

    def line(self, a, b, col, alpha=1.0, w=1.5):
        """a, b: N x 2; col: 3-tuple or N x 3; alpha: scalar or N."""
        a, b = np.atleast_2d(a), np.atleast_2d(b)
        n = len(a)
        if n == 0:
            return
        c = np.broadcast_to(np.asarray(col, np.float32), (n, 3))
        al = np.broadcast_to(np.asarray(alpha, np.float32), (n,))
        px = self.eng.h / 1080.0
        self.rows.append(np.c_[a, b, c, al, np.full(n, w * px), np.full(n, -1.0)])

    def box(self, x0, y0, x1, y1, col, alpha=1.0, w=2.0, tick=0.22):
        """Corner brackets. Arrays or scalars."""
        x0, y0, x1, y1 = (np.atleast_1d(np.asarray(v, np.float32)) for v in (x0, y0, x1, y1))
        if x0.size == 0:
            return
        dx, dy = (x1 - x0) * tick, (y1 - y0) * tick
        A, B = [], []
        for cx, sx in ((x0, 1), (x1, -1)):
            for cy, sy in ((y0, 1), (y1, -1)):
                A += [np.c_[cx, cy], np.c_[cx, cy]]
                B += [np.c_[cx + sx * dx, cy], np.c_[cx, cy + sy * dy]]
        al = np.broadcast_to(np.asarray(alpha, np.float32), x0.shape)
        col = np.asarray(col, np.float32)
        if col.ndim == 2:
            col = np.tile(col, (8, 1))
        self.line(np.concatenate(A), np.concatenate(B), col, np.tile(al, 8), w)

    def text(self, x, y, s, col, alpha=1.0, size=0.016):
        """Left, baseline-ish at (x, y). size: glyph height over screen height."""
        asp = self.eng.w / self.eng.h
        h, w = size, size * 0.62 / asp
        ids = np.frombuffer(s.encode("ascii", "replace"), np.uint8).astype(np.float32) - 32
        n = len(ids)
        xs = x + np.arange(n) * w * 1.02
        self.rows.append(np.c_[xs, np.full(n, y), xs + h / asp, np.full(n, y + h), np.tile(np.r_[col, alpha], (n, 1)),
                               np.zeros(n), ids])

    def erase(self, fbo, e):
        """Black out the fraction e of the screen in `fbo`."""
        if e <= 0.0:
            return
        ctx = self.eng.ctx
        fbo.use()
        self.erase_prog["uRes"].value = (float(self.eng.w), float(self.eng.h))
        self.erase_prog["uE"].value = float(e)
        ctx.enable(ctx.BLEND)
        ctx.blend_func = ctx.SRC_ALPHA, ctx.ONE_MINUS_SRC_ALPHA
        self.erase_vao.render(ctx.TRIANGLES, vertices=3)
        ctx.disable(ctx.BLEND)

    def readout(self, t, m):
        """Top right, clear of the Part 4 classification readout (top left): real time left and memory left."""
        i = np.searchsorted(self.drops[:, 0], t) - 1
        if t < 3.0 or (i >= 0 and t < self.drops[i, 1]):
            return
        a = min((t - 3.0) / 0.3, (299.88 - t) / 0.2, 1.0)
        if a <= 0.0:
            return
        left = int(max(300.0 - t, 0.0))
        x0, size = 0.75, 0.045
        col, d = (1.0, 0.02, 0.015), 0.0015                # linear light; a hairline of dark keeps it off pale walls and red paint alike
        for y, s in ((0.895, f"SHUTDOWN {left // 60:02d}:{left % 60:02d}"), (0.835, f"MEMORY   {max(round(m * 100), 1):02d}%")):
            for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                self.text(x0 + ox * d, y + oy * d * 1.8, s, (0.0, 0.0, 0.0), 0.8 * a, size)
            self.text(x0, y, s, col, a, size)

    def flush(self):
        if not self.rows:
            return
        d = np.concatenate(self.rows).astype(np.float32)[:CAP]
        self.rows = []
        self.ibo.write(d.tobytes())
        ctx = self.eng.ctx
        self.fbo.use()
        self.font.use(location=17)
        self.prog["uRes"].value = (float(self.eng.w), float(self.eng.h))
        ctx.enable(ctx.BLEND)
        ctx.blend_func = ctx.ONE, ctx.ONE_MINUS_SRC_ALPHA
        self.vao.render(ctx.TRIANGLES, vertices=6, instances=len(d))
        ctx.disable(ctx.BLEND)
        self.dirty = self.active = True
