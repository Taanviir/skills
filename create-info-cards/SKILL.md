---
name: create-info-cards
description: Turn long content such as a YouTube video, a web article or a PDF into a set of 1080x1350 image cards, shown in an Instagram-style collage HTML page with PNG export. Use when the user wants to share the key points of something long with friends as images, or asks for info cards, a carousel or "something easy to digest at a glance".
---

# create-info-cards

A set of info cards is a run of portrait images with one idea per card. Someone should be able to read each card in a chat app without opening anything. The output is one local HTML file that shows the cards in a collage grid, each with a Save PNG button. Write the file into the current working directory and keep it local.

Paths below are relative to this skill's folder.

## 1. Get the source

```bash
bash scripts/fetch_source.sh "<url or file.pdf>" <scratch-dir>
```

The script writes `<scratch-dir>/source.txt`. For YouTube it holds the captions with a timestamp each minute. For an article or a PDF it holds the extracted text. Use a scratch directory, not the working directory, and read all of `source.txt`. If the script fails on an article, use WebFetch. If a PDF has no text layer, use the pdf skill's OCR.

Done when you have read the whole source.

## 2. Fact sheet, confirmed

Pull out every number, date, name, duration and quotable line the cards might use. Note the timestamp or section for each one. Check the headline numbers against each other, so a "7 months" claim matches the dates. Auto-captions garble names and products, so list every proper noun you are unsure of.

Send the user one short message with four parts:
- the fact sheet
- the names you are unsure of
- your proposed angle, meaning who the cards are for and the one thing they should take away
- the planned card count from step 3

Wait for their corrections.

Done when the user has confirmed the facts, the angle and the count.

## 3. Storyboard

The source sets the card count. Plan one card per idea worth sharing, plus the cover. A short article may need 3 or 4 cards, and a long interview may need 10 or more. Past about 12, merge or cut the weakest ideas, because few people swipe further. If the user asked for more or fewer at step 2, use their number.

Card 1 is the hook. It carries the headline and the 3 or 4 numbers that make someone swipe. Every other card carries one idea and one component from `references/components.md`. Vary the components across the set so the grid reads as a collage. Budget about 70 to 90 words per card, and use the component table's heights to plan against the body's 1,100px.

Copy rules:
- Use only facts from the confirmed fact sheet. Quote only words the source actually contains.
- Write short, plain sentences, and give list items a bold lead-in that ends in a period.
- Run the unslop skill over the copy if it is available.
- Every card footer cites the source and date and shows `NN / total`.

## 4. Design for the topic

Read `references/design.md`. Then pick the subject's world, the palette, the three fonts and the `.card-top` motif. Copy `assets/template.html`, write those choices into its `:root` block, and put the one-line layout comment above it. Build the cards from the storyboard.

## 5. Fit check

```bash
python3 -I scripts/check.py <page.html> fit
```

The script prints each card's overflow and the free space above its footer, measured at full size. Fix an OVERFLOW card by cutting words or shrinking a component. A LOOSE card has more than 200px empty above the footer, so raise its type sizes or add a component that fits the content. Rerun the check until it prints `ALL CARDS FIT`.

Then look at the cards once.

```bash
python3 -I scripts/check.py <page.html> shot <scratch-dir>/shot.png
```

Read the PNG and fix what the numbers miss, such as a lone word on a last line, a label clipped inside a bar, a broken chip or clashing colors. If you change anything, rerun `fit`.

Done when `fit` prints `ALL CARDS FIT` and the screenshot shows no visible defects.

## 6. Export check and hand-off

```bash
python3 -I scripts/check.py <page.html> export
```

The check must print `ok: True`. Then give the user three things:
- the path to open, which on WSL is `file://wsl.localhost/$WSL_DISTRO_NAME/<absolute path>`
- the card list, one line per card
- every name or number from the fact sheet that is still unconfirmed

Render every check with `check.py`, which runs headless Chromium. Open a visible browser only if the user asks.
