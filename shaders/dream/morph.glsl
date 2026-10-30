// Latent mutation, without any generator: DINOv2 patch correspondences give a smooth field saying where each part of B
// lives in A (cloud ↔ wave ↔ hair); both paintings flow along it towards each other and only then change places.
uniform sampler2D uTexA, uTexB, uFlow;   // uFlow: rg = A→B displacement at B's uv, ba = B→A displacement at A's uv
uniform float uM, uAspA, uAspB, uSwirl;
vec2 cover(vec2 p, float pa) { float a = uRes.x / uRes.y; float s = min(1.0, pa / a); return 0.5 + vec2(p.x / pa, p.y) * s; }
vec3 lin(sampler2D t, vec2 uv) { return pow(texture(t, clamp(uv, 0.0, 1.0)).rgb, vec3(2.2)); }
vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float m = uM, w = sin(PI * m);
    vec2 ua = cover(p, uAspA), ub = cover(p, uAspB);
    vec2 sw = (vec2(fbm(p * 2.2 + uTime * 0.25), fbm(p * 2.2 + 5.0 - uTime * 0.21)) - 0.5) * uSwirl * w;
    vec4 F = texture(uFlow, ub), G = texture(uFlow, ua);
    vec3 a = lin(uTexA, ua + F.xy * m + sw), b = lin(uTexB, ub + G.zw * (1.0 - m) - sw);
    float n = 0.5 * fbm(p * 3.0 + 2.0) + 0.5 * vnoise(p * 9.0);
    float l = dot(b, vec3(0.3, 0.6, 0.1));
    float th = mix(1.15, -0.15, m);
    float k = smoothstep(th - 0.12, th + 0.12, n * 0.7 + 0.3 * clamp(l * 1.6, 0.0, 1.0));
    vec3 c = mix(a, b, k);
    return c + pal(0.15) * exp(-abs(n * 0.7 + 0.3 * clamp(l * 1.6, 0.0, 1.0) - th) * 22.0) * w * 0.35;
}
