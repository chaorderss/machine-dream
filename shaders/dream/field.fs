// Shared look of every tile: sheet / painting texture → flat colour → soft dot, with fog, simple light and emissive edges.
uniform sampler2D uSheet;
uniform float uPass, uFog, uLightAmt;
uniform vec3 uFogCol, uCamPos, uLightDir;
in vec2 vUV, vL, vCen;
in vec3 vTint, vN, vW;
flat in vec4 vF;
flat in float vEdge;
flat in vec4 vCol;
in float vFace;
out vec4 fragColor;
vec3 samp(vec2 uv, float lod) {
    return vF.w > 0.5 ? (lod < 0.0 ? texture(uPaint, uv).rgb : textureLod(uPaint, uv, 1.5).rgb)
                      : (lod < 0.0 ? texture(uSheet, uv).rgb : textureLod(uSheet, uv, lod).rgb);
}
void main() {
    float r = length(vL);
    if (vF.y > 0.5 && r > 1.0) discard;
    vec3 c = pow(samp(vUV, -1.0), vec3(2.2));
    vec3 m = pow(samp(vCen, 5.0), vec3(2.2));
    c = mix(c, m, abs(vFace) < 0.5 ? 1.0 : vF.x);        // box sides always show the tile's mean colour
    c *= vTint;
    c = mix(c, vCol.rgb, vCol.a);
    float l = 1.0 - uLightAmt + uLightAmt * (0.35 + 0.75 * max(dot(normalize(vN), uLightDir), 0.0));
    c *= l;
    if (vEdge > 0.0) {
        vec2 f = abs(vL);
        c += (vTint + 0.3) * vEdge * smoothstep(0.72, 1.0, max(f.x, f.y)) * 1.2;
    }
    c *= 1.0 + vF.z;
    if (vF.x > 1.5) c = vec3(1.0, 0.62, 0.16) * 0.065;        // flatten 2 = pure limbus gold
    if (vF.y > 0.0) {                                      // dot: gaussian core, no hard rim
        float g = exp(-r * r * 4.5) * smoothstep(1.0, 0.8, r);
        c = mix(c, c * g * 1.6, vF.y);
    }
    if (uFog > 0.0) c = mix(c, uFogCol * (uPass > 0.5 ? 0.0 : 1.0), 1.0 - exp(-length(vW - uCamPos) * uFog));
    if (any(isnan(c))) c = vec3(0.0);
    fragColor = vec4(max(c, 0.0), 1.0);
}
