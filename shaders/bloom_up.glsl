uniform sampler2D uSrc;   // smaller (already upsampled) level
uniform sampler2D uB;     // downsample of this level
vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 hp = 0.5 / vec2(textureSize(uSrc, 0));
    vec3 s = texture(uSrc, uv + vec2(-hp.x * 2.0, 0)).rgb + texture(uSrc, uv + vec2(hp.x * 2.0, 0)).rgb;
    s += texture(uSrc, uv + vec2(0, -hp.y * 2.0)).rgb + texture(uSrc, uv + vec2(0, hp.y * 2.0)).rgb;
    s += (texture(uSrc, uv + vec2(-hp.x, hp.y)).rgb + texture(uSrc, uv + hp).rgb +
          texture(uSrc, uv + vec2(hp.x, -hp.y)).rgb + texture(uSrc, uv - hp).rgb) * 2.0;
    return s / 12.0 + texture(uB, uv).rgb;
}
