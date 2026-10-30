// Final grade: bloom, chromatic aberration, ACES, centroid colour grade, fake-glitch tear,
// title overlay, vignette, grain/dither. Output is flipped so readback is top-down.
uniform sampler2D uHDR, uBloom, uTitle, uTitle2, uOverlay;
uniform float uOverlayOn;
uniform float uTitleAlpha2, uTDecode2, uTSeed2;   // second title layer (HUD readout)
uniform vec4 uTitleRect2;
uniform float uExposure, uBloomStr, uCA, uGrain, uVignette, uGrade, uTear, uTitleAlpha;
uniform float uGradeHue;  // smoothed spectral centroid
uniform float uSat;       // saturation / vibrance
uniform float uHue;       // hue rotation (radians)
uniform float uInvert;    // 0..1 negative flash on tutti
uniform float uTealGold;  // unified teal shadows / gold highlights grade over all paintings
uniform vec4 uTitleRect;  // title texture placement, top-down screen uv (x0, y0, x1, y1)
uniform float uTCell;     // titles seen like the picture: pixel cell (px) pulsing with the mosaic; 0 = sharp
uniform float uTDecode;   // 0..1: cells switch on in random order (decode in / out)
uniform float uTSeed;     // per-title seed for that order
uniform vec4 uTFlow;      // the picture's light / colour flow: amount L, amount C, speed, scale

vec3 titleColour(sampler2D T, float decode, float seed, vec2 tv, vec2 tr0, vec2 tr1, out float a) {
    vec2 px = tv * uRes;                                          // top-down pixels
    float s = max(uTCell, 1.0) * (1.0 + 7.0 * (1.0 - decode) * (1.0 - decode));
    vec2 id = floor(px / s), cen = (id + 0.5) * s;
    vec2 tr = (cen / uRes - tr0) / (tr1 - tr0);
    vec4 ti = (all(greaterThanEqual(tr, vec2(0.0))) && all(lessThan(tr, vec2(1.0)))) ? texture(T, tr) : vec4(0.0);
    float r = hash12(id + fract(seed * 0.137) * 731.0);
    float on = smoothstep(r - 0.04, r + 0.04, decode * 1.12 - 0.06);
    float glint = exp(-abs(r - decode) * 30.0) * (1.0 - decode * decode) * step(0.02, ti.a);
    // LED-matrix grout once the cells are big enough to see
    vec2 f = abs(px - cen) / s;
    float grout = mix(1.0, smoothstep(0.5, 0.36, max(f.x, f.y)), smoothstep(2.5, 5.0, s));
    // the picture's flow runs through the letters as light
    vec2 c = (cen - 0.5 * uRes) / uRes.y * uTFlow.w;
    float ft = uTime * uTFlow.z;
    float band = sin(dot(c, vec2(0.8, 0.6)) * 2.2 - 1.7 * ft);
    vec3 col = ti.rgb * (1.0 + 0.5 * uTFlow.x * band) * grout;
    col = mix(col, col * vec3(0.85, 1.0, 1.12), clamp(uTFlow.y * 3.0, 0.0, 0.6) * (0.5 + 0.5 * band));
    a = ti.a * on;
    return col + vec3(0.45, 0.9, 1.0) * glint * 1.4;
}

vec3 hueRotate(vec3 c, float a) {
    const vec3 k = vec3(0.57735);
    float ca = cos(a);
    return c * ca + cross(k, c) * sin(a) + k * dot(k, c) * (1.0 - ca);
}

vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }

vec3 render(vec2 fc) {
    vec2 tv = fc / uRes;                 // title texture is stored top-down
    vec2 uv = vec2(tv.x, 1.0 - tv.y);
    if (uTear > 0.0) {
        float tick = floor(uTime * 12.0);
        float rows = mix(14.0, 48.0, hash11(tick));
        float row = floor(uv.y * rows);
        if (hash12(vec2(row, tick)) < 0.4 * uTear)
            uv.x += (hash12(vec2(row + 7.0, tick)) - 0.5) * 0.18 * uTear;
        uv = fract(uv);
    }
    vec2 dc = uv - 0.5;
    float ca = uCA * 0.006 + uTear * 0.012;
    vec3 c;
    c.r = texture(uHDR, uv - dc * ca).r;
    c.g = texture(uHDR, uv).g;
    c.b = texture(uHDR, uv + dc * ca).b;
    c += texture(uBloom, uv).rgb * uBloomStr;
    c *= uExposure;
    c = max(hueRotate(c, uHue), 0.0);
    float lh = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = max(mix(vec3(lh), c, uSat), 0.0);
    c = aces(c);
    // split-tone by timbre: low centroid → deep-sea blue shadows / black-gold highlights,
    // high centroid → violet shadows / white-neon highlights
    float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
    vec3 sh = mix(vec3(-0.01, 0.01, 0.05), vec3(0.04, -0.01, 0.07), uGradeHue);
    vec3 hi = mix(vec3(0.07, 0.03, -0.05), vec3(0.03, 0.03, 0.06), uGradeHue);
    c = max(c + uGrade * (4.0 * lum * (1.0 - lum) * (1.0 - lum) * sh + lum * lum * hi), 0.0);   // never lifts pure black
    // one film look for 60 paintings from 6 centuries: teal shadows, gold highlights (black stays black)
    float l2 = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(c, c * mix(vec3(0.86, 1.01, 1.08), vec3(1.05, 0.99, 0.90), smoothstep(0.08, 0.65, l2)), uTealGold);
    // vignette
    c *= 1.0 - uVignette * smoothstep(0.35, 0.95, length(dc * vec2(uRes.x / uRes.y, 1.0)) * 0.9);
    c = mix(c, vec3(1.0) - min(c, vec3(1.0)), uInvert);
    c = hud(fc, c);
    if (uOverlayOn > 0.5) {
        vec4 ov = texture(uOverlay, vec2(fc.x, uRes.y - fc.y) / uRes);
        c = c * (1.0 - ov.a) + ov.rgb;
    }
    // title / HUD label
    vec2 tr = (tv - uTitleRect.xy) / (uTitleRect.zw - uTitleRect.xy);
    vec2 tr2 = (tv - uTitleRect2.xy) / (uTitleRect2.zw - uTitleRect2.xy);
    if (all(greaterThanEqual(tr2, vec2(-0.05))) && all(lessThan(tr2, vec2(1.05))) && uTitleAlpha2 > 0.0) {
        float ta2;
        vec3 tc2 = titleColour(uTitle2, uTDecode2, uTSeed2, tv, uTitleRect2.xy, uTitleRect2.zw, ta2);
        c = mix(c, tc2, ta2 * uTitleAlpha2);
    }
    if (all(greaterThanEqual(tr, vec2(-0.05))) && all(lessThan(tr, vec2(1.05))) && uTitleAlpha > 0.0) {
        if (uTCell > 0.0) {
            float ta;
            vec3 tc = titleColour(uTitle, uTDecode, uTSeed, tv, uTitleRect.xy, uTitleRect.zw, ta);
            c = mix(c, tc, ta * uTitleAlpha);
        } else if (all(greaterThanEqual(tr, vec2(0.0))) && all(lessThan(tr, vec2(1.0)))) {
            vec4 ti = texture(uTitle, tr);
            c = mix(c, ti.rgb, ti.a * uTitleAlpha);
        }
    }
    c = pow(c, vec3(1.0 / 2.2));
    // grain + dither (kills 8-bit banding in dark gradients)
    float g = hash12(fc + fract(uTime * 13.7) * 1000.0) - 0.5;
    c += g * (uGrain * 0.08 + 1.5 / 255.0);
    return c;
}
