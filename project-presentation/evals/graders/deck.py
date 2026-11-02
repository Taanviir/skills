"""Deterministic graders for project-presentation eval runs.

Usage:
  python3 -I deck.py built <run-dir> <slug> <brand-hex or ->

built  exactly one <slug>-presentation.html sits in the project root, it loads nothing from the
       network, every placeholder is filled, it has 4 to 7 slides, it uses the project's brand
       color, and its script parses. A brand of - skips the color check, for projects with
       no brand color of their own
"""
import glob
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


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "built":
        built(*sys.argv[2:])
    else:
        sys.exit(__doc__)
