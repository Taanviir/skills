#!/usr/bin/env node
// Resolves every Graphite UI color token to plain hex for both themes, for code that can't read
// CSS variables: MUI, Mantine or Ant Design themes, email and PDF renderers, native apps, Figma.
// Usage: node export.mjs [path/to/tokens.css] [--hue 256] [--chroma 1] [--tint 1] [--format json|css|fallback]
//   json (default)  { "light": { "bg-page": "#f8f9fb", ... }, "dark": { ... } }
//   css             :root with the light hex values, and a prefers-color-scheme block with the dark ones
//   fallback        light hex values for browsers without light-dark(); load it after tokens.css
import { loadTokens, toHex } from './oklch.mjs';

const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? undefined : args.splice(i, 2)[1];
};
const knobs = { '--gr-accent-h': flag('hue'), '--gr-accent-c': flag('chroma'), '--gr-tint': flag('tint') };
const format = flag('format') ?? 'json';
if (!['json', 'css', 'fallback'].includes(format) || args.some((a) => a.startsWith('-'))) {
  console.error('usage: node export.mjs [path/to/tokens.css] [--hue H] [--chroma C] [--tint T] [--format json|css|fallback]');
  process.exit(2);
}
const { names, resolve, toScreen } = loadTokens(args[0], knobs);

// Primitives stay out: apps get the semantic tier only, the same rule as in CSS.
const SEMANTIC = /^--gr-(?:bg|fg|border|accent|success|warning|danger|info|series)-|^--gr-scrim$/;
const out = { light: {}, dark: {} };
for (const name of names.filter((n) => SEMANTIC.test(n) && !n.endsWith('-h') && !n.endsWith('-c'))) {
  for (const theme of ['light', 'dark']) {
    const [rgb, , alpha] = toScreen(resolve(name, theme));
    out[theme][name.slice(5)] = toHex(rgb, alpha);
  }
}

if (format === 'json') {
  console.log(JSON.stringify(out, null, 2));
} else if (format === 'fallback') {
  // Custom properties aren't checked when parsed, so tokens.css would override a plain :root block
  // even where light-dark() is unknown. Only an @supports block after it wins there.
  const block = Object.entries(out.light).map(([k, v]) => `    --gr-${k}: ${v};`).join('\n');
  console.log(`@supports not (color: light-dark(#000, #fff)) {\n  :root {\n${block}\n  }\n}`);
} else {
  const block = (theme, indent) => Object.entries(out[theme]).map(([k, v]) => `${indent}--gr-${k}: ${v};`).join('\n');
  console.log(`:root {\n${block('light', '  ')}\n}\n@media (prefers-color-scheme: dark) {\n  :root {\n${block('dark', '    ')}\n  }\n}`);
}
