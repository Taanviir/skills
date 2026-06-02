---
name: project-presentation
description: Generate a single self-contained HTML slide deck that presents a software project, using the repository itself as the source of truth for content, brand colors, and identity. Use when the user asks to "make a presentation", "slide deck", "project overview/pitch", "present this project", or wants a shareable one-file HTML deck about a codebase.
---

# Project Presentation Builder

Produce **one self-contained `.html` file** — an interactive, keyboard-navigable slide deck that
explains a software project to a stakeholder audience (leadership, committee, client, new team
member). Everything (CSS + JS) is inline; the file opens by double-clicking, no server or build step.

The repository is the source of truth. Read it first, infer the story, then write the deck. Do not
invent features, metrics, or status — only present what the repo actually supports.

## Workflow

### 1. Gather project context
Read what the repo tells you about itself. Prioritize, in order:
- `README.md` / `docs/` — the elevator pitch, features, architecture, status.
- `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` etc. — name, description, deps (reveals the stack).
- Entry points and top-level dirs — what the system actually does and how it's structured.
- `CLAUDE.md`, `CONTRIBUTING.md`, ADRs, roadmap/TODO, recent CHANGELOG or git log — status and direction.

Extract: the **project name**, a **one-sentence pitch**, the **3–4 things it delivers**, **how it works**
(the pipeline/architecture), the **headline/differentiating feature**, and **current status vs. what's next**.

If the project's purpose is genuinely ambiguous after reading, ask the user 1–2 targeted questions
(audience? the one thing to emphasize?) rather than guessing. Otherwise proceed.

### 2. Derive the brand identity
Find the project's real colors so the deck looks like it belongs to the project:
- Look for design tokens / theme files: CSS `:root` variables, `tailwind.config.*`, `theme.*`, SCSS
  variables, a design-system package, or a `--primary`/`--brand` color anywhere in the styles.
- Check `manifest.json` (`theme_color`), favicon/logo SVGs, or brand assets for the dominant hue.
- If nothing exists, pick a tasteful palette that fits the domain (e.g. fintech → deep blue/green,
  energy → gold/slate, dev tooling → indigo/violet) and tell the user what you chose.

Map the brand into the template's CSS variables: `--accent` (primary), `--accent-deep` (darker, for
gradients/text), `--accent-soft` (a light tint for icon chips). Keep `--ink`/`--muted`/`--bg` neutral
unless the brand demands otherwise. Aim for strong contrast and an executive, restrained look.

### 3. Build the deck from the template
Start from `assets/template.html` (in this skill's directory). It already contains the full styling,
entrance animations, and navigation (← →, click left/right half, dot indicators, progress bar, slide
counter). **Copy its CSS and `<script>` verbatim** — only swap colors and content.

Replace every `{{PLACEHOLDER}}` with real content. The default 5-slide arc works for most projects:
1. **Cover** — project name, context/org line, one-sentence pitch, optional tagline.
2. **What it delivers** — 3–4 cards, each a concrete capability (not a marketing adjective).
3. **How it works** — a 3–4 step pipeline + a few grounding bullets (what's reliable/auditable/notable).
4. **Headline feature** — the differentiator, with a dark "Why this matters" callout box.
5. **Status & design** — design principles on the left; "Working today" (with `live` tag) vs "Next" on the right.

Adapt freely: add or drop slides, reorder, or reuse the component classes (`.card`, `.step`,
`.feature`, `.two`, `.grid`, `.tag`) to fit the project. Keep slide count tight (4–7). The included
SVG icons are generic line icons — swap the `<path>`/`<rect>` for ones that match each capability.

### 4. Content quality bar
- **Specific, not generic.** "Deterministic price engine over S&P benchmarks" beats "Powerful processing."
- **Audience = decision-makers.** Lead with value and outcomes; keep jargon minimal and explained.
- **Honest status.** Only tag things `live` if the repo shows they actually work. Put aspirational items under "Next."
- **Tight copy.** Headlines short; card descriptions one or two sentences; bullets scannable.
- **Bilingual / RTL** if the project is (the source example used an Arabic tagline) — mirror the project's languages.

### 5. Output
- Write the file to the **project's** root (not this skill's directory), named like
  `<project-slug>-presentation.html` (e.g. `petroleum-ai-presentation.html`).
- The file must be fully self-contained: no external CSS/JS/CDN/font/image requests. If a logo is
  essential, inline it as an SVG or a base64 data URI.
- Tell the user the path and how to view it (open in a browser, or `python3 -m http.server` then visit
  the file). Note the navigation: arrow keys / click / dots, `Home`/`End` to jump.

## Reference
`assets/template.html` — the working scaffold with all placeholders. The styling and navigation are
proven; your job is accurate content and on-brand colors, not rebuilding the machinery.
