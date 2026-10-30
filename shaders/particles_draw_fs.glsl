in vec3 vCol;
in float vSize;
out vec4 fragColor;
void main() {
    float d = length(gl_PointCoord - 0.5) * 2.0;
    float small = exp(-d * d * 3.5);
    // large discs: flat body with a brighter rim, like real lens bokeh
    float disc = smoothstep(1.0, 0.9, d) * (0.75 + 0.45 * smoothstep(0.55, 0.92, d));
    float k = smoothstep(4.0, 12.0, vSize);
    float a = mix(small, disc, k);
    fragColor = vec4(vCol * a, 1.0);
}
