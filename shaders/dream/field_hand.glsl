// The machine's hand. iA = x, y, z, half size; iB = painting uv rect; iC = g (0 fingertip .. 1 shoulder), seed, seed, height above the skin in cubes
// uS sweeps along the arm: skin → small glowing cubes → cubes lift off → a hand of pixels, still reaching.
uniform float uS, uReach, uKeep, uTurn;
uniform vec3 uPivot;
void place(inout Tile T) {
    float g = iC.x, s1 = iC.y, s2 = iC.z, shell = iC.w;
    float p0_ = (uS * 1.3 - g) / 0.28;                               // this cell's own moment (g holds its jitter)
    float p = clamp(p0_, 0.0, 1.0);
    float lit = smoothstep(0.0, 0.22, p), lift = smoothstep(0.18, 0.62, p), land = smoothstep(0.62, 1.0, p);
    vec3 p0 = iA.xyz;
    vec3 away = normalize(vec3(s1 - 0.5, s2 - 0.5, 0.9)) * (0.028 + 0.05 * s2);
    float t = uTime;
    vec3 hover = vec3(sin(t * 1.3 + s1 * 40.0), cos(t * 1.1 + s2 * 40.0), sin(t * 0.9 + s2 * 20.0)) * 0.0016 * land;
    float tip = exp(-max(g - 0.1, 0.0) * 5.0);
    vec3 home = p0 + vec3(0.0, 0.0, 0.0) + hover;
    vec3 pos = mix(p0, p0 + away, lift * (1.0 - land)) + hover;
    pos.x -= uReach * tip * (0.6 + 0.4 * sin(t * 2.4));
    vec3 arm = pos - uPivot;                                          // it swings out of the wall, the fingertip stays where it is
    float ca = cos(uTurn * land), sa = sin(uTurn * land);
    pos = uPivot + vec3(arm.x * ca - arm.z * sa, arm.y, arm.x * sa + arm.z * ca);
    float sz = iA.w * mix(1.04, 0.92, lit) * mix(1.0, 0.8, lift * (1.0 - land));
    sz *= step(0.0, p0_);
    if (shell > 0.5) sz *= step(0.05, lift);                         // inner voxels exist only once the skin has opened
    if (uKeep < 0.5) {                                                // no landing: the figure goes with the wind
        float f = smoothstep(0.1, 1.0, p);
        pos = p0 + vec3(0.1 + 0.5 * s1, (s2 - 0.45) * 0.25, 0.1 + 0.2 * s2) * f * f + vec3(0.0, 0.0, 0.0);
        sz = iA.w * (1.0 - 0.6 * f) * step(0.0, p0_) * (1.0 - smoothstep(0.85, 1.0, f));
        land = 0.0;
    }
    T.pos = pos;
    T.x = vec3(sz, 0.0, 0.0); T.y = vec3(0.0, sz, 0.0); T.z = vec3(0.0, 0.0, sz * mix(0.25, 1.0, lit));
    T.uv = iB; T.hero = 1.0;
    T.flatten = smoothstep(0.1, 0.5, p);
    T.tint = mix(vec3(1.0), mix(vec3(0.95, 1.0, 1.1), vec3(0.62, 0.86, 1.25) * (0.5 + 0.14 * shell), land), lit);
    T.glow = 0.9 * lit * (1.0 - 0.45 * land) + (0.09 * shell + 0.8 * tip * (1.0 + 0.5 * sin(t * 2.4))) * land;
    T.edge = 0.34 * lit;
}
