#!/usr/bin/env bash
# Renders library-report.html to library-report.pdf with headless Chromium.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
chrome="${CHROME:-$(ls -d ~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome 2>/dev/null | sort | tail -1)}"
"$chrome" --headless=new --no-sandbox --no-pdf-header-footer \
  --print-to-pdf="$here/library-report.pdf" "file://$here/library-report.html" 2>/dev/null
pdftotext "$here/library-report.pdf" - | head -3
