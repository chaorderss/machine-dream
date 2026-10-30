// The painted arm stays paint until its cell's moment has come; then only the clean plate is left behind the voxels.
uniform sampler2D uTexA, uData;
uniform float uS;
vec3 shade(vec2 uv, vec3 c) {
    c = (uS * 1.3 - texture(uData, uv).r) / 0.28 > 0.0 ? pow(texture(uTexA, uv).rgb, vec3(2.2)) * 0.62 : c;
    return c * mix(1.0, 0.22, smoothstep(0.12, 0.9, uS));        // the wall goes dark so the machine's hand can be light
}
