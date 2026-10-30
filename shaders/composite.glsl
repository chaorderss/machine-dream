// Chapter transitions: A = outgoing chapter, B = incoming.
uniform sampler2D uA, uB;
uniform float uMix;
uniform int uType;        // 0 none, 1 crossfade, 2 dissolve, 3 iris, 4 zoom-through, 5 portal, 6 match, 7 whip, 8 morph,
                          // 9.. the v9 library (see TRANSITIONS in engine/timeline.py): every shot change is its own
uniform float uVar;       // per-transition variant 0..1 (count, shape, sign...)
uniform float uAng;       // per-transition direction, radians
uniform vec2 uTrC;        // per-transition point (bottom-up uv), e.g. where the pupil opens
uniform float uMaster;
uniform vec2 uPortal;     // screen uv of A's portal point (the painting's focus)
uniform vec2 uPortalB;    // screen uv of B's subject (match cut lines it up with A's)

vec2 mirUV(vec2 uv) { return 1.0 - abs(1.0 - mod(uv, 2.0)); }
vec3 TA(vec2 u) { return texture(uA, mirUV(u)).rgb; }
vec3 TB(vec2 u) { return texture(uB, mirUV(u)).rgb; }
float lum(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
bool inside(vec2 u) { return u.x >= 0.0 && u.x <= 1.0 && u.y >= 0.0 && u.y <= 1.0; }
vec2 rot2(vec2 v, float a) { float c = cos(a), s = sin(a); return vec2(c * v.x - s * v.y, s * v.x + c * v.y); }
const vec3 GLOW = vec3(1.0, 0.86, 0.62);

vec3 library(vec2 fc, vec2 uv, vec2 p, float m) {
    float asp = uRes.x / uRes.y;
    float e = smoothstep(0.0, 1.0, m);
    float w = sin(3.14159 * m);
    vec2 dv = vec2(cos(uAng), sin(uAng));
    vec3 a = TA(uv), b = TB(uv);
    if (uType == 9) {            // linear wipe, soft (var 0) .. hard (var 1) edge with a light seam
        float r = 0.5 * (abs(dv.x) * asp + abs(dv.y));
        float s = dot(p, dv), pos = mix(-r - 0.1, r + 0.1, e), sw = mix(0.12, 0.004, uVar);
        float k = smoothstep(pos + sw, pos - sw, s);
        return mix(a, b, k) + GLOW * exp(-abs(s - pos) * 70.0) * w * 0.5;
    }
    if (uType == 10) {           // push: B shoves A off screen along uAng (axis aligned)
        vec2 d = vec2(round(dv.x), round(dv.y));
        vec2 ua = uv - d * e, ub = uv + d * (1.0 - e);
        vec3 c = inside(ua) ? TA(ua) : TB(ub);
        return c * (1.0 - 0.25 * w * smoothstep(0.03, 0.0, min(abs(dot(ua - 0.5, d)) - 0.5, 1.0) + 0.03));
    }
    if (uType == 11) {           // barn doors: A splits down the middle (var < .5) or across (var >= .5) and slides apart
        float x = uVar < 0.5 ? uv.x : uv.y;
        float o = 0.5 * e;
        float xa = x < 0.5 ? x + o : x - o;
        bool door = x < 0.5 ? xa < 0.5 : xa > 0.5;
        vec2 u2 = uVar < 0.5 ? vec2(xa, uv.y) : vec2(uv.x, xa);
        vec3 bb = TB(0.5 + (uv - 0.5) / (1.0 + 0.08 * (1.0 - e)));
        float shade = 1.0 - 0.5 * exp(-abs(xa - 0.5) * 40.0) * w;
        return door ? TA(u2) * shade : bb;
    }
    if (uType == 12) {           // blinds: slats along uAng, count from var, opening one after another
        float n = 4.0 + floor(uVar * 14.0);
        float s = dot(uv - 0.5, vec2(-dv.y, dv.x)) * n + 50.0;
        float id = floor(s), f = fract(s);
        float ei = clamp(m * 1.6 - fract(id * 0.618) * 0.6, 0.0, 1.0);
        return mix(a, b, smoothstep(ei, ei - 0.04, abs(f - 0.5) * 2.0 * 0.999));
    }
    if (uType == 13) {           // tiles flipping over in random order, grid size from var
        float n = 3.0 + floor(uVar * 9.0);
        vec2 g = vec2(n * asp, n);
        vec2 id = floor(uv * g), lc = fract(uv * g) - 0.5;
        float ei = clamp((m - hash12(id + 3.1) * 0.6) / 0.4, 0.0, 1.0);
        float sx = abs(cos(3.14159 * ei));
        if (abs(lc.x) > 0.5 * sx) return vec3(0.0);
        vec2 u2 = (id + 0.5 + vec2(lc.x / max(sx, 1e-3), lc.y)) / g;
        return (ei < 0.5 ? TA(u2) : TB(u2)) * (0.6 + 0.4 * sx);
    }
    if (uType == 14) {           // pixelate: A breaks into blocks, the blocks turn into B, B resolves
        float s = 1.0 + (30.0 + 70.0 * uVar) * pow(w, 1.5) * uRes.y / 1080.0;
        vec2 q = (floor(fc / s) + 0.5) * s / uRes;
        return mix(TA(q), TB(q), smoothstep(0.42, 0.58, m));
    }
    if (uType == 15) {           // clock: a hand sweeps round from uAng, clockwise (var < .5) or not
        float an = atan(p.y, p.x) - uAng;
        float f = fract((uVar < 0.5 ? -an : an) / 6.28318);
        float k = smoothstep(e * 1.02 + 0.01, e * 1.02 - 0.01, f);
        return mix(a, b, k) + GLOW * exp(-abs(f - e) * 120.0) * w * 0.4 * smoothstep(0.0, 0.1, length(p));
    }
    if (uType == 16) {           // shatter: A breaks into shards that fly outwards, B behind
        vec2 q = p * (3.0 + uVar * 6.0);
        vec2 i = floor(q), f = fract(q);
        float d1 = 8.0, d2 = 8.0; vec2 cc = vec2(0.0);
        for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
            vec2 g = vec2(x, y), o = vec2(hash12(i + g), hash12(i + g + 9.7));
            float d = length(g + o - f);
            if (d < d1) { d2 = d1; d1 = d; cc = i + g + o; } else if (d < d2) d2 = d;
        }
        float r = hash12(cc * 1.3);
        float k = smoothstep(r * 0.55, r * 0.55 + 0.35, m);
        vec2 off = normalize(cc + 0.01) * k * 0.35 + vec2(0.0, -k * k * 0.3);
        vec3 sa = TA(uv - off / vec2(asp, 1.0));
        float crack = smoothstep(0.06, 0.0, d2 - d1) * smoothstep(0.0, 0.15, m) * (1.0 - k);
        return mix(sa * (1.0 - 0.6 * crack), b, smoothstep(0.7, 1.0, k));
    }
    if (uType == 17) {           // luma: B's darks arrive first (var < .5) or its lights first
        float l = clamp(lum(b) / (1.0 + lum(b)) * 1.6, 0.0, 1.0);
        float v = uVar < 0.5 ? l : 1.0 - l;
        float th = e * 1.25 - 0.1;
        return mix(a, b, smoothstep(th + 0.08, th - 0.08, v));
    }
    if (uType == 18) {           // ripple: rings run out from a point, the picture changes under the water
        vec2 c = (vec2(0.5) + 0.3 * (vec2(hash12(vec2(uVar, 1.0)), hash12(vec2(uVar, 2.0))) - 0.5)) ;
        vec2 dd = (uv - c) * vec2(asp, 1.0);
        float d = length(dd);
        vec2 off = dd / max(d, 1e-3) * sin(d * 45.0 - m * 28.0) * 0.012 * w * exp(-d * 1.5);
        vec2 u2 = uv + off / vec2(asp, 1.0);
        return mix(TA(u2), TB(u2), smoothstep(0.25, 0.75, m + 0.15 * (0.6 - d)));
    }
    if (uType == 19) {           // glitch: rows of blocks jump sideways, channels split, rows flip to B
        float rows = 10.0 + floor(uVar * 20.0);
        float by = floor(uv.y * rows), ph = floor(m * 14.0);
        float r = hash12(vec2(by, ph));
        float sh = (r - 0.5) * 0.25 * w * step(0.4, r);
        bool sw = hash12(vec2(by, 7.0)) < m;
        vec2 u2 = vec2(uv.x + sh, uv.y);
        float ca = 0.012 * w;
        return sw ? vec3(TB(u2 + vec2(ca, 0)).r, TB(u2).g, TB(u2 - vec2(ca, 0)).b)
                  : vec3(TA(u2 + vec2(ca, 0)).r, TA(u2).g, TA(u2 - vec2(ca, 0)).b);
    }
    if (uType == 20) {           // spiral wipe, arms from var, turning with sign of uAng
        float arms = 1.0 + floor(uVar * 3.0);
        float d = length(p);
        float an = atan(p.y, p.x) * sign(uAng + 1e-3);
        float v = 0.55 * d / 0.95 + 0.45 * fract(an * arms / 6.28318 + d * 1.6);
        return mix(a, b, smoothstep(v + 0.04, v - 0.04, e * 1.12));
    }
    if (uType == 21) {           // shape wipe: a polygon (3..7 sides from var) grows from the centre, turned by uAng
        float N = 3.0 + floor(uVar * 4.99);
        float an = atan(p.y, p.x) + uAng;
        float sec = 6.28318 / N;
        float r = length(p) * cos(mod(an, sec) - 0.5 * sec) / cos(0.5 * sec);
        float R = e * 1.25;
        return mix(a, b, smoothstep(R + 0.015, R - 0.015, r)) + GLOW * exp(-abs(r - R) * 60.0) * w * 0.5;
    }
    if (uType == 22) {           // scanline: a bright scan bar sweeps (down, or across when var >= .5), B behind it
        float y = uVar < 0.5 ? 1.0 - uv.y : uv.x;
        float pos = e * 1.1 - 0.05;
        float near = exp(-abs(y - pos) * 25.0) * w;
        vec2 u2 = uv + vec2(uVar < 0.5 ? (hash12(vec2(floor(uv.y * 200.0), floor(m * 30.0))) - 0.5) * 0.02 * near : 0.0, 0.0);
        vec3 c = y < pos ? TB(u2) : TA(u2);
        c *= 1.0 - 0.25 * near * step(0.5, fract(fc.y * 0.5));
        return c + vec3(0.6, 0.9, 1.0) * exp(-abs(y - pos) * 300.0) * w * 0.8;
    }
    if (uType == 23) {           // burn: the picture burns away along a noise front, embers at the edge
        float n = fbm(p * (2.5 + 2.0 * uVar) + 1.7);
        float th = e * 1.3 - 0.15;
        float k = smoothstep(th - 0.015, th + 0.015, n);
        float edge = exp(-abs(n - th) * 35.0) * w;
        vec3 c = mix(b, a * (1.0 - 0.7 * exp(-(n - th) * 12.0) * w), k);
        return c + vec3(1.0, 0.45, 0.12) * edge * 1.2;
    }
    if (uType == 24) {           // twirl: A twists down the drain, B untwists out of it (sign of uAng = direction)
        float d = length(p), fall = 1.0 - smoothstep(0.0, 0.9, d);
        float sg = sign(uAng + 1e-3);
        vec2 pa = rot2(p, sg * 7.0 * e * fall), pb = rot2(p, -sg * 7.0 * (1.0 - e) * fall);
        vec2 ua = pa / vec2(asp, 1.0) + 0.5, ub = pb / vec2(asp, 1.0) + 0.5;
        return mix(TA(ua), TB(ub), smoothstep(0.3, 0.7, m));
    }
    if (uType == 25) {           // film roll: the strip runs on to the next frame (down when var < .5), with a frame line
        float g = 0.05, sg = uVar < 0.5 ? 1.0 : -1.0;
        vec3 c = vec3(0.0);
        for (int i = 0; i < 5; i++) {
            float off = (e + 0.02 * w * (float(i) / 4.0 - 0.5)) * (1.0 + g);
            float y = uv.y + sg * off;
            vec3 ci;
            if (sg > 0.0) ci = y <= 1.0 ? TA(vec2(uv.x, y)) : (y < 1.0 + g ? vec3(0.02) : TB(vec2(uv.x, y - 1.0 - g)));
            else ci = y >= 0.0 ? TA(vec2(uv.x, y)) : (y > -g ? vec3(0.02) : TB(vec2(uv.x, y + 1.0 + g)));
            c += ci;
        }
        return c / 5.0;
    }
    if (uType == 26) {           // card flip round the vertical axis (var < .5) or the horizontal one
        float th = 3.14159 * e;
        float cw = cos(th);
        vec2 q = uv - 0.5;
        if (uVar >= 0.5) q = q.yx;
        float wdt = abs(cw);
        if (abs(q.x) > 0.5 * wdt) return vec3(0.0);
        float persp = 1.0 + 0.35 * sin(th) * q.x / max(wdt, 1e-3) * sign(cw);
        vec2 qs = vec2(q.x / max(wdt, 1e-3), q.y * persp);
        if (uVar >= 0.5) qs = qs.yx;
        vec2 u2 = qs + 0.5;
        if (!inside(u2)) return vec3(0.0);
        return (cw > 0.0 ? TA(u2) : TB(u2)) * (0.55 + 0.45 * wdt);
    }
    if (uType == 27) {           // cube: A's face turns away to the left (or down when var >= .5), B's turns in
        float x = uVar < 0.5 ? uv.x : uv.y, y = uVar < 0.5 ? uv.y : uv.x;
        float xb = 1.0 - e;
        bool onA = x < xb;
        float lx = onA ? x / max(xb, 1e-3) : (x - xb) / max(1.0 - xb, 1e-3);
        float depth = onA ? lx * e : (1.0 - lx) * (1.0 - e);
        float yy = 0.5 + (y - 0.5) / (1.0 - 0.18 * depth);
        if (yy < 0.0 || yy > 1.0) return vec3(0.0);
        vec2 u2 = uVar < 0.5 ? vec2(lx, yy) : vec2(yy, lx);
        return (onA ? TA(u2) : TB(u2)) * (1.0 - 0.45 * depth);
    }
    if (uType == 28) {           // dip through black
        return m < 0.5 ? a * pow(1.0 - 2.0 * m, 1.5) : b * pow(2.0 * m - 1.0, 1.5);
    }
    if (uType == 29) {           // slit: B opens in a band through the middle (horizontal band var < .5, vertical else)
        float d = uVar < 0.5 ? abs(uv.y - 0.5) : abs(uv.x - 0.5);
        float h = e * 0.55;
        float k = smoothstep(h + 0.01, h - 0.01, d);
        return mix(a * (1.0 - 0.35 * w), b, k) + GLOW * exp(-abs(d - h) * 120.0) * w * 0.5;
    }
    if (uType == 30) {           // kaleidoscope: A folds into a mandala of itself, unfolds as B
        float n = 4.0 + floor(uVar * 6.0) * 2.0;
        float d = length(p), an = atan(p.y, p.x) + m * 1.5;
        float sec = 6.28318 / n;
        float af = abs(mod(an, sec) - 0.5 * sec);
        vec2 pk = d * vec2(cos(af), sin(af));
        vec2 uk = mix(uv, pk / vec2(asp, 1.0) + 0.5, smoothstep(0.0, 0.5, w));
        return mix(TA(uk), TB(uk), smoothstep(0.4, 0.6, m));
    }
    if (uType == 31) {           // melt: A runs down in columns of different speed, B shows from the top
        float cols = 30.0 + floor(uVar * 90.0);
        float r = hash12(vec2(floor(uv.x * cols), 5.0));
        float drop = e * e * (1.2 + 1.2 * r);
        float y = uv.y + drop;
        return y <= 1.0 ? TA(vec2(uv.x, y)) * (1.0 - 0.3 * smoothstep(0.9, 1.0, y)) : b;
    }
    if (uType == 32) {           // zoom blur: A rushes into the screen (out of it when var >= .5), B lands from the blur
        float dir = uVar < 0.5 ? 1.0 : -1.0;
        float za = 1.0 + dir * 0.8 * e, zb = 1.0 + dir * 0.8 * (e - 1.0);
        vec3 ca = vec3(0.0), cb = vec3(0.0);
        for (int i = 0; i < 8; i++) {
            float s = 1.0 - 0.03 * float(i) * w;
            ca += TA(0.5 + (uv - 0.5) / max(za, 0.2) * s);
            cb += TB(0.5 + (uv - 0.5) / max(zb, 0.2) * s);
        }
        return mix(ca, cb, smoothstep(0.35, 0.65, m)) / 8.0;
    }
    if (uType == 33) {           // static: the signal drops into snow and comes back on the other channel
        float n = hash12(floor(fc * 0.5) + floor(uTime * 60.0) * 1.7);
        float roll = fract(uv.y + m * 2.0);
        float amt = pow(w, 0.7) * (0.6 + 0.3 * uVar);
        vec3 c = m < 0.5 ? a : b;
        return mix(c, vec3(n * 0.7 + 0.1) * (0.85 + 0.15 * step(0.03, roll)), amt);
    }
    if (uType == 34) {           // halftone: B arrives as dots that grow until they merge
        float g = (14.0 + uVar * 26.0) * uRes.y / 1080.0;
        vec2 c = (floor(fc / g) + 0.5) * g;
        float r = (e * 0.85 + 0.15 * (hash12(floor(fc / g)) - 0.5) * w) * g;
        return mix(a, b, smoothstep(r + 1.0, r - 1.0, length(fc - c)));
    }
    if (uType == 35) {           // hex cells turn over in a wave from a corner (corner from uAng)
        vec2 r = vec2(1.0, 1.7320508), h = r * 0.5;
        vec2 q = fc / (uRes.y * (0.03 + 0.05 * uVar));
        vec2 A2 = mod(q, r) - h, B2 = mod(q - h, r) - h;
        vec2 g = dot(A2, A2) < dot(B2, B2) ? A2 : B2;
        vec2 cen = (q - g) * uRes.y * (0.03 + 0.05 * uVar) / uRes;
        vec2 o = 0.5 + 0.7 * dv;
        float dl = length((cen - o) * vec2(asp, 1.0)) / (1.2 * asp);
        float ei = clamp((m * 1.5 - dl * 0.8), 0.0, 1.0);
        float sc = abs(cos(3.14159 * ei));
        float hx = max(dot(abs(g), normalize(vec2(1.0, 1.7320508))), abs(g.x));
        if (hx > 0.5 * sc) return vec3(0.0);
        return ei < 0.5 ? a : b;
    }
    if (uType == 36) {           // spin: A turns and shrinks away into the dark, B turns in and grows
        float sg = sign(uAng + 1e-3);
        vec2 pa = rot2(p, sg * e * 1.6) / max(1.0 - 0.75 * e, 0.05);
        vec2 pb = rot2(p, -sg * (1.0 - e) * 1.6) / mix(0.25, 1.0, e);
        vec2 ua = pa / vec2(asp, 1.0) + 0.5, ub = pb / vec2(asp, 1.0) + 0.5;
        vec3 ca = inside(ua) ? TA(ua) : vec3(0.0), cb = inside(ub) ? TB(ub) : vec3(0.0);
        return mix(ca, cb, smoothstep(0.35, 0.65, m));
    }
    if (uType == 37) {           // quad split: the four quarters of A slide off to their corners
        vec2 s = sign(uv - 0.5);
        vec2 ua = uv - s * 0.5 * e * vec2(1.0, 1.0);
        bool keep = sign(ua.x - 0.5) == s.x && sign(ua.y - 0.5) == s.y && inside(ua);
        return keep ? TA(ua) : TB(0.5 + (uv - 0.5) / (1.0 + 0.1 * (1.0 - e)));
    }
    if (uType == 38) {           // slices: strips slide out alternately left and right, staggered
        float n = 6.0 + floor(uVar * 12.0);
        float id = floor(uv.y * n);
        float sg = mod(id, 2.0) < 1.0 ? 1.0 : -1.0;
        float ei = clamp(m * 1.5 - fract(id * 0.37) * 0.5, 0.0, 1.0);
        float x = uv.x + sg * ei * ei * 1.1;
        return (x >= 0.0 && x <= 1.0) ? TA(vec2(x, uv.y)) : b;
    }
    if (uType == 39) {           // brush: a ragged painted edge drags across along uAng
        float r = 0.5 * (abs(dv.x) * asp + abs(dv.y));
        vec2 pp = vec2(-dv.y, dv.x);
        float s = dot(p, dv) + 0.12 * (fbm(vec2(dot(p, pp) * 9.0, 1.0)) - 0.5) + 0.05 * (fbm(p * 20.0) - 0.5);
        float pos = mix(-r - 0.15, r + 0.15, e);
        return mix(a, b, smoothstep(pos + 0.01 + 0.03 * uVar, pos - 0.01, s));
    }
    if (uType == 40) {           // light leak: a warm glow washes across along uAng and leaves B behind
        float s = dot(p, dv);
        float pos = mix(-1.2, 1.2, e);
        float g = exp(-pow((s - pos) * (2.0 + 2.0 * uVar), 2.0)) * w;
        vec3 c = mix(a, b, smoothstep(pos + 0.3, pos - 0.3, s));
        return c * (1.0 - 0.2 * g) + vec3(1.0, 0.6, 0.3) * g * 0.6;
    }
    if (uType == 41) {           // RGB split: B's red, green and blue arrive one after another from different sides
        vec3 c;
        float er = smoothstep(0.0, 0.6, m), eg = smoothstep(0.2, 0.8, m), eb = smoothstep(0.4, 1.0, m);
        vec2 o = dv * 0.15 * (0.5 + uVar);
        c.r = mix(TA(uv - o * er).r, TB(uv + o * (1.0 - er)).r, er);
        c.g = mix(TA(uv).g, TB(uv).g, eg);
        c.b = mix(TA(uv + o * eb).b, TB(uv - o * (1.0 - eb)).b, eb);
        return c;
    }
    if (uType == 42) {           // rack focus: A goes soft, B comes up sharp
        float rad = 0.02 * w * (0.6 + uVar);
        vec3 ca = vec3(0.0), cb = vec3(0.0);
        for (int i = 0; i < 12; i++) {
            float an = float(i) * 2.39996, rr = rad * sqrt((float(i) + 0.5) / 12.0);
            vec2 o = vec2(cos(an), sin(an)) * rr / vec2(asp, 1.0);
            ca += TA(uv + o); cb += TB(uv + o);
        }
        return mix(ca, cb, smoothstep(0.3, 0.7, m)) / 12.0;
    }
    // ── v12: the machine's own five ways of changing a picture (everything happens on a grid of cells)
    float px1080 = uRes.y / 1080.0;
    if (uType == 43) {           // GRID COLLAPSE: A's grid grows until each cell is one flat tone, the tones become B's
        float s = mix(5.0, 70.0 + 110.0 * uVar, pow(w, 1.5)) * px1080;
        vec2 id = floor(fc / s), cen = (id + 0.5) * s;
        float o = 0.25 * s;
        vec3 ca = (TA(cen / uRes) * 2.0 + TA((cen + vec2(o, o)) / uRes) + TA((cen - vec2(o, o)) / uRes)
                 + TA((cen + vec2(o, -o)) / uRes) + TA((cen + vec2(-o, o)) / uRes)) / 6.0;
        vec3 cb = (TB(cen / uRes) * 2.0 + TB((cen + vec2(o, o)) / uRes) + TB((cen - vec2(o, o)) / uRes)
                 + TB((cen + vec2(o, -o)) / uRes) + TB((cen + vec2(-o, o)) / uRes)) / 6.0;
        float r = hash12(id + 0.37);
        vec3 col = mix(ca, cb, smoothstep(0.3 + 0.3 * r, 0.4 + 0.3 * r, m));
        vec2 f = abs(fc - cen) / s;
        col *= mix(1.0, smoothstep(0.5, 0.44, max(f.x, f.y)), smoothstep(0.2, 0.6, w));
        return mix(m < 0.5 ? a : b, col, smoothstep(0.0, 0.2, w));
    }
    if (uType == 44) {           // RECURSIVE SPLIT: B arrives as one cell that keeps splitting into four
        float d = clamp(m * 1.35 - 0.3 * hash12(floor(uv * vec2(asp, 1.0) * 3.0) + uVar), 0.0, 1.0) * 9.0;
        if (d < 1.0) return a;
        float L = floor(d);
        float s = uRes.y * 0.9 / exp2(L);
        vec2 id = floor(fc / s), cen = (id + 0.5) * s;
        float o = 0.25 * s;
        vec3 cb = (TB(cen / uRes) * 2.0 + TB((cen + vec2(o, o)) / uRes) + TB((cen - vec2(o, o)) / uRes)
                 + TB((cen + vec2(o, -o)) / uRes) + TB((cen + vec2(-o, o)) / uRes)) / 6.0;
        vec2 f = abs(fc - cen) / s;
        float line = smoothstep(0.5 - 1.5 / s, 0.5, max(f.x, f.y)) * (1.0 - fract(d));
        return mix(cb * (1.0 - 0.35 * line) + vec3(0.45, 0.85, 1.0) * line * 0.5 * w, b, smoothstep(0.88, 1.0, m));
    }
    if (uType == 45) {           // PIXEL SORT: bright pixels run ahead in streaks, the streaks settle as B
        vec2 dir = uVar < 0.5 ? vec2(0.0, -1.0) : vec2(sign(uAng + 1e-3), 0.0);
        float span = 0.35 * w;
        vec3 ca = a, cb = b;
        for (int i = 1; i <= 14; i++) {
            float th = float(i) / 14.0, o = span * th;
            vec3 sa = TA(uv - dir * o), sb = TB(uv + dir * o);
            if (lum(sa) > 0.15 + 0.8 * th) ca = sa;
            if (lum(sb) > 0.15 + 0.8 * th) cb = sb;
        }
        float k = smoothstep(0.0, 1.0, clamp(m * 1.5 - 0.25 + (lum(b) - 0.5) * 0.5, 0.0, 1.0));
        return mix(ca, cb, k);
    }
    if (uType == 46) {           // LATENT MORPH: two paintings drift through the same cells and become each other
        float s = (7.0 + 20.0 * uVar) * px1080 * (1.0 + 1.2 * w);
        vec2 id = floor(fc / s), cen = (id + 0.5) * s / uRes;
        vec2 q = cen * vec2(asp, 1.0) * 2.0;
        vec2 flow = vec2(fbm(q + uTime * 0.2), fbm(q + vec2(5.2, 1.3) - uTime * 0.2)) - 0.5;
        vec3 ca = TA(cen + flow * 0.12 * w), cb = TB(cen - flow * 0.12 * w);
        float r = 0.55 * hash12(id) + 0.45 * fbm(q * 1.3 + 3.0);
        float k = smoothstep(r - 0.1, r + 0.1, m * 1.3 - 0.15);
        return mix(mix(a, b, k), mix(ca, cb, k), smoothstep(0.0, 0.3, w));
    }
    if (uType == 47) {           // FRACTURE: A's grid cracks, cells twist, shrink and drop out, B shows through
        float s = (28.0 + 70.0 * uVar) * px1080;
        vec2 id = floor(fc / s), lc = fract(fc / s) - 0.5;
        float r = hash12(id + 1.7);
        float k = clamp((m - r * 0.55) / 0.45, 0.0, 1.0);
        float ang = (hash12(id + 3.3) - 0.5) * 2.4 * k * k;
        float sc = 1.0 - 0.85 * k;
        vec2 l2 = rot2(lc - vec2((hash12(id + 5.1) - 0.5) * 0.3, -0.35) * k * k, -ang) / max(sc, 0.05);
        float crack = smoothstep(0.5 - 1.5 / s, 0.5, max(abs(lc.x), abs(lc.y))) * smoothstep(0.0, 0.12, m) * (1.0 - k);
        if (max(abs(l2.x), abs(l2.y)) < 0.5 && k < 1.0)
            return TA((id + 0.5 + l2) * s / uRes) * (1.0 - 0.5 * k) + vec3(0.8, 0.9, 1.0) * crack * 0.6;
        return b;
    }
    if (uType == 48) {           // PUPIL: the eye of every painting opens around a point (var < .5: out of it; else into it)
        bool rev = uVar >= 0.5;
        float mm = rev ? 1.0 - m : m;
        float ee = 1.0 - pow(1.0 - smoothstep(0.0, 1.0, mm), 2.0);
        vec2 c = mix(uTrC, vec2(0.5), ee);
        float z = mix(9.0, 1.0, ee);
        vec2 ue = 0.5 + (uv - c) / z;
        vec3 eye = rev ? (inside(ue) ? TA(ue) : vec3(0.0)) : (inside(ue) ? TB(ue) : vec3(0.0));
        vec2 ui = uTrC + (uv - c) * 9.0 / z;
        vec3 inner = rev ? TB(ui) : TA(ui);
        float R = 0.125 * z;
        float dd = length((uv - c) * vec2(asp, 1.0));
        float kin = smoothstep(R, R - 0.01, dd) * (1.0 - smoothstep(0.55, 1.0, ee));
        return mix(eye, inner, kin);
    }
    if (uType == 49) {           // LIGHT: the last point of light opens onto B round uTrC
        float R = 1.7 * m * m * m;
        float dd = length((uv - uTrC) * vec2(asp, 1.0));
        float k = 1.0 - smoothstep(R * 0.55, R + 1e-4, dd);
        vec3 col = mix(a, b, k);
        float fall = 1.0 - smoothstep(0.35, 1.0, m);
        return col + vec3(1.0, 0.93, 0.82) * (exp(-dd * dd / (R * R + 0.0006)) * 9.0 + exp(-abs(dd - R) * 14.0) * 2.5) * fall;
    }
    return mix(a, b, e);
}

vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec3 b = texture(uB, uv).rgb;
    vec3 col = b;
    float m = clamp(uMix, 0.0, 1.0);
    if (uType == 1) {
        col = mix(texture(uA, uv).rgb, b, smoothstep(0.0, 1.0, m));
    } else if (uType == 2) {
        float n = fbm(p * 3.0 + uTime * 0.2);
        float th = m * 1.3 - 0.15;
        float k = smoothstep(th + 0.04, th - 0.04, n);
        float seam = exp(-abs(n - th) * 60.0) * (1.0 - abs(2.0 * m - 1.0));
        col = mix(texture(uA, uv).rgb, b, k) + pal(0.3) * seam * 2.0;
    } else if (uType == 3) {
        float rad = m * m * 1.2;
        float k = smoothstep(rad + 0.02, rad - 0.06, length(p));
        float ring = exp(-abs(length(p) - rad) * 50.0) * (1.0 - m);
        col = mix(texture(uA, uv).rgb, b, k) + pal(0.1) * ring * 1.5;
    } else if (uType == 4) {
        vec2 uvA = 0.5 + (uv - 0.5) / (1.0 + m * m * 6.0);
        vec3 a = texture(uA, uvA).rgb * (1.0 - m);
        float k = smoothstep(m * 1.4, m * 1.4 - 0.3, length(p));
        col = mix(a, b, k * smoothstep(0.0, 0.3, m));
    } else if (uType == 5) {
        // portal: rush into A's focus point while B, shrunk to fit a growing hole, opens out of it
        float asp = uRes.x / uRes.y;
        float e = m * m * m;
        vec2 uvA = uPortal + (uv - uPortal) / (1.0 + e * 9.0);
        vec3 a = vec3(0.0);
        for (int i = 0; i < 6; i++)                                      // radial speed blur
            a += texture(uA, mirUV(uPortal + (uvA - uPortal) * (1.0 - 0.025 * float(i) * m))).rgb;
        a /= 6.0;
        vec2 cc = mix(uPortal, vec2(0.5), smoothstep(0.45, 1.0, m));     // B recentres as it lands
        float R = 1.3 * smoothstep(0.12, 1.0, m);
        float sc = max(1.0, 0.55 / max(R, 0.02));
        vec2 d = (uv - cc) * vec2(asp, 1.0);
        vec3 bb = texture(uB, mirUV(0.5 + (uv - cc) * sc)).rgb;
        float k = smoothstep(R, R - 0.1, length(d));
        float ring = exp(-abs(length(d) - R) * 45.0) * (1.0 - m) * smoothstep(0.1, 0.3, m);
        col = mix(a, bb, k) + pal(0.1) * ring * 1.6;
    } else if (uType == 6) {
        // match cut: hard cut, B starts shifted so its subject sits where A's was, then settles; A ghosts out
        float e = 1.0 - pow(1.0 - m, 3.0);
        vec2 off = (uPortalB - uPortal) * (1.0 - e);
        vec2 z = (uv + off - uPortalB) / (1.0 + 0.12 * (1.0 - e)) + uPortalB;
        vec3 bb = texture(uB, mirUV(z)).rgb;
        vec3 a = texture(uA, uv).rgb;
        col = mix(bb, max(bb, a), 0.55 * (1.0 - m) * (1.0 - m));
    } else if (uType == 7) {
        // whip pan: A flies out left, B in from the right, smeared along the motion
        float e = smoothstep(0.0, 1.0, m);
        float blur = 0.18 * sin(3.14159 * m);
        col = vec3(0.0);
        for (int i = 0; i < 12; i++) {
            float x = uv.x + blur * (float(i) / 11.0 - 0.5) + e;
            col += x < 1.0 ? texture(uA, mirUV(vec2(x, uv.y))).rgb : texture(uB, mirUV(vec2(x - 1.0, uv.y))).rgb;
        }
        col /= 12.0;
    } else if (uType == 8) {
        // morph: both pictures flow through one noise field; B's bright shapes surface first, A dissolves into them
        float e = smoothstep(0.0, 1.0, m);
        float w = sin(3.14159 * m);
        vec2 q = p * 2.2;
        vec2 flow = vec2(fbm(q + vec2(0.0, uTime * 0.15)), fbm(q + vec2(5.2, 1.3) - uTime * 0.15)) - 0.5;
        vec3 a = texture(uA, mirUV(uv + flow * 0.12 * w * (0.4 + e))).rgb;
        vec3 bb = texture(uB, mirUV(uv - flow * 0.12 * w * (1.4 - e))).rgb;
        float lb = dot(bb, vec3(0.2126, 0.7152, 0.0722));
        float n = 0.55 * fbm(p * 3.0 + 2.0) + 0.45 * clamp(2.0 * lb / (1.0 + lb), 0.0, 1.0);
        float th = 1.15 - 1.3 * e;
        float k = smoothstep(th - 0.1, th + 0.1, n);
        col = mix(a, bb, k) + pal(0.15) * exp(-abs(n - th) * 25.0) * w * 0.8;
    } else if (uType >= 9) {
        col = library(fc, uv, p, m);
    }
    return col * uMaster;
}
