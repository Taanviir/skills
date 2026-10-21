#!/usr/bin/env node
// Finds styling that bypasses Graphite UI tokens. No dependencies.
// Usage: node audit.mjs [dir ...] [--json] [--all] [--ignore path,path]
//   --all     list every finding instead of the first 8 per rule
//   --json    machine-readable output
// Exit code 1 when anything is found, so it can gate CI.
// Files under a directory named "graphite-ui" are the system itself and are skipped.
// A line carrying a /* gr-allow: reason */ comment is a reviewed exception and is skipped.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { extname, join, relative } from 'node:path';

const argv = process.argv.slice(2);
const opt = (name) => argv.includes(`--${name}`);
const ignoreIdx = argv.indexOf('--ignore');
const extraIgnores = ignoreIdx === -1 ? [] : argv.splice(ignoreIdx, 2)[1].split(',');
const roots = argv.filter((a) => !a.startsWith('--'));
if (roots.length === 0) roots.push('.');

const SKIP_DIRS = new Set(['node_modules', '.git', 'dist', 'build', 'out', '.next', '.nuxt', '.svelte-kit', '.output', 'vendor', 'coverage', '.turbo', '.vercel', '.wrangler', 'storybook-static', 'graphite-ui']);
const STYLE_EXT = new Set(['.css', '.scss', '.sass', '.less', '.pcss', '.styl']);
const MARKUP_EXT = new Set(['.html', '.htm', '.php', '.vue', '.svelte', '.astro', '.erb', '.twig', '.blade', '.hbs', '.njk', '.liquid', '.jinja', '.j2']);
const SCRIPT_EXT = new Set(['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']);

const SPACE_PX = new Set([0, 1, 2, 4, 6, 8, 10, 12, 16, 20, 24, 32, 40, 48, 64]);
const RADIUS_PX = new Set([0, 4, 8, 12, 999, 9999]);

const RULES = {
  'color-literal': 'Color written as a literal. Use a semantic --gr-* color token.',
  'legacy-token': 'Custom property defined outside Graphite UI. Map its uses to an --gr-* token, then delete it.',
  'legacy-ref': 'Reads a legacy custom property. Point it at the --gr-* token from the mapping table.',
  'off-scale-space': 'Spacing off the 4px scale. Use --gr-space-* (2 4 6 8 10 12 16 20 24 32 40 48 64).',
  'raw-radius': 'Radius literal. Use --gr-radius-sm/control/surface/pill.',
  'raw-font-size': 'Font size literal. Use a --gr-text-* role.',
  'raw-font-family': 'Font family literal. Use --gr-font-sans/mono/arabic.',
  'raw-shadow': 'Shadow literal. Use --gr-shadow-*.',
  'raw-duration': 'Duration literal in a transition or animation. Use --gr-dur-fast/dur/dur-slow.',
  'raw-easing': 'Easing literal. Use --gr-ease-out or --gr-ease-in-out.',
  'raw-z-index': 'z-index literal. Use --gr-z-*.',
  'important': '!important. Usually a specificity fight left over from the old system.',
  'inline-style': 'Inline style attribute. Move it into a class.',
  'tw-palette': 'Tailwind palette class. Use a semantic color utility (bg-surface, text-fg-secondary, ...).',
  'tw-arbitrary': 'Tailwind arbitrary value. Use a scale step or add a token.',
};

function walk(p, out) {
  let st;
  try { st = statSync(p); } catch { return; }
  if (st.isDirectory()) {
    const base = p.split(/[\\/]/).pop();
    if (SKIP_DIRS.has(base) && !roots.includes(p)) return;
    for (const e of readdirSync(p)) walk(join(p, e), out);
  } else if (st.size < 2_000_000) {
    const ext = extname(p).toLowerCase();
    if (STYLE_EXT.has(ext) || MARKUP_EXT.has(ext) || SCRIPT_EXT.has(ext)) out.push(p);
  }
}

const files = [];
for (const r of roots) walk(r, files);

const findings = [];
const seen = new Set();
const add = (rule, file, line, text) => {
  const key = `${rule}:${file}:${line}`;
  if (seen.has(key)) return;
  seen.add(key);
  findings.push({ rule, file: relative(process.cwd(), file), line, text: text.trim().slice(0, 140) });
};

