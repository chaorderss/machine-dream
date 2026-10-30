// HUD / occult line-art overlays, drawn after tonemapping so lines stay crisp and ungraded.
// Up to two element types per chapter (uHud0, uHud1); uHudFocus = the painting's focus on screen.
//  1 golden spiral + phi grid      2 wireframe scan          3 crosshair / tracking box
//  4 protractor ruler              5 vector-arrow field      6 spectrum waveform
//  7 Kepler nested solids          8 alchemical sun          9 flower of life
// 10 Chladni nodal lines          11 star-chart rings       12 EEG trace
// 13 code rain                    14 4x4 magic-square grid
uniform float uHud0, uHud1, uHudA;
uniform vec3 uHudCol;
uniform vec2 uHudFocus;

float hseg(vec2 p, vec2 a, vec2 b) {
    vec2 pa = p - a, ba = b - a;
    return length(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0));
}

float hudLines(float type, vec2 p, vec2 f, float px) {
    float w = 1.2 * px;
    float L = 0.0;
    vec2 q = p - f;
    float r = length(q), a = atan(q.y, q.x);
    float beat = exp(-uPulseAge * 4.0);
    if (type == 1.0) {                                  // golden spiral r = e^(b θ), b = ln φ / (π/2)
        float b = 0.30634;
        float th = a + uTime * 0.15;
        float k = floor((log(max(r, 1e-4) / 0.02) / b - th) / TAU + 0.5);
        float rk = 0.02 * exp(b * (th + TAU * k));        // nearest spiral arm at this angle
        L = max(L, lineAA(abs(r - rk) * 0.95, w) * step(r, 0.9));
        for (int i = 0; i < 4; i++) {
            float g = (i < 2 ? 0.382 : 0.618);
            vec2 asp = vec2(uRes.x / uRes.y, 1.0);
            float x = (g - 0.5) * asp.x, y = (g - 0.5);
            L = max(L, 0.45 * (i % 2 == 0 ? lineAA(abs(p.x - x), w) : lineAA(abs(p.y - y), w)));
        }
    } else if (type == 2.0) {                           // perspective wireframe floor + scanning bar
        float hz = -0.08;
        if (p.y < hz) {
            float z = 0.25 / (hz - p.y);
            vec2 g = vec2(p.x * z, z + uTime * 1.5);
            vec2 gf = abs(fract(g * 2.0) - 0.5) / (2.0 * fwidth(g * 2.0) + 1e-5);
            L = max(L, (1.0 - min(min(gf.x, gf.y), 1.0)) * smoothstep(0.0, 0.25, hz - p.y) * 0.6);
        }
        float sy = 0.5 - fract(uTime * 0.45) * 1.0;
        L = max(L, lineAA(abs(p.y - sy), w * 1.5) + 0.25 * smoothstep(0.08, 0.0, p.y - sy) * step(sy, p.y));
    } else if (type == 3.0) {                           // crosshair + corner tracking box at the focus
        float s = 0.11 * (1.0 + 0.15 * beat);
        vec2 aq = abs(q);
        float box = max(aq.x, aq.y);
        L = max(L, lineAA(abs(box - s), w) * step(s * 0.6, min(aq.x, aq.y)));   // four corner brackets
        L = max(L, lineAA(abs(r - s * 0.35), w));
        L = max(L, lineAA(aq.x, w) * step(s * 0.5, aq.y) * step(aq.y, s * 1.6));
        L = max(L, lineAA(aq.y, w) * step(s * 0.5, aq.x) * step(aq.x, s * 1.6));
    } else if (type == 4.0) {                           // protractor arcs with ticks, needle on the pulse
        float R = 0.36;
        float rot = uStep * 0.5236;
        float ang = mod(a - rot, TAU);
        float tick = abs(fract(ang / (TAU / 72.0) + 0.5) - 0.5) * (TAU / 72.0) * r;
        float big = abs(fract(ang / (TAU / 12.0) + 0.5) - 0.5) * (TAU / 12.0) * r;
        L = max(L, lineAA(abs(r - R), w));
        L = max(L, lineAA(tick, w) * step(R, r) * step(r, R + 0.015));
        L = max(L, lineAA(big, w) * step(R, r) * step(r, R + 0.04));
        vec2 nd = vec2(cos(rot), sin(rot));
        L = max(L, lineAA(hseg(q, vec2(0.0), nd * (R + 0.06)), w));
        L = max(L, 0.6 * lineAA(abs(r - R * 0.62), w));
    } else if (type == 5.0) {                           // vector arrows following a curl field
        vec2 cell = floor(p * 9.0), cp = (cell + 0.5) / 9.0;
        float n = fbm(cp * 2.0 + uTime * 0.1) * TAU * 2.0;
        vec2 dir = vec2(cos(n), sin(n)) * 0.035 * (0.5 + uRms);
        vec2 t0 = cp - dir, t1 = cp + dir;
        vec2 side = vec2(-dir.y, dir.x) * 0.4;
        L = max(L, lineAA(hseg(p, t0, t1), w));
        L = max(L, lineAA(min(hseg(p, t1, t1 - dir * 0.5 + side), hseg(p, t1, t1 - dir * 0.5 - side)), w));
    } else if (type == 6.0) {                           // live spectrum as a single waveform line
        float x = p.x / (uRes.x / uRes.y) + 0.5;
        float y0 = -0.36, amp = 0.12;
        float v = spec(x) * amp + y0;
        float dv = (spec(x + 0.004) - spec(x - 0.004)) * amp / (0.008 * uRes.x / uRes.y);
        L = max(L, lineAA(abs(p.y - v) / sqrt(1.0 + dv * dv), w));
        L = max(L, 0.3 * lineAA(abs(p.y - y0), w));
    } else if (type == 7.0) {                           // Kepler's Mysterium: cube in sphere, octahedron
        float t = uTime * 0.4 + uStep * 0.3;
        mat3 R3 = mat3(cos(t), 0, sin(t), 0, 1, 0, -sin(t), 0, cos(t));
        mat3 R4 = mat3(1, 0, 0, 0, cos(t * 0.7), -sin(t * 0.7), 0, sin(t * 0.7), cos(t * 0.7));
        float S = 0.17;
        float d = 1e9;
        for (int i = 0; i < 12; i++) {                  // cube edges
            int ax = i / 4, k = i % 4;
            vec3 o = vec3(-1.0);
            vec3 e = vec3(0.0);
            e[ax] = 2.0;
            int j = 0;
            for (int c = 0; c < 3; c++) if (c != ax) { o[c] = ((k >> j) & 1) == 1 ? 1.0 : -1.0; j++; }
            vec3 A3 = R4 * R3 * o * S, B3 = R4 * R3 * (o + e) * S;
            d = min(d, hseg(q, A3.xy / (1.0 + A3.z * 0.6), B3.xy / (1.0 + B3.z * 0.6)));
        }
        for (int i = 0; i < 12; i++) {                  // octahedron edges inside
            vec3 v[6] = vec3[6](vec3(1, 0, 0), vec3(-1, 0, 0), vec3(0, 1, 0), vec3(0, -1, 0), vec3(0, 0, 1), vec3(0, 0, -1));
            int pairs[24] = int[24](0, 2, 0, 3, 0, 4, 0, 5, 1, 2, 1, 3, 1, 4, 1, 5, 2, 4, 2, 5, 3, 4, 3, 5);
            vec3 A3 = R3 * R4 * v[pairs[2 * i]] * S, B3 = R3 * R4 * v[pairs[2 * i + 1]] * S;
            d = min(d, hseg(q, A3.xy / (1.0 + A3.z * 0.6), B3.xy / (1.0 + B3.z * 0.6)));
        }
        L = max(L, lineAA(d, w));
        L = max(L, 0.7 * lineAA(abs(r - S * 1.75), w));
        L = max(L, 0.5 * lineAA(abs(r - S * 2.6), w));
    } else if (type == 8.0) {                           // alchemical sun: circle, point, 12 rays, triangle
        float R = 0.16 * (1.0 + 0.08 * beat);
        L = max(L, lineAA(abs(r - R), w * 1.5));
        L = max(L, 1.0 - smoothstep(0.012, 0.016, r));
        float ra = abs(fract((a + uStep * 0.5236) / (TAU / 12.0) + 0.5) - 0.5) * (TAU / 12.0) * r;
        L = max(L, lineAA(ra, w) * step(R * 1.15, r) * step(r, R * (1.6 + 0.3 * beat)));
        float tri = 1e9;
        for (int i = 0; i < 3; i++) {
            float a0 = uTime * 0.1 + float(i) * TAU / 3.0 + PI / 2.0, a1 = a0 + TAU / 3.0;
            tri = min(tri, hseg(q, vec2(cos(a0), sin(a0)) * R * 2.2, vec2(cos(a1), sin(a1)) * R * 2.2));
        }
        L = max(L, 0.7 * lineAA(tri, w));
    } else if (type == 9.0) {                           // flower of life: 19 circles on a hex lattice
        float R = 0.075;
        vec2 qq = q * rot(uTime * 0.05);
        for (int i = -2; i <= 2; i++) for (int j = -2; j <= 2; j++) {
            if (abs(i + j) > 2) continue;
            vec2 c = R * (float(i) * vec2(1.0, 0.0) + float(j) * vec2(0.5, 0.8660254));
            L = max(L, lineAA(abs(length(qq - c) - R), w));
        }
        L = max(L, lineAA(abs(r - R * 3.0), w * 1.5));
    } else if (type == 10.0) {                          // Chladni plate nodal lines, mode per pulse
        float n = 2.0 + mod(floor(uStep), 5.0), m = n + 1.0 + mod(floor(uStep * 0.5), 3.0);   // n == m would be all-node
        vec2 x = q * 2.2;
        float v = sin(n * PI * x.x) * sin(m * PI * x.y) - sin(m * PI * x.x) * sin(n * PI * x.y);
        L = max(L, lineAA(abs(v) / (length(vec2(dFdx(v), dFdy(v))) / px + 1e-4), w) * smoothstep(0.75, 0.55, r));
    } else if (type == 11.0) {                          // star chart / armillary rings with zodiac ticks
        for (int i = 1; i <= 4; i++) {
            float R = 0.09 * float(i);
            L = max(L, lineAA(abs(r - R), w) * (i == 4 ? 1.0 : 0.6));
        }
        float spin = uTime * 0.1 + uStep * 0.2;
        float z = abs(fract((a + spin) / (TAU / 12.0) + 0.5) - 0.5) * (TAU / 12.0) * r;
        L = max(L, lineAA(z, w) * step(0.27, r) * step(r, 0.36));
        vec2 e = q * rot(0.41);                         // ecliptic ellipse
        L = max(L, 0.8 * lineAA(abs(length(e * vec2(1.0, 2.6)) - 0.3) / 1.8, w));
    } else if (type == 12.0) {                          // EEG trace across the lower third
        float x = p.x * 6.0 - uTime * 3.0;
        float v = 0.03 * sin(x * 3.1) + 0.02 * sin(x * 7.3 + 1.0) + 0.06 * exp(-pow(fract(x * 0.25) - 0.5, 2.0) * 400.0) * (0.5 + uHit);
        L = max(L, lineAA(abs(p.y + 0.33 - v), w * 1.4));
        L = max(L, 0.25 * lineAA(abs(fract(p.x * 4.0) - 0.5) * 0.25, w) * step(abs(p.y + 0.33), 0.08));
    } else if (type == 13.0) {                          // code rain: falling glyph blocks
        vec2 g = p * vec2(36.0, 22.0);
        float col = floor(g.x);
        float speed = 2.0 + 4.0 * hash11(col);
        float y = g.y + uTime * speed + hash11(col + 3.0) * 50.0;
        vec2 cell = vec2(col, floor(y));
        vec2 f = fract(vec2(g.x, y));
        float glyph = step(0.5, hash12(cell + floor(uTime * 6.0) * step(0.9, hash12(cell)))) *
                      step(0.15, f.x) * step(f.x, 0.85) * step(0.1, f.y) * step(f.y, 0.9);
        float trail = pow(fract(-y / 22.0 + hash11(col)), 6.0);
        L = max(L, glyph * trail * 0.9);
    } else if (type == 14.0) {                          // Dürer's 4x4 magic square grid
        vec2 g = (q + 0.16) / 0.08;
        if (all(greaterThanEqual(g, vec2(0.0))) && all(lessThan(g, vec2(4.0)))) {
            vec2 gf = abs(fract(g) - 0.5);
            L = max(L, lineAA((0.5 - max(gf.x, gf.y)) * 0.08, w));
            float cell = floor(g.x) + 4.0 * floor(g.y);
            L = max(L, 0.5 * step(hash11(cell + floor(uStep * 3.0)), 0.25) * step(max(gf.x, gf.y), 0.32));
        }
    }
    return L;
}

vec3 hud(vec2 fc, vec3 c) {
    if (uHudA <= 0.0 || (uHud0 == 0.0 && uHud1 == 0.0)) return c;
    vec2 up = vec2(fc.x, uRes.y - fc.y);                // post renders flipped: back to y-up
    vec2 asp = vec2(uRes.x / uRes.y, 1.0);
    vec2 p = (up / uRes - 0.5) * asp;
    vec2 f = (uHudFocus - 0.5) * asp;
    float px = 1.0 / uRes.y;
    float L = max(uHud0 > 0.0 ? hudLines(uHud0, p, f, px) : 0.0, uHud1 > 0.0 ? 0.8 * hudLines(uHud1, p, f, px) : 0.0);
    float flick = 0.85 + 0.15 * step(0.08, hash11(floor(uTime * 24.0)));
    return mix(c, uHudCol, clamp(L * uHudA * flick, 0.0, 1.0) * 0.85);
}
