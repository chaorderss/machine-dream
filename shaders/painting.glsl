// Masterpiece engine: one public-domain painting per slot, rewritten by five master algorithms.
//   M0 depth   : 0 relief canyon + golden cracks, 1 contour slices, 2 Droste recursion, 3 tunnel
//   M1 kaleido : 0 polar kaleidoscope, 1 pixel sort, 2 recursive triangle cuts, 3 mirrored spine
//   M2 fluid   : 0 lava domain warp, 1 mercury ripples, 2 water mirror, 3 vortex storm, 4 RGB tear, 5 melt
//   M3 bio     : 0 ink bloom, 1 ferrofluid spikes, 2 boiling cells, 3 circuit traces, 4 neon specimen
//   M4 swarm   : 0 shatter dots, 1 galaxy swirl, 2 pointillist lift, 3 sand drift, 4 montage eye, 5 bokeh dust
// uReveal opens the painting onto uInput (a math scene chained before this layer) or deep space:
//   style 0 cracks/falling shards, 1 depth peel (far first), 2 iris from focus, 3 canvas tear, 4 peel near first
// Every pulse (~1 s, uStep) shifts light, symmetry, flow or burst: scaled by uMicro.
uniform sampler2D uInput, uSpace, uAtlas;
uniform vec4 uView;          // painting uv centre, uv per screen unit, painting aspect
uniform vec2 uFocusS;        // focus point, screen uv
uniform float uPMode, uPVar, uMicro, uRelief, uFx, uPaintGain;
uniform float uReveal, uRevealStyle, uHasInput, uSpaceMix, uAtlasN;

