// The tower of Babel as bricks. iA = theta, y, radius, half size; iB = rect on the painting; iC = seed, recess, tier, 1 above the painting
// iD = rect on the sheet (another painting), iE = target x, y on the Starry Night plane, seed2, is-window; iF = rect on that plane's sheet
uniform float uGrow, uDis, uSwap, uDepthK, uAxisX, uFold, uBurst, uSpinT, uCover;
uniform vec3 uCamPos, uR, uU, uF;
uniform mat4 uCopy;
void place(inout Tile T) {
    float th = iA.x, y = iA.y, r = iA.z, sz = iA.w, s1 = iC.x, tier = iC.z, up = iC.w;
    float vis = smoothstep(-0.015, 0.03, uGrow - y);
    if (vis <= 0.0 && uDis <= 0.0) { T.x = vec3(0.0); T.y = vec3(0.0); T.pos = vec3(1e3); return; }
    // higher tiers grow stranger: the wall folds with a rising frequency
    float cx = up * smoothstep(0.0, 3.0, tier * 0.1);
    float fold = uFold * cx * 0.05 * (sin(th * (5.0 + 2.0 * floor(tier * 0.5)) + y * 18.0) + 0.5 * sin(th * (19.0 + tier) - y * 40.0));
    float rr = (r + fold) * (1.0 - 0.28 * iC.y * uDepthK);
    float a = th + uSpinT * up * 0.3;
    vec3 n = vec3(sin(a), 0.0, cos(a));
    vec3 p = vec3(uAxisX, y, 0.0) + vec3(n.x * rr, 0.0, n.z * rr * uDepthK);
    vec3 tang = vec3(n.z, 0.0, -n.x);
    float hs = sz * vis * (1.0 + 1.1 * uFold * cx);
    vec3 ax = tang * hs, ay = vec3(0.0, hs * 0.72, 0.0), az = n * hs * (0.35 + 0.9 * iC.y) * uDepthK;
    p = (uCopy * vec4(p, 1.0)).xyz;
    ax = mat3(uCopy) * ax; ay = mat3(uCopy) * ay; az = mat3(uCopy) * az;
    float swap = step(s1, uSwap * (0.15 + 0.85 * smoothstep(-0.45, 0.6, y)));
    T.hero = (up > 0.5 || swap > 0.5) ? 0.0 : 1.0;
    T.uv = T.hero > 0.5 ? iB : iD;
    T.tint = vec3(1.0);
    if (T.hero < 0.5) T.tint = vec3(1.05);
    if (iE.w > 0.5) { ax *= 2.1; ay *= 2.6; T.glow = 1.2; T.uv = iD; T.hero = 0.0; az *= 0.2; }
    T.pos = p; T.x = ax; T.y = ay; T.z = az;
    // collapse into the Starry Night: top first, every brick spirals to its own place on one huge sheet
    if (uDis > 0.0) {
        float k = clamp((uDis * 1.75 - 0.5 * (1.0 - clamp((y + 0.5) / 4.0, 0.0, 1.0)) - 0.25 * iE.z), 0.0, 1.0);
        k = k * k * (3.0 - 2.0 * k);
        vec2 q = iE.xy;
        vec2 c = vec2(-0.05, 0.22);
        vec2 d = q - c;
        float ang = (1.0 - k) * (5.0 + 3.0 * iE.z) + 0.35 * uBurst / (0.25 + length(d));
        d = rot(ang) * d * (1.0 + 2.5 * (1.0 - k));
        q = c + d;
        vec3 tgt = uCamPos + uF * 2.0 + uR * q.x * 2.03 + uU * q.y * 2.03;
        float e = smoothstep(0.0, 0.5, k);
        T.pos = mix(p, tgt, k);
        float s = uCover;
        T.x = mix(ax, uR * s, e); T.y = mix(ay, uU * s, e); T.z = mix(az, vec3(0.0), e);
        T.uv = e > 0.5 ? iF : T.uv;
        if (e > 0.5) T.hero = 0.0;
        T.tint *= 1.0 + 0.6 * sin(3.14159 * k);
        T.glow += 0.0;
    }
}
