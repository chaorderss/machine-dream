// IRIS-01, the protagonist: a small chrome probe with one glowing lens (the machine's eye), an orbit ring and a
// light trail. It is drawn over the finished HDR frame and mirrors it in its chrome, so it lives inside the
// painting it flies through. State: iris colour, glow, golden overheating cracks, red organic veins.
uniform sampler2D uA;
uniform vec4 uProbe;        // x, y (bottom-up screen uv), radius (fraction of screen height), alpha
uniform vec2 uLook;         // where the lens points, -1..1 (x right, y up)
uniform vec3 uIris;
uniform float uGlow, uCrack, uVein, uRingA;
uniform float uSpark;      // 1 = no probe, just a point of light (radius = core size)
uniform vec3 uTrail[8];     // past positions x, y, r (most recent first)

float segDist(vec2 p, vec2 a, vec2 b) {
    vec2 ab = b - a;
    float h = clamp(dot(p - a, ab) / max(dot(ab, ab), 1e-8), 0.0, 1.0);
    return length(p - a - ab * h);
}

vec3 env(vec2 uv) {          // soft environment lookup from the frame itself
    vec3 c = vec3(0.0);
    for (int i = 0; i < 5; i++) {
        float a = float(i) * 1.2566;
        c += texture(uA, clamp(uv + vec2(cos(a), sin(a)) * 0.012, 0.0, 1.0)).rgb;
    }
    return c / 5.0;
}

vec3 render(vec2 fc) {
    vec2 uv = fc / uRes;
    vec3 col = texture(uA, uv).rgb;
    float A = uProbe.w;
    if (A <= 0.001) return col;
    float asp = uRes.x / uRes.y;
    vec2 c = uProbe.xy;
    float R = max(uProbe.z, 1e-4);
    vec2 p = (uv - c) * vec2(asp, 1.0);
    float glow = uGlow * (0.85 + 0.5 * uHit);
    if (uSpark > 0.5) {      // a soft point of light with a faint four-point glint, breathing slowly
        float d = length(p) / R;
        float br = 0.85 + 0.15 * sin(uTime * 2.3);
        float g = exp(-d * d * 1.5) * 2.5 + exp(-d * 0.9) * 0.35
                + 0.25 * exp(-abs(p.y) / R * 6.0) * exp(-abs(p.x) / R * 0.45)
                + 0.15 * exp(-abs(p.x) / R * 6.0) * exp(-abs(p.y) / R * 0.6);
        return col + uIris * g * glow * br * A;
    }

    // light trail through the last positions
    vec2 prev = c;
    float tr = 0.0;
    for (int i = 0; i < 8; i++) {
        vec2 q = uTrail[i].xy;
        float w = uTrail[i].z * (0.35 - 0.035 * float(i));
        float d = segDist(uv * vec2(asp, 1.0), prev * vec2(asp, 1.0), q * vec2(asp, 1.0));
        tr += exp(-d / max(w, 1e-4)) * (1.0 - float(i) / 8.0);
        prev = q;
    }
    col += uIris * tr * 0.5 * glow * A;

    // orbit ring (tilted ellipse); the back half hides behind the sphere
    float ang = 0.35 * sin(uTime * 0.7) + uRingA;
    mat2 rot = mat2(cos(ang), -sin(ang), sin(ang), cos(ang));
    vec2 rq = rot * p / R;
    float e = length(rq / vec2(1.65, 0.38));
    float ring = exp(-abs(e - 1.0) * 28.0);
    float dSph = length(p) / R;
    bool back = rq.y > 0.0;
    float ringVis = (back && dSph < 1.0) ? 0.0 : ring;

    // halo around the body
    col += uIris * exp(-max(dSph - 1.0, 0.0) * 3.0) * 0.12 * glow * A * smoothstep(1.0, 1.05, dSph);

    if (dSph < 1.04) {
        float edge = smoothstep(1.0, 0.97, dSph);
        vec3 n = vec3(p / R, sqrt(max(0.0, 1.0 - dSph * dSph)));
        vec3 v = vec3(0.0, 0.0, 1.0);
        vec3 r = reflect(-v, n);
        float fres = 0.25 + 0.75 * pow(1.0 - n.z, 3.0);
        vec3 chrome = env(uv + r.xy * 0.18) * (0.35 + 0.9 * fres) + vec3(0.02, 0.025, 0.03);
        vec3 L = normalize(vec3(-0.5, 0.7, 0.6));
        chrome += vec3(1.0, 0.95, 0.9) * pow(max(dot(reflect(-L, n), v), 0.0), 60.0) * 3.0;
        chrome += vec3(0.6, 0.8, 1.0) * pow(max(dot(reflect(-normalize(vec3(0.6, -0.4, 0.4)), n), v), 0.0), 30.0) * 0.6;
        // panel seams
        float seam = smoothstep(0.012, 0.0, abs(n.y + 0.15 * n.x)) + smoothstep(0.01, 0.0, abs(n.x - 0.55 * n.y - 0.2));
        chrome *= 1.0 - 0.6 * seam * (1.0 - smoothstep(0.85, 1.0, dSph));

        // lens: a disc on the sphere facing uLook
        vec3 ld = normalize(vec3(uLook * 0.8, 1.0));
        float la = acos(clamp(dot(n, ld), -1.0, 1.0));
        vec3 body = chrome;
        if (la < 0.5) {
            vec3 t1 = normalize(cross(ld, vec3(0.0, 1.0, 0.0)));
            vec3 t2 = cross(t1, ld);
            float pa = atan(dot(n, t2), dot(n, t1));
            float iris = smoothstep(0.30, 0.27, la) * smoothstep(0.10, 0.13, la);
            float fib = 0.6 + 0.4 * sin(pa * 24.0 + uTime * 0.5) * sin(pa * 7.0);
            float pupil = smoothstep(0.1, 0.0, la);
            vec3 glass = vec3(0.01, 0.012, 0.02) + env(uv - r.xy * 0.1) * 0.15;
            vec3 em = uIris * (iris * fib * 1.6 + pupil * 4.0) * glow;
            em += uIris * exp(-abs(la - 0.3) * 60.0) * 0.8 * glow;            // limbal ring
            body = mix(chrome, glass + em, smoothstep(0.5, 0.46, la));
            body += vec3(1.0) * smoothstep(0.06, 0.0, length(n.xy - ld.xy * 0.9 - vec2(-0.12, 0.12))) * 2.0;   // glint
        }
        // corruption: red veins crawl over the chrome
        if (uVein > 0.0) {
            float vn = fbm(n.xy * 5.0 + vec2(uTime * 0.05, 0.0));
            float vein = smoothstep(0.03, 0.0, abs(vn - 0.5)) * smoothstep(0.2, 1.0, uVein + 0.3 * n.z);
            body = mix(body, vec3(0.45, 0.02, 0.03) + vec3(1.2, 0.1, 0.05) * uHit, vein * uVein);
        }
        // overheating: golden cracks glow through
        if (uCrack > 0.0) {
            float cn = fbm(n.xy * 3.5 + 7.0);
            float crack = smoothstep(0.022, 0.0, abs(cn - 0.52)) * step(0.45, uCrack + 0.4 * fbm(n.xy * 2.0));
            body += vec3(1.6, 0.8, 0.25) * crack * uCrack * (2.0 + 2.0 * uHit);
        }
        col = mix(col, body, edge * A);
    }
    col += uIris * ringVis * 0.9 * glow * A + vec3(0.8) * ringVis * 0.25 * A;
    return col;
}
