// Narcissus: above the water the boy leans; below, his reflection is half a second late, and its hand keeps going down.
// The water turns into a round LED mirror, and the face in it slowly becomes the machine's eye.
uniform sampler2D uTexA, uData;           // eye of every painting, boy mask
uniform float uReach, uReachLate, uDeep, uLed, uEyeMix, uAspP, uFit, uZoom, uCY;
const float WATER = 0.435;                // bottom-up v of the waterline
vec2 bend(vec2 uv, float reach) {         // the arms and head lean down towards the water
    float m = texture(uData, uv).r;
    float arm = smoothstep(0.62, 0.45, uv.y);
    return uv + vec2(0.0, reach * 0.05 * m * arm);
}
vec3 lin(vec2 uv) { return pow(texture(uPaint, uv).rgb, vec3(2.2)); }
vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec2 uv = vec2(0.42, uCY) + vec2(p.x / uAspP, p.y) / uZoom;
    if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) return vec3(0.0);
    if (uv.y > WATER) return lin(bend(uv, uReach));
    float d = WATER - uv.y;                                // depth below the line → mirrored height above it
    vec2 ripple = vec2(sin(uv.y * 90.0 + uTime * 1.6), 0.0) * 0.0018 * smoothstep(0.0, 0.2, d);
    vec2 r = vec2(uv.x, WATER + d / (1.0 + uDeep * 0.9 * smoothstep(0.0, 0.3, d))) + ripple;
    vec3 c = lin(bend(r, uReachLate)) * 1.15;
    // the reflected face becomes the eye
    vec2 ec = vec2(0.30, WATER - (0.78 - WATER));
    vec2 eq = (uv - ec) * vec2(uAspP, 1.0) / 0.2;
    float er = length(eq);
    if (uEyeMix > 0.0) {
        vec3 e = pow(texture(uTexA, 0.5 + eq * vec2(0.5 * 9.0 / 16.0, 0.5) * 1.05).rgb, vec3(2.2));
        c = mix(c, e, uEyeMix * smoothstep(1.02, 0.86, er));
    }
    if (uLed > 0.0) {
        float s = mix(0.0075, 0.0042, smoothstep(0.0, 1.0, uLed));
        vec2 g = uv * vec2(uAspP, 1.0) / s;
        vec2 id = floor(g) + 0.5;
        vec3 cell = pow(texture(uPaint, r).rgb, vec3(2.2)) * 1.15;
        cell = mix(cell, c, 0.8);
        float l = dot(cell, vec3(0.3, 0.6, 0.1));
        float dot_ = smoothstep(0.5, 0.42, length(g - id) / (0.45 + 0.5 * sqrt(clamp(l, 0.0, 1.0))));
        float front = smoothstep(uLed * 0.35 - 0.02, uLed * 0.35 + 0.02, d) ;
        float on = smoothstep(0.0, 0.12, uLed);
        c = mix(c, cell * dot_ * 2.2 + vec3(0.02, 0.04, 0.06) * dot_, on * mix(1.0, 1.0, front));
    }
    return c * (1.0 + 0.3 * exp(-d * 90.0));
}
