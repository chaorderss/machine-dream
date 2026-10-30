// Julia set with c orbiting |c| = 0.7885 (dendritic, near the Mandelbrot boundary); smooth bands flow outward.
uniform float uJZoom, uJC;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    p = rot(uTime * 0.04 + 0.2 * uStep) * p;
    vec2 z = p * uJZoom * (1.0 - 0.06 * uSpring);
    float ph = uJC + uTime * 0.05 + 0.02 * uStep;
    vec2 c = 0.7885 * vec2(cos(ph), sin(ph));
    float it = 0.0, m2 = 0.0, trap = 1e9;
    for (int i = 0; i < 256; i++) {
        z = vec2(z.x * z.x - z.y * z.y, 2.0 * z.x * z.y) + c;
        m2 = dot(z, z);
        trap = min(trap, abs(z.x * z.y));
        if (m2 > 1e4) break;
        it += 1.0;
    }
    if (it > 255.0) return pal(trap * 6.0 + 0.6) * 0.03;
    float sm = it - log2(log2(m2)) + 4.0;
    vec3 col = pal(sm * 0.02 + uTime * 0.02 + 0.04 * uStep);
    col *= 0.3 + 0.7 * (0.5 + 0.5 * cos(sm * 0.35 - uTime * 2.0));
    col *= 1.0 + 0.6 * uHit;
    return col * 1.1;
}
