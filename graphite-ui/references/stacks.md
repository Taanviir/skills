# Stacks

Detect the stack before installing. Signals:
- `tailwindcss` in package.json. Version 4 has `@import "tailwindcss"` in CSS; version 3 has `tailwind.config.*`.
- `components.json` means shadcn.
- `.php`, `.erb`, `.twig`, `.blade.php` or `.html` templates with a linked stylesheet means server-rendered with plain CSS.
- `.scss` means Sass.
- `styled-components` or `@emotion` means CSS-in-JS.

Wherever the app keeps styles, copy the files to a directory named `graphite-ui` (`src/styles/graphite-ui/`, `public/assets/graphite-ui/`). The audit skips that directory by name, so the system's own literals don't count against the app.

Load order is always tokens, base, then the app's CSS, with components where the branch says.

## Plain CSS (server-rendered, static, Vite without Tailwind)
1. Copy `tokens.css`, `base.css` and `components.css` into `graphite-ui/`.
2. Link them in the layout `<head>` before the app stylesheet:
   ```html
   <link rel="stylesheet" href="/assets/graphite-ui/tokens.css">
   <link rel="stylesheet" href="/assets/graphite-ui/base.css">
   <link rel="stylesheet" href="/assets/graphite-ui/components.css">
   <link rel="stylesheet" href="/assets/style.css">
   ```
   In a bundled app, use `@import` lines at the top of the entry CSS instead.
3. Linking `components.css` is optional when every component is ported. Leave it out if no markup uses its class names, so two definitions of `.btn` never fight.
4. Fonts: add the Google Fonts link for Instrument Sans (see `preview.html`), or self-host with `@fontsource-variable/instrument-sans`. Without either, the stack falls back to the system UI font, which is acceptable.

## Sass
Same as plain CSS. Import the `.css` files from the entry `.scss` with `@use "graphite-ui/tokens.css"`, or plain `@import` for older Sass. Sass color variables (`$primary: #4f46e5`) go in the token map like custom properties. Point each one at its CSS variable (`$primary: var(--gr-accent-solid)`) only while you rewrite their uses, then delete it. Sass color functions (`darken($primary, 10%)`) can't run on CSS variables. Replace each with the `-hover` or `-subtle` token it was approximating.

## Tailwind v4
1. Copy `tokens.css`, `base.css` and `tailwind.css`.
2. Entry CSS:
   ```css
   @import "tailwindcss";
   @import "./graphite-ui/tokens.css";
   @import "./graphite-ui/base.css";
   @import "./graphite-ui/tailwind.css";
   ```
3. `tailwind.css` clears Tailwind's palette, type, radius and shadow scales, so the build fails on every `bg-blue-500` or `text-lg` left behind. Use that as the to-do list. The spacing scale stays (it's already 4px). Utilities to use: `bg-surface`, `text-fg-secondary`, `border-separator`, `rounded-control`, `shadow-border`, `text-body`, `ease-out`.
4. Recipes are ported into `@layer components` in the app CSS, or written as utilities in the markup. Pick one per app and stay with it.

## Tailwind v3
Upgrade to v4 first if the app allows it (`npx @tailwindcss/upgrade`). Otherwise extend `theme.colors` in `tailwind.config.js` with the same names as `tailwind.css`, valued as `'var(--gr-bg-surface)'`. Set `theme.colors` itself (not `extend`) to drop the default palette.

## shadcn/ui
1. Do the Tailwind v4 branch.
2. Copy `shadcn.css` and import it after `tailwind.css`.
3. Delete the `:root { --background: ... }` and `.dark { ... }` blocks that `shadcn init` wrote, plus `@custom-variant dark` if it's there. Tokens switch themes on their own.
4. In shadcn, "accent" means the hover fill. Graphite UI's brand color is `bg-brand` / `text-brand-text` there.
5. Restyle shadcn components by editing their class strings in `components/ui/*`. Follow the matching recipe: `h-9` for a 36px control, `rounded-control`, `shadow-border` instead of `border`, `text-body`, and transitions limited to color and shadow. Keep shadcn's props and structure.
6. After every future `shadcn add`, check the app CSS for re-added `:root` or `.dark` blocks.

## CSS-in-JS
Import `tokens.css` and `base.css` once at the app root. Theme objects (`theme.colors.primary`) become `'var(--gr-accent-solid)'` strings. Keep the theme object only if components read it, and delete its literal values. Port recipes into styled components by copying their declarations.

## Dark mode in the app
If the app has a theme toggle, it sets `data-theme="light"` or `"dark"` on `<html>`, or removes the attribute to follow the OS. Delete the app's old dark-mode mechanism: a `.dark` class, a separate stylesheet, or JS-swapped colors. If the app has no toggle, dark mode follows the OS with no further work. If the app owner wants light only, add `:root { color-scheme: light; }` after tokens.css.
