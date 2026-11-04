#!/usr/bin/env bash
# Assembles the GitHub Pages site into _site/. Pages runs this; run it locally to preview.
# To refresh the eval snapshot: python3 -I evals/report.py <results-dir> --compare <older-dir> --out site/evals
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site
mkdir -p _site/graphite-ui
cp -r site/evals _site/
python3 -I - <<'PY'
import json
s = json.load(open("site/evals/summary.json"))
page = open("site/index.html", encoding="utf-8").read()
for k in ("passed", "runs", "cases"):
    page = page.replace("{{%s}}" % k, str(s[k]))
page = page.replace("{{cost}}", f"{s['cost']:.2f}")
open("_site/index.html", "w", encoding="utf-8").write(page)
PY
cp skills/graphite-ui/assets/{tokens.css,base.css,components.css,press.js,preview.html} _site/graphite-ui/
echo "_site/ ready"
