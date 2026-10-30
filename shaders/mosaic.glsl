// Machine vision: the finished frame re-sampled into cells, as the AI "sees" it. Drawn after the composite and
// before bloom / grade / titles, so captions stay sharp. Cell size and form come from the timeline per act and
// pulse on the beat; the subject (focus point) is seen in finer cells than the periphery (attention).
uniform sampler2D uA;
uniform float uAmt;         // 0 = clear image .. 1 = full mosaic
uniform float uCell;        // cell size, fraction of screen height
uniform float uShape;       // 0 square pixels, 1 hex, 2 triangles, 3 voronoi shards, 4 quadtree (detail-adaptive), 5 LED dots,
                            // 6 soft light dots (it first feels light), 7 organic flowing grid (crystallises with uCrystal)
uniform float uGap;         // dark grout between cells 0..1
uniform float uQuant;       // colour levels per channel (0 = off)
uniform float uFovea;       // 0..1: how much finer the cells get around the focus
uniform vec2 uFocus;        // focus, screen uv (bottom-up)
uniform float uFlowL;       // light flowing across the cells: travelling bands + noise + a ring from the focus on the beat
uniform float uFlowC;       // colour flowing across the cells: hue rotation at constant luma, so the picture stays legible
uniform float uFlowS;       // flow speed
uniform float uFlowK;       // flow scale (waves per screen height)
uniform vec4 uMask;         // rect (bottom-up x0, y0, x1, y1) the mosaic is confined to: human view | machine view
uniform float uOutside;     // mosaic amount outside the rect (1 = everywhere)
uniform float uCrystal;     // shape 7: 0 = soft, interpolated cells (organic) .. 1 = hard square pixels
uniform float uMaskCrystal; // inside the mask rect: force crystal 1 and coarser cells (the machine's own hand)
float CRYSTAL = 0.0;

vec3 tap(vec2 px) { return texture(uA, clamp(px / uRes, 0.0, 1.0)).rgb; }

vec3 cellColor(vec2 c, float s) {   // box-ish average over the cell so big cells don't shimmer
    float o = s * 0.25;
    return (tap(c) * 2.0 + tap(c + vec2(o, o)) + tap(c + vec2(-o, o)) + tap(c + vec2(o, -o)) + tap(c + vec2(-o, -o))) / 6.0;
}

float luma(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }

vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return fract(sin(p) * 43758.5453);
}

// returns cell colour (rgb) and edge distance in cell units (a): 0 at the border, ~0.5 at the centre
vec2 CEN;                   // centre (px) of the cell the last mosaic() call landed in

