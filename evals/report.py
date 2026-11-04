"""Turn an eval results folder into a few local HTML pages styled with Graphite UI.

Usage: python3 -I evals/report.py [results-dir] [--compare older-results-dir]

Writes <results-dir>/report/index.html plus one page per run, and prints the index path.
With no results-dir it uses the newest run.
"""
import argparse
import glob
import html
import json
import os
import re
import shutil
import statistics
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens  # noqa: E402

GRAPHITE = os.path.join(tokens.ROOT, "skills", "graphite-ui", "assets")

CSS = """
.topbar { padding: 0; border-bottom: 0; background: var(--gr-bg-page); backdrop-filter: none; }
.topbar .bar { display: flex; align-items: center; width: 100%; max-width: var(--gr-content-max); margin: 0 auto; padding: 0 var(--gr-space-6); }
.brand { font-weight: var(--gr-weight-semibold); color: var(--gr-fg-primary); text-decoration: none; }
.content { gap: var(--gr-space-10); }
.intro { display: grid; gap: var(--gr-space-2); }
.intro p { color: var(--gr-fg-secondary); }
.runs { display: flex; gap: var(--gr-space-3); }
.fail { color: var(--gr-danger-text); }
.turn { display: grid; gap: var(--gr-space-3); }
.prompt { padding-inline-start: var(--gr-space-3); border-inline-start: 2px solid var(--gr-accent-solid); }
.text { white-space: pre-wrap; overflow-wrap: anywhere; }
.text code { font-size: 0.92em; }
.tools { display: grid; gap: var(--gr-space-1); margin-top: var(--gr-space-2); font-size: var(--gr-text-caption); color: var(--gr-fg-secondary); }
.tools code { overflow-wrap: anywhere; }
details > summary { cursor: pointer; font-size: var(--gr-text-caption); color: var(--gr-fg-secondary); }
pre.report { margin: 0; overflow-x: auto; font-size: var(--gr-text-label); line-height: 1.5; }
.graders { display: grid; gap: var(--gr-space-2); }
.graders .note { color: var(--gr-fg-secondary); font-size: var(--gr-text-caption); }
@media (max-width: 640px) { .topbar .bar, .content { padding-inline: var(--gr-space-4); } }
"""


def esc(s):
    return html.escape(str(s), quote=True)


def md(s):
    """Escaped text with the agent's **bold** and `code` shown as such."""
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))
    return re.sub(r"`([^`\n]+)`", r"<code>\1</code>", out)


def load(results_dir):
    runs = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        if "case" in r and "graders" in r:
            runs.append(r)
    return sorted(runs, key=lambda r: (r["skill"], r["case"], r["run"]))


def group(runs, key):
    out = {}
    for r in runs:
        out.setdefault(r[key], []).append(r)
    return out


def run_id(r):
    return f'{r["case"]}-{r["run"]}'


def tool_line(t):
    inp = t.get("input") or {}
    arg = inp.get("skill") or inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""
    return t["name"], str(arg).splitlines()[0][:120] if arg else ""


def outputs(results_dir, r):
    folder = os.path.join(results_dir, run_id(r))
    found = sorted(glob.glob(os.path.join(folder, "**", "*.html"), recursive=True))
    return [os.path.relpath(p, results_dir) for p in found if not os.path.basename(p).startswith("._")]


def event_runs(results_dir, root):
    """(case, run) -> the run as tokens.py rebuilds it from its event stream."""
    return {(r["case"], r["run"]): r for r in tokens.load_results(results_dir, tokens.load_skills(root))}


def agent_costs(runs):
    """Median agent cost per case, judge calls left out."""
    per_case = {}
    for run in runs.values():
        per_case.setdefault(run["case"], []).append(tokens.run_totals(run)["cost"])
    return {case: statistics.median(v) for case, v in per_case.items()}


def shell(title, body, up=""):
    css = "file://" + quote(GRAPHITE) + "/"
    links = "".join(f'<link rel="stylesheet" href="{css}{name}">' for name in ("tokens.css", "base.css", "components.css"))
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(title)}</title>'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400..700&display=swap">'
        f'{links}<style>{CSS}</style></head><body>'
        f'<header class="topbar"><div class="bar"><a class="brand" href="{up or "./"}">Eval report</a></div></header>'
        f'<main class="content">{body}</main></body></html>')


