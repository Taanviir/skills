#!/usr/bin/env bash
# Assembles the GitHub Pages site into _site/. Pages runs this; run it locally to preview.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site
mkdir -p _site/graphite-ui
cp site/index.html site/favicon.svg _site/
cp skills/graphite-ui/assets/{tokens.css,base.css,components.css,press.js,preview.html} _site/graphite-ui/
# The board is copied in as is; give it the site's icon.
sed -i 's|<head>|<head><link rel="icon" href="../favicon.svg" type="image/svg+xml">|' _site/graphite-ui/preview.html
echo "_site/ ready"
