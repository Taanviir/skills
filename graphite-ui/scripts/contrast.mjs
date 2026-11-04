#!/usr/bin/env node
// Checks WCAG 2 contrast for the semantic color pairs in tokens.css, in both themes.
// Usage: node contrast.mjs [path/to/tokens.css] [--hue 256] [--chroma 1] [--tint 1]
// Exits 1 when a pair fails or a color falls outside sRGB.
import { loadTokens, ratio } from './oklch.mjs';

const USAGE = 'usage: node contrast.mjs [path/to/tokens.css] [--hue 256] [--chroma 1] [--tint 1]';
const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h')) {
  console.log(USAGE);
  process.exit(0);
}
const flag = (name) => {
  const i = args.indexOf(`--${name}`);
  return i === -1 ? undefined : args.splice(i, 2)[1];
};
const knobs = { '--gr-accent-h': flag('hue'), '--gr-accent-c': flag('chroma'), '--gr-tint': flag('tint') };
const unknown = args.find((a) => a.startsWith('-'));
if (unknown) {
  console.error(`unknown option ${unknown}\n${USAGE}`);
  process.exit(2);
}
const { resolve, toScreen } = loadTokens(args[0], knobs);

// [foreground, background, minimum ratio]. Text is 4.5; icons, edges, dots and chart marks are 3.
const PAIRS = [
  ...['page', 'surface', 'raised', 'sunken', 'hover', 'selected'].map((bg) => ['--gr-fg-primary', `--gr-bg-${bg}`, 4.5]),
  ...['page', 'surface', 'raised', 'sunken', 'hover', 'selected'].map((bg) => ['--gr-fg-secondary', `--gr-bg-${bg}`, 4.5]),
  ['--gr-fg-tertiary', '--gr-bg-surface', 3],
  ['--gr-fg-tertiary', '--gr-bg-page', 3],
  ['--gr-fg-inverse', '--gr-bg-inverse', 4.5],
  ['--gr-border-control', '--gr-bg-surface', 3],
  ['--gr-border-focus', '--gr-bg-surface', 3],
  ['--gr-border-focus', '--gr-bg-page', 3],
  ['--gr-fg-on-accent', '--gr-accent-solid', 4.5],
  ['--gr-fg-on-accent', '--gr-accent-solid-hover', 4.5],
  ['--gr-fg-on-accent', '--gr-danger-solid', 4.5],
  ['--gr-accent-text', '--gr-bg-surface', 4.5],
  ['--gr-accent-text', '--gr-bg-page', 4.5],
  ['--gr-accent-text', '--gr-accent-bg-subtle', 4.5],
  ...['success', 'warning', 'danger', 'info'].flatMap((s) => [
    [`--gr-${s}-text`, '--gr-bg-surface', 4.5],
    [`--gr-${s}-text`, '--gr-bg-page', 4.5],
    [`--gr-${s}-text`, `--gr-${s}-bg-subtle`, 4.5],
    [`--gr-${s}-solid`, '--gr-bg-surface', 3],
  ]),
  ...[1, 2, 3, 4, 5].map((n) => [`--gr-series-${n}`, '--gr-bg-surface', 3]),
];

let failures = 0;
for (const theme of ['light', 'dark']) {
  console.log(`\n${theme}`);
  for (const [fg, bg, min] of PAIRS) {
    const [f, fLost] = toScreen(resolve(fg, theme));
    const [b, bLost] = toScreen(resolve(bg, theme));
    const r = ratio(f, b);
    const lost = Math.max(fLost, bLost);
    // Losing a quarter of the chroma visibly dulls the color; lower --gr-accent-c instead.
    const status = r < min ? 'FAIL ' : lost > 0.25 ? 'GAMUT' : 'ok   ';
    if (status !== 'ok   ') failures++;
    const note = status === 'GAMUT' ? `  out of sRGB: the screen drops ${Math.round(lost * 100)}% of its chroma, so lower --chroma` : '';
    console.log(`  ${status} ${r.toFixed(2).padStart(5)} >= ${min}  ${fg} on ${bg}${note}`);
  }
}
console.log(failures ? `\n${failures} failing` : '\nall pairs pass');
process.exit(failures ? 1 : 0);
