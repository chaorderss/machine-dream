// Power-n Mandelbulb, orbit-trap coloured; the power shifts with the pulse clock.
uniform float uPower, uMBDist;
vec4 gMB;

float mapMB(vec3 p) {
    vec3 w = p;
    float m = dot(w, w);
    vec4 trap = vec4(abs(w), m);
    float dz = 1.0;
    float P = uPower + 0.5 * sin(0.5 * uStep);
    for (int i = 0; i < 5; i++) {
        float r = sqrt(m);
        dz = P * pow(r, P - 1.0) * dz + 1.0;
        float b = P * acos(clamp(w.y / r, -1.0, 1.0));
        float a = P * atan(w.x, w.z);
        w = p + pow(r, P) * vec3(sin(b) * sin(a), cos(b), sin(b) * cos(a));
        trap = min(trap, vec4(abs(w), m));
        m = dot(w, w);
        if (m > 256.0) break;
    }
    gMB = trap;
    return 0.25 * log(m) * sqrt(m) / dz;
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float an = uTime * 0.12 + 0.3 * uStep;
    float dist = uMBDist * (1.0 - 0.05 * uSpring);
    vec3 ro = vec3(dist * sin(an), 0.6 * sin(uTime * 0.07), dist * cos(an));
    vec3 ww = normalize(-ro), uu = normalize(cross(ww, vec3(0, 1, 0))), vv = cross(uu, ww);
    vec3 rd = normalize(p.x * uu + p.y * vv + 1.6 * ww);
    vec3 col = pal(0.7 + 0.3 * p.y) * 0.04 * (1.0 - length(p));
    float t = 0.0;
    int i;
    for (i = 0; i < 160; i++) {
        float d = mapMB(ro + rd * t);
        if (d < 0.0004 * t || t > 6.0) break;
        t += d;
    }
    if (t < 6.0) {
        vec3 pos = ro + rd * t;
        vec4 tr = gMB;
        vec2 e = vec2(1.0, -1.0) * 0.0005 * t;
        vec3 n = normalize(e.xyy * mapMB(pos + e.xyy) + e.yyx * mapMB(pos + e.yyx) + e.yxy * mapMB(pos + e.yxy) + e.xxx * mapMB(pos + e.xxx));
        float ao = clamp(tr.w * 1.5, 0.0, 1.0) * (1.0 - float(i) / 160.0);
        vec3 base = pal(tr.w * 0.7 + tr.y * 0.6 + 0.04 * uStep);
        base = mix(base, pal(0.5 + tr.x), clamp(tr.z * 2.0, 0.0, 1.0) * 0.5);
        vec3 L = normalize(vec3(0.6, 0.8, -0.3));
        float dif = clamp(dot(n, L), 0.0, 1.0);
        float spe = pow(clamp(dot(reflect(rd, n), L), 0.0, 1.0), 24.0);
        float fre = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0);
        col = base * (0.2 + 1.4 * dif) * ao + spe * 0.8 * ao + pal(0.9) * fre * 0.6 * ao;
        col += pal(tr.w + 0.3) * exp(-tr.w * 6.0) * 0.6 * (1.0 + uHit);
    }
    return col;
}
