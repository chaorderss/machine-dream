// Transform-feedback particle update: explosion → curl-noise drift → optional collapse.
in vec4 in_pos;   // xyz, seed
in vec4 in_vel;   // xyz, spare
out vec4 out_pos;
out vec4 out_vel;
uniform float uFlow;
uniform float uCollapse;
uniform float uDrag;

vec3 n3(vec3 p) { return vec3(vnoise3(p), vnoise3(p + vec3(31.4, 17.2, 9.1)), vnoise3(p + vec3(-7.3, 41.7, 23.9))); }
vec3 curl(vec3 p) {
    const float e = 0.12;
    vec3 dx = vec3(e, 0, 0), dy = vec3(0, e, 0), dz = vec3(0, 0, e);
    vec3 x0 = n3(p - dx), x1 = n3(p + dx), y0 = n3(p - dy), y1 = n3(p + dy), z0 = n3(p - dz), z1 = n3(p + dz);
    return vec3((y1.z - y0.z) - (z1.y - z0.y), (z1.x - z0.x) - (x1.z - x0.z), (x1.y - x0.y) - (y1.x - y0.x)) / (2.0 * e);
}

void main() {
    vec3 p = in_pos.xyz, v = in_vel.xyz;
    float dt = uDt;
    vec3 flow = curl(p * 0.35 + vec3(0.0, 0.0, uTime * 0.04)) * uFlow;
    v = mix(v, flow, 1.0 - exp(-dt * uDrag));
    float c = uCollapse;
    v = mix(v, -p * 2.5, 1.0 - exp(-dt * 5.0 * c * c));
    p += v * dt;
    p = mix(p, vec3(0.0), 1.0 - exp(-dt * 6.0 * c * c * c));
    out_pos = vec4(p, in_pos.w);
    out_vel = vec4(v, in_vel.w);
}