vec4 mosaic(vec2 fc, float s, int shape) {
    if (shape == 1) {                                   // hexagons (pointy-top)
        vec2 r = vec2(1.0, 1.7320508);
        vec2 h = r * 0.5;
        vec2 p = fc / s;
        vec2 a = mod(p, r) - h, b = mod(p - h, r) - h;
        vec2 g = dot(a, a) < dot(b, b) ? a : b;
        vec2 c = (p - g) * s;
        CEN = c;
        vec2 q = abs(g);
        float e = 0.5 - max(dot(q, normalize(vec2(1.0, 1.7320508))), q.x);
        return vec4(cellColor(c, s), e);
    }
    if (shape == 2) {                                   // triangles: each square split along a diagonal
        vec2 p = fc / s, i = floor(p), f = fract(p);
        bool up = f.x + f.y < 1.0;
        vec2 c = (i + (up ? vec2(0.333) : vec2(0.667))) * s;
        CEN = c;
        float e = up ? min(min(f.x, f.y), (1.0 - f.x - f.y) * 0.707) : min(min(1.0 - f.x, 1.0 - f.y), (f.x + f.y - 1.0) * 0.707);
        return vec4(cellColor(c, s * 0.7), e);
    }
    if (shape == 3) {                                   // voronoi shards, the seeds drifting slowly
        vec2 p = fc / s, i = floor(p), f = fract(p);
        float d1 = 8.0, d2 = 8.0;
        vec2 best = vec2(0.0);
        for (int y = -1; y <= 1; y++)
            for (int x = -1; x <= 1; x++) {
                vec2 g = vec2(x, y);
                vec2 o = hash2(i + g);
                o = 0.5 + 0.42 * sin(uTime * 0.6 + TAU * o);
                float d = length(g + o - f);
                if (d < d1) { d2 = d1; d1 = d; best = i + g + o; }
                else if (d < d2) d2 = d;
            }
        CEN = best * s;
        return vec4(cellColor(best * s, s), (d2 - d1) * 0.5);
    }
    if (shape == 4) {                                   // quadtree: split where the picture has detail
        float S = s * 4.0;
        vec2 c = (floor(fc / S) + 0.5) * S;
        for (int k = 0; k < 3; k++) {
            float o = S * 0.3;
            float l0 = luma(tap(c + vec2(o, o))), l1 = luma(tap(c + vec2(-o, o)));
            float l2 = luma(tap(c + vec2(o, -o))), l3 = luma(tap(c + vec2(-o, -o)));
            float m = 0.25 * (l0 + l1 + l2 + l3);
            float v = abs(l0 - m) + abs(l1 - m) + abs(l2 - m) + abs(l3 - m);
            if (v < 0.12 * (m + 0.05)) break;
            S *= 0.5;
            c = (floor(fc / S) + 0.5) * S;
        }
        vec2 f = abs(fc - c) / S;
        CEN = c;
        return vec4(cellColor(c, S), 0.5 - max(f.x, f.y));
    }
    if (shape == 6) {                                   // soft light dots over a dim, soft image; edges breathe with noise
        vec2 c6 = (floor(fc / s) + 0.5) * s;
        CEN = c6;
        vec3 col = cellColor(c6, s);
        vec3 under = cellColor((floor(fc / (s * 3.0)) + 0.5) * s * 3.0, s * 3.0) * 0.55;
        float wob = fbm(c6 / uRes.y * 6.0 + uTime * 0.25) - 0.5;
        float rad = 0.34 + 0.18 * wob + 0.12 * sqrt(clamp(luma(col), 0.0, 1.5) / 1.5);
        float dotA = exp(-pow(length(fc - c6) / s / rad, 2.0) * 1.6);
        return vec4(mix(under, col * 1.12, dotA), 1.0);
    }
    if (shape == 7) {                                   // organic: colours interpolated between cell centres, flowing
        vec2 g = fc / s - 0.5, i = floor(g), f = fract(g);
        vec2 warp = (vec2(fbm(i * 0.21 + uTime * 0.12), fbm(i * 0.21 + 3.7 - uTime * 0.12)) - 0.5) * 0.6 * (1.0 - CRYSTAL);
        vec3 c00 = cellColor((i + 0.5 + warp) * s, s), c10 = cellColor((i + vec2(1.5, 0.5) + warp) * s, s);
        vec3 c01 = cellColor((i + vec2(0.5, 1.5) + warp) * s, s), c11 = cellColor((i + 1.5 + warp) * s, s);
        vec2 u = f * f * (3.0 - 2.0 * f);
        vec3 soft = mix(mix(c00, c10, u.x), mix(c01, c11, u.x), u.y);
        vec2 cq = (floor(fc / s) + 0.5) * s;
        CEN = cq;
        vec3 hard = cellColor(cq, s);
        vec2 fq = abs(fc - cq) / s;
        return vec4(mix(soft, hard, CRYSTAL), mix(1.0, 0.5 - max(fq.x, fq.y), CRYSTAL));
    }
    vec2 c = (floor(fc / s) + 0.5) * s;                 // square pixels (0) / LED dots (5)
    CEN = c;
    vec2 f = abs(fc - c) / s;
    if (shape == 5) {
        vec3 col = cellColor(c, s);
        float rad = 0.22 + 0.3 * sqrt(clamp(luma(col), 0.0, 1.5) / 1.5);
        return vec4(col, rad - length(fc - c) / s);
    }
    return vec4(cellColor(c, s), 0.5 - max(f.x, f.y));
}

vec3 hueRotate(vec3 c, float a) {                       // YIQ rotation: hue turns, luma stays
    float y = dot(c, vec3(0.299, 0.587, 0.114));
    float i = dot(c, vec3(0.596, -0.274, -0.322)), q = dot(c, vec3(0.211, -0.523, 0.312));
    float ca = cos(a), sa = sin(a);
    vec2 iq = vec2(i * ca - q * sa, i * sa + q * ca);
    return max(vec3(y + 0.956 * iq.x + 0.621 * iq.y, y - 0.272 * iq.x - 0.647 * iq.y, y - 1.106 * iq.x + 1.703 * iq.y), 0.0);
}

