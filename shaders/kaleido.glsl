// Fractal kaleidoscope: polar mirror wedges + Kali-set iteration, orbit-trap coloured.
uniform float uSeg, uKZoom, uKSpin, uKMorph;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float r0 = length(p);
    p = rot(uTime * uKSpin + 0.35 * uStep) * p;
    p *= 1.0 - 0.06 * uHit;
    float N = uSeg + 2.0 * mod(floor(uStep), 3.0);
    float s = TAU / N;
    float a = mod(atan(p.y, p.x), s);
    a = abs(a - 0.5 * s);
    vec2 q = length(p) * vec2(cos(a), sin(a)) * uKZoom;
    vec2 k = vec2(0.82 + 0.12 * sin(uTime * 0.11 + uKMorph), 0.58 + 0.1 * cos(uTime * 0.07 + 2.0 * uKMorph)) + 0.04 * uSpring;
    vec3 col = vec3(0.0);
    float trap = 1e9;
    for (int i = 0; i < 10; i++) {
        q = abs(q) / clamp(dot(q, q), 0.08, 1e4) - k;
        q = rot(0.15 * float(i) + 0.05 * uTime) * q;
        trap = min(trap, abs(length(q) - 0.6));
        col += pal(float(i) * 0.09 + length(q) * 0.08 + uTime * 0.03 + 0.06 * uStep) * exp(-abs(q.y) * 5.0) * 0.16;
    }
    col += pal(trap * 1.5 + 0.4 + 0.05 * uStep) * exp(-trap * 25.0) * 1.2;
    col *= 0.75 + 0.6 * uRms;
    return col * smoothstep(1.3, 0.1, r0);
}
