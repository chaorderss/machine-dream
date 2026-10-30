// iA block centre on the wall, block centre on the similarity map; iB eye x, y, offset inside the block
// iC uv rect; iD eye colour, painting; iE half size, cell seed, block seed, block scale on the map
uniform float uA, uB, uC, uFuse, uBeat;
vec2 curl(vec2 p, float t) {
    float e = 0.2;
    float a = vnoise(p + vec2(0.0, e) + t), b = vnoise(p - vec2(0.0, e) + t), c = vnoise(p + vec2(e, 0.0) + t), d = vnoise(p - vec2(e, 0.0) + t);
    return vec2(a - b, d - c) / (2.0 * e);
}
void place(inout Tile T) {
    float s = iE.y, bs = iE.z, b2 = fract(bs * 37.7), b3 = fract(bs * 113.1);
    float pid = iD.w;
    float t = uTime;
    // 1 every block breaks free of its painting and turns (quarter turns, each on its own moment)
    float a = smoothstep(bs * 0.55, bs * 0.55 + 0.45, uA);
    float q = floor(b2 * 4.0) * 1.5708 + (b3 - 0.5) * 0.5;
    // 2 blocks fly to whatever looks like them
    float b = smoothstep(0.65 * b3, 0.65 * b3 + 0.35, uB);
    b = b * b * (3.0 - 2.0 * b);
    // 3 the cells leave their blocks and close on the eye
    float c = smoothstep(0.6 * s, 0.6 * s + 0.4, uC);
    c = 1.0 - pow(1.0 - c, 3.0);
    vec2 cen = mix(iA.xy, iA.zw, b);
    vec2 fl = curl(cen * 0.11, t * 0.17) * 2.6 * a * (1.0 - b) + curl(cen * 0.05, t * 0.11 + 7.0) * 2.2 * uFuse;
    float spin = q * a + (1.0 - 2.0 * step(0.5, b2)) * 6.283 * b * (1.0 - b) * 2.0;
    float sc = mix(1.0, iE.w, b) * (1.0 + 0.9 * uFuse * b3) * (1.0 + 0.25 * uBeat * a * (1.0 - uFuse));
    vec2 off = rot(spin) * iB.zw * sc;
    float scatter = 0.18 * (1.0 - c);                                 // the grid of a block opens up as it flies
    off *= 1.0 + scatter * sin(3.14159 * a) * (1.0 - b);
    vec2 p = cen + fl + off;
    float z = (b3 - 0.5) * (9.0 * a * (1.0 - b) + 5.0 * uFuse);
    p = mix(p, iB.xy, c);
    z *= 1.0 - c;
    float h = mix(iE.x * 1.08 * sc, 0.0222, c);
    float ang = spin * (1.0 - c);
    T.pos = vec3(p, z);
    T.x = vec3(rot(ang) * vec2(h, 0.0), 0.0); T.y = vec3(rot(ang) * vec2(0.0, h), 0.0);
    T.uv = vec4(iC.xy, iC.xy + iC.zw);
    T.col = iD.rgb;
    T.solid = c;
}
