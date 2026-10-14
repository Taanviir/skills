# Rules

Graphite UI looks dense, calm and flat. Surfaces are separated by 1px rings, there is one accent color, and the type is small and steady. It is a tool people use all day, so it is quiet by default and loud only where there is a decision to make.

Apply every rule to every screen you touch. Each rule says what to do; the audit catches the mechanical ones, and the rest are your judgement.

## Color
- The accent goes on one primary action per view, the current nav item, the active tab, checked controls, links and focus. Everything else is gray.
- Status colors carry status only, and always next to a word or icon. A red border alone is not an error state; the `.error` text under the field is.
- Fills come in two strengths: `bg-subtle` behind text, `solid` for dots and bars. Status text sits on `bg-surface` or its own `bg-subtle`.
- Gradients, colored page backgrounds and tinted cards go. A section that needs separation gets spacing or a `--gr-border-separator` rule.

## Surfaces and depth
- One card level. Cards inside cards become list rows or sections inside the card.
- `--gr-shadow-border` replaces `border: 1px solid` on cards and buttons. Real borders stay on inputs (`--gr-border-control`) and on dividers (`--gr-border-separator`).
- Radius follows size: `control` (8) on things you click, `surface` (12) on things that hold content, `group` (10) on tracks that hold controls, `pill` on badges and avatars. A full-bleed element gets no radius.

## Type
- `body` (14px) for all UI text. Bigger body copy makes dense screens feel like marketing pages.
- Weight 600 for headings and stat values, 500 for buttons, labels, nav and the first line of a row. Bold elsewhere is noise.
- Numbers in tables, stats and counts use `font-variant-numeric: tabular-nums` (`.nums`, `.table` has it).
- Uppercase only for `.overline` section labels, with `--gr-tracking-caps`.
- Sentence case for buttons, headings, tabs and menu items.

## Density and layout
- Controls are 36px (`--gr-control-md`), 32px in toolbars and tables, 44px on touch and for the one primary CTA on a form.
- Table rows are around 48px, list rows around 52px. Pages with more than about 20 rows of data get `.table.compact`.
- Page structure, top to bottom: `.page-head` (breadcrumbs, `h1`, one line of description, actions on the right), then sections with `.section-head`. Content is capped at `--gr-content-max`, prose at `--gr-prose-max`.
- Sidebar navigation is at most two levels. Group headers are `.overline`.
- Every screen works at 375px wide: the sidebar becomes a drawer, `.fields-2` stacks, tables scroll inside `.table-wrap`, dialogs become bottom sheets.

## Motion
- Transitions only on `color`, `background-color`, `box-shadow`, `opacity`, `translate`, `scale`. Never `all`.
- Durations: `--gr-dur-fast` for hover and press, `--gr-dur` for menus and toggles, `--gr-dur-slow` for dialogs, sheets and toasts. Easing `--gr-ease-out` for anything entering, `--gr-ease-in-out` for anything moving between two places.
- Buttons scale to `--gr-press-scale` when pressed. Nothing bounces.
- `base.css` already handles reduced motion. Hover effects sit inside `@media (hover: hover)`.

## Interaction and accessibility
- Every interactive element shows `:focus-visible` with the 2px `--gr-border-focus` outline. Removing an outline without a replacement fails the step.
- Hit areas are at least 40px even when the visible control is smaller (`.btn.icon::after` shows how).
- Native elements first: `<dialog>` for modals, the `popover` attribute for menus, `<select>` for short lists, radios for segmented controls, `<details>` for disclosure. Custom widgets only where the native one can't do the job, and then with the ARIA pattern from the APG.
- Every form control has a visible `<label>`. Placeholder text is an example, never the label.
- Disabled buttons explain themselves nearby, or stay enabled and show the error on click.
- Use logical properties (`margin-inline-start`, `inset-inline-end`, `text-align: start`) so RTL works with only `dir="rtl"`.

## Icons
- One icon set per app, stroke icons, 16px in controls and 20px in empty states, `stroke-width` 1.5 to 1.75. Lucide is the default.
- An icon next to a label is decorative (`aria-hidden="true"`). An icon-only button needs `aria-label`.

## Logos and images
- Every logo has to read in both themes. Check each one in dark mode.
- If it is a single-color mark, use SVG with `fill="currentColor"` so it takes the text color. For a PNG, use a CSS mask over `--gr-fg-primary`.
- If it is multi-color artwork, ship a light and a dark file and switch between them with `<picture><source media="(prefers-color-scheme: dark)" srcset="logo-dark.png">`.
- `filter: invert()` is a last resort. It turns brand colors into their opposites.

## Copy that comes with the visual change
Leave the app's wording alone, except in these three places, where layout and wording are the same thing:
- Button labels become verbs that name the outcome ("Close registration", not "OK").
- Empty states say what goes here and how to add the first one.
- Errors say what went wrong and how to fix it, next to the field.
