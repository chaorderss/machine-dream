// A painting as a displaced sheet: plane height 1, width uAspectP, relief along +z from alpha depth.
in vec2 aUV;
uniform mat4 uVP;
uniform float uAspectP, uReliefZ, uLodD;
uniform vec4 uRegion;       // sub-rect of the painting this sheet covers
out vec2 vUV;
out vec3 vW;
out float vD;
void main() {
    vec2 uv = mix(uRegion.xy, uRegion.zw, aUV);
    float d = textureLod(uPaint, uv, uLodD).a;
    vec3 w = vec3((uv.x - 0.5) * uAspectP, uv.y - 0.5, d * uReliefZ);
    vUV = uv; vW = w; vD = d;
    gl_Position = uVP * vec4(w, 1.0);
}
