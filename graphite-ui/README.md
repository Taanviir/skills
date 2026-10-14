# Graphite UI

A design system that ships as an agent skill. Give it to Claude Code (or any agent that reads `SKILL.md`), point it at an app, and it reworks the app's look onto Graphite UI. The markup, routes, copy and behavior stay as they are.

The look is dense, calm and flat: 1px rings instead of borders, one accent color, 14px UI text, light and dark themes that follow the OS.

## What's inside

```
graphite-ui/
├── SKILL.md              the workflow the agent follows
├── assets/
│   ├── tokens.css        OKLCH tokens, light and dark via light-dark()
│   ├── base.css          element defaults
│   ├── components.css    recipes: button, input, table, dialog, shell, ...
│   ├── tailwind.css      Tailwind v4 bridge (clears the default palette)
│   ├── shadcn.css        shadcn/ui role mapping
│   ├── bootstrap.css     Bootstrap 5.3 variable mapping
│   └── preview.html      every recipe on one page, with theme and hue controls
├── references/           token guide, design rules, component name map, per-stack install
└── scripts/              Node, no dependencies
    ├── audit.mjs         finds styling that bypasses the tokens; exits 1 if any
    ├── contrast.mjs      WCAG check of every color pair, both themes
    └── brand.mjs         brand hex → hue and chroma knobs
```

## Use it

Install the skill:

```sh
ln -s "$PWD/graphite-ui" ~/.claude/skills/graphite-ui
```

Then, inside the app's repo:

> Rework this app's design with graphite-ui.

The agent goes through these steps:
1. Surveys the app and runs a baseline audit.
2. Shows you a plan, then waits for your approval. The plan has the stack, the brand knobs, an old→new token map and a component map.
3. Installs the tokens.
4. Remaps every old token and deletes the old ones.
5. Reworks the components.
6. Sweeps up one-off values until the audit is clean.
7. Checks contrast, then reports before and after numbers.

Two other requests work too:
- "Audit this app against graphite-ui." Report only, no changes.
- "Build this page with graphite-ui." For a new UI.

## Keep your brand

```sh
node scripts/brand.mjs "#4f46e5"
# --gr-accent-h: 277;
# --gr-accent-c: 0.95;
```

Put the two lines on `:root` in the app's CSS. The whole accent ramp, focus ring and gray tint follow the new hue. `contrast.mjs --hue 277 --chroma 0.95` confirms both themes still pass.

## Try it without an app

Open `assets/preview.html` in a browser. Switch between light, dark and RTL, and drag the hue slider.

## Browser support

The CSS needs `light-dark()`, `oklch()`, `:has()` and `@starting-style`. Chrome and Edge 123+, Safari 17.5+ and Firefox 129+ have all four. Older browsers get no theme switching.
