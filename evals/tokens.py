#!/usr/bin/env python3
"""Token and cost report per skill, built from eval results already on disk.

    python3 -I evals/tokens.py [results-dir]

Reads the <case>-<n>.json records and <case>-<n>.events.jsonl streams that run.py
writes. It never starts a session.
"""
import fnmatch
import glob
import json
import os
import re
import shlex
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_PARTS = ("references", "assets", "scripts")
READERS = {"cat", "head", "tail", "sed", "grep", "egrep", "rg", "awk", "nl", "less", "more"}
FALLBACK_BYTES_PER_TOKEN = 4.0


# ---------- skills and cases ----------

def load_skills(root):
    skills = {}
    for skill_md in sorted(glob.glob(os.path.join(root, "*", "SKILL.md"))):
        d = os.path.dirname(skill_md)
        files = {"SKILL.md": os.path.getsize(skill_md)}
        for part in SKILL_PARTS:
            for path in sorted(glob.glob(os.path.join(d, part, "*"))):
                if os.path.isfile(path):
                    files[f"{part}/{os.path.basename(path)}"] = os.path.getsize(path)
        with open(skill_md, encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"^description:\s*(.*)$", text, re.M)
        skills[os.path.basename(d)] = {"files": files, "description": m.group(1) if m else ""}
    return skills


