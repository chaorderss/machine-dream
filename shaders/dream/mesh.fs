in vec2 vUV;
in vec3 vW;
in float vD;
uniform vec3 uCamPos, uFogCol;
uniform float uFog;
out vec4 fragColor;
void main() {
    vec4 s = texture(uPaint, vUV);
    vec3 c = shade(vUV, pow(s.rgb, vec3(2.2)));
    if (uFog > 0.0) c = mix(c, uFogCol, 1.0 - exp(-length(vW - uCamPos) * uFog));
    if (any(isnan(c))) c = vec3(0.0);
    fragColor = vec4(max(c, 0.0), 1.0);
}
