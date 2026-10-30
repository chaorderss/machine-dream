// Instanced tile / box field. place() (from a field_*.glsl file) decides where every instance is at this moment.
layout(location = 0) in vec3 aC;
layout(location = 1) in vec3 aN;
in vec4 iA, iB, iC, iD, iE, iF;
uniform mat4 uVP;
uniform float uPass;        // 0 opaque, 1 additive
struct Tile {
    vec3 pos, x, y, z;      // centre, half-extent axes (z = 0: a flat quad)
    vec4 uv;                // texture rect (u0, v0, u1, v1) on the sheet, or on uPaint when hero > 0
    vec3 tint;              // multiplies the texture
    float flatten;          // 0 textured .. 1 one flat colour (the tile's mean)
    float round_;           // 0 rectangle .. 1 soft glowing dot
    float glow;             // emissive gain
    float add;              // draw in the additive pass
    float hero;             // 1: sample uPaint (full resolution) instead of the sheet
    float edge;             // 0 .. 1 bright cell edges
    vec3 col;               // solid colour replacing the texture by `solid` (0..1)
    float solid;
};
vec3 axis(vec3 a, vec3 b) { return normalize(a) * length(b); }
mat3 rotX(float a) { float c = cos(a), s = sin(a); return mat3(1, 0, 0, 0, c, s, 0, -s, c); }
mat3 rotY(float a) { float c = cos(a), s = sin(a); return mat3(c, 0, -s, 0, 1, 0, s, 0, c); }
mat3 rotZ(float a) { float c = cos(a), s = sin(a); return mat3(c, s, 0, -s, c, 0, 0, 0, 1); }
