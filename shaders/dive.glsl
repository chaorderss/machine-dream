// High-speed plunge through the cracks of an infinite Menger lattice.
// Camera rides uTravel (integral of the director speed curve); feedback adds speed streaks.

uniform float uTwist;
uniform float uStreak;    // 0..1 feedback motion blur
uniform float uWarmth;    // 0 neon .. 1 gold (continuity with the cathedral)

float gEdge;

float mapD(vec3 p) {
    p.xy *= rot(p.z * uTwist * 0.12);
    float d = -1e5;
    float s = 1.0;
    gEdge = 1e5;
    for (int m = 0; m < 5; m++) {
        vec3 a = mod(p * s, 2.0) - 1.0;
        s *= 3.0;
        vec3 r = abs(1.0 - 3.0 * abs(a));
        float da = max(r.x, r.y), db = max(r.y, r.z), dc = max(r.z, r.x);
        float c = (min(da, min(db, dc)) - 1.0) / s;
        d = max(d, c);
    }
    return d;
}

// distance (world units) to the nearest crease where two hole faces meet
float creases(vec3 p) {
    p.xy *= rot(p.z * uTwist * 0.12);
    float e = 1e5, s = 1.0;
    for (int m = 0; m < 3; m++) {
        vec3 a = mod(p * s, 2.0) - 1.0;
        s *= 3.0;
        vec3 q = abs(abs(1.0 - 3.0 * abs(a)) - 1.0) / s;
        float second = q.x + q.y + q.z - max(q.x, max(q.y, q.z)) - min(q.x, min(q.y, q.z));
        e = min(e, second);
    }
    return e;
}

vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float z = uTravel;
    vec3 ro = vec3(0.0, 0.0, z);
    // lens breathes with the music, fisheye gets stronger with intensity
    float fish = 0.25 + 0.5 * uIntensity;
    vec3 rd = normalize(vec3(p, 1.0 - fish * dot(p, p)));
    rd.xy *= rot(uTime * 0.3 + 0.15 * uSpring + 0.3 * uStep);

    float t = 0.0, d;
    float glow = 0.0;
    int i;
    for (i = 0; i < 110; i++) {
        d = mapD(ro + rd * t);
        glow += exp(-d * 90.0) * 0.006;
        if (d < 0.0004 * (1.0 + t) || t > 14.0) break;
        t += d * 0.85;
    }
    vec3 pos = ro + rd * t;
    float depth = pos.z;
    vec3 neon = pal(depth * 0.04 + uTime * 0.05);
    vec3 gold = vec3(1.0, 0.7, 0.3);
    vec3 tint = mix(neon, gold, uWarmth);

    vec3 col = vec3(0.0);
    if (t < 14.0) {
        float edge = smoothstep(0.003 * (1.0 + t), 0.0, creases(pos));
        float ao = 1.0 - float(i) / 110.0;
        // light bands rushing past, re-lit by every note
        float band = exp(-abs(fract(depth * 0.5) - 0.5) * 30.0) * (0.3 + 1.2 * uHit);
        col = tint * (0.02 + 1.0 * edge + 0.5 * band) * ao * ao / (1.0 + t * t * 0.3);
    }
    col += tint * glow * (0.4 + uRms);
    col = mix(col, tint * 0.12, 1.0 - exp(-t * 0.1));
    col += tint * 1.5 * exp(-length(p) * 9.0);              // light at the end of the crack
    // speed streaks: blend with zoomed previous frame
    float k = uDt * 60.0;   // keep feedback identical at 30/60 fps
    vec2 puv = 0.5 + (uv - 0.5) * pow(0.965, k);
    col = max(col, texture(uPrev, puv).rgb * pow(0.72, k) * uStreak);
    return col;
}
