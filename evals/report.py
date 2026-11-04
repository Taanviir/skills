"""Turn an eval results folder into one HTML page.

Usage: python3 -I evals/report.py [results-dir] [--compare older-results-dir] [--out site-dir]

Writes <results-dir>/report.html and prints its path. With no results-dir it uses the newest run.
--out writes a publishable copy instead: <site-dir>/index.html, summary.json and each run's built files,
with the home directory shown as ~. The site dir is replaced.
"""
import argparse
import glob
import html
import json
import os
import shutil
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens  # noqa: E402

CSS = """
:root { color-scheme: light dark;
  --page: light-dark(#f7f7f8, #111214); --surface: light-dark(#fff, #1a1b1e); --ring: light-dark(#e4e4e7, #2c2d31);
  --fg: light-dark(#18181b, #ececee); --muted: light-dark(#5f5f68, #a1a1aa);
  --pass: light-dark(#15803d, #4ade80); --pass-bg: light-dark(#dcfce7, #10291a);
  --fail: light-dark(#b91c1c, #f87171); --fail-bg: light-dark(#fee2e2, #2d1515); }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--fg); font: 14px/1.5 system-ui, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 20px; margin: 0 0 4px; } h2 { font-size: 15px; margin: 32px 0 8px; }
.muted { color: var(--muted); } .nums { font-variant-numeric: tabular-nums; }
.box { background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: start; padding: 8px 12px; border-bottom: 1px solid var(--ring); vertical-align: top; }
tr:last-child td { border-bottom: 0; } th { font-weight: 500; color: var(--muted); }
.cells { display: flex; gap: 6px; flex-wrap: wrap; }
.cell { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; text-decoration: none; }
.cell.pass { background: var(--pass-bg); color: var(--pass); } .cell.fail { background: var(--fail-bg); color: var(--fail); }
details.run { background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; margin: 8px 0; }
details.run > summary { padding: 10px 14px; cursor: pointer; display: flex; gap: 12px; align-items: center; }
details.run > div { padding: 0 14px 14px; }
.turn { border-top: 1px solid var(--ring); padding-top: 10px; margin-top: 10px; }
.prompt { font-weight: 500; } pre { white-space: pre-wrap; overflow-wrap: anywhere; margin: 6px 0; font: 13px/1.5 ui-monospace, monospace; }
.reply { max-height: 320px; overflow-y: auto; background: var(--page); border-radius: 8px; padding: 8px 10px; }
.tools { color: var(--muted); font-size: 12px; }
ul.graders { margin: 6px 0; padding-inline-start: 18px; } .x { color: var(--fail); } .ok { color: var(--pass); }
.delta-up { color: var(--fail); } .delta-down { color: var(--pass); }
"""


def esc(s):
    return html.escape(str(s), quote=True)


def load(results_dir):
    runs = []
    for path in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            r = json.load(f)
        if "case" in r and "graders" in r:
            runs.append(r)
    return sorted(runs, key=lambda r: (r["skill"], r["case"], r["run"]))


def by_case(runs):
    cases = {}
    for r in runs:
        cases.setdefault(r["case"], []).append(r)
    return cases


def run_id(r):
    return f'{r["case"]}-{r["run"]}'


def tool_line(t):
    inp = t.get("input") or {}
    arg = inp.get("skill") or inp.get("file_path") or inp.get("command") or inp.get("pattern") or ""
    return t["name"] + (f" {str(arg).splitlines()[0][:80]}" if arg else "")


def outputs(results_dir, r):
    folder = os.path.join(results_dir, run_id(r))
    found = sorted(glob.glob(os.path.join(folder, "**", "*.html"), recursive=True))
    return [os.path.relpath(p, results_dir) for p in found if not os.path.basename(p).startswith("._")]


def agent_costs(results_dir, root):
    """Median agent cost per case, rebuilt from events so runs from before the cost fix compare fairly."""
    per_case = {}
    for run in tokens.load_results(results_dir, tokens.load_skills(root)):
        per_case.setdefault(run["case"], []).append(tokens.run_totals(run)["cost"])
    return {case: statistics.median(v) for case, v in per_case.items()}


def summary_table(cases, now, older):
    head = "<tr><th>Case</th><th>Skill</th><th>Runs</th><th>Median agent cost</th>"
    head += "<th>Before</th>" if older else ""
    rows = []
    for name, runs in cases.items():
        cost = now.get(name, 0)
        cells = "".join(
            f'<a class="cell {"pass" if r["pass"] else "fail"}" href="#{esc(run_id(r))}">'
            f'{"pass" if r["pass"] else "fail"} {r["run"]}</a>' for r in runs)
        row = f'<tr><td>{esc(name)}</td><td class="muted">{esc(runs[0]["skill"])}</td><td><div class="cells">{cells}</div></td>'
        row += f'<td class="nums">${cost:.2f}</td>'
        if older:
            if name in older:
                was = older[name]
                cls = "delta-up" if cost > was * 1.05 else "delta-down" if cost < was * 0.95 else "muted"
                row += f'<td class="nums {cls}">${was:.2f}</td>'
            else:
                row += '<td class="muted">new</td>'
        rows.append(row + "</tr>")
    return f'<div class="box"><table>{head}</tr>{"".join(rows)}</table></div>'


