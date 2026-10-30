// Domain-warped fbm: liquid marble / oil-slick, bump-lit.
uniform float uWScale;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y * uWScale;
    p = rot(0.12 * uStep) * p;
    float t = uTime * 0.12;
    vec2 q = vec2(fbm(p + t), fbm(p + vec2(5.2, 1.3) - t));
    vec2 r = vec2(fbm(p + 4.0 * q + vec2(1.7, 9.2) + 0.15 * t + 0.3 * uSpring), fbm(p + 4.0 * q + vec2(8.3, 2.8) - 0.126 * t));
    float f = fbm(p + 4.0 * r);
    float fx = fbm(p + 4.0 * r + vec2(0.01, 0.0)) - f;
    float fy = fbm(p + 4.0 * r + vec2(0.0, 0.01)) - f;
    vec3 n = normalize(vec3(-fx * 60.0, -fy * 60.0, 1.0));
    vec3 col = pal(f * 1.3 + length(q) * 0.5 + 0.05 * uStep);
    col = mix(col, pal(0.6 + r.x), clamp(length(r) * 0.6, 0.0, 1.0) * 0.5);
    float dif = clamp(dot(n, normalize(vec3(0.4, 0.6, 0.7))), 0.0, 1.0);
    float spe = pow(clamp(dot(reflect(vec3(0, 0, -1), n), normalize(vec3(0.4, 0.6, 0.7))), 0.0, 1.0), 30.0);
    col *= (0.15 + 1.0 * f * f) * (0.35 + 0.7 * dif);
    col += spe * 0.6 * (1.0 + uHit);
    return col;
}
