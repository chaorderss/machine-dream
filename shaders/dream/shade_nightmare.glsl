// The demon holds still. Its shadow does not: it leaves the wall and climbs towards the lens.
uniform sampler2D uData;
uniform float uGain, uShadow, uGrow;
uniform vec2 uSC;
vec3 shade(vec2 uv, vec3 c) {
    vec2 q = (uv - uSC) / (1.0 + uGrow * 5.0) + vec2(0.63, 0.86) + vec2(-0.1, 0.0) * (1.0 - uGrow);
    float s = 0.0;
    for (int i = 0; i < 6; i++) s += texture(uData, q + vec2(cos(float(i)), sin(float(i))) * 0.008 * (1.0 + uGrow * 2.0)).r;
    s /= 6.0;
    float wob = 1.0 + 0.12 * sin(uv.y * 30.0 + uTime * 2.0) * uShadow;
    float body = smoothstep(0.3, 0.7, texture(uData, uv).r);        // the demon itself never moves
    return c * uGain * (1.0 - clamp(s * 1.3 * wob * uShadow, 0.0, 0.97) * (1.0 - body));
}
