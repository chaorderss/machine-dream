// A face made of eyes. iA = x, y, size, threshold; iB = sheet rect; iC = blink seed
uniform float uEyes, uStare;
void place(inout Tile T) {
    float on = smoothstep(iA.w, iA.w + 0.04, uEyes);
    float b = 1.0 - (1.0 - uStare) * smoothstep(0.92, 1.0, sin(uTime * (1.3 + iC.x) + iC.y * 40.0));
    float s = iA.z * on;
    T.pos = vec3(iA.xy, 0.01 + iA.w * 0.02);
    T.x = vec3(s, 0.0, 0.0); T.y = vec3(0.0, s * 0.72 * b, 0.0);
    T.uv = iB;
    T.hero = 1.0;
    T.round_ = 0.55;
    T.tint = vec3(1.25);
    if (s <= 0.0) T.pos = vec3(1e3);
}
