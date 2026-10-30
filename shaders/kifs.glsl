// Glowing crystal: rotating Kaleidoscopic IFS (octahedral folds), glass rim + inner glow.
uniform float uKA, uKB;
float gKT;

float mapK(vec3 p) {
    p.xz = rot(uTime * 0.2 + 0.3 * uStep) * p.xz;
    p.xy = rot(uTime * 0.13) * p.xy;
    float s = 1.0;
    gKT = 1e9;
    for (int i = 0; i < 10; i++) {           // Sierpinski-tetrahedron folds with a twist per level
        if (p.x + p.y < 0.0) p.xy = -p.yx;
        if (p.x + p.z < 0.0) p.xz = -p.zx;
        if (p.y + p.z < 0.0) p.zy = -p.yz;
        p.xy = rot(uKB + 0.05 * sin(uTime * 0.3)) * p.xy;
        p.yz = rot(0.5 * uKB) * p.yz;
        p = p * 2.0 - vec3(uKA + 0.05 * uSpring);
        s *= 2.0;
        gKT = min(gKT, dot(p, p));
    }
    return length(p) / s - 0.002;
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec3 ro = vec3(0.0, 0.0, -4.3 + 0.3 * uSpring);
    vec3 rd = normalize(vec3(p, 1.5));
    float t = 0.0, glow = 0.0;
    int i;
    for (i = 0; i < 120; i++) {
        float d = mapK(ro + rd * t);
        glow += exp(-d * 30.0) * 0.012;
        if (d < 0.0005 || t > 12.0) break;
        t += d * 0.9;
    }
    vec3 col = pal(0.6 + glow * 0.2) * glow * 0.35;
    if (t < 12.0) {
        vec3 pos = ro + rd * t;
        float tr = gKT;
        vec2 e = vec2(1.0, -1.0) * 0.0007;
        vec3 n = normalize(e.xyy * mapK(pos + e.xyy) + e.yyx * mapK(pos + e.yyx) + e.yxy * mapK(pos + e.yxy) + e.xxx * mapK(pos + e.xxx));
        float fre = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0);
        float dif = clamp(dot(n, normalize(vec3(0.5, 0.8, -0.6))), 0.0, 1.0);
        vec3 base = pal(log(tr + 1e-3) * 0.12 + pos.y * 0.35 + 0.05 * uStep);
        col = base * (0.08 + 1.3 * dif * dif) + pal(0.8 + pos.x * 0.2) * fre * 1.1 + base * exp(-tr * 2.0) * 0.6 * (1.0 + uHit);
        col *= 1.0 - float(i) / 140.0;
    }
    return col;
}
