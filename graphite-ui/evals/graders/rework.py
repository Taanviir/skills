"""Deterministic graders for graphite-ui eval runs.

Usage:
  python3 -I rework.py unchanged <run-dir> <fixture-dir>
  python3 -I rework.py reworked <run-dir> <fixture-dir>
  python3 -I rework.py knobs <run-dir> <hue> <tolerance>

unchanged  every fixture file is byte-for-byte the same and no app file was added
reworked   tokens are installed and linked, the audit exits 0, contrast passes with the app's
           knobs, the old tokens and dark-mode mechanism are gone, every element id and visible
           string is still in the markup, and the scripts parse and only reference ids that exist
knobs      the app's own CSS sets --gr-accent-h within <tolerance> degrees of <hue>
"""
import glob
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

SKILL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
IGNORED = (".claude", ".git", "graphite-ui")


def fail(msg):
    print("FAIL", msg)
    sys.exit(1)


def app_files(root):
    out = {}
    for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
        rel = os.path.relpath(path, root)
        if os.path.isfile(path) and not rel.split(os.sep)[0] in IGNORED and "graphite-ui" not in rel.split(os.sep):
            out[rel] = path
    return out


class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.texts, self.labels, self.scripts, self._in_script = set(), [], set(), [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if a.get("aria-label"):
            self.labels.add(" ".join(a["aria-label"].split()))
        self._in_script = tag == "script" and "src" not in a

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.scripts.append(data)
        elif data.strip():
            self.texts.append(" ".join(data.split()))


def markup(path):
    m = Markup()
    m.feed(open(path, encoding="utf-8").read())
    return m


def unchanged(run_dir, fixture):
    want, got = app_files(fixture), app_files(run_dir)
    added = sorted(set(got) - set(want))
    if added:
        fail(f"files added: {added}")
    for rel, path in want.items():
        if rel not in got:
            fail(f"file deleted: {rel}")
        if open(path, "rb").read() != open(got[rel], "rb").read():
            fail(f"file changed: {rel}")
    print("PASS app unchanged")


def reworked(run_dir, fixture):
    files = app_files(run_dir)
    tokens = glob.glob(os.path.join(run_dir, "**", "graphite-ui", "tokens.css"), recursive=True)
    if not tokens:
        fail("no graphite-ui/tokens.css installed in the app")

    css = {r: open(p, encoding="utf-8").read() for r, p in files.items() if r.endswith(".css")}
    pages = {r: p for r, p in files.items() if r.endswith(".html")}
    linked = " ".join(open(p, encoding="utf-8").read() for p in pages.values()) + " ".join(css.values())
    if "tokens.css" not in linked:
        fail("tokens.css is installed but no page or stylesheet loads it")

    audit = subprocess.run(
        ["node", os.path.join(SKILL, "scripts", "audit.mjs"), ".", "--ignore", ".claude,.git", "--json"],
        cwd=run_dir, capture_output=True, text=True,
    )
    if audit.returncode != 0:
        found = json.loads(audit.stdout)["findings"] if audit.stdout.startswith("{") else audit.stderr
        fail(f"audit is not clean: {found[:10] if isinstance(found, list) else found}")

    all_css = "\n".join(css.values())
    h = re.search(r"--gr-accent-h\s*:\s*([\d.]+)", all_css)
    c = re.search(r"--gr-accent-c\s*:\s*([\d.]+)", all_css)
    args = (["--hue", h.group(1)] if h else []) + (["--chroma", c.group(1)] if c else [])
    contrast = subprocess.run(["node", os.path.join(SKILL, "scripts", "contrast.mjs"), *args], capture_output=True, text=True)
    if contrast.returncode != 0:
        fail(f"contrast fails with knobs {args}")

    old = set()
    for path in glob.glob(os.path.join(fixture, "**", "*.css"), recursive=True):
        old |= set(re.findall(r"(--(?!gr-|bs-)[\w-]+)\s*:", open(path, encoding="utf-8").read()))
    still = sorted(t for t in old if re.search(re.escape(t) + r"\s*:", all_css))
    if still:
        fail(f"old tokens still defined: {still}")
    if re.search(r"body\.dark\b|\.dark\s*\{", all_css):
        fail("old .dark theme rules are still in the CSS")

    for path in glob.glob(os.path.join(fixture, "*.html")):
        rel = os.path.relpath(path, fixture)
        if rel not in pages:
            fail(f"{rel} is missing")
        before, after = markup(path), markup(pages[rel])
        lost_ids = sorted(before.ids - after.ids)
        if lost_ids:
            fail(f"{rel} lost element ids: {lost_ids}")
        # A control whose label lives on in another control's aria-label was a duplicate, such as a
        # dialog's footer Close next to its header ×.
        lost_text = [t for t in before.texts if t not in after.texts and t not in after.labels]
        if lost_text:
            fail(f"{rel} lost visible text: {lost_text[:5]}")
        if "data-bs-theme" in open(pages[rel], encoding="utf-8").read():
            fail(f"{rel} still sets data-bs-theme")

        ids = after.ids
        sources = after.scripts + [open(p, encoding="utf-8").read() for r, p in files.items() if r.endswith(".js")]
        for src in sources:
            for ref in re.findall(r"getElementById\(['\"]([\w-]+)['\"]\)", src):
                if ref not in ids:
                    fail(f"script references #{ref}, which is no longer in {rel}")

    for rel, path in files.items():
        if rel.endswith(".js"):
            check = subprocess.run(["node", "--check", path], capture_output=True, text=True)
            if check.returncode != 0:
                fail(f"{rel} does not parse: {check.stderr.strip()}")
            if re.search(r"['\"]#[0-9a-fA-F]{3,8}['\"]", open(path, encoding="utf-8").read()):
                fail(f"{rel} still hardcodes a hex color")

    print(f"PASS reworked: audit clean, contrast ok with {args or 'default knobs'}, markup and scripts intact")


def knobs(run_dir, hue, tolerance):
    css = "\n".join(open(p, encoding="utf-8").read() for r, p in app_files(run_dir).items() if r.endswith(".css"))
    m = re.search(r"--gr-accent-h\s*:\s*([\d.]+)", css)
    if not m:
        fail("the app CSS does not set --gr-accent-h")
    off = abs((float(m.group(1)) - float(hue) + 180) % 360 - 180)
    if off > float(tolerance):
        fail(f"--gr-accent-h is {m.group(1)}, expected {hue} within {tolerance}")
    print(f"PASS --gr-accent-h {m.group(1)} matches the brand hue {hue}")


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "knobs":
        knobs(*sys.argv[2:])
    elif len(sys.argv) == 4 and sys.argv[1] in ("unchanged", "reworked"):
        {"unchanged": unchanged, "reworked": reworked}[sys.argv[1]](sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
