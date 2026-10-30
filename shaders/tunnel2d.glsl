// Polar neon tunnel: tiled walls rushing at the camera, twisting.
uniform float uTwist2;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    p = rot(0.2 * uStep + 0.1 * uTime) * p;
    float r = length(p), a = atan(p.y, p.x);
    float z = 0.35 / (r + 0.02) + uTravel * 0.6 + uTime * 0.8;
    vec2 uv = vec2(a / PI * 8.0 + z * uTwist2 * 0.6, z * 3.0);
    vec2 g = fract(uv) - 0.5, id = floor(uv);
    float cell = max(abs(g.x), abs(g.y));
    float edge = smoothstep(0.42, 0.5, cell);
    float h = hash12(vec2(mod(id.x, 16.0), id.y));
    vec3 col = pal(id.y * 0.015 + h * 0.3 + 0.05 * uStep) * (0.03 + 0.5 * step(0.75, h) * (1.0 + 2.0 * uHit));
    col += pal(0.65 + 0.01 * id.y) * edge * 0.9;
    col *= smoothstep(0.0, 0.3, r) * (1.0 + 1.5 * exp(-fract(z * 0.25 - uTime * 0.5) * 6.0) * 0.3);
    col += pal(0.1) * 0.6 * exp(-r * 10.0);
    return col * (0.7 + 0.5 * uRms);
}
