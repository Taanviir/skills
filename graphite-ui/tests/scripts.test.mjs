// Run with: node --test graphite-ui/tests/*.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const script = (name) => join(ROOT, 'scripts', name);

function run(name, args, cwd = ROOT) {
  const r = spawnSync(process.execPath, [script(name), ...args], { cwd, encoding: 'utf8' });
  return { code: r.status, out: r.stdout, err: r.stderr };
}

// Writes { 'path/file.css': 'text' } into a fresh temp dir and returns the dir.
function project(files) {
  const dir = mkdtempSync(join(tmpdir(), 'gr-audit-'));
  for (const [path, text] of Object.entries(files)) {
    mkdirSync(dirname(join(dir, path)), { recursive: true });
    writeFileSync(join(dir, path), text);
  }
  return dir;
}

function audit(files, roots = ['.']) {
  const dir = project(files);
  const r = run('audit.mjs', [...roots, '--json'], dir);
  const json = JSON.parse(r.out);
  return { ...r, json, rules: (file) => json.findings.filter((f) => !file || f.file === file).map((f) => `${f.rule}:${f.line}`) };
}

// ---------- audit.mjs ----------

test('audit: clean token-only CSS passes with exit 0', () => {
  const r = audit({ 'a.css': '.x { color: var(--gr-fg-primary); padding: var(--gr-space-4); }\n' });
  assert.equal(r.code, 0);
  assert.equal(r.json.total, 0);
});

test('audit: a value spread over several lines is checked', () => {
  const r = audit({ 'a.css': '.card {\n  box-shadow:\n    0 1px 2px rgba(0,0,0,.2),\n    0 0 0 1px #e5e7eb;\n}\n' });
  assert.equal(r.code, 1);
  assert.deepEqual(r.rules().sort(), ['color-literal:2', 'raw-shadow:2']);
});

test('audit: legacy tokens and their reads are flagged, bridges are not', () => {
  const r = audit({
    'a.css': ':root {\n  --primary: #4f46e5;\n  --brand: var(--gr-accent-solid);\n}\n.b { color: var(--primary); }\n.c { color: var(--brand); }\n',
  });
  assert.deepEqual(r.rules().sort(), ['color-literal:2', 'legacy-ref:5', 'legacy-token:2']);
});

test('audit: each scale rule fires on an off-system literal', () => {
  const r = audit({
    'a.css': [
      '.a { padding: 13px; }',
      '.b { border-radius: 5px; }',
      '.c { font-size: 15px; }',
      '.d { font-family: Arial, sans-serif; }',
      '.e { transition: opacity 200ms ease-in; }',
      '.f { z-index: 50; }',
      '.g { color: var(--gr-fg-primary) !important; }',
    ].join('\n'),
  });
  assert.deepEqual(r.rules().sort(), [
    'important:7', 'off-scale-space:1', 'raw-duration:5', 'raw-easing:5', 'raw-font-family:4', 'raw-font-size:3', 'raw-radius:2', 'raw-z-index:6',
  ]);
});

test('audit: on-scale values pass', () => {
  const r = audit({ 'a.css': '.a { margin: 0 auto; padding: 8px 16px; border-radius: 8px; z-index: 1; top: 50%; }\n' });
  assert.equal(r.json.total, 0);
});

test('audit: gr-allow skips a value, also when the comment trails the line', () => {
  const r = audit({ 'a.css': '.a { padding: 13px; /* gr-allow: widget needs it */ }\n.b {\n  font-size: 16px; /* gr-allow: iOS zoom */\n}\n' });
  assert.equal(r.json.total, 0);
});

test('audit: selectors, media queries and SCSS line comments are not read as declarations', () => {
  const r = audit({ 'a.scss': '// color: #fff\n.a:hover { color: var(--gr-accent-text); }\n.a:is(:active, [data-pressed]) { color: var(--gr-accent-text); }\n@media (max-width: 600px) { .b { display: none; } }\n' });
  assert.equal(r.json.total, 0);
});

test('audit: a skipped folder name is scanned when passed as a root, in any position', () => {
  const files = { 'src/a.css': '.a { color: #000; }\n', 'dist/a.css': '.a { color: #000; }\n' };
  assert.equal(audit(files, ['src', 'dist']).json.findings.length, 2);
  assert.equal(audit(files, ['.']).json.findings.length, 1);
});

test('audit: files under a graphite-ui folder are the system and are skipped', () => {
  const r = audit({ 'styles/graphite-ui/tokens.css': ':root { --gr-white: #fff; }\n', 'styles/app.css': '.a { color: var(--gr-fg-primary); }\n' });
  assert.equal(r.json.total, 0);
});

test('audit: inline styles in markup and JSX are flagged', () => {
  const r = audit({
    'page.html': '<div style="color: red">x</div>\n<div style="x" data-note="gr-allow: email client">y</div>\n',
    'App.jsx': 'export const A = () => <div style={{ color: "red" }} />;\n',
  });
  assert.deepEqual(r.rules('page.html'), ['inline-style:1']);
  assert.deepEqual(r.rules('App.jsx'), ['inline-style:1']);
});

