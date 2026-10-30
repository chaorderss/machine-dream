uniform float uGain;
vec3 shade(vec2 uv, vec3 c) { return c * uGain; }
