// One transparent layer of a body. Ink becomes light, paper becomes nothing: skin, muscle, bone, nerve hang in space.
uniform sampler2D uData;
uniform float uFilter, uInv, uGain;
float L(vec2 uv) { return dot(texture(uPaint, uv).rgb, vec3(0.3, 0.6, 0.1)); }
vec3 shade(vec2 uv, vec3 c) {
    float l = dot(c, vec3(0.3, 0.6, 0.1));
    float m = uFilter < 3.5 ? smoothstep(0.3, 0.7, texture(uData, uv).r) : 1.0;
    float ink = smoothstep(0.22, 0.02, l);
    vec2 e = vec2(1.5 / 1000.0, 0.0);
    float lap = abs(4.0 * L(uv) - L(uv + e.xy) - L(uv - e.xy) - L(uv + e.yx) - L(uv - e.yx));
    vec3 tint = vec3(1.0, 0.86, 0.68);                      // skin
    if (uFilter > 0.5) tint = vec3(0.6, 0.27, 0.19);        // muscle
    if (uFilter > 1.5) tint = vec3(0.86, 0.92, 1.0);        // bone
    vec3 x = tint * (ink * 1.5 + 0.09);
    if (uFilter > 2.5 && uFilter < 3.5) x = vec3(0.2, 0.85, 1.0) * smoothstep(0.3, 0.8, lap) * 1.3;     // nerve
    if (uFilter > 3.5) x = c * 0.35;                        // the whole man again, seen through the others
    return mix(c, x * m, uInv) * uGain;
}