// The audit reports one finding per rule per line, so each class sits on its own line.
test('audit: Tailwind palette and arbitrary classes are flagged, token arbitraries are not', () => {
  const r = audit({
    'App.tsx': [
      'const a = <div className="bg-blue-500" />;',
      'const b = <div className="hover:text-white tap" />;',
      'const c = <div className="p-[13px]" />;',
      'const d = <div className="bg-[var(--gr-bg-surface)] bg-surface" />;',
    ].join('\n'),
  });
  assert.deepEqual(r.json.findings.map((f) => `${f.rule}:${f.text}`).sort(), [
    'tw-arbitrary:p-[13px]', 'tw-palette:bg-blue-500', 'tw-palette:hover:text-white',
  ]);
});

test('audit: colors in scripts and SVG paint attributes are flagged, selector strings are not', () => {
  const r = audit({
    'chart.js': "const c = { line: '#ff0000', grid: 'rgba(0,0,0,.1)' };\ndocument.querySelector('#add');\nconst t = 'Room #12';\n// '#ffffff'\n",
    'page.html': '<svg><path fill="#123456"/></svg>\n<script>ctx.fillStyle = "#abcdef";</script>\n',
  });
  assert.deepEqual(r.json.findings.map((f) => `${f.rule}:${f.file}:${f.line}`).sort(), [
    'script-color:chart.js:1', 'script-color:page.html:1', 'script-color:page.html:2',
  ]);
});

test('audit: a hex color inside an SVG data URL is flagged', () => {
  const r = audit({ 'a.css': `.a { background: url("data:image/svg+xml,%3Csvg fill='%23ff0000'/%3E"); }\n` });
  assert.deepEqual(r.json.findings.map((f) => f.rule), ['color-literal']);
});

test('audit: every Tailwind class on a line is its own finding', () => {
  const r = audit({ 'App.tsx': 'const c = <div className="bg-red-500 text-gray-700 p-[13px] m-[7px]" />;\n' });
  assert.equal(r.json.findings.filter((f) => f.rule === 'tw-palette').length, 2);
  assert.equal(r.json.findings.filter((f) => f.rule === 'tw-arbitrary').length, 2);
});

test("audit: the system's recipe files have no findings", () => {
  const r = run('audit.mjs', ['assets/components.css', 'assets/base.css', 'assets/shadcn.css', 'assets/bootstrap.css', '--json']);
  assert.equal(r.code, 0, r.out);
});

// ---------- brand.mjs ----------

const knobs = (out) => ({
  h: +out.match(/--gr-accent-h: (\d+);/)[1],
  c: +out.match(/--gr-accent-c: ([\d.]+);/)[1],
});

test('brand: known brand colors map to known knobs', () => {
  const expected = {
    '#4f46e5': [277, 0.95], '#eab308': [86, 0.6], '#14b8a6': [183, 0.55], '#22c55e': [150, 0.85],
    '#06b6d4': [215, 0.5], '#ef4444': [25, 1], '#a855f7': [304, 1], '#64748b': [257, 0.3],
  };
  for (const [hex, [h, c]] of Object.entries(expected)) {
    const r = run('brand.mjs', [hex]);
    assert.equal(r.code, 0, hex);
    assert.deepEqual(knobs(r.out), { h, c }, hex);
  }
});

test('brand: a 3-digit hex works and a bad one exits 2', () => {
  assert.equal(run('brand.mjs', ['#f00']).code, 0);
  assert.equal(run('brand.mjs', ['blue']).code, 2);
});

test('brand: a tokens file with no accent colors exits 2', () => {
  const dir = project({ 'tokens.css': ':root { --gr-white: oklch(100% 0 0); }\n' });
  assert.equal(run('brand.mjs', ['#4f46e5', join(dir, 'tokens.css')]).code, 2);
});

// ---------- contrast.mjs ----------

test('contrast: the default tokens pass in both themes', () => {
  const r = run('contrast.mjs', []);
  assert.equal(r.code, 0, r.out);
  assert.match(r.out, /all pairs pass/);
});

test('contrast: a yellow hue at full chroma fails', () => {
  assert.equal(run('contrast.mjs', ['--hue', '90', '--chroma', '1']).code, 1);
});

test('contrast: every knob pair brand.mjs prints passes', () => {
  for (const hex of ['#4f46e5', '#eab308', '#14b8a6', '#22c55e', '#84cc16', '#06b6d4', '#ef4444', '#ec4899', '#a855f7', '#64748b']) {
    const { h, c } = knobs(run('brand.mjs', [hex]).out);
    const r = run('contrast.mjs', ['--hue', String(h), '--chroma', String(c)]);
    assert.equal(r.code, 0, `${hex} -> ${h}/${c}\n${r.out}`);
  }
});
