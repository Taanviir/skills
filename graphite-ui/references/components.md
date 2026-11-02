# Components

Every recipe is in `assets/components.css` under a `/* ===== name */` header. `assets/preview.html` shows each one with real markup; read its markup when you need the expected structure.

## Two ways to apply a recipe

- **Port** (existing apps, the default). Keep the app's selector and markup. Replace the declarations on that selector with the recipe's, translating class hooks as you go (for example the recipe's `[aria-selected="true"]` becomes the app's `.active`). Delete the old declarations; don't stack new ones on top of them. Porting changes no templates, so behavior and tests survive.
- **Adopt** (new apps, or a component whose old CSS is beyond saving). Link `components.css` and use the recipe's class names in the markup.

Pick per component, not per app. Write the choice in the component map.

## Name map

Common names in existing apps and the recipe that replaces them:

| App has | Recipe |
|---|---|
| `.btn`, `.button`, `.btn-primary`, `.btn-secondary`, `.btn-outline-*`, `.btn-link` | `.btn` + `primary` / default / `ghost` |
| `.btn-danger`, `.btn-delete` | `.btn.danger` (outline) or `.btn.danger.solid` for the confirm in a destructive dialog |
| `.form-control`, `.form-input`, `.input`, `input[type=text]` | `.input` |
| `.form-select`, `.custom-select` | `.select` |
| `.form-group`, `.form-row`, `.field` | `.field`, `.fields`, `.fields-2` |
| `.form-check`, `.checkbox` | native checkbox + `.check`; toggles become `.switch` |
| `.btn-group` acting as a filter, `.toggle-group` | `.seg` |
| `.nav-tabs`, `.tabs` | `.tabs` / `.tab` |
| `.card`, `.panel`, `.box`, `.widget` | `.card` + `.card-head` / `.card-body` / `.card-foot` |
| `.list-group`, `.list-item` | `.list` + `.list-row` |
| `.table`, `.data-table`, `.datatable` | `.table-wrap` + `.table` |
| `.badge`, `.label`, `.tag`, `.pill` | `.badge` + tone |
| `.chip`, `.filter-chip`, a toggle in a row of filters | `.chip` with `aria-pressed` |
| `.bottom-nav`, `.tab-bar`, `.mobile-nav` | `.tabbar` + `.tabbar-item`, `.tabbar-add` |
| `.carousel`, `.swiper`, `.slider` of pages | `.pager` + `.dots` |
| a sideways scrolling strip of chips or cards | `.scroll-row` |
| `.highlight`, `.just-saved`, a yellow-fade | `.flash` |
| a colored word or dot showing state | `.status` + tone |
| `.alert`, `.callout`, `.banner`, `.flash` | `.notice` + tone |
| `.modal`, `.popup`, SweetAlert, `confirm()` | native `<dialog class="dialog">` |
| `.dropdown-menu`, `.context-menu` | `.menu` + `.menu-item` with the `popover` attribute |
| `.toast`, `.snackbar`, `.notification` | `.toast-region` + `.toast` |
| `.stat`, `.kpi`, `.metric`, `.counter` | `.stats` + `.stat` |
| `.navbar`, `.header`, `.top-nav` | `.topbar` |
| `.sidebar`, `.side-nav`, `.drawer` | `.sidebar` + `.nav` + `.nav-item` |
| `.page-header`, `.page-title`, `.hero` inside the app | `.page-head` |
| `.empty`, `.no-data`, "No results" text | `.empty` |
| `.loader`, `.spinner` | `.spinner`; for content loading, `.skeleton` in the content's shape |

Anything not in the table is built from tokens using the nearest recipe as the pattern. If two screens need the same new pattern, write it once as a recipe in the app's own stylesheet.

## Recipe notes

- **Button.** One `primary` per view. Icon-only buttons are `.btn.icon` with an `aria-label`. A link that looks like a button is an `<a class="btn">`; a button that navigates should be a link.
- **Inputs.** The edge is `--gr-border-control` (3:1). On focus the border goes transparent and a 2px focus outline takes its place, so the input doesn't shift. Invalid state is `aria-invalid="true"` plus `.error` text.
- **Select.** The chevron is drawn with gradients so it follows the theme. Don't swap in an SVG data URL; a hardcoded hex in it breaks dark mode.
- **Segmented.** Native radios inside labels, so arrow keys and forms work for free.
- **Table.** The header is sticky inside `.table-wrap`. Numeric columns get `.num` (end-aligned, tabular). Row actions go in a last column of `.btn.icon` buttons that open a `.menu`. A sortable header uses a `<button>` inside the `th`, plus `aria-sort` on the `th`.
- **Status vs badge.** `.status` (dot plus word) is for a state in a table cell or row. `.badge` is for a label or category. Neither uses color alone.
- **Dialog.** `<dialog class="dialog">` opened with `showModal()`. Add `closedby="any"` for light dismiss. On narrow screens it becomes a bottom sheet. Destructive confirms name the action in the title and the button. Under 640px it is a bottom sheet that slides up and back down; keep its content rendered while it closes (render the form always, not only while open), or an empty sheet slides away.
- **Menu.** `<div class="menu" popover id="m">` opened by `<button popovertarget="m">`. Position it with CSS anchor positioning where supported, or with the app's existing positioning library.
- **Toast.** One persistent `.toast-region` with `aria-live="polite"` in the layout; swap the text in. Toasts confirm; errors that need action go in a `.notice` where the problem is. One toast at a time: a new one replaces the old. About 3s for a message, 5s when it carries an action such as Undo; the action closes it. Above a `.tabbar` the region lifts on its own.
- **Shell.** `.app` > `.sidebar` + `.main` > `.topbar` + `.content`. Under 960px the sidebar becomes a drawer toggled by `data-open="true"`. The app's existing toggle script only needs to set that attribute.
- **Tab bar.** `<nav class="tabbar">` as the last child of the shell, with `.tabbar-item` links carrying `aria-current="page"` and at most one `.tabbar-add` button (`<span>` around its icon) in the middle. Up to five destinations, every one with a visible label.
- **Chip.** A `<button class="chip" aria-pressed>` for a filter that is on or off. A row of them goes in `.scroll-row`.
- **Pager.** `.pager` holds full-width pages that snap; `.dots` under it has one button per page, `aria-current="true"` on the one in view, and a tap scrolls to its page.
- **Flash.** Add `.flash` to a row for about 3s after it is saved, added or restored. It is an animation, so remove and re-add it to replay.
- **Folded sidebar.** On desktop the sidebar can fold to icons. Save the choice in `localStorage` and set `data-sidebar="collapsed"` on `<html>` from a small inline script before first paint, so it never flashes open. Wrap each label (and its count) in `.fold`, and add a `.fold-dot` to rows that carry a count. Parts with no icon of their own, such as a list of projects, get `.fold-hide` so they also leave the tab order. A folded row still needs a name: `.fold` only fades, so the label still names the row for screen readers. Show a `.tooltip` to its right on hover and focus, and keep `aria-label` on icon-only buttons. Put the toggle at the foot of the sidebar with `aria-keyshortcuts="["`, and bind `[`.
- **Charts.** Series colors come from `--gr-series-*` in order. Gridlines use `--gr-border-separator`, axis text `--gr-fg-secondary` at `caption` size. Each series also gets a second cue: a direct label, a dash pattern or a marker. A `<canvas>` chart takes its width from CSS, so set its drawing size from that CSS size times `devicePixelRatio`, and again on resize. A fixed-size canvas stretched to full width renders blurry.
