// Corridor beyond the mirror. iA = side, z, along, half size; iB = sheet rect; iC = aspect, seed
uniform float uCamZ_;
#define WIDE 0.34
#define TALL 0.26
void place(inout Tile T) {
    float side = iA.x, z = iA.y, off = iA.z, s = iA.w;
    vec3 n, r, u = vec3(0.0, 1.0, 0.0);
    if (side < 0.5) { T.pos = vec3(-WIDE, off, z); r = vec3(0.0, 0.0, -1.0); }
    else if (side < 1.5) { T.pos = vec3(WIDE, off, z); r = vec3(0.0, 0.0, 1.0); }
    else if (side < 2.5) { T.pos = vec3(off * 1.3, TALL, z); r = vec3(1.0, 0.0, 0.0); u = vec3(0.0, 0.0, -1.0); }
    else { T.pos = vec3(off * 1.3, -TALL, z); r = vec3(1.0, 0.0, 0.0); u = vec3(0.0, 0.0, 1.0); }
    T.x = r * s * iC.x; T.y = u * s;
    T.uv = iB;
    T.edge = 0.35;
    T.tint = vec3(0.95);
}