vec3 flow(vec3 col, vec2 cen) {                         // one value per cell, so the flow itself is a mosaic
    vec2 c = (cen - 0.5 * uRes) / uRes.y;
    vec2 q = c * uFlowK;
    float T = uTime * uFlowS;
    float n = fbm(q + vec2(0.31 * T, -0.23 * T));
    float band = sin(dot(q, vec2(0.8, 0.6)) * 2.2 - 1.7 * T + 4.0 * n);
    vec2 f = (uFocus - 0.5) * vec2(uRes.x / uRes.y, 1.0);
    float ring = exp(-abs(length(c - f) - uPulseAge * 0.9) * 9.0) * exp(-uPulseAge * 1.6);
    float L = 1.0 + uFlowL * (0.55 * band + 0.9 * (n - 0.5) + 0.7 * ring);
    float n2 = fbm(q * 2.3 + vec2(-0.4 * T, 0.27 * T) + 7.1);                    // finer second layer, zero-mean hue
    float h = uFlowC * TAU * (1.2 * (n2 - 0.5) + 0.35 * band);
    return hueRotate(col, h) * max(L, 0.2);
}

vec3 render(vec2 fc) {
    vec3 src = texture(uA, fc / uRes).rgb;
    vec2 u = fc / uRes;
    float px = 1.5 / uRes.y;
    float inR = smoothstep(uMask.x - px, uMask.x + px, u.x) * smoothstep(uMask.z + px, uMask.z - px, u.x)
              * smoothstep(uMask.y - px, uMask.y + px, u.y) * smoothstep(uMask.w + px, uMask.w - px, u.y);
    float amt = uAmt * mix(uOutside, 1.0, inR);
    // the seam between the two ways of seeing: a thin cool line on the rect's inner edges
    float seam = 0.0;
    if (uOutside < 0.999 && uAmt > 0.001) {
        float asp = uRes.x / uRes.y;
        if (uMask.x > 0.002) seam = max(seam, exp(-abs(u.x - uMask.x) * asp * uRes.y * 0.5));
        if (uMask.z < 0.998) seam = max(seam, exp(-abs(u.x - uMask.z) * asp * uRes.y * 0.5));
        if (uMask.y > 0.002) seam = max(seam, exp(-abs(u.y - uMask.y) * uRes.y * 0.5));
        if (uMask.w < 0.998) seam = max(seam, exp(-abs(u.y - uMask.w) * uRes.y * 0.5));
        seam *= uAmt * (1.0 - uOutside);
    }
    if (amt <= 0.001) return src + vec3(0.55, 0.85, 1.0) * seam * 0.6;
    int shape = int(floor(uShape + 0.5));
    float s = max(uCell * uRes.y, 1.0);
    if (shape == 7) {
        CRYSTAL = clamp(mix(uCrystal, 1.0, inR * uMaskCrystal), 0.0, 1.0);
        s *= 1.0 + 0.25 * inR * uMaskCrystal;
    }
    vec4 m = mosaic(fc, s, shape);
    vec2 cen = CEN;
    if (uFovea > 0.001) {                                // attention: finer cells near what it is looking at
        vec2 d = (fc / uRes - uFocus) * vec2(uRes.x / uRes.y, 1.0);
        float w = uFovea * exp(-dot(d, d) / 0.045);
        if (w > 0.02) m = mix(m, mosaic(fc, max(s * 0.3, 1.0), shape), smoothstep(0.15, 0.6, w));
    }
    vec3 col = m.rgb;
    if (uFlowL + uFlowC > 0.001) col = flow(col, cen);
    if (uQuant > 1.5) col = floor(col * uQuant + 0.5) / uQuant;
    float edge = shape == 5 ? smoothstep(-0.03, 0.03, m.a) : smoothstep(0.0, 0.06, m.a);
    if (shape == 6) edge = 1.0;
    col *= mix(1.0, edge, uGap);
    return mix(src, col, amt) + vec3(0.55, 0.85, 1.0) * seam * 0.6;
}
