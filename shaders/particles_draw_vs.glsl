// Bokeh particles: point size = circle of confusion, energy-conserving brightness.
in vec4 in_pos;
uniform mat4 uViewProj;
uniform vec3 uCamPos;
uniform float uFocus, uAperture, uPxScale, uBright, uCollapse;
out vec3 vCol;
out float vSize;

void main() {
    gl_Position = uViewProj * vec4(in_pos.xyz, 1.0);
    float seed = in_pos.w;
    float dist = max(length(in_pos.xyz - uCamPos), 0.05);
    float coc = uAperture * abs(1.0 / dist - 1.0 / uFocus) * 60.0;
    float hero = step(0.994, hash11(seed * 5.3));            // 0.6% are big lens-bokeh lights
    float size = (1.0 + 1.4 * hash11(seed * 91.7) + coc * hero * 2.5) * uPxScale;
    size = clamp(size, 1.0, 140.0 * uPxScale);
    gl_PointSize = size;
    vSize = size / uPxScale;
    float tw = 0.65 + 0.35 * sin(uTime * (0.7 + 2.0 * hash11(seed * 13.1)) + seed * 40.0);
    float energy = mix(0.18, 3.0, hero) * 4.0 / max(vSize * vSize, 4.0) + hero * 0.05;
    vec3 c = pal(hash11(seed * 3.7) * 0.7 + 0.1 * uCentroid + 0.04 * uStep);
    vCol = c * uBright * tw * energy * (0.7 + 0.6 * uHigh) * (1.0 - 0.7 * uCollapse);
}
