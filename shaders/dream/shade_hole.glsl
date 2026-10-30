// A painting with a round way through: the convex mirror.
uniform vec2 uHole;
uniform float uHoleR, uAspectP2, uGain;
vec3 shade(vec2 uv, vec3 c) {
    float d = length((uv - uHole) * vec2(uAspectP2, 1.0));
    if (d < uHoleR) discard;
    return c * uGain + vec3(1.0, 0.8, 0.5) * exp(-(d - uHoleR) * 500.0) * 0.8;
}
