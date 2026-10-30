// Living crystal cells: animated Voronoi, glowing borders, notes light up random cells.
uniform float uVScale;

vec3 voro(vec2 x) {
    vec2 n = floor(x), f = fract(x);
    vec2 mg = vec2(0), mr = vec2(0);
    float md = 8.0;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
        vec2 g = vec2(i, j);
        vec2 o = 0.5 + 0.5 * sin(uTime * 0.6 + TAU * hash22(n + g));
        vec2 r = g + o - f;
        float d = dot(r, r);
        if (d < md) { md = d; mr = r; mg = g; }
    }
    md = 8.0;
    for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
        vec2 g = mg + vec2(i, j);
        vec2 o = 0.5 + 0.5 * sin(uTime * 0.6 + TAU * hash22(n + g));
        vec2 r = g + o - f;
        if (dot(mr - r, mr - r) > 1e-5) md = min(md, dot(0.5 * (mr + r), normalize(r - mr)));
    }
    return vec3(md, hash12(n + mg), length(mr));
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec3 col = vec3(0.0);
    for (int L = 0; L < 2; L++) {
        float fl = float(L);
        vec2 q = rot(0.1 * fl + 0.03 * uTime + 0.08 * uStep) * p * uVScale * (1.0 + fl * 1.3) + vec2(fl * 7.3, uTime * 0.05);
        vec3 v = voro(q);
        float lit = step(0.82, hash11(v.y * 91.0 + uNoteCount)) * exp(-uNoteAge * 3.0);
        vec3 cell = pal(v.y * 0.8 + 0.05 * uStep + uTime * 0.02) * (0.05 + 0.3 * smoothstep(0.6, 0.0, v.z) + 1.5 * lit);
        cell *= smoothstep(0.0, 0.08, v.x);
        cell += pal(0.75 + v.y * 0.2) * exp(-v.x * 45.0) * 1.2;
        col += cell / (1.0 + fl * 2.0);
    }
    return col * (0.8 + 0.4 * uRms);
}
