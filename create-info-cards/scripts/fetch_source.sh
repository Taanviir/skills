#!/usr/bin/env bash
# Usage: fetch_source.sh <youtube-url | article-url | file.pdf> <out-dir>
# Writes <out-dir>/source.txt. Downloads go into <out-dir>/raw/.
set -euo pipefail
src="$1"; out="$2"
here="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$out/raw"

case "$src" in
  *youtube.com/*|*youtu.be/*)
    # Use the latest yt-dlp because older builds break on YouTube. Captions often download even when no video format does.
    uvx yt-dlp@latest --skip-download --ignore-no-formats-error \
      --write-subs --write-auto-subs --sub-langs "en,en-orig" --sub-format vtt \
      --print "%(title)s" --no-simulate -o "$out/raw/video.%(ext)s" "$src" > "$out/raw/title.txt"
    vtt="$(ls "$out"/raw/video.en.vtt "$out"/raw/video.en-orig.vtt 2>/dev/null | head -1)"
    [ -n "$vtt" ] || { echo "No English captions found" >&2; exit 1; }
    python3 -I "$here/vtt2txt.py" "$vtt" "$out/source.txt"
    sed -i 's/&gt;/>/g; s/&lt;/</g; s/&amp;/\&/g' "$out/source.txt"
    echo "Title: $(cat "$out/raw/title.txt")"
    ;;
  *.pdf|*.PDF)
    pdftotext -layout "$src" "$out/source.txt"
    ;;
  http://*|https://*)
    uvx trafilatura --output-format txt --with-metadata -u "$src" > "$out/source.txt"
    ;;
  *)
    echo "Unknown source type: $src" >&2; exit 1
    ;;
esac
wc -w "$out/source.txt"