def index_page(results_dir, runs, now, older, token_text, compare_name):
    passed = sum(r["pass"] for r in runs)
    name = os.path.basename(os.path.normpath(results_dir))
    compared = f" Costs are compared with run {esc(compare_name)}." if compare_name else ""
    body = [
        f'<section class="intro"><h1>Run {esc(name)}</h1><p>{passed} of {len(runs)} runs passed across '
        f'{len(group(runs, "case"))} cases, for ${sum(r["cost"] for r in runs):.2f}.{compared}</p></section>'
    ]
    for skill, skill_runs in group(runs, "skill").items():
        rows = []
        for case, case_runs in group(skill_runs, "case").items():
            links = "".join(
                f'<a href="runs/{quote(run_id(r))}.html"{"" if r["pass"] else " class=\"fail\""}>'
                f'{r["run"]}{"" if r["pass"] else " failed"}</a>' for r in case_runs)
            ok = sum(r["pass"] for r in case_runs)
            cost = now.get(case, 0)
            before = ""
            if older is not None:
                was = older.get(case)
                before = f'<td class="num">{f"${was:.2f}" if was is not None else "new"}</td>'
            rows.append(f'<tr><td>{esc(case)}</td><td class="num">{ok}/{len(case_runs)}</td>'
                        f'<td><div class="runs">{links}</div></td><td class="num">${cost:.2f}</td>{before}'
                        f'<td class="num">{statistics.median(r["seconds"] for r in case_runs):.0f}s</td></tr>')
        head = ('<tr><th>Case</th><th class="num">Passed</th><th>Runs</th><th class="num">Median cost</th>'
                + ('<th class="num">Before</th>' if older is not None else "") + '<th class="num">Median time</th></tr>')
        ok = sum(r["pass"] for r in skill_runs)
        body.append(
            f'<section class="section"><h2>{esc(skill)} <span class="text-secondary">{ok}/{len(skill_runs)}</span></h2>'
            f'<div class="table-wrap"><table class="table"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div></section>')
    body.append(f'<section class="section"><details><summary>Token and cost report</summary>'
                f'<pre class="report mono">{esc(token_text)}</pre></details></section>')
    return "".join(body)


def run_page(results_dir, r, costs):
    turns = len(r["turns"])
    result = "Passed" if r["pass"] else '<span class="fail">Failed</span>'
    body = [
        f'<section class="intro"><p><a href="../">All runs</a></p><h1>{esc(r["case"])}, run {r["run"]}</h1>'
        f'<p class="nums">{result} · ${r["cost"]:.2f} · {r["seconds"]}s · {turns} turn{"s" if turns != 1 else ""}</p></section>',
    ]
    rows = []
    for g in r["graders"]:
        mark = "✓" if g["pass"] else '<span class="fail">✗</span>'
        note = "" if g["pass"] else f'<div class="note text">{esc(g.get("note", ""))}</div>'
        rows.append(f'<div>{mark} {esc(g["name"])}{note}</div>')
    body.append(f'<section class="section"><h2>Graders</h2><div class="graders">{"".join(rows)}</div></section>')
    files = outputs(results_dir, r)
    if files:
        links = " · ".join(f'<a href="../../{esc(p)}">{esc(os.path.basename(p))}</a>' for p in files)
        body.append(f'<section class="section"><h2>Built files</h2><p>{links}</p></section>')
    if not r["pass"]:
        body.append(f'<p class="text-caption text-secondary">Workspace kept at <code>{esc(r["workspace"])}</code></p>')
    for i, t in enumerate(r["turns"]):
        calls = t.get("tools", [])
        tools = "".join(f"<div><strong>{esc(n)}</strong> <code>{esc(a)}</code></div>" for n, a in map(tool_line, calls))
        more = (f'<details><summary>{len(calls)} tool call{"s" if len(calls) != 1 else ""}</summary>'
                f'<div class="tools">{tools}</div></details>') if calls else ""
        body.append(
            f'<section class="section"><h2>Turn {i + 1} <span class="text-secondary nums">${costs[i] if i < len(costs) else 0:.2f}</span></h2>'
            f'<div class="turn"><div class="prompt text">{esc(t["prompt"])}</div>'
            f'<div class="text">{md(t.get("text", ""))}</div>{more}</div></section>')
    return "".join(body)


def write_report(results_dir, out_dir, older_dir=None, root=tokens.ROOT):
    runs = load(results_dir)
    if not runs:
        sys.exit(f"no run results in {results_dir}")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(os.path.join(out_dir, "runs"))
    events = event_runs(results_dir, root)
    older = agent_costs(event_runs(older_dir, root)) if older_dir else None
    compare_name = os.path.basename(os.path.normpath(older_dir)) if older_dir else None
    body = index_page(results_dir, runs, agent_costs(events), older, tokens.report(results_dir, root), compare_name)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(shell("Eval report", body))
    for r in runs:
        ev = events.get((r["case"], r["run"]))
        costs = [t["cost"] for t in ev["turns"]] if ev else []
        with open(os.path.join(out_dir, "runs", f"{run_id(r)}.html"), "w", encoding="utf-8") as f:
            f.write(shell(f'{r["case"]} run {r["run"]}', run_page(results_dir, r, costs), up="../"))
    return os.path.join(out_dir, "index.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?")
    ap.add_argument("--compare")
    args = ap.parse_args()
    results_dir = args.results or tokens.newest_results()
    print(write_report(results_dir, os.path.join(results_dir, "report"), args.compare))


if __name__ == "__main__":
    main()
