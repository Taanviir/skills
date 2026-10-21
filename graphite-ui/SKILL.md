---
name: graphite-ui
description: Graphite UI design system. Tokens, component recipes and an audit script for reworking an app's UI. Use when asked to restyle, redesign or rework an existing app with Graphite UI, to start a new UI on Graphite UI, or to audit an app for hardcoded styling against it.
---

# Graphite UI

Graphite UI is a design system that ships inside this skill. `assets/` has the CSS. `scripts/` has three scripts that need Node 21 or newer and no dependencies:
- `audit.mjs` lists styling that bypasses the tokens.
- `contrast.mjs` checks color pairs.
- `brand.mjs` turns a brand color into token knobs.

`GR` below means this skill's directory.

The job is a **rework**: the app keeps its markup structure, routes, copy and behavior. Its visual layer is replaced by Graphite UI tokens and recipes, and the old layer is deleted, not left underneath. Three branches:
- **Existing app**: every step below.
- **New app**: steps 3 and 6, then build with the recipes.
- **Audit only**: step 1, then report the findings grouped by rule with the worst files.

## Steps

### 1. Survey
- Identify the stack using `references/stacks.md`.
- List every stylesheet the app ships, the layout template or root component, and where colors live outside CSS (JS chart configs, theme objects, per-tenant settings, email templates).
- Note what exists today: dark mode, RTL, a theme toggle, per-tenant branding.
- Run the baseline audit and keep its output:
  ```sh
  node $GR/scripts/audit.mjs <source dirs>
  ```

Done when you can name every stylesheet and every place a color is defined, and you have the baseline counts.

### 2. Plan
Write the plan in a reply to the user. Don't write it to a file in their repo. It has four parts:
- **Stack branch** from `references/stacks.md`.
- **Brand.** The app's current brand color run through `node $GR/scripts/brand.mjs "#hex"`, and the knobs it prints. If the user wants a different hue, use theirs.
- **Token map.** One row for each custom property, Sass variable and JS color constant the app defines, mapped to an `--gr-*` token, a bridge, or "delete". `references/tokens.md` explains how to choose.
- **Component map.** One row for each repeated UI pattern in the app. Each row gives the app's selector, the recipe from `references/components.md`, and port or adopt.

Done when every legacy token from the survey has a row, and the user has approved the plan. Wait for that approval.

### 3. Install
- Copy the files the stack branch lists into a directory named `graphite-ui` in the app, and wire the imports.
- Set the brand knobs on `:root` in the app's own CSS.
- Load the font.

Done when the app builds and the page background and text color have visibly changed.

### 4. Remap tokens
- Rewrite every read of a legacy token to its mapped `--gr-*` token, following the token map.
- Delete the legacy definitions.
- Move JS color copies onto the CSS variables (`references/tokens.md`, item 5).

Done when the audit reports zero `legacy-token` and zero `legacy-ref`.

### 5. Rework components
Take the component map one row at a time. Apply the recipe by port or adopt, apply `references/rules.md`, and delete the old declarations for that component. Start with what appears on every page: buttons, inputs, cards, tables and the shell.

Done when every row in the component map is done, and every screen reachable from the nav renders with no old component styles left.

### 6. Sweep one-offs
Run the audit again and fix each finding. A value with a real reason to stay gets a `/* gr-allow: reason */` comment on its line; an inline style gets the comment inside its tag. Keep allowances rare. Typical reasons are a third-party widget's required size or an iOS zoom fix.

Done when the audit exits 0.

### 7. Verify
- `node $GR/scripts/contrast.mjs --hue H --chroma C` with the app's knobs. All pairs must pass.
- Check light theme, dark theme, keyboard focus on every control, a 375px-wide viewport, and RTL if the app has Arabic or Hebrew. Run the app for these checks only if a dev server is already running or the user agrees to start one. Otherwise list them as remaining checks for the user.
- Report to the user:
  - baseline and final audit counts,
  - files and tokens deleted,
  - every `gr-allow` with its reason,
  - anything left unchecked.

## References
- `references/tokens.md`: which token to use, the knobs, building the token map.
- `references/rules.md`: the design rules every reworked screen follows.
- `references/components.md`: port or adopt, the name map from common class names, notes on each recipe.
- `references/stacks.md`: install steps for plain CSS, Bootstrap 5, Sass, Tailwind v3/v4, shadcn and CSS-in-JS, plus dark mode.
- `assets/preview.html`: every recipe with real markup, plus a theme switch and a hue slider.
