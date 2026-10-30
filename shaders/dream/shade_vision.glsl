// The machine's reading of a painting: depth, segments, edges, sky and ground, a point cloud.
uniform sampler2D uData;
uniform float uDim, uDepthV, uSegV, uEdge, uSweep, uZone, uZoneT, uPts, uPtD, uAspP2;
vec3 ramp(float x) { return mix(mix(vec3(0.02, 0.01, 0.14), vec3(0.8, 0.1, 0.45), smoothstep(0.0, 0.5, x)), vec3(1.0, 0.86, 0.35), smoothstep(0.45, 1.0, x)); }
vec3 hue_(float h) { return 0.5 + 0.5 * cos(TAU * (h + vec3(0.0, 0.33, 0.67))); }
float Lm(vec2 uv) { return dot(texture(uPaint, uv).rgb, vec3(0.3, 0.6, 0.1)); }
vec3 shade(vec2 uv, vec3 c) {
    float d = texture(uPaint, uv).a;
    vec3 o = c * uDim;
    if (uDepthV > 0.0) o = mix(o, ramp(d) * (0.35 + 0.9 * dot(c, vec3(0.3, 0.6, 0.1)) + 0.2), uDepthV);
    if (uSegV > 0.0) {
        float l = texture(uData, uv).r, sw = smoothstep(uSweep - 0.03, uSweep, 1.0 - uv.y);
        vec2 e = 2.0 / vec2(textureSize(uData, 0));
        float b = step(0.5, abs(texture(uData, uv + vec2(e.x, 0.0)).r - l) + abs(texture(uData, uv + vec2(0.0, e.y)).r - l));
        vec3 f = l < 0.5 ? c * 0.5 : hue_(l * 0.0618) * (0.25 + 1.2 * dot(c, vec3(0.3, 0.6, 0.1)));
        o = mix(o, f + b * vec3(0.9), uSegV * (1.0 - sw));
    }
    if (uEdge > 0.0) {
        vec2 e = 1.4 / vec2(textureSize(uPaint, 0));
        float g = length(vec2(Lm(uv + vec2(e.x, 0.0)) - Lm(uv - vec2(e.x, 0.0)), Lm(uv + vec2(0.0, e.y)) - Lm(uv - vec2(0.0, e.y))));
        float sw = smoothstep(uSweep - 0.015, uSweep, uv.x);
        o = mix(o, c * 0.07 + vec3(0.2, 0.9, 1.0) * smoothstep(0.03, 0.2, g) * 1.7, uEdge * (1.0 - sw));
        o += vec3(0.4, 0.95, 1.0) * exp(-abs(uv.x - uSweep) * 260.0) * uEdge;
    }
    if (uZone > 0.0) {
        float s = 1.0 - smoothstep(uZoneT - 0.02, uZoneT + 0.02, d);
        o = mix(o, o * mix(vec3(1.0, 0.72, 0.42), vec3(0.42, 0.72, 1.0), s) * 1.3, uZone);
        o += vec3(1.0) * uZone * exp(-abs(d - uZoneT) * 240.0) * 0.5;
    }
    if (uPts > 0.0) {
        vec2 g = uv * vec2(uAspP2, 1.0) / uPtD;
        if (length(fract(g) - 0.5) > mix(0.8, 0.26, uPts)) discard;
    }
    return o;
}
