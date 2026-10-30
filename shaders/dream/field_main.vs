out vec2 vUV, vL, vCen;
out vec3 vTint, vN, vW;
flat out vec4 vF;           // flatten, round, glow, hero
flat out float vEdge;
flat out vec4 vCol;
out float vFace;
void main() {
    Tile T;
    T.pos = vec3(0.0); T.x = vec3(1.0, 0.0, 0.0); T.y = vec3(0.0, 1.0, 0.0); T.z = vec3(0.0);
    T.uv = vec4(0.0, 0.0, 1.0, 1.0); T.tint = vec3(1.0);
    T.flatten = 0.0; T.round_ = 0.0; T.glow = 0.0; T.add = 0.0; T.hero = 0.0; T.edge = 0.0; T.col = vec3(0.0); T.solid = 0.0;
    place(T);
    if (abs(T.add - uPass) > 0.5) { gl_Position = vec4(2.0, 2.0, 2.0, 1.0); return; }
    vec3 w = T.pos + T.x * aC.x + T.y * aC.y + T.z * aC.z;
    vW = w;
    vL = aC.xy;
    vUV = mix(T.uv.xy, T.uv.zw, aC.xy * 0.5 + 0.5);
    vCen = 0.5 * (T.uv.xy + T.uv.zw);
    vTint = T.tint;
    vF = vec4(T.flatten, T.round_, T.glow, T.hero);
    vEdge = T.edge;
    vCol = vec4(T.col, T.solid);
    vFace = aN.z;
    float zz = dot(T.z, T.z);
    vN = normalize(T.x * aN.x / max(dot(T.x, T.x), 1e-9) + T.y * aN.y / max(dot(T.y, T.y), 1e-9)
                   + (zz > 0.0 ? T.z * aN.z / zz : cross(T.x, T.y) * aN.z));
    gl_Position = uVP * vec4(w, 1.0);
}
