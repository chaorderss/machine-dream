// The eye of every painting. iA = radius, angle, tunnel z, half size; iB = sheet rect; iC = seeds, laps per 300 s, kind
uniform float uLoop, uShatter, uDive, uBreath, uFocusK, uMem;
uniform vec3 uCamPos;
#define D 1.3737        // camera distance at frame 0
#define TUNNEL 16.0
void place(inout Tile T) {
    float kind = iC.w, s1 = iC.x, s2 = iC.y;
    float L = uLoop / 300.0;
    float focus = 1.0 + 0.045 * sin(TAU * 25.0 * L) * sin(TAU * 4.0 * L) + 0.05 * uBreath;     // the eye focusing
    focus *= 1.0 + uFocusK;                                    // wide open, then the pupil clamps down on the viewer
    T.uv = iB;
    if (kind < 0.5) {                                          // iris shard on its orbit
        // memory: shard by shard the eye goes dark; what is left at the end is only ever Adam
        float gone = 1.0 - smoothstep(0.0, 0.008, 0.12 + 0.88 * uMem - fract(s2 * 7.31 + s1 * 3.17));
        if (uMem < 0.1 * s1) T.uv = iD;
        float a = iA.y + TAU * iC.z * L + 0.03 * sin(TAU * (11.0 + floor(s1 * 9.0)) * L + s2 * TAU);
        float r = iA.x + 0.006 * sin(TAU * (7.0 + floor(s2 * 8.0)) * L + s1 * TAU);
        r = 0.125 * focus + (r - 0.125) * (1.0 - 0.125 * focus) / 0.875;
        float k = smoothstep(0.125, 0.33, r);
        vec2 d = vec2(cos(a), sin(a));
        float z = -0.5 * pow(1.0 - clamp((r - 0.125) / 0.345, 0.0, 1.0), 2.0) + 0.01 * sin(TAU * 9.0 * L + s1 * TAU);
        float wide = r * (D - z) / D;                          // funnel: stays where it was on screen at frame 0
        vec3 p = vec3(d * wide, z);
        float tw = (s1 - 0.5) * 0.3 + 0.14 * sin(TAU * (5.0 + floor(s1 * 5.0)) * L + s2 * TAU);   // each shard has its own turn
        vec2 tan_ = rot(tw) * vec2(-d.y, d.x), rad = rot(tw) * d;
        float h = iA.w * (1.0 - 0.12 * smoothstep(0.0, 1.0, s2));
        T.x = vec3(tan_, 0.0) * iA.w;
        T.y = vec3(rad, 0.0) * h;
        // breaking up: shards fly off the orbit
        float b = uShatter * uShatter;
        p += vec3(d * (0.02 + 0.3 * s1 * s1), (s2 - 0.3) * 0.35) * b * (0.3 + s2);
        T.pos = p + vec3(0.0, 0.0, -40.0) * step(0.5, gone);
        T.tint = vec3(1.3 * (0.42 + 0.58 * k)) * (1.0 - gone);
        T.edge = 0.05;
    } else if (kind < 1.5) {                                   // the fall inside the pupil
        float z = mod(iA.z + TUNNEL * 40.0 * L, TUNNEL);
        float x = z / TUNNEL;
        float r = 0.135 * focus * (0.16 + 0.84 / (1.0 + z * 0.35));
        float a = iA.y + z * 0.7 + TAU * 6.0 * L;
        vec2 d = vec2(cos(a), sin(a));
        float wz = -0.5 - z;
        r *= (D - wz) / D;
        T.pos = vec3(d * r, wz);
        float sz = iA.w * mix(1.25, 0.6, x) * (D - wz) / D;
        vec2 tan_ = vec2(-d.y, d.x);
        T.x = vec3(tan_, 0.0) * sz;
        T.y = vec3(d, 0.0) * sz;
        // near: paintings. deeper: one-colour pixels. deepest: points of light
        T.flatten = smoothstep(0.08, 0.26, x);
        T.round_ = smoothstep(0.34, 0.44, x);
        T.add = T.round_ > 0.5 ? 1.0 : 0.0;
        float dist = length(T.pos - uCamPos);
        float at = smoothstep(0.0, 0.02, x) * smoothstep(1.0, 0.96, x);
        if (T.add > 0.5) {                                     // data points: bright only as they pass the camera
            T.x *= 0.3; T.y *= 0.3;
            float g = uDive > 0.0 ? clamp(0.5 / (dist * dist + 0.1), 0.0, 1.6) : 0.0;
            T.tint = vec3(at * (0.03 + g)) * mix(vec3(0.7, 0.92, 1.3), vec3(1.3, 1.0, 0.7), s1);
            T.flatten = 1.0;
            T.glow = 1.0;
        } else {
            float frame0 = 1.0 - (1.0 - step(0.001, uDive)) * 0.62;
            T.tint = vec3(at * mix(1.1, 1.5, T.flatten) * frame0 * mix(0.25, 1.0, uMem));
        }
    } else {                                                   // limbus
        float a = iA.y;
        T.pos = vec3(vec2(cos(a), sin(a)) * iA.x * (1.0 + 0.02 * uShatter), -0.002);
        T.x = vec3(iA.w, 0.0, 0.0); T.y = vec3(0.0, iA.w, 0.0);
        T.flatten = 2.0; T.round_ = 1.0; T.add = 1.0;
        T.uv = vec4(0.5);
    }
}
