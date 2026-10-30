// Shared uniforms + helpers. Prepended to every program after #version.
// Director signals come from config/timeline.json, music signals from analysis/features.npz.

uniform vec2  uRes;
uniform float uTime;        // global seconds
uniform float uLocal;       // seconds since chapter start
uniform float uProgress;    // 0..1 through chapter
uniform float uDt;
uniform float uIntensity;   // director curve 0..1
uniform float uTravel;      // integral of director speed curve (camera distance)

// music
uniform float uBass, uLowMid, uMid, uHigh, uRms;
uniform float uSpring;      // loudness through damped spring: has weight + overshoot
uniform float uSpringV;     // spring velocity
uniform float uOnset;       // onset strength (smoothed)
uniform float uHit;         // decaying envelope from note onsets
uniform float uCentroid;    // 0 dark/low .. 1 bright/high
uniform float uNoteCount, uNoteAge;   // note onsets
uniform float uHiCount, uHiAge;       // high-band (violin/flute) onsets
uniform float uCutCount, uCutAge;     // tutti events → camera cuts
uniform float uPulseCount, uPulseAge; // ~1/s pulses
uniform float uStep;                  // pulse counter eased between integers: micro-variation clock

uniform vec3 uPalA, uPalB, uPalC, uPalD;
uniform sampler2D uSpectrum;
uniform sampler2D uPrev;
uniform sampler2D uPaint;   // this chapter's painting (bottom-up), alpha = math-only depth (1 = near)
uniform sampler2D uPalTex;  // cyclic palette extracted from that painting
uniform float uPalPaint;    // 0 = cosine palette .. 1 = painting palette

#define PI  3.14159265359
#define TAU 6.28318530718

mat2 rot(float a) { float c = cos(a), s = sin(a); return mat2(c, s, -s, c); }
vec3 pal(float t) {
    vec3 c = uPalA + uPalB * cos(TAU * (uPalC * t + uPalD));
    return uPalPaint > 0.0 ? mix(c, texture(uPalTex, vec2(t, 0.5)).rgb, uPalPaint) : c;
}
float spec(float x) { return texture(uSpectrum, vec2(clamp(x, 0.0, 1.0), 0.5)).r; }

float hash11(float p) { p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float hash12(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
vec2 hash22(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * vec3(0.1031, 0.1030, 0.0973)); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.xx + p3.yz) * p3.zy); }
float hash13(vec3 p3) { p3 = fract(p3 * 0.1031); p3 += dot(p3, p3.zyx + 31.32); return fract((p3.x + p3.y) * p3.z); }

float vnoise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash12(i), hash12(i + vec2(1, 0)), u.x),
               mix(hash12(i + vec2(0, 1)), hash12(i + vec2(1, 1)), u.x), u.y);
}
float fbm(vec2 p) {
    float s = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++) { s += a * vnoise(p); p = rot(0.5) * p * 2.03 + 3.1; a *= 0.5; }
    return s;
}
float vnoise3(vec3 p) {
    vec3 i = floor(p), f = fract(p);
    vec3 u = f * f * (3.0 - 2.0 * f);
    float a = mix(mix(hash13(i), hash13(i + vec3(1, 0, 0)), u.x), mix(hash13(i + vec3(0, 1, 0)), hash13(i + vec3(1, 1, 0)), u.x), u.y);
    float b = mix(mix(hash13(i + vec3(0, 0, 1)), hash13(i + vec3(1, 0, 1)), u.x), mix(hash13(i + vec3(0, 1, 1)), hash13(i + vec3(1, 1, 1)), u.x), u.y);
    return mix(a, b, u.z);
}
float smin(float a, float b, float k) { float h = clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0); return mix(b, a, h) - k * h * (1.0 - h); }

#ifdef FRAG
float lineAA(float d, float w) { float aa = fwidth(d) * 1.2 + 1e-6; return 1.0 - smoothstep(w, w + aa, d); }
#endif
