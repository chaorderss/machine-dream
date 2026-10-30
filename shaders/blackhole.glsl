// Gravitational lensing of the live input + inward-spiralling feedback ("spaghettification").
uniform sampler2D uInput;
uniform float uHoleR;
uniform float uSpin;
uniform float uSpaghetti;
uniform float uDisk;

vec2 toUV(vec2 p, float asp) { return vec2(p.x / asp, p.y) + 0.5; }
vec2 mirrorUV(vec2 uv) { return 1.0 - abs(1.0 - mod(uv, 2.0)); }

vec3 render(vec2 fc) {
    float asp = uRes.x / uRes.y;
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float r = length(p);
    float Rs = max(uHoleR, 1e-4);
    vec2 dir = p / max(r, 1e-4);
    // thin-lens point mass: beta = theta - thetaE^2/theta (inside the ring the image flips)
    float thE = Rs * 1.9;
    vec2 src = p - dir * thE * thE / max(r, 1e-3);
    src = rot(uSpin * Rs / (r + 0.02)) * src;
    vec3 lensed = texture(uInput, mirrorUV(toUV(src, asp))).rgb;

    float k = uDt * 60.0;
    float omega = uSpin * 0.025 * k / (pow(r, 1.5) + 0.04);
    vec2 fp = rot(-omega) * p * (1.0 + 0.015 * k * Rs / (r + 0.03));
    vec3 prev = min(texture(uPrev, toUV(fp, asp)).rgb, vec3(3.0)) * pow(0.9, k);
    vec3 col = lensed * (1.0 - 0.5 * uSpaghetti) + prev * uSpaghetti * 0.55;

    // accretion disk (tilted), doppler-brightened on the approaching side
    vec2 dp = rot(0.35) * p;
    dp.y *= 3.2;
    float dr = length(dp);
    float band = smoothstep(Rs * 1.5, Rs * 2.2, dr) * smoothstep(Rs * 5.0, Rs * 2.4, dr);
    float swirl = fbm(vec2(atan(dp.y, dp.x) * 3.0 - uTime * 1.5 / max(dr, 0.05), dr * 18.0));
    float dop = 1.0 + 0.8 * dp.x / max(dr, 1e-3);
    col += mix(vec3(1.0, 0.55, 0.2), pal(0.1 + swirl), 0.4) * band * swirl * dop * 0.8 * uDisk * (0.6 + uRms);
    // photon ring + horizon
    col += pal(0.05 + uTime * 0.02) * exp(-abs(r - Rs * 1.5) * 220.0) * 1.2 * uDisk;
    col *= smoothstep(Rs * 0.97, Rs * 1.04, r);
    return col;
}