vec2 mir(vec2 uv) { return 1.0 - abs(1.0 - mod(uv, 2.0)); }
vec2 toUV(vec2 p) { return uView.xy + vec2(p.x / uView.w, p.y) * uView.z; }
vec4 Praw(vec2 uv) { return texture(uPaint, mir(uv)); }
vec3 P(vec2 p) { return pow(Praw(toUV(p)).rgb, vec3(2.2)) * uPaintGain; }
float D(vec2 p) { return Praw(toUV(p)).a; }
float lum(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
float sH(float k) { return hash11(floor(uStep) * 1.37 + k); }                                    // per pulse
float sS(float k) { return mix(hash11(floor(uStep) * 1.37 + k), hash11((floor(uStep) + 1.0) * 1.37 + k), fract(uStep)); }
vec3 space(vec2 p) {
    vec2 uv = 0.5 + p * 0.55 * rot(uTime * 0.01) + vec2(uTime * 0.004, 0.0);
    return pow(texture(uSpace, mir(uv)).rgb, vec3(2.2)) * 1.4;
}

// ---------------------------------------------------------------- M0 depth
vec3 m0(vec2 p, vec2 fp) {
    float m = uMicro;
    if (uPVar == 1.0) {                                          // contour slices, bass shakes layers
        const int N = 36;
        for (int i = 0; i < N; i++) {
            float l = 1.0 - float(i) / float(N);
            vec2 off = vec2(0.0, sin(l * 13.0 + uTime * 2.0) * 0.012 * uFx * (1.0 + 2.0 * uBass) + (sS(l * 7.0) - 0.5) * 0.04 * m * uFx);
            vec2 q = p - off;
            float d = D(q);
            if (d >= l - 1.0 / float(N)) {
                vec3 c = P(q) * (0.35 + 0.65 * l);
                float edge = smoothstep(0.75, 1.0, fract(d * float(N)));
                return c + pal(l) * edge * 0.6 * uFx;
            }
        }
        return vec3(0.0);
    }
    if (uPVar == 2.0) {                                          // Droste: the focus contains the painting again
        vec2 d = p - fp;
        float r = length(d), a = atan(d.y, d.x);
        float S = 0.24, L = -log(S);
        float lr = log(max(r, 1e-5)) - uLocal * 0.35 * uFx - floor(uStep) * 0.15 * m;
        float rr = exp(mod(lr, L) - L) * 0.95;
        a += lr * 0.18 * uFx;
        return P(fp + vec2(cos(a), sin(a)) * rr);
    }
    if (uPVar == 3.0) {                                          // painting rolled into an infinite tunnel
        vec2 d = p - fp * 0.3;
        float r = length(d), a = atan(d.y, d.x) + uStep * 0.5236 * m;
        float z = 0.25 / max(r, 1e-3) + uTravel * 0.15;
        vec2 tuv = vec2(abs(mod(a, TAU) - PI) / PI, z * 0.8);                   // |a|/π: no seam
        float lod = log2(max(fwidth(z * 0.8) * float(textureSize(uPaint, 0).y), 1.0));     // no mip jump at the fold
        vec3 c = pow(textureLod(uPaint, mir(tuv), lod).rgb, vec3(2.2)) * uPaintGain;
        return c * smoothstep(0.0, 0.35, r) * (0.6 + 0.4 * uFx);
    }
    // relief canyon: parallax-occlusion through the depth map, light jumps every pulse
    float la = 0.8 + TAU * sS(3.0) * m;
    vec2 tilt = vec2(cos(la), sin(la)) * 0.3 * m + (p - fp) * 0.25;
    vec2 dir = tilt * uRelief * 0.08;
    vec2 q = p;
    float h = 1.0, d = D(q);
    for (int i = 0; i < 40; i++) {
        if (d >= h) break;
        h -= 1.0 / 40.0;
        q -= dir / 40.0;
        d = D(q);
    }
    vec3 c = P(q);
    vec2 e = vec2(0.003, 0.0);
    vec2 g = vec2(D(q + e.xy) - D(q - e.xy), D(q + e.yx) - D(q - e.yx)) / 0.006;
    vec3 n = normalize(vec3(-g * uRelief * 0.06, 1.0));
    vec3 Ld = normalize(vec3(cos(la), sin(la), 0.9));
    float sh = 0.45 + 0.75 * max(dot(n, Ld), 0.0);
    float k = clamp(uRelief, 0.0, 1.0);
    c *= mix(1.0, sh, k) * mix(1.0, 0.2 + 0.8 * d, clamp(uRelief * 0.6, 0.0, 1.0));
    // golden fractal lightning from the focus + gold in the deepest creases
    float crease = smoothstep(0.5, 2.5, length(g)) * uFx;
    float rr = length(p - fp);
    float bolt = exp(-abs(fbm((p - fp) * rot(sH(9.0) * TAU) * 5.0 + uLocal * 0.7) - 0.5) * 70.0) *
                 smoothstep(0.1 + 0.35 * uFx, 0.0, rr) * uFx;
    c += vec3(1.0, 0.7, 0.25) * (crease * 0.08 * lum(c) + bolt * (0.8 + 2.0 * uHit));
    return c;
}

// ---------------------------------------------------------------- M1 kaleido / sort
vec2 kfold(vec2 d, float n, float spin) {
    float r = length(d), a = atan(d.y, d.x) + spin;
    float seg = TAU / n;
    a = abs(mod(a, seg) - seg * 0.5);
    return vec2(cos(a), sin(a)) * r;
}
vec3 m1(vec2 p, vec2 fp) {
    float m = uMicro;
    if (uPVar == 1.0) {                                          // pixel sort: bright pixels drip along the beat
        vec2 dir = sH(4.0) > 0.5 ? vec2(1.0, 0.0) : vec2(0.0, -1.0);
        float len = (0.04 + 0.3 * uFx) * (1.0 + 1.5 * uHit);
        float th = 0.55 - 0.25 * uFx;
        vec3 base = P(p), best = base;
        float bl = lum(base);
        for (int i = 1; i < 28; i++) {
            vec3 s = P(p - dir * len * float(i) / 28.0);
            float l = lum(s);
            if (l > th && l > bl) { best = s; bl = l; }
        }
        return mix(base, best, smoothstep(0.0, 0.2, uFx));
    }
    float n = uPVar == 2.0 ? 3.0 : (m > 0.0 ? vec4(6.0, 8.0, 12.0, 16.0)[int(sH(1.0) * 3.99)] : 8.0);
    float spin = uStep * 0.5236 * m + uLocal * 0.1;
    vec2 d = (p - fp) * (1.0 + 0.3 * uFx);
    if (uPVar == 3.0) {                                          // mirrored spine, endlessly repeated
        d.x = abs(d.x);
        d.y = abs(mod(d.y + uTravel * 0.1, 0.5) - 0.25) * 2.0 - 0.1;
        return mix(P(p), P(fp + d), uFx);
    }
    vec2 k = kfold(d, n, spin);
    if (uPVar == 2.0) {                                          // recursive triangle cuts, one level per pulse
        int lv = 1 + int(mod(floor(uStep), 4.0) * m);
        for (int i = 0; i < 4; i++) {
            if (i >= lv) break;
            k = kfold(k * 1.9 - vec2(0.18, 0.0), 3.0, 0.3 * float(i));
        }
    }
    return mix(P(p), P(fp + k), smoothstep(0.0, 1.0, uFx));
}

// ---------------------------------------------------------------- M2 fluid
vec3 m2(vec2 p, vec2 fp) {
    float m = uMicro, t = uTime * 0.25;
    if (uPVar == 1.0) {                                          // mercury: every note rings the surface
        vec2 nc = fp + (vec2(hash11(uNoteCount), hash11(uNoteCount + 5.0)) - 0.5) * 0.5;
        float r = length(p - nc);
        float ring = sin(r * 70.0 - uNoteAge * 22.0) * exp(-uNoteAge * 1.6) * exp(-abs(r - uNoteAge * 0.5) * 5.0);
        float base = sin(length(p - fp) * 30.0 - uTime * 2.0) * 0.15;
        float hgt = (ring + base) * uFx;
        vec2 g = vec2(dFdx(hgt), dFdy(hgt)) * uRes.y;
        vec2 q = p + g * 0.0005;
        vec3 c = P(q);
        vec3 n = normalize(vec3(-g * 0.015, 1.0));
        vec3 chrome = pal(0.5 + n.x * 0.3 + n.y * 0.2) * (0.4 + 0.8 * pow(max(n.z, 0.0), 6.0));
        float spec = pow(max(dot(n, normalize(vec3(0.4, 0.6, 1.0))), 0.0), 60.0);
        return mix(c, chrome * lum(c) * 1.3 + c * 0.6, 0.3 * uFx) + spec * 0.8 * uFx;
    }
    if (uPVar == 2.0) {                                          // water mirror: gravity flips on the pulse
        float flip = mix(mod(floor(uStep), 2.0), mod(floor(uStep) + 1.0, 2.0), fract(uStep)) * m;
        vec2 q = p;
        float hz = fp.y - 0.05;
        if (q.y < hz) q.y = 2.0 * hz - q.y + sin(q.x * 40.0 + uTime * 3.0) * 0.004 * (hz - p.y) * 10.0;
        q.y = mix(q.y, -q.y + 2.0 * fp.y, flip);
        vec3 c = P(q) * (p.y < hz ? 0.7 : 1.0);
        float ghost = smoothstep(0.6, 0.9, fbm(p * 3.0 + t)) * (1.0 - smoothstep(0.0, 0.25, lum(c)));
        return c + pal(0.55) * ghost * 0.6 * uFx;
    }
    if (uPVar == 3.0) {                                          // vortex storm round the focus
        vec2 d = p - fp;
        float r = length(d);
        float sw = uFx * (0.9 / (r + 0.12)) * (0.6 + uLocal * 0.25) + uStep * 0.3 * m;
        d = rot(sw) * d * (1.0 + 0.2 * uFx);
        vec2 w = vec2(fbm(d * 3.0 + t), fbm(d * 3.0 - t + 4.0)) - 0.5;
        return P(fp + d + w * 0.08 * uFx);
    }
    if (uPVar == 4.0) {                                          // RGB channel tear on every hit
        float band = floor(p.y * mix(8.0, 40.0, sH(2.0)));
        float o = (hash11(band + floor(uTime * 10.0)) - 0.5) * 0.06 * (uFx * 0.4 + uHit) ;
        vec2 w = (vec2(fbm(p * 2.0 + t), fbm(p * 2.0 + 3.0 - t)) - 0.5) * 0.1 * uFx;
        return vec3(P(p + w + vec2(o, 0.0)).r, P(p + w).g, P(p + w - vec2(o * 1.6, 0.0)).b);
    }
    if (uPVar == 5.0) {                                          // melt / pour downwards
        float drip = fbm(vec2(p.x * 7.0, 1.3)) * 0.8 + 0.2;
        vec2 q = p + vec2(0.0, uFx * 0.35 * drip * (0.3 + uProgress));
        vec3 c = P(q);
        for (int i = 1; i < 6; i++) c = max(c, P(q + vec2(0.0, 0.015 * float(i) * uFx)) * (1.0 - 0.15 * float(i)));
        return c;
    }
    // lava domain warp (IQ): oil paint starts to boil
    vec2 q = p * 1.6;
    vec2 w1 = vec2(fbm(q + t), fbm(q + 5.2 - t));
    vec2 w2 = vec2(fbm(q + 4.0 * w1 + 1.7 + 0.5 * t), fbm(q + 4.0 * w1 + 9.2));
    vec2 off = (w2 - 0.5) * 0.35 * uFx * (1.0 + 0.6 * uHit) + (vec2(sS(5.0), sS(6.0)) - 0.5) * 0.08 * m * uFx;
    vec3 c = P(p + off);
    return c + pal(w2.x + 0.2) * pow(length(w1 - 0.5), 2.0) * 0.6 * uFx;
}

// ---------------------------------------------------------------- M3 bio
float spikeH(vec2 p, float dark) {
    vec2 g = p * 26.0;
    vec2 f = fract(g + vec2(0.5 * mod(floor(g.y), 2.0), 0.0)) - 0.5;
    float cone = max(0.0, 1.0 - length(f) * 2.3);
    return pow(cone, 1.4) * dark * (0.3 + 1.4 * uBass);
}
vec3 m3(vec2 p, vec2 fp) {
    float m = uMicro;
    vec3 c = P(p);
    if (uPVar == 1.0) {                                          // ferrofluid: the darkness grows spikes on the bass
        float dark = smoothstep(0.25, 0.02, lum(c)) * uFx;
        float h = spikeH(p, dark);
        vec2 e = vec2(1.5 / uRes.y, 0.0);
        vec2 g = vec2(spikeH(p + e.xy, dark) - spikeH(p - e.xy, dark), spikeH(p + e.yx, dark) - spikeH(p - e.yx, dark)) / (2.0 * e.x);
        vec3 n = normalize(vec3(-g * 0.02, 1.0));
        vec3 L = normalize(vec3(cos(uStep), sin(uStep), 0.8));
        float spec = pow(max(dot(reflect(-L, n), vec3(0, 0, 1)), 0.0), 40.0);
        return mix(c, vec3(0.005), dark) + (pal(0.1 + n.x * 0.4) * spec * 2.0 + pal(0.6) * 0.15 * h) * dark;
    }
    if (uPVar == 2.0) {                                          // boiling cells: each cell eats its neighbourhood
        vec2 g = p * 7.0;
        vec2 id = floor(g), best = vec2(0), cell = vec2(0);
        float d1 = 9.0, d2 = 9.0;
        for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
            vec2 o = vec2(x, y), h = hash22(id + o);
            vec2 pt = o + 0.5 + 0.4 * sin(uTime * 0.8 + h * TAU + uStep * m);
            float d = length(id + pt - g);
            if (d < d1) { d2 = d1; d1 = d; best = id + pt; cell = id + o; } else if (d < d2) d2 = d;
        }
        vec3 cc = P(best / 7.0);
        float edge = smoothstep(0.08, 0.0, d2 - d1);
        return mix(c, cc * (0.8 + 0.4 * (1.0 - d1)), uFx * 0.85) + pal(0.3 + hash12(cell)) * edge * (0.4 + uHit) * uFx;
    }
    if (uPVar == 3.0) {                                          // anatomy → logic gates: edges snap to circuit traces
        float G = 90.0;
        vec2 cellp = (floor(p * G) + 0.5) / G;
        float e = length(vec2(lum(P(cellp + vec2(1.0 / G, 0))) - lum(P(cellp - vec2(1.0 / G, 0))),
                              lum(P(cellp + vec2(0, 1.0 / G))) - lum(P(cellp - vec2(0, 1.0 / G)))));
        vec2 f = abs(fract(p * G) - 0.5);
        float trace = smoothstep(0.06, 0.15, e) * (1.0 - smoothstep(0.08, 0.14, min(f.x, f.y)));
        float blink = step(0.4, hash12(floor(p * G) + floor(uTime * 8.0)));
        return mix(c * (1.0 - 0.7 * uFx), c * 0.2, 0.0) + pal(0.55 + 0.2 * hash12(floor(p * G))) * trace * blink * 2.0 * uFx;
    }
    if (uPVar == 4.0) {                                          // 19th-century specimen glows like a deep-sea creature
        float ink = 1.0 - lum(pow(c / max(uPaintGain, 1e-3), vec3(1.0 / 2.2)));
        float breathe = 1.0 + 0.04 * uSpring;
        vec3 neon = pal(ink * 0.8 + p.y * 0.3 + uTime * 0.05 + uStep * 0.1 * m) * pow(ink, 2.0) * 2.5;
        return mix(c, neon * breathe, uFx);
    }
    // ink bloom: dark strokes spread and glow like living ink
    float rad = (0.002 + 0.012 * uFx) * (1.0 + uHit);
    float mn = lum(c);
    for (int i = 0; i < 12; i++) {
        float a = float(i) * TAU / 12.0 + uTime;
        mn = min(mn, lum(P(p + vec2(cos(a), sin(a)) * rad)));
    }
    float grow = clamp((lum(c) - mn) * 4.0, 0.0, 1.0) * uFx;
    return mix(c, c * 0.15, grow) + pal(0.35 + mn) * grow * (0.6 + 0.6 * uHit);
}