def run_block(results_dir, r):
    graders = "".join(
        f'<li><span class="{"ok" if g["pass"] else "x"}">{"✓" if g["pass"] else "✗"}</span> {esc(g["name"])}'
        + ("" if g["pass"] else f'<pre>{esc(g.get("note", ""))}</pre>') + "</li>" for g in r["graders"])
    turns = []
    for i, t in enumerate(r["turns"], 1):
        tools = "<br>".join(esc(tool_line(x)) for x in t.get("tools", []))
        turns.append(
            f'<div class="turn"><div class="muted">Turn {i} · ${t.get("cost", 0):.2f}</div>'
            f'<div class="prompt"><pre>{esc(t["prompt"])}</pre></div>'
            f'<div class="reply"><pre>{esc(t.get("text", ""))}</pre></div>'
            + (f'<details><summary class="tools">{len(t.get("tools", []))} tool calls</summary>'
               f'<div class="tools">{tools}</div></details>' if t.get("tools") else "") + "</div>")
    files = outputs(results_dir, r)
    links = " · ".join(f'<a href="{esc(p)}">{esc(os.path.basename(p))}</a>' for p in files)
    kept = "" if r["pass"] else f'<div class="muted">Workspace kept at <code>{esc(r["workspace"])}</code></div>'
    status = "pass" if r["pass"] else "fail"
    return (
        f'<details class="run" id="{esc(run_id(r))}"{"" if r["pass"] else " open"}>'
        f'<summary><span class="cell {status}">{status}</span><strong>{esc(r["case"])}</strong>'
        f'<span class="muted nums">run {r["run"]} · ${r["cost"]:.2f} · {r["seconds"]}s</span></summary>'
        f'<div><ul class="graders">{graders}</ul>{kept}'
        + (f'<div>Output: {links}</div>' if links else "") + "".join(turns) + "</div></details>")


def build(results_dir, older_dir=None, root=tokens.ROOT, back=None):
    runs = load(results_dir)
    if not runs:
        sys.exit(f"no run results in {results_dir}")
    cases = by_case(runs)
    older = agent_costs(older_dir, root) if older_dir else None
    passed = sum(r["pass"] for r in runs)
    title = os.path.basename(os.path.normpath(results_dir))
    compare = f' Compared with <code>{esc(os.path.basename(os.path.normpath(older_dir)))}</code>.' if older_dir else ""
    token_text = tokens.report(results_dir, root)
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>Evals {esc(title)}</title>'
        f'<style>{CSS}</style></head><body><main>'
        + (f'<p><a href="{esc(back)}">← Taanviir\'s skills</a></p>' if back else "")
        + f'<h1>Evals {esc(title)}</h1>'
        f'<p class="muted nums">{passed}/{len(runs)} runs passed · ${sum(r["cost"] for r in runs):.2f} total.{compare}</p>'
        f'<h2>Cases</h2>{summary_table(cases, agent_costs(results_dir, root), older)}'
        f'<h2>Runs</h2>{"".join(run_block(results_dir, r) for r in runs)}'
        f'<h2>Tokens</h2><details class="run"><summary>Token and cost report</summary>'
        f'<div><pre>{esc(token_text)}</pre></div></details>'
        f'</main></body></html>')


def publish(results_dir, out_dir, older_dir=None, root=tokens.ROOT):
    runs = load(results_dir)
    page = build(results_dir, older_dir, root, back="../").replace(os.path.expanduser("~"), "~")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    for r in runs:
        folder = os.path.join(results_dir, run_id(r))
        if os.path.isdir(folder):
            shutil.copytree(folder, os.path.join(out_dir, run_id(r)), ignore=shutil.ignore_patterns("._check_*"))
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    summary = {"run": os.path.basename(os.path.normpath(results_dir)), "passed": sum(r["pass"] for r in runs),
               "runs": len(runs), "cases": len(by_case(runs)), "cost": round(sum(r["cost"] for r in runs), 2)}
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f)
    return os.path.join(out_dir, "index.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?")
    ap.add_argument("--compare")
    ap.add_argument("--out")
    args = ap.parse_args()
    results_dir = args.results or tokens.newest_results()
    if args.out:
        print(publish(results_dir, args.out, args.compare))
        return
    out = os.path.join(results_dir, "report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(build(results_dir, args.compare))
    print(out)


if __name__ == "__main__":
    main()
