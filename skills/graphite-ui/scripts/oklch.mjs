// Reads tokens.css and resolves any --gr-* token to an on-screen sRGB color, per theme.
// Shared by contrast.mjs and export.mjs.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

export const DEFAULT_TOKENS = join(dirname(fileURLToPath(import.meta.url)), '../assets/tokens.css');

export function loadTokens(file = DEFAULT_TOKENS, knobs = {}) {
  const css = readFileSync(file, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const root = css.match(/:root\s*\{([\s\S]*?)\n\}/)?.[1] ?? '';
  const decls = {};
  for (const m of root.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)) decls[m[1]] = m[2].trim();
  for (const [k, v] of Object.entries(knobs)) if (v !== undefined) decls[k] = v;

  function splitArgs(s) {
    const out = [];
    let depth = 0, start = 0;
    for (let i = 0; i < s.length; i++) {
      if (s[i] === '(') depth++;
      else if (s[i] === ')') depth--;
      else if (s[i] === ',' && depth === 0) { out.push(s.slice(start, i).trim()); start = i + 1; }
    }
    out.push(s.slice(start).trim());
    return out;
  }

  // Replaces the innermost call matching `name(` each pass until none remain.
  function reduceCalls(s, name, fn) {
    for (;;) {
      const i = s.lastIndexOf(`${name}(`);
      if (i === -1) return s;
      let depth = 0, j = i + name.length;
      for (; j < s.length; j++) {
        if (s[j] === '(') depth++;
        else if (s[j] === ')' && --depth === 0) break;
      }
      s = s.slice(0, i) + fn(s.slice(i + name.length + 1, j)) + s.slice(j + 1);
    }
  }

  function resolve(name, theme, seen = new Set()) {
    if (seen.has(name)) throw new Error(`cycle at ${name}`);
    seen.add(name);
    let v = decls[name];
    if (v === undefined) throw new Error(`${name} is not defined`);
    v = reduceCalls(v, 'var', (inner) => resolve(splitArgs(inner)[0], theme, new Set(seen)));
    v = reduceCalls(v, 'light-dark', (inner) => splitArgs(inner)[theme === 'light' ? 0 : 1]);
    v = reduceCalls(v, 'calc', (inner) => String(Function(`return (${inner})`)()));
    return v;
  }

  function parseOklch(str) {
    const m = str.match(/oklch\(\s*([\d.]+)%\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?/);
    if (!m) throw new Error(`not an oklch color: ${str}`);
    return [m[1] / 100, +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
  }

  function oklchToLinearSrgb([L, C, H]) {
    const h = (H * Math.PI) / 180;
    const a = C * Math.cos(h), b = C * Math.sin(h);
    const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
    const mm = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
    const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
    return [
      4.0767416621 * l - 3.3077115913 * mm + 0.2309699292 * s,
      -1.2684380046 * l + 2.6097574011 * mm - 0.3413193965 * s,
      -0.0041960863 * l - 0.7034186147 * mm + 1.707614701 * s,
    ];
  }

  const inGamut = (rgb) => rgb.every((x) => x >= -0.0005 && x <= 1.0005);

  // Browsers show out-of-gamut colors on sRGB screens by lowering chroma (CSS Color 4 gamut
  // mapping), so contrast is measured on the mapped color. Returns [rgb, chroma lost, alpha].
  function toScreen(str) {
    const [L, C, H, alpha] = parseOklch(str);
    if (inGamut(oklchToLinearSrgb([L, C, H]))) return [oklchToLinearSrgb([L, C, H]), 0, alpha];
    let lo = 0, hi = C;
    for (let i = 0; i < 24; i++) {
      const mid = (lo + hi) / 2;
      if (inGamut(oklchToLinearSrgb([L, mid, H]))) lo = mid; else hi = mid;
    }
    return [oklchToLinearSrgb([L, lo, H]), (C - lo) / C, alpha];
  }

  const names = Object.keys(decls);
  return { names, resolve, toScreen };
}

export const luminance = ([r, g, b]) => {
  const c = (x) => Math.min(1, Math.max(0, x));
  return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b);
};

export const ratio = (fg, bg) => {
  const [hi, lo] = [luminance(fg), luminance(bg)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

export function toHex(rgb, alpha = 1) {
  const enc = (x) => {
    const c = Math.min(1, Math.max(0, x));
    return Math.round((c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055) * 255);
  };
  const a = alpha < 1 ? [Math.round(alpha * 255)] : [];
  return '#' + [...rgb.map(enc), ...a].map((n) => n.toString(16).padStart(2, '0')).join('');
}
