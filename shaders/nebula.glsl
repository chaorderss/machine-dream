// Faint deep-space backdrop behind the bokeh field.
uniform float uNebula;
vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float n = fbm(p * 1.6 + vec2(uTime * 0.01, -uTime * 0.006));
    float m = fbm(p * 3.1 - n + 4.0);
    vec3 col = pal(n * 0.6 + 0.4) * pow(m, 3.0) * 0.06 + vec3(0.002, 0.003, 0.008);
    return col * uNebula;
}
