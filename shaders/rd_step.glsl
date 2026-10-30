// Gray-Scott reaction-diffusion step (A in .r, B in .g). Runs at sim resolution.
uniform sampler2D uState;
uniform float uFeed, uKill;
uniform vec3 uDrop;       // xy = uv, z = radius (0 = none)

vec3 render(vec2 fc) {
    vec2 px = 1.0 / uRes;
    vec2 uv = fc * px;
    vec2 c = texture(uState, uv).rg;
    vec2 lap = -c;
    lap += 0.2 * (texture(uState, uv + vec2(px.x, 0)).rg + texture(uState, uv - vec2(px.x, 0)).rg +
                  texture(uState, uv + vec2(0, px.y)).rg + texture(uState, uv - vec2(0, px.y)).rg);
    lap += 0.05 * (texture(uState, uv + px).rg + texture(uState, uv - px).rg +
                   texture(uState, uv + vec2(px.x, -px.y)).rg + texture(uState, uv + vec2(-px.x, px.y)).rg);
    float a = c.r, b = c.g;
    float abb = a * b * b;
    a += 1.0 * lap.r - abb + uFeed * (1.0 - a);
    b += 0.5 * lap.g + abb - (uKill + uFeed) * b;
    if (uDrop.z > 0.0) {
        vec2 d = (uv - uDrop.xy) * vec2(uRes.x / uRes.y, 1.0);
        if (length(d) < uDrop.z) b = max(b, 0.8);
    }
    return vec3(clamp(a, 0.0, 1.0), clamp(b, 0.0, 1.0), 0.0);
}
