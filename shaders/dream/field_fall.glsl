// A continuous fall through three paintings. iA = x, y, plane z, half size; iB = rect; iC = seed, layer depth, plane, segment seed
uniform float uShred;
uniform vec3 uCamPos;
void place(inout Tile T) {
    float s1 = iC.x, s2 = iC.w;
    vec3 p = vec3(iA.xy, iA.z + iC.y);
    float d = uCamPos.z - p.z;                     // > 0: still below the camera
    float r = length(p.xy);
    // a hole opens round the fall line as the camera arrives; whole segments let go and tumble up past it
    float hole = (0.6 + 40.0 * smoothstep(7.0, 0.0, d)) * uShred * (0.7 + 0.6 * s2);
    float b = smoothstep(hole, hole * 0.55, r);
    vec2 dir = r > 1e-3 ? p.xy / r : vec2(1.0, 0.0);
    p.xy += dir * (0.5 + s2 * 2.5) * b;
    p.z += b * (2.0 + 6.0 * s2);
    float ang = (s2 - 0.5) * 7.0 * b + uTime * (s2 - 0.5) * 1.6 * b;
    float sz = iA.w * (1.0 + 0.6 * b);
    vec2 ex = rot(ang) * vec2(sz, 0.0), ey = rot(ang) * vec2(0.0, sz);
    T.pos = p; T.x = vec3(ex, (s1 - 0.5) * sz * 2.0 * b); T.y = vec3(ey, 0.0);
    T.uv = iB;
    T.edge = 0.7 * smoothstep(0.1, 0.7, b);        // bodies, wings and walls turn to wireframe grid as they go
    T.tint = vec3(1.1);
    T.flatten = 0.3 * b;
}
