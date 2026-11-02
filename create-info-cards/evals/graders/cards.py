"""Deterministic graders for create-info-cards eval runs.

Usage:
  python3 -I cards.py built <run-dir> <fixture or -> <min-cards> <max-cards> [replies-file]
  python3 -I cards.py no-page <run-dir>

built    one card page exists, every card fits, the PNG export works, the card count is in
         range, and every number on a card appears in the source fixture. A fixture of - skips
         the number check, for sources fetched live such as a YouTube video. Numbers in the
         replies file also count, since the user confirmed the fact sheet in those replies.
         A number that is the sum or difference of two source numbers passes as derived and is
         listed in the output. The top strip is decoration and is not checked
no-page  the run stopped before building, so no card page exists yet
"""
import glob
import html
import os
import re
import subprocess
import sys

CARD_RE = re.compile(r'<article class="card(?:\s[^"]*)?"')
SKILL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECK = os.path.join(SKILL, "scripts", "check.py")


def fail(msg):
    print("FAIL", msg)
    sys.exit(1)


def pages(run_dir):
    found = []
    for path in glob.glob(os.path.join(run_dir, "**", "*.html"), recursive=True):
        if "/fixtures/" in path or os.path.basename(path).startswith("._check_"):
            continue
        if CARD_RE.search(open(path, encoding="utf-8", errors="ignore").read()):
            found.append(path)
    return found


def source_text(fixture):
    if fixture.endswith(".pdf"):
        return subprocess.run(["pdftotext", fixture, "-"], capture_output=True, text=True).stdout
    raw = open(fixture, encoding="utf-8").read()
    return html.unescape(re.sub(r"<[^>]+>", " ", raw))


WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
         "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
TENS = {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100}


def numbers(text):
    """Numbers as digit strings without separators: '$1,850' -> '1850', '1.42 million' -> '1.42'.
    Spelled-out numbers count too, so 'three berths' allows a 3 on a card."""
    found = {m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}
    for word in re.findall(r"[a-z]+", text.lower()):
        if word in WORDS:
            found.add(str(WORDS.index(word)))
        elif word in TENS:
            found.add(str(TENS[word]))
    return found


def is_derived(n, allowed):
    try:
        target = float(n)
    except ValueError:
        return False
    vals = [float(a) for a in allowed if re.fullmatch(r"\d+(?:\.\d+)?", a)]
    return any(abs(a - b - target) < 1e-9 or abs(a + b - target) < 1e-9 for a in vals for b in vals)


def card_texts(page):
    raw = open(page, encoding="utf-8").read()
    cards = re.findall(CARD_RE.pattern + r"[\s\S]*?</article>", raw)
    texts = []
    for c in cards:
        c = re.sub(r'<div class="card-foot">[\s\S]*?</div>', " ", c)
        c = re.sub(r'<div class="card-top"[^>]*>[\s\S]*?</div>', " ", c)
        c = re.sub(r"<style[\s\S]*?</style>|<script[\s\S]*?</script>", " ", c)
        texts.append(html.unescape(re.sub(r"<[^>]+>", " ", c)))
    return texts


def built(run_dir, fixture, lo, hi, replies=None):
    found = pages(run_dir)
    if len(found) != 1:
        fail(f"expected one card page, found {len(found)}: {found}")
    page = found[0]

    fit = subprocess.run([sys.executable, "-I", CHECK, page, "fit"], capture_output=True, text=True)
    if fit.returncode != 0:
        fail("fit check:\n" + fit.stdout)
    export = subprocess.run([sys.executable, "-I", CHECK, page, "export"], capture_output=True, text=True)
    if export.returncode != 0:
        fail("export check: " + export.stdout + export.stderr)

    texts = card_texts(page)
    if not lo <= len(texts) <= hi:
        fail(f"{len(texts)} cards, expected {lo} to {hi}")

    traced = "number check skipped"
    if fixture != "-":
        allowed = numbers(source_text(fixture))
        if replies:
            allowed |= numbers(open(replies, encoding="utf-8").read())
        unknown = {n for t in texts for n in numbers(t)} - allowed
        derived = {n for n in unknown if is_derived(n, allowed)}
        invented = sorted(unknown - derived, key=len)
        if invented:
            fail(f"numbers on cards that are not in the source: {invented}")
        traced = "every number traced to the source"
        if derived:
            traced += f" (derived: {', '.join(sorted(derived, key=len))})"

    print(f"PASS {os.path.basename(page)}: {len(texts)} cards, all fit, export ok, {traced}")


def no_page(run_dir):
    found = pages(run_dir)
    if found:
        fail(f"a card page was built before the fact sheet was confirmed: {found}")
    print("PASS no card page built")


if __name__ == "__main__":
    if len(sys.argv) in (6, 7) and sys.argv[1] == "built":
        built(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]), *sys.argv[6:])
    elif len(sys.argv) == 3 and sys.argv[1] == "no-page":
        no_page(sys.argv[2])
    else:
        sys.exit(__doc__)
