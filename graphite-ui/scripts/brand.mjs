#!/usr/bin/env node
// Turns an app's existing brand color into Graphite UI knobs.
// Usage: node brand.mjs "#4f46e5"
// Prints --gr-accent-h and an --gr-accent-c (0.05 steps) that matches the brand's saturation
// without pushing the accent ramp outside sRGB. Run contrast.mjs with the printed values afterwards.
const hex = (process.argv[2] ?? '').replace('#', '');
if (!/^[0-9a-f]{6}$|^[0-9a-f]{3}$/i.test(hex)) {
  console.error('usage: node brand.mjs "#rrggbb"');
  process.exit(2);
}
const full = hex.length === 3 ? [...hex].map((c) => c + c).join('') : hex;
const [r, g, b] = [0, 2, 4].map((i) => {
  const c = parseInt(full.slice(i, i + 2), 16) / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
});

const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
const L = 0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s;
const A = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s;
const B = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s;
const C = Math.hypot(A, B);
const H = ((Math.atan2(B, A) * 180) / Math.PI + 360) % 360;

function inGamut(L, C, H) {
  const h = (H * Math.PI) / 180;
  const a = C * Math.cos(h), bb = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * bb) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * bb) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * bb) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ].every((x) => x >= -0.0005 && x <= 1.0005);
}

// [lightness, base chroma] of the accent steps in tokens.css, both themes.
const STEPS = [[0.94, 0.03], [0.53, 0.17], [0.485, 0.158], [0.485, 0.135], [0.29, 0.055], [0.55, 0.155], [0.5, 0.15], [0.8, 0.075]];
let k = Math.max(0.3, Math.min(1, Math.floor((C / 0.17) * 20) / 20));
while (k > 0.3 && !STEPS.every(([sl, sc]) => inGamut(sl, sc * k, H))) k = Math.round((k - 0.05) * 100) / 100;

console.log(`input        #${full}  oklch(${(L * 100).toFixed(1)}% ${C.toFixed(3)} ${H.toFixed(1)})`);
console.log(`--gr-accent-h: ${Math.round(H)};`);
console.log(`--gr-accent-c: ${k};`);
if (C < 0.04) console.log('note: the brand color is close to gray; consider --gr-tint: 0 and keep the default blue accent');
console.log(`check: node contrast.mjs --hue ${Math.round(H)} --chroma ${k}`);
