uniform sampler2D uSrc;
uniform float uWeight;
vec3 render(vec2 fc) { return texture(uSrc, fc / uRes).rgb * uWeight; }
