// One split-screen panel over the frame so far: uA = frame, uB = panel content (rendered full-screen,
// centre-cropped to the panel's aspect). blend 0 = opaque panel in a gilded altarpiece frame,
// 1 = superimposition (double exposure, light adds where the base is dark).
uniform sampler2D uA, uB;
uniform vec4 uRect;       // x0, y0, x1, y1 in bottom-up screen uv
uniform float uAlpha;
uniform int uBlend;
uniform float uBorder;

vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec3 a = texture(uA, uv).rgb;
    vec2 sz = uRect.zw - uRect.xy;
    vec2 q = (uv - uRect.xy) / sz;
    if (any(lessThan(q, vec2(0.0))) || any(greaterThan(q, vec2(1.0)))) return a;
    float pa = sz.x * uRes.x / (sz.y * uRes.y), fa = uRes.x / uRes.y;
    vec2 s = pa < fa ? vec2(pa / fa, 1.0) : vec2(1.0, fa / pa);
    vec3 b = texture(uB, 0.5 + (q - 0.5) * s).rgb;
    vec3 col = uBlend == 0 ? mix(a, b, uAlpha) : a + b * uAlpha / (1.0 + a);
    if (uBorder > 0.0) {
        vec2 px = min(q, 1.0 - q) * sz * uRes;
        float d = min(px.x, px.y);
        float bw = uBorder * uRes.y * 0.0035;
        float gutter = 1.0 - smoothstep(bw * 0.6, bw * 0.9, d);
        float gold = smoothstep(bw * 0.6, bw * 0.9, d) * (1.0 - smoothstep(bw * 1.6, bw * 2.0, d));
        col = mix(col, vec3(0.0), gutter * uAlpha);
        col = mix(col, vec3(1.0, 0.72, 0.32) * (0.8 + 0.4 * sin(q.x * 40.0 + q.y * 30.0)), gold * uAlpha);
    }
    return col;
}
