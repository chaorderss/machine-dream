// Golden fractal cathedral: Apollonian gasket rendered as gilded architecture.
// Organ blasts (uHit/uSpring) shatter the structure; the spring pulls it back together.

uniform float uPose;      // structure/camera clock; the finale replays pose 0 to loop into frame 1
uniform float uShatter;   // director-level shatter on top of the music-driven one
uniform float uGlow;      // window light intensity

vec4 gTrap;

float mapC(vec3 p, float s) {
    float scale = 1.0;
    gTrap = vec4(1000.0);
    for (int i = 0; i < 8; i++) {
        p = -1.0 + 2.0 * fract(0.5 * p + 0.5);
        float r2 = dot(p, p);
        gTrap = min(gTrap, vec4(abs(p), r2));
        float k = s / r2;
        p *= k;
        scale *= k;
    }
    return 0.25 * abs(p.y) / scale;
}

vec3 render(vec2 fc) {
    vec2 p = (fc - 0.5 * uRes) / uRes.y;
    float t = uPose * 0.35 + 1.3;

    // music: hits push the gasket parameter away, spring brings it home (overshoot = wobble)
    float shatter = clamp(uShatter + 0.55 * uHit + 0.25 * max(uSpring, 0.0), 0.0, 1.5);
    float s = 1.08 + 0.32 * shatter + 0.02 * sin(t);

    // camera drifts through the vaults (orbit after IQ's Apollonian), slightly low, looking up
    vec3 ro = vec3(2.8 * cos(0.1 + 0.33 * t), 0.35 + 0.25 * cos(0.37 * t), 2.8 * cos(0.5 + 0.35 * t));
    vec3 ta = vec3(1.9 * cos(1.2 + 0.41 * t), 0.75 + 0.10 * cos(0.27 * t), 1.9 * cos(2.0 + 0.38 * t));
    float roll = 0.15 * cos(0.1 * t) + 0.06 * uSpringV;
    vec3 ww = normalize(ta - ro);
    vec3 uu = normalize(cross(ww, vec3(sin(roll), cos(roll), 0.0)));
    vec3 vv = cross(uu, ww);
    vec3 rd = normalize(p.x * uu + p.y * vv + 1.4 * ww);

    float tt = 0.01, d = 0.0;
    int i;
    for (i = 0; i < 200; i++) {
        d = mapC(ro + rd * tt, s);
        if (d < 0.00015 * tt || tt > 14.0) break;
        tt += d * 0.9;
    }
    vec3 bg = vec3(0.10, 0.055, 0.015) * (0.6 + 0.4 * rd.y);
    vec3 col = bg;
    if (tt < 14.0) {
        vec3 pos = ro + rd * tt;
        vec4 tra = gTrap;
        vec2 e = vec2(1.0, -1.0) * 0.0003 * tt;
        vec3 n = normalize(e.xyy * mapC(pos + e.xyy, s) + e.yyx * mapC(pos + e.yyx, s) +
                           e.yxy * mapC(pos + e.yxy, s) + e.xxx * mapC(pos + e.xxx, s));
        float occ = clamp(tra.w * 2.2, 0.0, 1.0) * (1.0 - float(i) / 200.0);

        vec3 base = vec3(0.02);
        base = mix(base, vec3(1.0, 0.78, 0.25), clamp(6.0 * tra.y, 0.0, 1.0));
        base = mix(base, vec3(1.0, 0.50, 0.05), pow(clamp(1.0 - 2.0 * tra.z, 0.0, 1.0), 8.0));

        vec3 L1 = normalize(vec3(0.577, 0.577, -0.577));
        float dif = clamp(dot(n, L1), 0.0, 1.0);
        float spe = pow(clamp(dot(reflect(rd, n), L1), 0.0, 1.0), 40.0);
        float amb = 0.6 + 0.4 * n.y;
        float fre = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 4.0);

        col = base * (1.6 * dif + 0.35 * amb) * occ;
        col += vec3(1.0, 0.85, 0.5) * spe * 2.5 * occ;
        col += vec3(1.0, 0.7, 0.3) * fre * 0.35 * occ;
        // stained-glass embers in the tracery
        col += pal(tra.w * 3.0 + 0.05 * t) * smoothstep(0.015, 0.0, tra.x) * (0.3 + uGlow) * 2.0 * occ;
        col = mix(col, bg, 1.0 - exp(-0.08 * tt * tt));
    }
    // god ray from the rose window
    col += vec3(1.0, 0.75, 0.35) * 0.35 * pow(max(dot(rd, normalize(vec3(0.3, 1.0, 0.2))), 0.0), 10.0) * (1.0 + uSpring);
    return col;
}