// ---------------------------------------------------------------- M4 swarm
vec3 dots(vec2 s, float cs, float rad, float soft) {
    vec2 id = floor(s / cs);
    vec3 acc = vec3(0.0);
    for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
        vec2 c = id + vec2(x, y);
        vec2 h = hash22(c);
        vec2 ctr = (c + 0.5 + (h - 0.5) * 0.6) * cs;
        float d = length(s - ctr) / cs;
        float k = 1.0 - smoothstep(rad - soft, rad + soft, d);
        acc += P(ctr) * k * (1.0 + 0.6 * h.x);
    }
    return acc;
}
vec3 m4(vec2 p, vec2 fp) {
    float m = uMicro;
    vec2 d = p - fp;
    float r = length(d), a = atan(d.y, d.x);
    float burst = uFx * (1.0 + 0.4 * exp(-uPulseAge * 3.0) * m);
    if (uPVar == 4.0) {                                          // montage eye: every painting a tile of one iris
        float asp = uRes.x / uRes.y;
        vec2 q = p * (1.0 - 0.25 * uFx);
        float rr = length(q), aa = atan(q.y, q.x);
        float pupil = mix(0.16, 0.035, uFx) * (1.0 + 0.1 * uBass * uMicro);   // micro 0 = still (loop frames)
        float ring = floor((rr - pupil) / 0.045), sect = floor((aa + PI) / TAU * (12.0 + ring * 6.0));
        float n = max(uAtlasN, 1.0);
        // each tile shuffles a whole number of times n*k per 300 s loop, so the eye at the end is the eye at frame 0
        float laps = n * max(1.0, floor(1500.0 * (0.3 + hash12(vec2(sect, ring))) / n + 0.5));
        float cnt = floor(mod(uTime, 300.0) / 300.0 * laps + hash12(vec2(ring, sect) + 4.2));
        float idx = floor(mod(hash12(vec2(ring, sect)) * n + cnt, n));
        vec2 tl = fract(vec2((aa + PI) / TAU * (12.0 + ring * 6.0), (rr - pupil) / 0.045));
        vec2 auv = (vec2(mod(idx, 8.0), 7.0 - floor(idx / 8.0)) + 0.08 + tl * 0.84) / 8.0;
        vec3 c = pow(texture(uAtlas, auv).rgb, vec3(2.2)) * 1.3;
        float iris = smoothstep(0.48, 0.44, rr) * step(pupil, rr);
        float grout = smoothstep(0.0, 0.06, min(min(tl.x, 1.0 - tl.x), min(tl.y, 1.0 - tl.y)));
        c *= iris * grout * (0.5 + 0.5 * smoothstep(pupil, pupil + 0.2, rr));
        c += pal(0.1) * exp(-abs(rr - 0.47) * 60.0) * 1.5;
        return c + vec3(1.0, 0.95, 0.9) * smoothstep(0.85, 1.0, uFx) * 6.0 * exp(-rr * 3.0);
    }
    vec2 s;
    float cs = 1.0 / 100.0, rad = 0.5, soft = 0.12;
    if (uPVar == 1.0) {                                          // galaxy: spiral arms round the focus
        float sw = burst * 1.4 / (r + 0.08) + uLocal * 0.3 * uFx;
        s = fp + vec2(cos(a - sw), sin(a - sw)) * r / (1.0 + burst * 0.8);
    } else if (uPVar == 2.0) {                                   // pointillism: dots lift off in depth, by pitch
        cs = 1.0 / 95.0;
        rad = 0.38;
        float lift = burst * (0.5 + spec(clamp(0.5 + d.x, 0.0, 1.0)));
        s = fp + d / (1.0 + lift * 0.3);
    } else if (uPVar == 3.0) {                                   // sand drift: grains blow away sideways
        cs = 1.0 / 70.0;
        rad = 0.45;
        float gust = vnoise(vec2(p.y * 9.0, uTime * 0.3)) * vnoise(vec2(p.y * 31.0, 2.0));
        s = p - vec2(burst * 0.5 * gust * gust * (0.6 + p.y + 0.5), burst * 0.04 * (vnoise(p * 7.0) - 0.5));
    } else if (uPVar == 5.0) {                                   // bokeh dust: huge soft, slow, quiet
        cs = 1.0 / 26.0;
        rad = 0.35;
        soft = 0.3;
        s = p + vec2(sin(uTime * 0.2 + p.y * 3.0), cos(uTime * 0.17 + p.x * 2.0)) * 0.03;
        return mix(P(p) * 0.3, dots(s, cs, rad, soft) * 0.6, smoothstep(0.0, 0.3, uFx));
    } else {                                                     // shatter: explode from the focus
        s = fp + d / (1.0 + burst * 1.5) * rot(burst * 0.2);
    }
    vec3 c = dots(s, cs, rad, soft);
    return mix(P(p), c * 1.3, smoothstep(0.0, 0.15, uFx));
}

