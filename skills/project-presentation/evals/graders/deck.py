"""Deterministic graders for project-presentation eval runs.

Usage:
  python3 -I deck.py built <run-dir> <slug> <brand-hex or ->
  python3 -I deck.py phone <run-dir>

built  exactly one <slug>-presentation.html sits in the project root, it loads nothing from the
       network, every placeholder is filled, it has 4 to 7 slides, it uses the project's brand
       color, and its script parses. A brand of - skips the color check, for projects with
       no brand color of their own
phone  no slide of the deck is wider than a 390px phone screen, so the page never scrolls sideways.
       Needs headless Chromium from Playwright's cache, or CHROME=/path/to/chrome
"""
import glob
import json
import os
import re
import subprocess
import sys
import tempfile


def fail(msg):
    print("FAIL", msg)
    sys.exit(1)


def built(run_dir, slug, brand):
    decks = glob.glob(os.path.join(run_dir, "*presentation*.html"))
    if len(decks) != 1:
        fail(f"expected one deck in the project root, found {[os.path.basename(d) for d in decks]}")
    deck = decks[0]
    if os.path.basename(deck) != f"{slug}-presentation.html":
        fail(f"deck is named {os.path.basename(deck)}, expected {slug}-presentation.html")
    html = open(deck, encoding="utf-8").read()

    remote = re.findall(r"""(?:src|href)\s*=\s*["']((?:https?:)?//[^"']+)""", html) + re.findall(r"""url\(\s*["']?(https?://[^)"']+)""", html)
    remote += re.findall(r"""@import\s+["']?(https?://[^"';]+)""", html)
    if remote:
        fail(f"deck loads from the network: {remote[:5]}")

    left = sorted(set(re.findall(r"\{\{[A-Z0-9_]+\}\}", html)))
    if left:
        fail(f"unfilled placeholders: {left}")

    slides = len(re.findall(r"""<section[^>]*class=["'][^"']*\bslide\b""", html))
    if not 4 <= slides <= 7:
        fail(f"{slides} slides, expected 4 to 7")

    if brand != "-" and brand.lower().lstrip("#") not in html.lower():
        fail(f"brand color {brand} is not used")

    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", html)
    for s in scripts:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(s)
        check = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        os.unlink(f.name)
        if check.returncode != 0:
            fail(f"deck script does not parse: {check.stderr.strip()[:200]}")

    print(f"PASS {os.path.basename(deck)}: {slides} slides, self-contained" + ("" if brand == "-" else ", brand color used"))


# Loads the deck in a 390px iframe, shows each slide in turn and reports any wider than the frame. A slide
# can scroll on its own, so its width is measured as well as the page's.
PHONE_PAGE = """<!doctype html><body><iframe id="f" src="%s" style="width:390px;height:844px;border:0"></iframe><pre id="o"></pre>
<script>f.onload = () => setTimeout(() => {
  const d = f.contentDocument, slides = [...d.querySelectorAll('.slide')], wide = [];
  slides.forEach((s, n) => {
    slides.forEach((x) => x.classList.remove('active')); s.classList.add('active');
    const w = Math.max(d.documentElement.scrollWidth, s.scrollWidth);
    if (w > d.documentElement.clientWidth) wide.push([n + 1, w]);
  });
  o.textContent = JSON.stringify({ slides: slides.length, wide });
}, 800);</script></body>"""


def chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    found = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
    if not found:
        fail("no Chromium found; set CHROME=/path/to/chrome")
    return found[-1]


def phone(run_dir):
    decks = glob.glob(os.path.join(run_dir, "*presentation*.html"))
    if len(decks) != 1:
        fail(f"expected one deck in the project root, found {[os.path.basename(d) for d in decks]}")
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "phone.html")
        with open(page, "w", encoding="utf-8") as f:
            f.write(PHONE_PAGE % ("file://" + os.path.abspath(decks[0])))
        dom = subprocess.run([chrome(), "--headless=new", "--no-sandbox", "--allow-file-access-from-files",
                              # Its own profile, or a parallel Chrome takes the page and this one prints nothing.
                              f"--user-data-dir={os.path.join(tmp, 'profile')}",
                              "--virtual-time-budget=4000", "--dump-dom", "file://" + page],
                             capture_output=True, text=True, timeout=120).stdout
    m = re.search(r'<pre id="o">(.*?)</pre>', dom)
    if not m or not m.group(1):
        fail("the deck did not load in headless Chromium")
    r = json.loads(m.group(1).replace("&quot;", '"'))
    if not r["slides"]:
        fail("no slides found")
    if r["wide"]:
        fail("too wide for a 390px phone: " + ", ".join(f"slide {n} is {w}px" for n, w in r["wide"]))
    print(f"PASS {os.path.basename(decks[0])}: all {r['slides']} slides fit a 390px phone")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "built":
        built(*sys.argv[2:])
    elif len(sys.argv) == 3 and sys.argv[1] == "phone":
        phone(sys.argv[2])
    else:
        sys.exit(__doc__)