const COLOR_RE = /#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(/;
const NAMED_COLOR_RE = /(?:^|[\s:,(])(?:white|black|red|green|blue|gray|grey|orange|yellow|purple|pink|silver|navy|teal|maroon)(?=[\s;,)!]|$)/i;
const COLOR_PROP_RE = /^(?:color|background(?:-color)?|border(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?(?:-color)?|outline(?:-color)?|fill|stroke|box-shadow|text-shadow|caret-color|accent-color|text-decoration(?:-color)?|column-rule(?:-color)?|stop-color|flood-color)$/;
const SPACE_PROP_RE = /^(?:margin|padding|gap|row-gap|column-gap|inset|top|right|bottom|left)(?:-(?:top|right|bottom|left|block|inline)(?:-(?:start|end))?)?$/;
const stripVars = (v) => v.replace(/var\([^()]*(?:\([^()]*\)[^()]*)*\)/g, ' ');

// Yields [lineNumber, text, declarations[]] for each declaration, including values that span
// several lines. Comments and selectors are skipped. A gr-allow comment anywhere in the
// declaration, or later on its last line, skips it.
function* cssDeclarations(src, offsetLine = 0) {
  const blank = (c) => c.replace(/[^\n]/g, ' ');
  const clean = src.replace(/\/\*[\s\S]*?\*\//g, blank).replace(/^\s*\/\/.*$/gm, blank);
  let start = 0;
  for (let i = 0; i <= clean.length; i++) {
    const ch = clean[i];
    if (i < clean.length && ch !== ';' && ch !== '{' && ch !== '}') continue;
    const seg = clean.slice(start, i);
    const from = start;
    start = i + 1;
    if (ch === '{') continue;
    const m = seg.match(/^\s*(--[\w-]+|[a-zA-Z-]+)\s*:\s*([\s\S]+?)\s*$/);
    if (!m) continue;
    const lineEnd = src.indexOf('\n', i);
    if (/gr-allow/.test(src.slice(from, lineEnd === -1 ? src.length : lineEnd))) continue;
    const at = from + seg.search(/\S/);
    const line = clean.slice(0, at).split('\n').length + offsetLine;
    const text = seg.replace(/\s+/g, ' ').trim();
    yield [line, text, [[m[1].toLowerCase(), m[2].replace(/url\([^)]*\)/g, '')]]];
  }
}

// Custom properties that point at an --gr-* token (directly or through another bridge) are
// bridges: shadcn roles, per-component tones. Referencing them is fine.
const bridges = new Set();
function collectBridges(sources) {
  const defs = [];
  for (const [src, off] of sources) for (const [, , decls] of cssDeclarations(src, off)) for (const [p, v] of decls) if (p.startsWith('--')) defs.push([p, v]);
  for (let changed = true; changed;) {
    changed = false;
    for (const [p, v] of defs) {
      if (bridges.has(p)) continue;
      const refs = [...v.matchAll(/var\((--[\w-]+)/g)].map((m) => m[1]);
      if (refs.length && refs.every((r) => r.startsWith('--gr-') || bridges.has(r)) && !COLOR_RE.test(stripVars(v))) { bridges.add(p); changed = true; }
    }
  }
}

function scanCss(file, src, offsetLine = 0) {
  for (const [n, line, decls] of cssDeclarations(src, offsetLine)) {
    for (const [prop, value] of decls) {
      const literal = stripVars(value);
      if (prop.startsWith('--')) {
        if (!prop.startsWith('--gr-') && !prop.startsWith('--tw-') && !bridges.has(prop)) add('legacy-token', file, n, line);
        if (COLOR_RE.test(literal)) add('color-literal', file, n, line);
        continue;
      }
      for (const m of value.matchAll(/var\((--[\w-]+)/g)) {
        if (!m[1].startsWith('--gr-') && !m[1].startsWith('--tw-') && !bridges.has(m[1])) { add('legacy-ref', file, n, line); break; }
      }
      if (COLOR_PROP_RE.test(prop) && (COLOR_RE.test(literal) || NAMED_COLOR_RE.test(literal))) add('color-literal', file, n, line);
      if (SPACE_PROP_RE.test(prop)) {
        const offPx = [...literal.matchAll(/(-?\d*\.?\d+)px/g)].some((px) => !SPACE_PX.has(Math.abs(parseFloat(px[1]))));
        if (offPx || /\d*\.?\d+r?em\b/.test(literal)) add('off-scale-space', file, n, line);
      }
      if (/radius$/.test(prop)) {
        const nums = [...literal.matchAll(/(\d*\.?\d+)(px|rem|em|%)?/g)];
        if (nums.some(([, v, u]) => +v !== 0 && u !== '%' && !(u === 'px' && RADIUS_PX.has(+v)))) add('raw-radius', file, n, line);
      }
      if (prop === 'font-size' && /\d/.test(literal) && !/^\s*(?:100%|1em)\s*$/.test(literal)) add('raw-font-size', file, n, line);
      if (prop === 'font' && /\d*\.?\d+(?:px|r?em|pt)\b/.test(literal)) add('raw-font-size', file, n, line);
      if (prop === 'font-family' && /[a-z]/i.test(literal) && !/^\s*(?:inherit|initial)\s*$/.test(literal)) add('raw-font-family', file, n, line);
      if ((prop === 'box-shadow' || prop === 'text-shadow') && /\d/.test(literal)) add('raw-shadow', file, n, line);
      if (/^(?:transition|animation)(?:-duration|-delay)?$/.test(prop) && /(?<![\w-])\d*\.?\d+m?s\b/.test(literal)) add('raw-duration', file, n, line);
      if (/^(?:transition|animation)(?:-timing-function)?$/.test(prop) && /cubic-bezier\(|\bease(?:-in|-out|-in-out)?\b/.test(literal)) add('raw-easing', file, n, line);
      if (prop === 'z-index' && /^\s*-?\d+\s*$/.test(literal) && Math.abs(+literal) > 1) add('raw-z-index', file, n, line);
    }
    if (/!important/.test(line)) add('important', file, n, line);
  }
}

const TW_COLORS = 'slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white';
const TW_PALETTE_RE = new RegExp(`(?<![\\w-])(?:[a-z0-9-]+:)*(?:bg|text|border(?:-[trblxyse])?|ring|ring-offset|outline|fill|stroke|from|via|to|divide|decoration|placeholder|caret|accent|shadow)-(?:${TW_COLORS})(?:-\\d{2,3})?(?:\\/\\d+)?(?![\\w-])`, 'g');
const TW_ARBITRARY_RE = /(?<![\w-])(?:[a-z0-9-]+:)*-?[a-z]+(?:-[a-z]+)*-\[[^\]\s]+\]/g;

function scanClasses(file, src) {
  const lines = src.split('\n');
  lines.forEach((line, i) => {
    if (!/class(?:Name)?\s*=|\bclsx?\(|\bcn\(|\bcva\(|\btw`|@apply/.test(line) && !/^\s*["'`][^"'`]*["'`],?\s*$/.test(line)) return;
    for (const m of line.matchAll(TW_PALETTE_RE)) {
      add('tw-palette', file, i + 1, m[0]);
    }
    for (const m of line.matchAll(TW_ARBITRARY_RE)) {
      if (/\[(?:--gr-|var\(--gr-)/.test(m[0])) continue;
      add('tw-arbitrary', file, i + 1, m[0]);
    }
  });
}

function scanInlineStyles(file, src, jsx) {
  const re = jsx ? /style=\{\{/g : /\sstyle\s*=\s*["']/g;
  src.split('\n').forEach((line, i) => {
    if (re.test(line) && !/gr-allow/.test(line)) add('inline-style', file, i + 1, line);
    re.lastIndex = 0;
  });
}

const styleSources = (file, src) => {
  const ext = extname(file).toLowerCase();
  if (STYLE_EXT.has(ext)) return [[src, 0]];
  if (MARKUP_EXT.has(ext)) return [...src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => [m[1], src.slice(0, m.index).split('\n').length - 1]);
  return [];
};
const allSources = files.flatMap((f) => styleSources(f, readFileSync(f, 'utf8')));
collectBridges(allSources);

for (const file of files) {
  const rel = relative(process.cwd(), file);
  if (extraIgnores.some((ig) => rel.startsWith(ig))) continue;
  const ext = extname(file).toLowerCase();
  const src = readFileSync(file, 'utf8');
  if (STYLE_EXT.has(ext)) {
    scanCss(file, src);
    scanClasses(file, src);
  } else if (MARKUP_EXT.has(ext)) {
    for (const m of src.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) {
      scanCss(file, m[1], src.slice(0, m.index).split('\n').length - 1);
    }
    scanInlineStyles(file, src, false);
    scanClasses(file, src);
  } else {
    scanInlineStyles(file, src, /\.(?:jsx|tsx)$/.test(ext));
    scanClasses(file, src);
  }
}

if (opt('json')) {
  console.log(JSON.stringify({ files: files.length, total: findings.length, findings }, null, 2));
} else {
  const byRule = Object.groupBy(findings, (f) => f.rule);
  const perFile = Object.entries(Object.groupBy(findings, (f) => f.file)).sort((a, b) => b[1].length - a[1].length);
  console.log(`Scanned ${files.length} files. ${findings.length} findings.\n`);
  for (const [rule, desc] of Object.entries(RULES)) {
    const list = byRule[rule];
    if (!list) continue;
    console.log(`${rule} (${list.length})  ${desc}`);
    for (const f of opt('all') ? list : list.slice(0, 8)) console.log(`  ${f.file}:${f.line}  ${f.text}`);
    if (!opt('all') && list.length > 8) console.log(`  ... ${list.length - 8} more`);
    console.log('');
  }
  if (perFile.length) {
    console.log('Worst files');
    for (const [file, list] of perFile.slice(0, 10)) console.log(`  ${String(list.length).padStart(5)}  ${file}`);
  }
}
process.exit(findings.length ? 1 : 0);
