uniform sampler2D uSrc;
uniform float uThreshold;   // only the first level: keep bloom to highlights
vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 hp = 0.5 / uRes;
    vec3 s = texture(uSrc, uv).rgb * 4.0;
    s += texture(uSrc, uv - hp).rgb + texture(uSrc, uv + hp).rgb;
    s += texture(uSrc, uv + vec2(hp.x, -hp.y)).rgb + texture(uSrc, uv - vec2(hp.x, -hp.y)).rgb;
    s = min(s / 8.0, vec3(64.0));
    float l = max(s.r, max(s.g, s.b));
    return s * max(l - uThreshold, 0.0) / max(l, 1e-4);
}
