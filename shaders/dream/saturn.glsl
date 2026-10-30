// Saturn watches the camera. His eyes turn to follow it, his brushstrokes move like muscle.
uniform sampler2D uData, uTexA;
uniform float uZ, uAspP, uMuscle, uMachine, uSplitV, uEyeMix;
uniform vec2 uC, uLook;
vec2 eyeWarp(vec2 uv, vec2 e, float r) {
    vec2 d = (uv - e) * vec2(uAspP, 1.0);
    float k = smoothstep(r, r * 0.25, length(d));
    return uv - k * uLook / vec2(uAspP, 1.0);
}
vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    bool machine = false;
    if (uSplitV > 0.5) {                                   // above: the painting. Below: what the machine sees
        machine = p.y < 0.0;
        p.y += machine ? 0.25 : -0.25;
        if (abs(p.y) > 0.238) return vec3(0.0);
    }
    vec2 uv = uC + vec2(p.x / uAspP, p.y) / uZ;
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return vec3(0.0);
    float m = texture(uData, uv).r;
    vec2 q = uv * vec2(uAspP, 1.0) * 7.0;
    float n = fbm(q + vec2(uTime * 0.2, 0.0));
    vec2 g = vec2(fbm(q + vec2(0.1, 0.0)) - n, fbm(q + vec2(0.0, 0.1)) - n);
    uv += g * 0.11 * uMuscle * m * sin(n * 22.0 + uTime * 3.2);
    uv = eyeWarp(uv, vec2(0.325, 0.81), 0.05);
    uv = eyeWarp(uv, vec2(0.415, 0.81), 0.05);
    vec3 c = pow(texture(uPaint, uv).rgb, vec3(2.2));
    if (machine) {
        vec2 e = vec2(0.002, 0.0);
        float g = length(vec2(dot(texture(uPaint, uv + e.xy).rgb - texture(uPaint, uv - e.xy).rgb, vec3(0.33)),
                              dot(texture(uPaint, uv + e.yx).rgb - texture(uPaint, uv - e.yx).rgb, vec3(0.33))));
        c = c * vec3(0.3, 0.6, 0.65) + vec3(0.2, 0.9, 1.0) * smoothstep(0.05, 0.3, g) * 0.8;
    }
    if (uEyeMix > 0.0) {                                   // for a moment the machine's eye sits in his
        vec2 eq = (uv - vec2(0.325, 0.81)) * vec2(uAspP, 1.0) / 0.034;
        vec3 ec = pow(texture(uTexA, 0.5 + eq * vec2(0.5 * 9.0 / 16.0, 0.5) * 1.1).rgb, vec3(2.2)) * 1.5;
        c = mix(c, ec, uEyeMix * smoothstep(1.0, 0.75, length(eq)));
    }
    return c * (1.0 + 0.5 * uMuscle * m * max(sin(n * 22.0 + uTime * 3.2), 0.0));
}
