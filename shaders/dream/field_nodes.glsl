// Every recognised thing lifted out of the picture into a graph. iA = x, y, half w, half h; iB = rect; iC = goal xyz, seed
uniform float uK, uFloat;
void place(inout Tile T) {
    float k = clamp((uK - iC.w * 0.35) / 0.65, 0.0, 1.0);
    k = k * k * (3.0 - 2.0 * k);
    T.pos = mix(vec3(iA.xy, 0.03), iC.xyz, k);
    float s = 1.0 + 0.6 * k;
    T.x = vec3(iA.z * s, 0.0, 0.0); T.y = vec3(0.0, iA.w * s, 0.0);
    T.uv = iB; T.hero = 1.0; T.tint = vec3(1.25);
    if (uK <= 0.0) T.pos = vec3(1e3);
}
