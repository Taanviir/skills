# Tokens

`assets/tokens.css` holds the values. This file says which token to reach for and how to map an app's old tokens onto them.

## Picking a token

| You are styling | Token |
|---|---|
| Page background behind everything | `--gr-bg-page` |
| Card, table, panel, input fill | `--gr-bg-surface` |
| Menu, popover, dialog | `--gr-bg-raised` |
| Segmented track, code block, disabled input, well | `--gr-bg-sunken` |
| Hover fill on rows, ghost buttons, menu items | `--gr-bg-hover` |
| Selected row, current item | `--gr-bg-selected` |
| Toast, tooltip | `--gr-bg-inverse` with `--gr-fg-inverse` |
| Modal backdrop | `--gr-scrim` |
| Body text, headings, values | `--gr-fg-primary` |
| Hints, meta, table headers, inactive nav | `--gr-fg-secondary` |
| Placeholders, decorative icons, counts in nav | `--gr-fg-tertiary` (3:1, never sentences) |
| Text on accent or danger solids | `--gr-fg-on-accent` |
| Row dividers, section rules | `--gr-border-separator` |
| A card that needs a drawn border | `--gr-shadow-border` (preferred) or `--gr-border-default` |
| Input and select edges | `--gr-border-control` |
| Focus rings | `--gr-border-focus` |
| Primary button, active tab underline, checked controls | `--gr-accent-solid`, hover `--gr-accent-solid-hover` |
| Links, accent text, selected-item text | `--gr-accent-text` |
| Accent-tinted fill (selected chip, active badge) | `--gr-accent-bg-subtle` |
| Status text | `--gr-{success,warning,danger,info}-text` |
| Status fill behind text | `--gr-{status}-bg-subtle` |
| Status dot, progress bar, chart mark | `--gr-{status}-solid` |
| Chart series | `--gr-series-1` … `-5`, in order |

Elevation is a ladder. Use one rung per element:
- Flat in the page: no shadow.
- Card, button, table: `--gr-shadow-border`.
- Hovered card or button: `--gr-shadow-border-hover`.
- Menu, popover, toast: `--gr-shadow-raised`.
- Dialog, mobile sidebar: `--gr-shadow-overlay`.

Type is by role. The roles, from small to large: `label` 12, `caption` 13, `body` 14, `heading` 16, `title` 20, `page` 24, `display` 32. UI text is `body`. One `page` per screen. `display` is only for stat values and hero numbers.

Spacing tokens use Tailwind step names: `--gr-space-3` is 12px. Use the steps in this order:
- Inside a control: 6 to 12.
- Between related items: 8 to 12.
- Between groups: 16 to 24.
- Between page sections: 24 to 32.

## Knobs

- `--gr-accent-h`: brand hue. Get it from the app's current brand color with `node scripts/brand.mjs "#hex"`. That prints `--gr-accent-h` and `--gr-accent-c`.
- `--gr-accent-c`: chroma multiplier. Amber, yellow and teal need 0.55 to 0.65. `brand.mjs` picks it.
- `--gr-tint`: how far the grays lean toward the hue. Keep 1. Set 0 for neutral grays when the brand hue is warm and the grays would turn beige.

Set knobs in the app's own stylesheet on `:root`, after importing `tokens.css`. Never edit `tokens.css` in the app. Then run `node scripts/contrast.mjs --hue H --chroma C` and keep the knobs only when every pair passes.

Per-tenant branding (one app, many orgs, each with a color) is a knob per tenant. Render `<html style="--gr-accent-h: 277; --gr-accent-c: .95">` from the tenant record, computed once with `brand.mjs` logic. That replaces any per-tenant color palette the app has.

## Building the token map

The token map is a table with one row per custom property, Sass variable or JS color constant the app defines today. Each row ends in exactly one of these:
- an `--gr-*` token,
- a bridge (see below),
- "delete" because nothing reads it.

To fill a row, look at how the old token is used, not at its name:
1. Grep its uses. A `--primary` used only on buttons maps to `--gr-accent-solid`. One used for link text maps to `--gr-accent-text`. If it's used for both, split the uses.
2. For grays, sort the old grays by lightness and map them to the semantic layer by role. Darkest text is `fg-primary`, then `fg-secondary`, `fg-tertiary`, `border-control`, `border-default`, `border-separator`, `bg-hover`, `bg-sunken`, `bg-page`. White is `bg-surface`.
3. Status colors map by meaning. Green "success" and "paid" are `success`. A green used as decoration is not status: map it to the accent or delete it.
4. Old token sets often sit on top of each other: a Bootstrap-style `--primary-color` set over a Tailwind-style one. Map both sets to the same `--gr-*` targets, then delete both.
5. Tokens copied into JS (chart configs, canvas code, email or PDF renderers) get one of two treatments. Code that runs in the page reads the CSS variable: `getComputedStyle(document.documentElement).getPropertyValue('--gr-series-1')`. Code that runs elsewhere imports a generated constant. Two hand-kept copies is the bug to remove.

A **bridge** is a custom property whose value is only `--gr-*` references. Examples are shadcn's `--primary: var(--gr-accent-solid)`, or a component-scoped `--tone: var(--gr-success-solid)`. The audit allows bridges. Keep them only where a library demands the name or one component swaps a value by variant.
