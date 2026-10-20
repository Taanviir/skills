import re, sys
src, out = sys.argv[1], sys.argv[2]
lines, seen, last_ts = [], set(), -999
cur_ts = 0
for raw in open(src, encoding="utf-8"):
    m = re.match(r"(\d+):(\d+):(\d+)\.\d+ -->", raw)
    if m:
        cur_ts = int(m[1])*3600 + int(m[2])*60 + int(m[3]); continue
    t = re.sub(r"<[^>]+>", "", raw).strip()
    if not t or t.startswith(("WEBVTT", "Kind:", "Language:")) or "align:" in t: continue
    if t in seen: continue
    seen.add(t)
    if cur_ts - last_ts >= 60:
        h, r = divmod(cur_ts, 3600); mm, ss = divmod(r, 60)
        lines.append(f"\n\n[{h:01d}:{mm:02d}:{ss:02d}] "); last_ts = cur_ts
    lines.append(t + " ")
open(out, "w", encoding="utf-8").write("".join(lines).strip() + "\n")
