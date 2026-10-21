"""Headless Chromium checks for an info-card page.

Usage: python3 -I check.py <page.html> fit|shot|export [out.png]

fit     prints each card's overflow and free space above the footer, in card pixels
shot    saves a full-page screenshot of the gallery, next to the page as _shot.png unless out.png is given
export  renders card 1 through the page's own PNG export and prints the data URL size
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

LOOSE_PX = 200

FIT_JS = """
setTimeout(() => {
  const out = [...document.querySelectorAll('.card')].map(c => {
    const b = c.querySelector('.card-body');
    const s = c.getBoundingClientRect().width / 1080;
    const cs = getComputedStyle(b);
    const inner = b.clientHeight - parseFloat(cs.paddingTop);
    const rects = [...b.children].map(k => k.getBoundingClientRect());
    const spacers = [...b.querySelectorAll(':scope > .spacer')]
      .reduce((h, k) => h + k.getBoundingClientRect().height, 0);
    const used = (Math.max(...rects.map(r => r.bottom)) - Math.min(...rects.map(r => r.top)) - spacers) / s;
    return { name: c.dataset.name, overflow: b.scrollHeight - b.clientHeight, free: Math.round(inner - used) };
  });
  document.title = 'RESULT ' + JSON.stringify(out);
}, 1500);
"""

EXPORT_JS = """
setTimeout(async () => {
  try {
    await document.fonts.ready;
    const u = await htmlToImage.toPng(document.querySelector('.card'),
      { width: 1080, height: 1350, pixelRatio: 1, style: { transform: 'none' } });
    document.title = 'RESULT ' + JSON.stringify({ ok: true, bytes: u.length });
  } catch (e) {
    document.title = 'RESULT ' + JSON.stringify({ ok: false, error: String(e) });
  }
}, 1500);
"""


def chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    found = sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))
    if found:
        return found[-1]
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    sys.exit("No Chromium found. Set CHROME=/path/to/chrome.")


def run(args):
    base = [chrome(), "--headless=new", "--no-sandbox", "--hide-scrollbars", "--window-size=1200,3400"]
    return subprocess.run(base + args, capture_output=True, text=True, timeout=120).stdout


def inject(page, js):
    html = open(page, encoding="utf-8").read()
    html = html.replace("</body>", f"<script>{js}</script></body>")
    # Keep the copy beside the page so relative paths still resolve.
    fd, path = tempfile.mkstemp(suffix=".html", prefix="._check_", dir=os.path.dirname(os.path.abspath(page)))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def result(page, js, budget):
    tmp = inject(page, js)
    try:
        dom = run([f"--virtual-time-budget={budget}", "--dump-dom", "file://" + tmp])
    finally:
        os.remove(tmp)
    m = re.search(r"<title>RESULT (.*?)</title>", dom, re.S)
    if not m:
        sys.exit("Check script did not report. Is there a script error on the page?")
    return json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def main():
    page, mode = sys.argv[1], sys.argv[2]
    if mode == "fit":
        rows = result(page, FIT_JS, 6000)
        bad = 0
        for r in rows:
            status = "OVERFLOW" if r["overflow"] > 0 else ("LOOSE" if r["free"] > LOOSE_PX else "ok")
            bad += status != "ok"
            print(f'{r["name"]:<32} overflow={r["overflow"]:>4}  free={r["free"]:>5}  {status}')
        print("ALL CARDS FIT" if not bad else f"{bad} card(s) need work")
        sys.exit(1 if bad else 0)
    elif mode == "shot":
        out = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(page)[0] + "_shot.png"
        run(["--virtual-time-budget=5000", f"--screenshot={out}", "file://" + os.path.abspath(page)])
        print(out)
    elif mode == "export":
        r = result(page, EXPORT_JS, 15000)
        print(r)
        sys.exit(0 if r.get("ok") else 1)
    else:
        sys.exit(__doc__)


main()
