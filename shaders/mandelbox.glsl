// Infinite Mandelbox machine city. Each organ note performs one more box-fold twist;
// complexity (iterations) and speed grow through the fugue.

uniform float uIters;     // 3..10 fold iterations
uniform float uScaleMB;   // Mandelbox scale
uniform float uFoldStep;  // radians of twist added per note

float gTrapMB;

float foldPhase() { return uNoteCount + smoothstep(0.0, 0.18, uNoteAge) - 1.0; }

float mapB(vec3 p) {
    vec3 w = p;
    w.xy *= rot(w.z * 0.06);
    float corridor = 0.34 - max(abs(w.x), abs(w.y));   // square duct through the machine               // guaranteed flight path
    vec3 q = w;
    q.z = mod(q.z + 2.0, 4.0) - 2.0;
    q *= 0.9;
    vec4 z = vec4(q, 1.0);
    vec3 c = q;
    float ph = foldPhase() * uFoldStep;
    gTrapMB = 1e5;
    int n = int(uIters);
    for (int i = 0; i < 12; i++) {
        if (i >= n) break;
        z.xyz = clamp(z.xyz, -1.0, 1.0) * 2.0 - z.xyz;
        float r2 = dot(z.xyz, z.xyz);
        float k = clamp(max(0.25 / r2, 0.25), 0.0, 1.0) * 4.0;
        z *= k;
        z = z * uScaleMB + vec4(c, 1.0);
        z.xz *= rot(ph * 0.37);
        z.yz *= rot(ph * 0.21);
        gTrapMB = min(gTrapMB, abs(z.y) / abs(z.w));
    }
    float frac = (length(z.xyz) - abs(uScaleMB - 1.0)) / abs(z.w) / 0.9;
    return max(frac, corridor);
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    vec3 ro = vec3(0.0, 0.0, uTravel);
    vec3 rd = normalize(vec3(p, 1.1));
    rd.xy *= rot(0.05 * sin(uTime * 0.4) + 0.08 * uSpringV + 0.35 * uStep);
    // tutti → hard camera angle cut
    float cutAng = hash11(uCutCount * 5.3) * TAU * step(0.5, uCutCount);
    rd.xy *= rot(cutAng);

    float t = 0.02, d;
    int i;
    float glow = 0.0;
    for (i = 0; i < 140; i++) {
        d = mapB(ro + rd * t);
        glow += exp(-max(d, 0.0) * 120.0);
        if (d < 0.0003 * (1.0 + t * 2.0) || t > 10.0) break;
        t += d * 0.8;
    }
    vec3 col = vec3(0.0);
    if (t < 10.0) {
        vec3 pos = ro + rd * t;
        vec2 e = vec2(1.0, -1.0) * 0.0006 * (1.0 + t);
        vec3 n = normalize(e.xyy * mapB(pos + e.xyy) + e.yyx * mapB(pos + e.yyx) + e.yxy * mapB(pos + e.yxy) + e.xxx * mapB(pos + e.xxx));
        float ao = pow(1.0 - float(i) / 140.0, 2.0);
        vec3 L = normalize(vec3(0.0, 0.0, -1.0));            // headlight
        float dif = pow(clamp(dot(n, -rd), 0.0, 1.0), 1.5) * 2.2 / (1.0 + t * t * 0.8);
        vec3 metal = mix(pal(gTrapMB * 1.5 + pos.z * 0.02 + 0.04 * uStep) * 0.35, vec3(0.9, 0.65, 0.3), smoothstep(0.05, 0.6, gTrapMB) * 0.6);
        col = metal * dif * ao;
        // circuitry: thin emissive traces lit by notes
        float tw = fwidth(gTrapMB * 6.0);
        float trace = smoothstep(tw + 0.02, 0.0, abs(fract(gTrapMB * 6.0) - 0.5) - 0.46) * smoothstep(0.5, 0.05, tw);
        col += pal(0.55 + 0.15 * sin(pos.z * 0.2)) * trace * (0.25 + 1.0 * uHit) * ao / (1.0 + t);
        float spe = pow(clamp(dot(reflect(rd, n), -rd), 0.0, 1.0), 30.0);
        col += vec3(1.0, 0.9, 0.7) * spe * 0.6 * ao / (1.0 + t * t);
        // service lights racing along the corridor, one ring per 4 units
        float ring = exp(-abs(fract(pos.z * 0.25 + 0.5) - 0.5) * 50.0);
        col += pal(0.62) * ring * (0.6 + 1.5 * uHit) * ao * smoothstep(0.7, 0.36, length(pos.xy));
    }
    col += pal(0.55 + uTime * 0.02) * glow * 0.0015 * (0.5 + uRms);
    col = mix(col, vec3(0.0), 1.0 - exp(-t * 0.25));
    col += pal(0.1) * 0.25 * exp(-length(p) * 12.0);
    return col;
}
