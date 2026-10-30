// Light gathering into two hands. iA = start xyz, seed; iB = target xyz, seed
uniform float uGather;
void place(inout Tile T) {
    float s = iA.w, k = clamp((uGather - iB.w * 0.45) / 0.55, 0.0, 1.0);
    k = k * k * (3.0 - 2.0 * k);
    vec3 a = iA.xyz + vec3(sin(uTime * (0.3 + s) + s * 40.0), cos(uTime * (0.23 + s) + s * 17.0), 0.0) * 0.03;
    vec3 p = mix(a, iB.xyz, k);
    p += vec3(sin(uTime * 0.7 + s * 90.0), cos(uTime * 0.6 + s * 70.0), 0.0) * 0.0035 * (1.0 + 2.0 * (1.0 - k));
    float z = 0.0018 + 0.0018 * s;
    T.pos = p; T.x = vec3(z, 0.0, 0.0); T.y = vec3(0.0, z, 0.0);
    T.round_ = 1.0; T.add = 1.0; T.glow = 1.0; T.flatten = 1.0; T.solid = 1.0;
    T.col = mix(vec3(1.0, 0.62, 0.3), vec3(1.0, 0.9, 0.72), k) * (0.1 + 0.075 * k);
    T.tint = vec3(1.0);
}
