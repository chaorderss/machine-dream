uniform float uAspectC;
// A painting that breathes: strokes drift as soft light, water carries moving reflections.
uniform float uGain, uFlowA, uCaust, uWaterY, uGlowUp, uSplit, uGazeR;
uniform float uCutE;
uniform vec2 uGaze, uEyeA, uEyeB;
float hc(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec2 gazeAt(vec2 uv, vec2 e) {                          // the iris slides inside the eye opening, the lids stay
    float k = smoothstep(uGazeR, uGazeR * 0.45, length((uv - e) * vec2(1.0, 2.1)));
    return uv - uGaze * k;
}
vec3 shade(vec2 uv, vec3 c) {
    if (uCutE > 0.0 && 0.5 * hc(floor(uv * 9.0)) + 0.32 * hc(floor(uv * 36.0) + 7.0) + 0.18 * hc(floor(uv * 144.0) + 3.0) < uCutE) return vec3(0.0);
    if (uGazeR > 0.0) {
        vec2 w = gazeAt(gazeAt(uv, uEyeA), uEyeB);
        c = pow(texture(uPaint, w).rgb, vec3(2.2));
    }
    if (uFlowA > 0.0) {
        vec2 q = uv * vec2(uAspectC, 1.0) * 5.0;
        vec2 w = vec2(fbm(q + vec2(uTime * 0.09, 0.0)), fbm(q + vec2(4.1, -uTime * 0.08))) - 0.47;
        float band = smoothstep(0.82, 0.55, uv.y) * smoothstep(0.2, 0.42, uv.y);
        vec2 sp = vec2((uv.x > 0.5 ? -1.0 : 1.0) * uSplit * band * smoothstep(0.0, 0.25, abs(uv.x - 0.5)), 0.0);
        c = pow(texture(uPaint, uv + w * uFlowA + sp).rgb, vec3(2.2));
    }
    if (uCaust > 0.0) {
        vec2 q = uv * vec2(uAspectC, 3.0) * 9.0;
        float n = fbm(q + vec2(uTime * 0.25, uTime * 0.1)) + fbm(q * 1.7 - vec2(uTime * 0.2, 0.0));
        float k = pow(max(1.0 - abs(n - 1.0) * 5.0, 0.0), 3.0) * smoothstep(uWaterY + 0.05, uWaterY - 0.1, uv.y);
        c += (c + 0.05) * k * uCaust * 2.0;
    }
    return c * (uGain + uGlowUp * dot(c, vec3(0.3, 0.6, 0.1)));
}