// ---------------------------------------------------------------- reveal
float revealMask(vec2 p, vec2 fp, out vec2 shift, out float glow) {
    shift = vec2(0.0);
    glow = 0.0;
    if (uReveal <= 0.0) return 0.0;
    if (uRevealStyle == 1.0 || uRevealStyle == 4.0) {            // peel far-first (1) or near/bright-first (4)
        float far = (uRevealStyle == 4.0 ? D(p) : 1.0 - D(p)) + 0.05 * fbm(p * 8.0);
        float th = 1.05 - uReveal * 1.1;
        glow = exp(-abs(far - th) * 40.0) * (1.0 - uReveal);
        return smoothstep(th, th + 0.06, far);
    }
    if (uRevealStyle == 2.0) {                                   // iris from the focus
        float R = uReveal * 1.4, r = length(p - fp) + 0.03 * fbm(p * 6.0 + uTime);
        glow = exp(-abs(r - R) * 50.0) * (1.0 - uReveal);
        return smoothstep(R, R - 0.03, r);
    }
    if (uRevealStyle == 3.0) {                                   // canvas tears open diagonally
        float x = dot(p, normalize(vec2(1.0, 0.7))) + 0.12 * fbm(p * 5.0) + 1.0;
        float th = uReveal * 2.4;
        glow = exp(-abs(x - th) * 40.0) * (1.0 - uReveal);
        return smoothstep(th, th - 0.02, x);
    }
    // cracks: Voronoi shards break away from the focus outwards and fall
    vec2 g = p * 5.0;
    vec2 id = floor(g), cell = vec2(0), ctr = vec2(0);
    float d1 = 9.0, d2 = 9.0;
    for (int y = -1; y <= 1; y++) for (int x = -1; x <= 1; x++) {
        vec2 o = vec2(x, y), pt = o + hash22(id + o);
        float d = length(id + pt - g);
        if (d < d1) { d2 = d1; d1 = d; cell = id + o; ctr = (id + pt) / 5.0; } else if (d < d2) d2 = d;
    }
    float order = 0.6 * length(ctr - fp) / 1.1 + 0.4 * hash12(cell);
    float x = uReveal * 1.35 - order;                            // > 0: this shard has broken off
    float fall = clamp(x / 0.25, 0.0, 1.0);
    shift = vec2(0.0, fall * fall * 0.25) + (hash22(cell) - 0.5) * fall * 0.05;
    glow = smoothstep(0.035, 0.0, d2 - d1) * smoothstep(-0.25, 0.0, x) * (1.0 - fall);
    return smoothstep(0.85, 1.0, fall);
}

vec3 render(vec2 fc) {
    vec2 asp = vec2(uRes.x / uRes.y, 1.0);
    vec2 uv = fc / uRes;
    vec2 p = (uv - 0.5) * asp;
    vec2 fp = (uFocusS - 0.5) * asp;
    vec2 shift;
    float glow;
    float mask = revealMask(p, fp, shift, glow);
    vec2 q = p + shift;
    vec3 c;
    if (uPMode < 0.5) c = m0(q, fp);
    else if (uPMode < 1.5) c = m1(q, fp);
    else if (uPMode < 2.5) c = m2(q, fp);
    else if (uPMode < 3.5) c = m3(q, fp);
    else c = m4(q, fp);
    if (uRevealStyle == 0.0 && uReveal > 0.0)                     // falling shards darken as they drop away
        c *= 1.0 - 0.6 * smoothstep(0.0, 0.2, length(shift));
    c += space(p) * uSpaceMix * pow(1.0 - clamp(lum(c), 0.0, 1.0), 2.0);
    vec3 world = uHasInput > 0.5 ? texture(uInput, uv).rgb : space(p);
    c = mix(c, world, mask);
    c += vec3(1.0, 0.72, 0.3) * glow * (1.5 + 2.0 * uHit);
    return c;
}
