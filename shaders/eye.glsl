// The reveal: everything so far was a reflection in the cornea of a colossal alien eye.
// uZoom 0 = the screen IS the reflection (seamless hand-off), 1 = whole eye in frame.
uniform sampler2D uInput;
uniform float uZoom;

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float asp = uRes.x / uRes.y;
    float z = exp(mix(log(0.035), 0.0, uZoom));
    vec2 q = p * z;
    float R = 0.42;
    float r = length(q);
    float a = atan(q.y, q.x);

    // cornea reflection of the live input, identity mapping at zoom 0
    vec2 idUV = vec2(p.x / asp, p.y) + 0.5;
    float fe = 1.0 + 0.8 * dot(q, q) / (R * R);
    vec2 coUV = vec2(q.x / asp, q.y) / (R * 1.05) * 0.5 * fe * vec2(asp * 0.62, 1.0) + 0.5;
    float m = smoothstep(0.0, 0.45, uZoom);
    vec3 refl = texture(uInput, mix(idUV, coUV, m)).rgb;

    // iris: radial fibres + fractal crypts, pupil dilates with the music
    float Rp = R * (0.30 + 0.05 * uSpring);
    float fib = vnoise3(vec3(cos(a) * 38.0, sin(a) * 38.0, r * 9.0 - uTime * 0.1));
    float crypt = fbm(vec2(cos(a), sin(a)) * 4.0 + r * 14.0);
    float ir = smoothstep(Rp, Rp + 0.01, r) * smoothstep(R, R - 0.012, r);
    vec3 iris = mix(pal(0.08 + r * 1.5), pal(0.45 + crypt), fib * 0.7) * (0.15 + 0.7 * fib * fib) * (0.3 + crypt);
    iris *= 0.6 + 0.6 * smoothstep(Rp + 0.08, Rp, r);     // collarette glow
    iris += pal(0.9) * exp(-abs(r - R) * 160.0) * 1.2;   // limbal ring
    // sclera / alien tissue
    float vn = fbm(q * 7.0 + vec2(0.0, uTime * 0.02));
    float vein = 1.0 - smoothstep(0.0, 0.025, abs(vn - 0.5));          // thin branching veins
    vec3 tissue = vec3(0.025, 0.008, 0.02) * (0.5 + vn) + pal(0.75) * vein * 0.35 * (0.6 + uHit);
    tissue *= smoothstep(1.6, R, r) * (0.6 + 0.4 * smoothstep(R * 1.25, R, r));
    vec3 eye = r < R ? iris : tissue;

    // reflection strength: total at zoom 0, fresnel-weighted on the cornea afterwards
    float corneaW = (r < R) ? 0.12 + 0.45 * smoothstep(R * 0.3, R, r) : 0.0;
    refl *= mix(1.0, 0.7, m);
    float w = mix(1.0, corneaW, m);
    vec3 col = mix(eye, refl, w);
    if (r < Rp) col = mix(refl * mix(1.0, 0.85, m), col, 0.0);
    // specular window highlight
    vec2 hp = q - vec2(-0.12, 0.13);
    col += vec3(1.0) * 2.5 * smoothstep(0.035, 0.02, length(hp * vec2(1.0, 1.6))) * m;
    return col;
}
