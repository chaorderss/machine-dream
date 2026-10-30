// Seed the reaction-diffusion field from the edges of the previous frame:
// the frozen machine geometry literally becomes the creature's skeleton.
vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 o = 2.0 / uRes;
    vec3 w = vec3(0.3, 0.6, 0.1);
    float lx = dot(texture(uPrev, uv + vec2(o.x, 0)).rgb - texture(uPrev, uv - vec2(o.x, 0)).rgb, w);
    float ly = dot(texture(uPrev, uv + vec2(0, o.y)).rgb - texture(uPrev, uv - vec2(0, o.y)).rgb, w);
    float edge = length(vec2(lx, ly)) / (0.15 + dot(texture(uPrev, uv).rgb, w));
    float b = smoothstep(0.25, 0.6, edge);
    b = max(b, step(0.995, hash12(fc)));
    return vec3(1.0, 0.75 * b, 0.0);
}
