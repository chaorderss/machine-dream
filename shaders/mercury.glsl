// Acoustic mercury chamber: a liquid-metal sphere floating in black.
// Every piano note: a new Chladni standing-wave mode + an impact ripple, and gravity turns.

uniform float uAppear;    // 0..1 sphere materialises
uniform float uRipple;    // ripple gain
uniform float uShape;     // 0 sphere .. 1 torus
uniform float uTint;      // 0 chrome .. 1 palette-coloured metal

vec3 dirHash(float n) {
    float a = hash11(n * 1.17 + 0.3) * TAU;
    float b = acos(2.0 * hash11(n * 3.31 + 1.7) - 1.0);
    return vec3(sin(b) * cos(a), cos(b), sin(b) * sin(a));
}

float chladni(vec3 n, float a, float b) {
    vec3 q = n * PI;
    return cos(a * q.x) * cos(b * q.y) - cos(b * q.x) * cos(a * q.y)
         + 0.5 * (cos(a * q.y) * cos(b * q.z) - cos(b * q.y) * cos(a * q.z));
}

float noteAmp() { return (1.0 - exp(-uNoteAge * 30.0)) * exp(-uNoteAge * 1.1); }

vec3 gravity() {
    vec3 g0 = dirHash(uNoteCount - 1.0), g1 = dirHash(uNoteCount);
    return normalize(mix(g0, g1, smoothstep(0.0, 0.7, uNoteAge)) + 1e-4);
}

float mapM(vec3 p) {
    vec3 g = gravity();
    // sag toward gravity like a heavy droplet
    float along = dot(p, g);
    vec3 q = p - g * (0.10 * smoothstep(-1.0, 1.0, along) * (0.5 + 0.5 * uSpring));
    float r = length(q);
    vec3 n = q / max(r, 1e-4);
    float a = 2.0 + floor(hash11(uNoteCount * 7.1) * 5.0);
    float b = a + 1.0 + floor(hash11(uNoteCount * 2.3) * 3.0);
    float amp = noteAmp() * uRipple;
    float disp = 0.018 * amp * chladni(n, a, b);
    // travelling ring from the impact point
    vec3 hit = dirHash(uNoteCount + 11.0);
    float geo = acos(clamp(dot(n, hit), -1.0, 1.0));
    disp += 0.012 * uRipple * sin(geo * 26.0 - uNoteAge * 14.0) * exp(-uNoteAge * 1.6) * smoothstep(uNoteAge * 2.2 + 0.2, uNoteAge * 2.2 - 0.2, geo);
    disp += 0.004 * sin(n.x * 9.0 + uTime) * sin(n.y * 11.0 - uTime * 0.7);
    float R = 0.62 * uAppear;
    vec3 qt = q;
    qt.yz = rot(0.6 + 0.2 * uStep) * qt.yz;
    float tor = length(vec2(length(qt.xz) - R * 0.8, qt.y)) - R * 0.32;
    return mix(r - R, tor, uShape) - disp;
}

vec3 env(vec3 d) {
    // acoustic chamber: dark walls of glowing latitude rings, a hot key light, a palette rim light
    float lat = asin(clamp(d.y, -1.0, 1.0));
    float lon = atan(d.z, d.x);
    vec3 c = mix(vec3(0.0), pal(0.15) * 0.05, smoothstep(-0.2, 0.6, d.y));
    c += pal(0.1 + lat * 0.2) * 0.9 * exp(-abs(fract(lat * 4.0 / PI + 0.5) - 0.5) * 70.0) * (0.4 + 0.6 * smoothstep(-1.0, 1.0, d.y));
    c += vec3(1.0) * 0.5 * exp(-abs(fract(lon * 12.0 / TAU) - 0.5) * 120.0) * smoothstep(0.35, 0.0, abs(lat - 0.1));
    c += vec3(0.95, 0.97, 1.0) * 6.0 * smoothstep(0.93, 0.975, dot(d, normalize(vec3(0.5, 0.75, -0.4))));
    c += pal(0.6) * 2.0 * smoothstep(0.9, 0.97, dot(d, normalize(vec3(-0.8, 0.1, 0.5))));
    c += vec3(0.4, 0.5, 0.7) * 0.15 * smoothstep(0.0, -0.5, d.y);   // floor bounce
    return c;
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    // the whole room turns with gravity
    vec3 g = gravity();
    float ang = 0.15 * uTime + 0.4 * atan(g.x, g.y) + 0.25 * uStep;
    vec3 ro = vec3(3.0 * sin(ang), 0.4 * g.z, -3.0 * cos(ang));
    vec3 ww = normalize(-ro);
    vec3 uu = normalize(cross(ww, vec3(0, 1, 0)));
    vec3 vv = cross(uu, ww);
    vec3 rd = normalize(p.x * uu + p.y * vv + 1.9 * ww);

    float t = 1.0;
    float d = 1.0;
    for (int i = 0; i < 110; i++) {
        d = mapM(ro + rd * t);
        if (abs(d) < 0.0003 || t > 6.0) break;
        t += d * 0.7;
    }
    vec3 col = env(rd) * 0.08;
    // dust motes
    vec2 gp = p * 60.0 + vec2(0.0, uTime * 0.3);
    vec2 cell = floor(gp), f = fract(gp) - hash22(cell) * 0.6 - 0.2;
    col += vec3(0.6, 0.7, 1.0) * 0.6 * step(0.97, hash12(cell)) * smoothstep(0.08, 0.0, length(f));
    if (t < 6.0) {
        vec3 pos = ro + rd * t;
        vec2 e = vec2(1.0, -1.0) * 0.0015;
        vec3 n = normalize(e.xyy * mapM(pos + e.xyy) + e.yyx * mapM(pos + e.yyx) + e.yxy * mapM(pos + e.yxy) + e.xxx * mapM(pos + e.xxx));
        vec3 r = reflect(rd, n);
        float fre = 0.65 + 0.35 * pow(1.0 - max(dot(n, -rd), 0.0), 5.0);
        vec3 metal = mix(vec3(0.82, 0.86, 0.92), pal(dot(n, g) * 0.4 + 0.05 * uStep) * 1.2, uTint);
        col = env(r) * metal * fre;
        // faint iridescent sheen where the standing wave is strongest
        col += pal(dot(n, g) * 0.5 + 0.3) * 0.05 * noteAmp() * uRipple;
    }
    return col;
}
