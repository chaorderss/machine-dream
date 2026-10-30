// {p,q} tiling of the Poincare disk, drifting by a hyperbolic (Moebius) translation.
uniform float uP, uQ, uHMove;

vec2 cmul(vec2 a, vec2 b) { return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x); }
vec2 cdiv(vec2 a, vec2 b) { return cmul(a, vec2(b.x, -b.y)) / dot(b, b); }

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec2 z = p / 0.49;
    float rr = length(z);
    vec2 m = 0.55 * vec2(cos(uTime * uHMove), sin(uTime * uHMove * 0.7)) * (0.6 + 0.4 * sin(uTime * 0.13));
    z = cdiv(z + m, vec2(1.0, 0.0) + cmul(vec2(m.x, -m.y), z));
    z = rot(uTime * 0.05 + 0.4 * uStep) * z;
    float sp = sin(PI / uP), cq = cos(PI / uQ);
    float c = 1.0 / sqrt(1.0 - sp * sp / (cq * cq));
    float r = sqrt(c * c - 1.0);
    vec2 C = vec2(c, 0.0);
    float flips = 0.0;
    float w = TAU / uP;
    for (int i = 0; i < 48; i++) {
        float a = atan(z.y, z.x), l = length(z);
        a = mod(a, w);
        if (a > 0.5 * w) { a = w - a; flips += 1.0; }
        z = l * vec2(cos(a), sin(a));
        vec2 d = z - C;
        float dd = dot(d, d);
        if (dd < r * r) { z = C + d * (r * r / dd); flips += 1.0; } else break;
    }
    float dc = abs(length(z - C) - r);
    float dl = min(abs(z.y), abs(dot(z, vec2(-sin(PI / uP), cos(PI / uP)))));
    float par = mod(flips, 2.0);
    vec3 col = pal(par * 0.5 + flips * 0.02 + uTime * 0.02 + 0.07 * uStep) * (0.25 + 0.45 * par);
    col += pal(0.8 + 0.1 * uStep) * exp(-dc * 70.0) * (1.0 + uHit);
    col += pal(0.2) * exp(-dl * 90.0) * 0.5;
    col *= smoothstep(1.0, 0.985, rr);
    col += pal(0.6) * exp(-abs(rr - 1.0) * 40.0) * 0.6;
    return col * (0.8 + 0.5 * uRms);
}
