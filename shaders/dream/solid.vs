in vec3 aP, aN;
in vec3 aF;       // face uv, face id
uniform mat4 uVP, uM;
out vec3 vF, vN, vW;
void main() { vec4 w = uM * vec4(aP, 1.0); vF = aF; vN = mat3(uM) * aN; vW = w.xyz; gl_Position = uVP * w; }
