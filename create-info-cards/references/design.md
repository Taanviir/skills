# Designing a set

Every set gets its own look, taken from the subject's world. The template's colors and fonts are placeholders, so replace all of them.

## Find the world

Name the one object, document or place the source belongs to, and borrow its conventions. The motif shows up in three places. It fills the `.card-top` strip, it sets the card ground with a texture, grid or paper tone, and it restyles one component to match.

| Source is about | World to borrow | Example motif |
|---|---|---|
| An AI lab shipping a model with evals | eval spreadsheet | column letters in the top strip, a cell grid ground, pass and fail cells |
| A chef or restaurant | recipe card, kitchen ticket | a ticket stub top, a ruled index-card ground, quantities in mono |
| A fund or an earnings call | annual report, ticker | a ticker tape strip, figure tables, up and down chips |
| A historical figure | archive file | a catalogue number strip, aged paper stock, typewriter labels |
| An athlete or team | scoreboard, match program | a scoreline strip, jersey numbers as the page counter |
| A health or science study | lab report | a specimen ID strip, result ranges drawn as bars |
| A founder's story | pitch deck, cap table | funding round labels on the timeline |

## Tokens

- **Palette.** Set the ground, ink, muted, rule and one accent. Take the accent from the world, such as kitchen-ticket red, ledger green or archive sepia.
- **Type.** Pick a display face with character, a plain body face, and a mono or condensed face for labels and numbers, all from Google Fonts. Choose them for the world. A field manual suits a slab, sports suit a condensed grotesk, and an archive suits a typewriter mono.
- **Looks every AI page already has.** These are cream paper with a serif and terracotta, near-black with acid green, purple-to-blue gradients, Inter or Space Grotesk, emoji as icons, and the same rounded shadowed box on everything. Pick one only when the subject really is that world.

## The set reads as one series

- Every card has the same top strip, footer, margins and page counter.
- Card 1 is the hook, with the boldest headline and the numbers that make someone swipe.
- Change the component from card to card so the grid view looks like a collage. A stats card can sit next to a timeline, a quote or a chart.
- The gallery page color, `--page`, frames the collage. Pick one that sets the cards off.
- The cards are images, so one fixed look is enough and dark mode is unnecessary.
