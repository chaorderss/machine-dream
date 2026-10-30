// Recursive reality: painting A holds B in a small window, B holds C. uF 0..1 zooms from A into that window; when it has
// filled the screen the event steps along its chain. The window can be an eye (0), a square cell or brick (1).
uniform sampler2D uTexA, uTexB, uTexC;
uniform vec2 uAA, uAB, uAC;      // anchors (uv, bottom-up)
uniform vec3 uAsp;               // painting aspects
uniform vec2 uR;                 // window radius of A, B (fractions of painting height)
uniform float uF, uShape, uPix, uRimK, uSpin;
vec3 lin(sampler2D t, vec2 uv) { return pow(texture(t, 1.0 - abs(1.0 - mod(uv, 2.0))).rgb, vec3(2.2)); }
float win(vec2 q, float r, out float rim) {
    float d = uShape > 0.5 ? max(abs(q.x), abs(q.y)) : length(q);
    rim = exp(-abs(d - r) / (r * 0.05));
    return smoothstep(r, r * (uShape > 0.5 ? 0.985 : 0.86), d);
}
vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float Z = pow(0.5 / uR.x, uF);
    vec2 q = rot(uSpin * uF) * p / Z;
    vec2 ua = uAA + q / vec2(uAsp.x, 1.0);
    vec3 c;
    if (uPix > 0.0) {                                    // the outer painting is a grid: each cell one colour
        float s = 2.0 * uR.x;
        vec2 qq = (floor(q / s + 0.5)) * s;
        vec2 f = (q / s + 0.5) - floor(q / s + 0.5);
        vec3 cell = lin(uTexA, uAA + qq / vec2(uAsp.x, 1.0));
        cell *= 0.82 + 0.18 * smoothstep(0.0, 0.06, min(min(f.x, f.y), min(1.0 - f.x, 1.0 - f.y)));
        c = mix(lin(uTexA, ua), cell, uPix);
    } else c = lin(uTexA, ua);
    float rim;
    float k = win(q, uR.x, rim);
    vec2 q2 = q / (2.0 * uR.x);
    vec3 b = lin(uTexB, uAB + q2 / vec2(uAsp.y, 1.0));
    float rim2, k2 = win(q2, uR.y, rim2);
    vec2 q3 = q2 / (2.0 * uR.y);
    b = mix(b, lin(uTexC, uAC + q3 / vec2(uAsp.z, 1.0)), k2);
    b += vec3(1.0, 0.8, 0.5) * rim2 * 0.5 * uRimK;
    c = mix(c, b, k);
    return c + vec3(1.0, 0.82, 0.55) * rim * 0.9 * uRimK;
}
