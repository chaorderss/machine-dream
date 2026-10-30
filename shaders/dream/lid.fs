#version 430
// The eyelids: black everywhere outside an almond of half height uA.
uniform float uA;
uniform vec2 uRes;
out vec4 fragColor;
void main() {
    vec2 p = (gl_FragCoord.xy - 0.5 * uRes) / uRes.y;
    float h = uA * max(1.0 - pow(p.x / 1.25, 2.0), 0.0);
    float m = uA <= 0.001 ? 1.0 : smoothstep(h - 0.012, h + 0.012, abs(p.y));
    fragColor = vec4(0.0, 0.0, 0.0, m);
}
