// Three charts of the heavens as nested shells. iA = u, v, shell, cell width in v; iB = rect; iC = seed, seed, half size, star; iD = ring radius, angle; iE = mandala rect
uniform float uRise, uRing, uStarsUp;
uniform vec3 uCamPos;
void place(inout Tile T) {
    float u = iA.x, v = iA.y, sh = iA.z, s1 = iC.x, s2 = iC.y, star = iC.w;
    float R = 0.8 + sh * 0.62;
    float th = (u - 0.5) * TAU * 0.92 + uTime * (0.05 - 0.032 * sh);
    float ph = (v - 0.5) * PI * 0.86;
    vec3 sph = vec3(cos(ph) * sin(th), sin(ph), cos(ph) * cos(th)) * R;
    vec3 flat_ = vec3((u - 0.5) * 1.0 + (sh - 1.0) * 0.62, (v - 0.5) * 1.0 + (sh - 1.0) * 0.08, -sh * 0.05);
    float k = smoothstep(s1 * 0.5, s1 * 0.5 + 0.5, uRise);
    k = k * k * (3.0 - 2.0 * k);
    vec3 p = mix(flat_, sph, k);
    float wide = iC.z * mix(1.0, 5.8 * R * cos(ph), k), tall = iC.z * mix(1.0, 2.75 * R, k);
    // holes open in the shells so that the next one shows through
    float keep = step(0.42 * k, fbm(vec2(u * 9.0 + sh * 3.0, v * 7.0)) * 0.9 + star);
    vec3 n = normalize(sph), rr = normalize(cross(vec3(0.0, 1.0, 0.0), n)), uu = cross(n, rr);
    vec3 ax = mix(vec3(wide, 0.0, 0.0), rr * wide, k), ay = mix(vec3(0.0, tall, 0.0), uu * tall, k);
    T.uv = iB; T.tint = vec3(1.05);
    if (star > 0.5) {                                                 // stars leave the paper as spheres of light
        T.round_ = 1.0; T.add = 1.0; T.glow = 1.6 * k; T.flatten = 1.0;
        float b = (1.0 + 7.0 * uStarsUp); ax = normalize(ax) * iC.z * b * 1.3; ay = normalize(ay) * iC.z * b * 1.3;
        T.tint = vec3(1.2, 1.0, 0.75) * k;
    }
    if (uRing > 0.0) {
        float e = smoothstep(s2 * 0.6, s2 * 0.6 + 0.4, uRing);
        float a = iD.y + uTime * 0.1 * (1.0 - e * 0.7);
        p = mix(p, vec3(cos(a), sin(a), 0.0) * iD.x, e);
        ax = mix(ax, vec3(0.0092, 0.0, 0.0), e); ay = mix(ay, vec3(0.0, 0.0092, 0.0), e);
        keep = max(keep, e);
        if (e > 0.5) { T.uv = iE; T.round_ = 0.0; T.add = 0.0; T.glow = 0.0; T.flatten = 0.0; T.tint = vec3(1.0); }
    }
    float near = smoothstep(0.03, 0.22, length(p - uCamPos));         // cells passing the lens shrink away
    T.pos = p; T.x = ax * near * keep; T.y = ay * near * keep;
}
