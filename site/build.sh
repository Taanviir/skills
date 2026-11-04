#!/usr/bin/env bash
# Assembles the GitHub Pages site into _site/. Pages runs this; run it locally to preview.
# To refresh the eval snapshot: python3 -I evals/report.py <results-dir> --compare <older-dir> --out site/evals
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site
mkdir -p _site/graphite-ui
cp -r site/evals _site/
python3 -I - <<'PY'
import json, re
s = json.load(open("site/evals/summary.json"))
values = {k: s[k] for k in ("passed", "runs", "cases")}
values["cost"] = f"{s['cost']:.2f}"
for name, v in s["skills"].items():
    values.update({f"skills.{name}.{k}": v[k] for k in ("passed", "runs")})
    values[f"skills.{name}.tone"] = "success" if v["passed"] == v["runs"] else "warning"
page = re.sub(r"\{\{([\w.-]+)\}\}", lambda m: str(values[m.group(1)]), open("site/index.html", encoding="utf-8").read())
open("_site/index.html", "w", encoding="utf-8").write(page)
PY
cp skills/graphite-ui/assets/{tokens.css,base.css,components.css,press.js,preview.html} _site/graphite-ui/
cp site/favicon.svg _site/
# The board is copied in as is; give it the site's icon.
sed -i 's|<head>|<head><link rel="icon" href="../favicon.svg" type="image/svg+xml">|' _site/graphite-ui/preview.html
echo "_site/ ready"