def load_cases(root, skills):
    cases = {}
    for name in skills:
        path = os.path.join(root, name, "evals", "cases.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for case in json.load(f):
                baseline = any(g["type"] == "skill_used" and g.get("expect") is False for g in case["graders"])
                cases[case["name"]] = {"skill": name, "baseline": baseline}
    return cases


# ---------- which skill files a tool call loads ----------

def _match_skill_file(token, skills, base):
    """Resolve a path argument to (skill, relpath) or None. `base` is (skill, subdir) from a cd."""
    names = "|".join(re.escape(s) for s in skills)
    m = re.search(rf"(?:^|/)({names})/(SKILL\.md|(?:{'|'.join(SKILL_PARTS)})/[^/\s]+)$", token)
    if m:
        candidates = [(m.group(1), m.group(2))]
    elif base and not token.startswith("/"):
        skill, sub = base
        rel = os.path.normpath(os.path.join(sub, token)) if sub else os.path.normpath(token)
        candidates = [(skill, rel)]
    else:
        return []
    out = []
    for skill, rel in candidates:
        files = skills[skill]["files"]
        out += [(skill, f) for f in files if fnmatch.fnmatchcase(f, rel)]
    return out


def _cd_target(token, skills):
    names = "|".join(re.escape(s) for s in skills)
    m = re.search(rf"(?:^|/)({names})(?:/({'|'.join(SKILL_PARTS)}))?/?$", token)
    return (m.group(1), m.group(2) or "") if m else None


def _expand_braces(text):
    pat = re.compile(r"([^\s{}]*)\{([^{}\s]*,[^{}\s]*)\}([^\s{}]*)")
    while True:
        new = pat.sub(lambda m: " ".join(m.group(1) + p + m.group(3) for p in m.group(2).split(",")), text)
        if new == text:
            return text
        text = new


def _split_commands(command):
    """[(segment, separator after it)] split on unquoted &&, ||, ;, | and newlines."""
    segments, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == quote:
                quote = None
            elif ch == "\\" and quote == '"' and i + 1 < len(command):
                buf.append(ch)
                i += 1
                ch = command[i]
        elif ch in "'\"":
            quote = ch
        else:
            sep = next((s for s in ("&&", "||", ";", "|", "\n") if command.startswith(s, i)), None)
            if sep:
                segments.append(("".join(buf).strip(), sep))
                buf = []
                i += len(sep)
                continue
        buf.append(ch)
        i += 1
    segments.append(("".join(buf).strip(), ""))
    return segments


POSITIONAL_SCRIPT = {"sed", "grep", "egrep", "rg", "awk"}


def bash_reads(command, skills):
    """What a Bash command prints into the context.

    Returns ([(skill, rel, full)], other files read, other commands that print).
    """
    command = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\1\b", "", command, flags=re.S)
    variables = {}
    reads, others, noisy, base = [], 0, 0, None
    segments = _split_commands(command)
    for i, (seg, sep) in enumerate(segments):
        for name, value in variables.items():
            seg = re.sub(rf"\$\{{{name}\}}|\${name}\b", value, seg)
        seg = _expand_braces(seg)
        try:
            words = shlex.split(seg)
        except ValueError:
            words = seg.split()
        while words and re.fullmatch(r"\w+=\S*", words[0]):
            k, v = words.pop(0).split("=", 1)
            variables[k] = v
        if not words:
            continue
        cmd, args = os.path.basename(words[0]), words[1:]
        piped_in = i > 0 and segments[i - 1][1] == "|"
        if cmd == "cd":
            base = _cd_target(args[0], skills) if args else None
            continue
        if cmd in SILENT or piped_in:
            continue
        if cmd not in READERS or (cmd == "sed" and any(a.startswith("-i") for a in args)):
            noisy += 1
            continue
        if re.search(r"(?<![0-9&])>", seg):
            continue
        full = cmd == "cat" and sep != "|"
        positional = [a for a in args if not a.startswith("-")]
        if cmd in POSITIONAL_SCRIPT and positional:
            positional = positional[1:]
        for a in positional:
            hits = _match_skill_file(a, skills, base)
            if hits:
                reads += [(s, rel, full) for s, rel in hits]
            else:
                others += 1
    return reads, others, noisy


SILENT = {"mkdir", "cp", "mv", "rm", "export", "true", "set", "touch"}


def tool_reads(name, inp, skills):
    """([(skill, rel, full)], other files read, other output) for one tool call."""
    if name == "Skill":
        skill = str(inp.get("skill", "")).split(":")[-1]
        return ([(skill, "SKILL.md", True)] if skill in skills else []), 0, 0
    if name == "Read":
        hits = _match_skill_file(inp.get("file_path", ""), skills, None)
        full = "offset" not in inp and "limit" not in inp
        return [(s, rel, full) for s, rel in hits], (0 if hits else 1), 0
    if name == "Grep":
        return [(s, rel, False) for s, rel in _match_skill_file(inp.get("path", ""), skills, None)], 0, 0
    if name == "Bash":
        return bash_reads(inp.get("command", ""), skills)
    return [], 0, 0


# ---------- one run ----------

def _block_text(content):
    if isinstance(content, str):
        return content, False
    text, image = [], False
    for b in content or []:
        if b.get("type") == "text":
            text.append(b["text"])
        elif b.get("type") == "image":
            image = True
    return "".join(text), image


def parse_events(lines, skills):
    turns, calls, cur = [], [], None
    tool_uses, spent = {}, {}
    for line in lines:
        ev = json.loads(line)
        kind = ev.get("type")
        if kind == "assistant":
            msg = ev["message"]
            if cur is None or cur["id"] != msg["id"]:
                u = msg.get("usage", {})
                cur = {"id": msg["id"], "turn": len(turns), "blocks": [], "after_bytes": 0, "image": False,
                       "ctx": u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                       + u.get("cache_read_input_tokens", 0), "loads": []}
                calls.append(cur)
            cur["blocks"] += msg["content"]
            for b in msg["content"]:
                if b.get("type") == "tool_use":
                    tool_uses[b["id"]] = (b, cur)
        elif kind == "user" and cur is not None:
            content = ev["message"]["content"]
            for b in content if isinstance(content, list) else [{"type": "text", "text": content}]:
                if b.get("type") == "tool_result":
                    text, image = _block_text(b.get("content"))
                    cur["after_bytes"] += len(text.encode())
                    cur["image"] |= image
                    use = tool_uses.get(b.get("tool_use_id"))
                    if use:
                        use[0]["_result_bytes"] = len(text.encode())
                elif b.get("type") == "text":
                    cur["after_bytes"] += len(b["text"].encode())
                    if ev.get("isSynthetic") or "Base directory for this skill" in b["text"]:
                        cur["synthetic_bytes"] = cur.get("synthetic_bytes", 0) + len(b["text"].encode())
        elif kind == "result":
            u = ev.get("usage", {})
            # total_cost_usd keeps counting across a resumed session; usage does not.
            session_cost = ev.get("total_cost_usd") or 0
            turn_cost = session_cost - spent.get(ev.get("session_id"), 0)
            spent[ev.get("session_id")] = session_cost
            turns.append({
                "input": u.get("input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0),
                "thinking": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0),
                "cost": turn_cost, "seconds": (ev.get("duration_ms") or 0) / 1000,
            })
            cur = None
    for b, call in tool_uses.values():
        reads, others, noisy = tool_reads(b["name"], b.get("input", {}), skills)
        if reads:
            result_bytes = b.get("_result_bytes", 0)
            if b["name"] == "Skill":
                result_bytes += call.get("synthetic_bytes", 0)
            call["loads"].append({"tool": b["name"], "reads": reads, "others": others, "noisy": noisy,
                                  "result_bytes": result_bytes, "input_bytes": len(json.dumps(b.get("input", {})))})
    for c in calls:
        c["calls_in_turn_end"] = False
    for t in range(len(turns)):
        in_turn = [c for c in calls if c["turn"] == t]
        if in_turn:
            in_turn[-1]["calls_in_turn_end"] = True
    return turns, calls


def load_run(json_path, skills):
    with open(json_path, encoding="utf-8") as f:
        record = json.load(f)
    events_path = json_path[: -len(".json")] + ".events.jsonl"
    with open(events_path, encoding="utf-8") as f:
        turns, calls = parse_events(f, skills)
    fired = {r[0] for c in calls for load in c["loads"] if load["tool"] == "Skill" for r in load["reads"]}
    return {"case": record["case"], "skill": record["skill"], "run": record.get("run"),
            "turns": turns, "calls": calls, "fired": record["skill"] in fired}


def load_results(results_dir, skills):
    runs = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        if os.path.exists(path[: -len(".json")] + ".events.jsonl"):
            runs.append(load_run(path, skills))
    return runs


# ---------- calibration ----------

def _lstsq(xs, ys):
    """Solve ys ~ xs @ beta for a few columns with the normal equations."""
    n = len(xs[0])
    a = [[sum(x[i] * x[j] for x in xs) for j in range(n)] + [sum(x[i] * y for x, y in zip(xs, ys))] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(a[r][i]))
        a[i], a[p] = a[p], a[i]
        if abs(a[i][i]) < 1e-12:
            return None
        for r in range(n):
            if r != i:
                f = a[r][i] / a[i][i]
                a[r] = [v - f * w for v, w in zip(a[r], a[i])]
    return [a[i][n] / a[i][i] for i in range(n)]


SMALL_SAMPLE_BYTES = 2000


def calibrate_tokens(runs, skills):
    """Measure tokens per byte from prompt growth between API calls.

    A clean sample is an API call whose only output is one tool_use, followed by a call in the
    same turn. The next prompt is this prompt plus that tool_use and its result, so the growth
    is the tokens of those bytes plus a fixed per-call overhead. The overhead is the intercept
    of a fit over small samples, where it dominates; the ratio comes from all samples.
    A sample that loads exactly one skill file in full measures that file directly.
    """
    samples = []
    for r in runs:
        calls = r["calls"]
        for c, nxt in zip(calls, calls[1:]):
            if c["calls_in_turn_end"] or c["image"] or nxt["turn"] != c["turn"]:
                continue
            uses = [b for b in c["blocks"] if b.get("type") == "tool_use"]
            if len(uses) != 1 or len(uses) != len(c["blocks"]):
                continue
            in_bytes = len(json.dumps(uses[0].get("input", {})))
            samples.append({"x": in_bytes + c["after_bytes"], "in": in_bytes, "delta": nxt["ctx"] - c["ctx"], "call": c})
    small = [s for s in samples if s["x"] < SMALL_SAMPLE_BYTES]
    if len(small) < 5 or len(samples) == len(small):
        return None
    beta = _lstsq([[1, s["x"]] for s in small], [s["delta"] for s in small])
    if not beta:
        return None
    overhead = beta[0]
    big = [s for s in samples if s["x"] >= SMALL_SAMPLE_BYTES]
    bpt = sum(s["x"] for s in big) / sum(s["delta"] - overhead for s in big)
    measured = {}
    for s in samples:
        loads = s["call"]["loads"]
        if len(loads) != 1 or loads[0]["others"] or loads[0]["noisy"]:
            continue
        files = {(sk, rel) for sk, rel, full in loads[0]["reads"] if full}
        if len(files) == 1 and len(loads[0]["reads"]) == 1:
            measured.setdefault(files.pop(), []).append(s["delta"] - overhead - s["in"] / bpt)
    by_ext = {}
    for (sk, rel), v in measured.items():
        by_ext.setdefault(os.path.splitext(rel)[1], []).append(skills[sk]["files"][rel] / statistics.median(v))
    return {"n": len(samples), "n_small": len(small), "overhead": overhead, "bytes_per_token": bpt,
            "measured": {k: (statistics.median(v), len(v)) for k, v in measured.items()},
            "ext": {k: statistics.median(v) for k, v in by_ext.items()}}


def calibrate_prices(runs):
    """Per-token prices that best explain each turn's total_cost_usd, in $ per million tokens.

    Uncached input is a handful of tokens per call, too few to fit, so it is left out.
    """
    rows = [t for r in runs for t in r["turns"] if t["cost"]]
    if len(rows) < 4:
        return None
    keys = ("cache_write", "cache_read", "output")
    xs = [[t[k] for k in keys] for t in rows]
    beta = _lstsq(xs, [t["cost"] for t in rows])
    if not beta:
        return None
    worst = max(abs(sum(b * x for b, x in zip(beta, row)) - t["cost"]) / t["cost"] for row, t in zip(xs, rows))
    return {**{k: b * 1e6 for k, b in zip(keys, beta)}, "worst_error": worst, "n": len(rows)}


def file_tokens(skill, rel, size, cal):
    """(tokens, method) for one skill file."""
    if not cal:
        return size / FALLBACK_BYTES_PER_TOKEN, f"bytes/{FALLBACK_BYTES_PER_TOKEN:.0f}"
    if (skill, rel) in cal["measured"]:
        tokens, n = cal["measured"][(skill, rel)]
        return tokens, f"measured, {n} load{'s' if n > 1 else ''}"
    ext = os.path.splitext(rel)[1]
    if ext in cal["ext"]:
        return size / cal["ext"][ext], f"bytes/{cal['ext'][ext]:.2f} (measured {ext})"
    return size / cal["bytes_per_token"], f"bytes/{cal['bytes_per_token']:.2f} (all reads)"


# ---------- aggregation ----------

def run_totals(run):
    t = run["turns"]
    total = {k: sum(x[k] for x in t) for k in ("input", "cache_write", "cache_read", "output", "thinking", "cost", "seconds")}
    total["prompt"] = total["input"] + total["cache_write"] + total["cache_read"]
    total["calls"] = len(run["calls"])
    total["peak"] = max((c["ctx"] for c in run["calls"]), default=0)
    return total


METRICS = ("prompt", "output", "thinking", "calls", "cost", "seconds", "peak")


def med_max(runs):
    totals = [run_totals(r) for r in runs]
    return {m: (statistics.median(t[m] for t in totals), max(t[m] for t in totals)) for m in METRICS} if totals else {}


def read_counts(runs):
    """{(skill, rel): {case: [full_runs, partial_only_runs]}} over the given runs."""
    counts = {}
    for r in runs:
        seen = {}
        for c in r["calls"]:
            for load in c["loads"]:
                for skill, rel, full in load["reads"]:
                    seen[(skill, rel)] = seen.get((skill, rel), False) or full
        for key, full in seen.items():
            slot = counts.setdefault(key, {}).setdefault(r["case"], [0, 0])
            slot[0 if full else 1] += 1
    return counts


def loaded_tokens(run, skills, cal):
    """Tokens of skill files fully loaded in this run, each file once."""
    files = {(s, rel) for c in run["calls"] for load in c["loads"] for s, rel, full in load["reads"] if full}
    return sum(file_tokens(s, rel, skills[s]["files"][rel], cal)[0] for s, rel in files)


def carried_tokens(run, skills, cal):
    """(tokens of skill content loaded, prompt tokens spent re-sending it on later API calls)."""
    bpt = cal["bytes_per_token"] if cal else FALLBACK_BYTES_PER_TOKEN
    carried = spent = 0
    for c in run["calls"]:
        spent += carried
        for load in c["loads"]:
            result = load["result_bytes"] / bpt
            if load["others"] or load["noisy"]:
                full ={(s, rel) for s, rel, f in load["reads"] if f}
                result = min(result, sum(file_tokens(s, rel, skills[s]["files"][rel], cal)[0] for s, rel in full))
            carried += result
    return carried, spent


# ---------- formatting ----------

def fmt_tok(n):
    if n >= 1e6:
        return f"{n / 1e6:.2f}M"
    if n >= 1e4:
        return f"{n / 1e3:.0f}k"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return f"{n:.0f}"


def fmt(metric, v):
    if metric == "cost":
        return f"${v:.2f}"
    if metric == "seconds":
        return f"{v:.0f}s"
    if metric == "calls":
        return f"{v:g}"
    return fmt_tok(v)


def table(headers, rows, left=1):
    widths = [max(len(str(x)) for x in col) for col in zip(headers, *rows)]
    lines = []
    for i, row in enumerate([headers, *rows]):
        cells = [str(x).ljust(w) if j < left else str(x).rjust(w) for j, (x, w) in enumerate(zip(row, widths))]
        lines.append("  ".join(cells).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines)


def short(case, skill):
    prefix = {"create-info-cards": "cards-", "project-presentation": "deck-", "graphite-ui": "graphite-"}.get(skill, "")
    return case[len(prefix):] if prefix and case.startswith(prefix) else case


# ---------- report ----------

def report(results_dir, root=ROOT):
    skills = load_skills(root)
    cases = load_cases(root, skills)
    runs = load_results(results_dir, skills)
    cal = calibrate_tokens(runs, skills)
    prices = calibrate_prices(runs)
    out = [f"Token report for {results_dir}", f"{len(runs)} runs, {len({r['case'] for r in runs})} cases. "
           "Costs are the agent's total_cost_usd per turn; judge calls are left out."]

    out.append("\n== 1. Static footprint ==")
    if cal:
        out.append(f"Tokens are calibrated on {cal['n']} clean tool round trips (an API call whose only output is "
                   "one tool_use, and the growth of the next call's prompt).")
        out.append(f"Fixed cost per tool call: {cal['overhead']:.0f} tokens (intercept over the {cal['n_small']} "
                   f"calls under {SMALL_SAMPLE_BYTES} bytes). All reads average {cal['bytes_per_token']:.2f} bytes/token.")
        out.append("'measured' = prompt growth after a call that loaded only that file (the Skill tool for SKILL.md, "
                   "which also strips the frontmatter;\nRead adds line numbers). Other files use the ratio of "
                   "measured files with the same extension, else the all-reads ratio.")
    else:
        out.append(f"Token estimate: bytes/{FALLBACK_BYTES_PER_TOKEN:.0f}; not enough clean samples to calibrate.")
    for name, info in skills.items():
        rows = [["description (always in the skill list)", len(info["description"].encode()),
                 fmt_tok(len(info["description"].encode()) / (cal["bytes_per_token"] if cal else FALLBACK_BYTES_PER_TOKEN)), ""]]
        total = 0
        for rel, size in info["files"].items():
            tokens, method = file_tokens(name, rel, size, cal)
            total += tokens
            rows.append([rel, size, fmt_tok(tokens), method])
        rows.append(["all files", sum(info["files"].values()), fmt_tok(total), ""])
        out.append(f"\n{name}\n" + table(["file", "bytes", "~tokens", "method"], rows))

    out.append("\n== 2. Skill files the agent loaded ==")
    out.append("Cell = runs that loaded the file in full; +Np = runs that only read part of it (head, sed -n, grep, offset).")
    counts = read_counts(runs)
    for name, info in skills.items():
        skill_cases = sorted({r["case"] for r in runs if r["skill"] == name})
        if not skill_cases:
            continue
        nruns = {c: sum(1 for r in runs if r["case"] == c) for c in skill_cases}
        cols = [f"c{i + 1}" for i in range(len(skill_cases))]
        rows = []
        for rel in info["files"]:
            per = counts.get((name, rel), {})
            if not per:
                continue
            cells = []
            for c in skill_cases:
                full, part = per.get(c, [0, 0])
                cells.append((str(full) if full or not part else "") + (f"+{part}p" if part else "") or "-")
            rows.append([rel, *cells])
        never = [rel for rel in info["files"] if (name, rel) not in counts]
        loaded = [statistics.median(loaded_tokens(r, skills, cal) for r in runs if r["case"] == c) for c in skill_cases]
        rows.append(["~tokens loaded (median)", *[fmt_tok(x) for x in loaded]])
        out.append(f"\n{name}\n" + table(["file", *cols], rows))
        out.append("  " + "  ".join(f"{col}={short(c, name)} ({nruns[c]})" for col, c in zip(cols, skill_cases)))
        if never:
            out.append("  never read: " + ", ".join(never))

    out.append("\n== 3. Cost per case (median / max over runs) ==")
    out.append("prompt = input + cache write + cache read tokens over every API call. peak = largest prompt of one call.")
    for name in skills:
        skill_runs = [r for r in runs if r["skill"] == name]
        if not skill_runs:
            continue
        rows = []
        for case in sorted({r["case"] for r in skill_runs}):
            rs = [r for r in skill_runs if r["case"] == case]
            mm = med_max(rs)
            tag = "no-fire" if cases.get(case, {}).get("baseline") else "fire"
            rows.append([short(case, name), tag, f"{sum(r['fired'] for r in rs)}/{len(rs)}",
                         *[f"{fmt(m, mm[m][0])}/{fmt(m, mm[m][1])}" for m in METRICS]])
        fired = [r for r in skill_runs if r["fired"]]
        unfired = [r for r in skill_runs if not r["fired"]]
        for label, group in (("ALL skill loaded", fired), ("ALL not loaded", unfired)):
            if group:
                mm = med_max(group)
                rows.append([label, "", f"{len(group)}", *[f"{fmt(m, mm[m][0])}/{fmt(m, mm[m][1])}" for m in METRICS]])
        if fired and unfired:
            a, b = med_max(fired), med_max(unfired)
            rows.append(["overhead (median)", "", "", *[fmt(m, a[m][0] - b[m][0]) for m in METRICS]])
        out.append(f"\n{name}\n" + table(["case", "expect", "fired", *METRICS], rows, left=2))

    out.append("\n== 4. Where the tokens go (runs that loaded the skill) ==")
    if prices:
        out.append(f"Prices fitted to the cost of {prices['n']} turns, $/M tokens: cache write "
                   f"{prices['cache_write']:.2f}, cache read {prices['cache_read']:.2f}, output {prices['output']:.2f} "
                   f"(worst turn off by {prices['worst_error']:.1%}).")
    first = [r["calls"][0]["ctx"] for r in runs if r["calls"]]
    if first:
        out.append(f"Every session starts with a {fmt_tok(statistics.median(first))}-token prompt (median first call: "
                   "system prompt, tools, CLAUDE.md, skill list) before any skill loads.")
    rows = []
    for name in skills:
        fired = [r for r in runs if r["skill"] == name and r["fired"]]
        if not fired:
            continue
        tot =[run_totals(r) for r in fired]
        s = {k: sum(t[k] for t in tot) for k in ("input", "cache_write", "cache_read", "output", "thinking", "prompt", "calls", "cost")}
        carried = [carried_tokens(r, skills, cal) for r in fired]
        row = [name, f"{s['cache_read'] / s['prompt']:.0%}", f"{s['cache_write'] / s['prompt']:.0%}",
               fmt_tok(s["prompt"] / s["calls"]), f"{s['thinking'] / max(s['output'], 1):.0%}",
               f"{sum(c[1] for c in carried) / s['prompt']:.0%}"]
        if prices:
            parts = {k: s[k] * prices[k] / 1e6 for k in ("cache_write", "cache_read", "output")}
            whole = sum(parts.values()) or 1
            skill_cost = statistics.median((c[0] * prices["cache_write"] + c[1] * prices["cache_read"]) / 1e6 for c in carried)
            row += [f"{parts['cache_read'] / whole:.0%}", f"{parts['cache_write'] / whole:.0%}",
                    f"{parts['output'] / whole:.0%}", f"${skill_cost:.3f}"]
        rows.append(row)
    headers = ["skill", "read%", "write%", "avg prompt", "think/out", "skill text%"]
    if prices:
        headers += ["$read", "$write", "$output", "skill text $/run"]
    out.append(table(headers, rows))
    out.append("read%/write% = share of prompt tokens served from cache / written to cache. avg prompt = mean prompt "
               "size per API call.\nskill text% = share of prompt tokens that are skill file content re-sent on later "
               "calls (approx.). $read/$write/$output = share of cost.\nskill text $/run = median cost of writing the "
               "loaded skill text to cache once and reading it back on every later call.")
    rows = []
    for name in skills:
        fired = [r for r in runs if r["skill"] == name and r["fired"]]
        for case in sorted({r["case"] for r in fired}):
            rs = [r for r in fired if r["case"] == case]
            ends = {}
            for r in rs:
                for c in r["calls"]:
                    if c["calls_in_turn_end"]:
                        ends.setdefault(c["turn"], []).append(c["ctx"])
            rows.append([name, short(case, name), *[f"{fmt_tok(statistics.median(v))}/{fmt_tok(max(v))}" for _, v in sorted(ends.items())]])
    out.append("\nPrompt size at the last API call of each turn, median/max (the context the turn ended with):")
    width = max((len(r) for r in rows), default=2)
    out.append(table(["skill", "case", *[f"turn {t + 1}" for t in range(width - 2)]],
                     [r + [""] * (width - len(r)) for r in rows], left=2))
    return "\n".join(out)


def newest_results(root=ROOT):
    dirs = sorted(d for d in glob.glob(os.path.join(root, "evals", "results", "*")) if os.path.isdir(d))
    if not dirs:
        sys.exit("no results under evals/results; pass a results directory")
    return dirs[-1]


def main():
    results_dir = sys.argv[1] if len(sys.argv) > 1 else newest_results()
    print(report(results_dir))


if __name__ == "__main__":
    main()
