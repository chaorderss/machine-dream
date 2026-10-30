// Living mathematics: reaction-diffusion skin lit as a 3D membrane with volumetric shafts.
// Violin onsets (high band) make the tendrils twitch.
uniform sampler2D uRD;
uniform float uWarp;
uniform float uPaintTint;   // 0..1: the creature wears the colours of the painting it grew out of
uniform vec4 uView;

float B(vec2 uv) { return texture(uRD, uv).g; }

vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    // slow breathing zoom around the centre
    vec2 cuv = 0.5 + (uv - 0.5) * (0.92 - 0.03 * uSpring);
    vec2 w = vec2(fbm(p * 2.5 + uTime * 0.15), fbm(p * 2.5 + 7.3 - uTime * 0.12)) - 0.5;
    float twitch = exp(-uHiAge * 7.0);
    vec2 dir = vec2(cos(hash11(uHiCount) * TAU), sin(hash11(uHiCount) * TAU));
    vec2 suv = cuv + w * (0.01 + 0.03 * uWarp) + dir * twitch * 0.006 * (fbm(p * 6.0) - 0.3);
    float h = B(suv);
    vec2 px = 1.5 / vec2(textureSize(uRD, 0));
    float hx = B(suv + vec2(px.x, 0)) - B(suv - vec2(px.x, 0));
    float hy = B(suv + vec2(0, px.y)) - B(suv - vec2(0, px.y));
    vec3 n = normalize(vec3(-hx * 14.0, -hy * 14.0, 1.0));
    vec3 L = normalize(vec3(0.5 * cos(uTime * 0.2), 0.5 * sin(uTime * 0.2), 0.7));
    float dif = max(dot(n, L), 0.0);
    float spe = pow(max(dot(reflect(-L, n), vec3(0, 0, 1)), 0.0), 28.0);
    vec3 skin = pal(h * 0.9 + 0.05 * uTime * 0.2 + 0.3 * length(p) + 0.05 * uStep);
    if (uPaintTint > 0.0) {
        vec2 puv = uView.xy + vec2(p.x / uView.w, p.y) * uView.z;
        vec3 pc = pow(texture(uPaint, puv).rgb, vec3(2.2)) * 1.8;
        skin = mix(skin, pc * (0.6 + 0.8 * h), uPaintTint);
    }
    vec3 col = vec3(0.012, 0.0, 0.03);
    float cav = smoothstep(0.05, 0.35, h);                   // valleys fall into darkness
    col += skin * cav * (0.05 + 1.3 * dif * dif) + vec3(1.0, 0.9, 1.0) * spe * cav * 0.9;
    // bioluminescent veins along pattern fronts
    float vein = smoothstep(0.12, 0.25, h) * (1.0 - smoothstep(0.25, 0.4, h));
    col += pal(0.65 + h) * vein * (0.5 + 0.45 * uHit + 0.35 * twitch);
    // volumetric shafts: march toward a wandering light, membrane occludes
    vec2 lc = vec2(0.5 + 0.25 * sin(uTime * 0.11), 0.55 + 0.2 * cos(uTime * 0.13));
    vec2 st = (lc - cuv) / 20.0;
    vec2 sp = cuv;
    float shaft = 0.0;
    for (int i = 0; i < 20; i++) { sp += st; shaft += 1.0 - smoothstep(0.1, 0.3, B(sp)); }
    shaft /= 20.0;
    col += pal(0.15) * pow(shaft, 4.0) * 0.5 * (0.4 + uRms) * smoothstep(1.2, 0.0, length(uv - lc));
    return col;
}

