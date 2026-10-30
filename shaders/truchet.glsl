// Neon Truchet arcs in three parallax layers, light flowing along the curves.
uniform float uTScale;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec3 col = vec3(0.0);
    for (int L = 0; L < 3; L++) {
        float fl = float(L);
        vec2 q = rot(0.2 * fl + 0.05 * uTime + 0.1 * uStep) * p * uTScale * (1.0 + fl * 0.9) + vec2(uTime * 0.3 * (fl + 1.0), fl * 3.1);
        vec2 id = floor(q), f = fract(q) - 0.5;
        if (hash12(id + fl * 17.0) > 0.5) f.x = -f.x;
        vec2 c1 = f - 0.5, c2 = f + 0.5;
        float d1 = abs(length(c1) - 0.5), d2 = abs(length(c2) - 0.5);
        float d = min(d1, d2);
        float ang = d1 < d2 ? atan(c1.y, c1.x) : atan(c2.y, c2.x);
        float flow = 0.5 + 0.5 * sin(ang * 4.0 - uTime * 4.0 + (id.x + id.y) * 1.7);
        float line = smoothstep(0.06, 0.02, d);
        vec3 c = pal(fl * 0.3 + hash12(id) * 0.4 + 0.05 * uStep + uTime * 0.02);
        col += c * (line * (0.3 + 1.2 * flow * (1.0 + uHit)) + exp(-d * 12.0) * 0.25) / (1.0 + fl * 1.2);
    }
    return col * (0.7 + 0.6 * uRms);
}
