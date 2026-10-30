// Dürer's solid: each face a painting; the faces keep subdividing, every triangle its own painting; one tiny triangle holds a whole sky.
uniform sampler2D uSheet, uTexA;
uniform float uLevel, uStar;
uniform vec3 uFaceTgt;      // face uv u, v, id of the triangle that holds the stars
in vec3 vF, vN, vW;
out vec4 fragColor;
vec3 tile(float id, vec2 l) {
    float n = floor(hash11(id * 0.77 + 3.1) * 56.0);
    vec2 base = (vec2(mod(n, 8.0), floor(n / 8.0)) + 0.5) / 8.0;
    return pow(texture(uSheet, base + (l - 0.5) * 0.045).rgb, vec3(2.2));
}
vec3 lev(float level, out float inTgt) {
    float N = pow(2.0, level);
    vec2 g = vF.xy * N, i = floor(g), f = fract(g);
    float up = step(1.0, f.x + f.y);
    vec2 l = up > 0.5 ? 1.0 - f : f;
    float id = dot(i, vec2(17.0, 311.0)) + up * 7.0 + vF.z * 1013.0 + level * 91.0;
    vec3 c = tile(id, l);
    float e = min(min(l.x, l.y), 1.0 - l.x - l.y);
    c *= 0.72 + 0.28 * smoothstep(0.0, 0.05, e);
    vec2 tg = uFaceTgt.xy * N, ti = floor(tg), tf = fract(tg);
    inTgt = (abs(vF.z - uFaceTgt.z) < 0.5 && i == ti && up == step(1.0, tf.x + tf.y)) ? 1.0 : 0.0;
    return c;
}
void main() {
    float a, b;
    vec3 c = mix(lev(floor(uLevel), a), lev(floor(uLevel) + 1.0, b), smoothstep(0.3, 0.7, fract(uLevel)));
    float t = max(a, b);
    if (t > 0.5 && uStar > 0.0) c = mix(c, pow(texture(uTexA, vF.xy * 22.0 + 0.3).rgb, vec3(2.2)) * 2.4, uStar);
    float l = 0.35 + 0.85 * max(dot(normalize(vN), normalize(vec3(0.4, 0.7, 0.6))), 0.0);
    fragColor = vec4(c * mix(l, 1.0, uStar * t), 1.0);
}
