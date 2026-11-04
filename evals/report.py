"""Turn an eval results folder into a small HTML site styled with Graphite UI.

Usage: python3 -I evals/report.py [results-dir] [--compare older-results-dir] [--out site-dir]

Writes <results-dir>/report/index.html plus one page per run, and prints the index path.
With no results-dir it uses the newest run.
--out writes the copy the GitHub Pages site serves instead: the same pages and a summary.json,
with no built files and the home directory shown as ~. The site dir is replaced.
"""
import argparse
import glob
import html
import json
import re
import os
import shutil
import statistics
import sys
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tokens  # noqa: E402

GRAPHITE = os.path.join(tokens.ROOT, "skills", "graphite-ui", "assets")
SITE = os.path.join(tokens.ROOT, "site")
GITHUB = "https://github.com/Taanviir/skills"
ICONS = {"graphite-ui": "i-palette", "project-presentation": "i-slides", "create-info-cards": "i-image"}

CSS = """
.runs { display: flex; flex-wrap: wrap; gap: var(--gr-space-1-5); }
.runs a { text-decoration: none; }
.turn { display: grid; gap: var(--gr-space-3); }
.bubble { justify-self: end; max-width: 80%; padding: var(--gr-space-3) var(--gr-space-4); border-radius: var(--gr-radius-surface); background: var(--gr-accent-bg-subtle); }
.text { white-space: pre-wrap; overflow-wrap: anywhere; }
.text code { font-size: 0.92em; }
.reply { max-height: 480px; overflow-y: auto; }
.tools { display: grid; gap: var(--gr-space-1); font-size: var(--gr-text-caption); color: var(--gr-fg-secondary); }
.tools code { overflow-wrap: anywhere; }
.tools-foot { display: block; }
details > summary { cursor: pointer; }
pre.report { margin: 0; overflow-x: auto; font-size: var(--gr-text-label); line-height: 1.5; }
.up { color: var(--gr-danger-text); } .down { color: var(--gr-success-text); }
.graders .list-row { grid-template-columns: minmax(0, 1fr) auto; }
@media (max-width: 640px) { .bubble { max-width: 100%; } }
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


def agent_costs(results_dir, root):
    """Median agent cost per case, rebuilt from events so runs from before the cost fix compare fairly."""
    per_case = {}
    for run in tokens.load_results(results_dir, tokens.load_skills(root)):
        per_case.setdefault(run["case"], []).append(tokens.run_totals(run)["cost"])
    return {case: statistics.median(v) for case, v in per_case.items()}


def chip(r, href):
    tone, word = ("success", "pass") if r["pass"] else ("danger", "fail")
    return f'<a class="badge {tone}" href="{esc(href)}" title="Run {r["run"]}: {word}">{word} {r["run"]}</a>'


def shell(title, body, site, up=""):
    """site: the published copy, with the site's nav. up: path from this page back to the evals index."""
    if site:
        home = up + "../"
        css, site_css, icon = home + "graphite-ui/", home + "site.css", home + "favicon.svg"
        nav = (f'<a class="btn ghost" href="{home}#skills">Skills</a>'
               f'<a class="btn ghost" href="{up or "./"}" aria-current="page">Eval results</a>'
               f'<a class="btn ghost" href="{home}graphite-ui/preview.html">Graphite UI board</a>'
               f'<a class="btn ghost" href="{GITHUB}">GitHub</a>')
        brand = f'<a class="brand" href="{home}"><img src="{icon}" alt=""><span>Taanviir\'s skills</span></a>'
    else:
        css = "file://" + quote(GRAPHITE) + "/"
        site_css, icon = "file://" + quote(os.path.join(SITE, "site.css")), "file://" + quote(os.path.join(SITE, "favicon.svg"))
        nav = ""
        brand = f'<a class="brand" href="{up or "./"}"><img src="{icon}" alt=""><span>Eval report</span></a>'
    links = "".join(f'<link rel="stylesheet" href="{css}{name}">' for name in ("tokens.css", "base.css", "components.css"))
    with open(os.path.join(SITE, "icons.svg"), encoding="utf-8") as f:
        icons = f.read()
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{esc(title)}</title><link rel="icon" href="{icon}" type="image/svg+xml">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400..700&display=swap">'
        f'{links}<link rel="stylesheet" href="{site_css}"><style>{CSS}</style></head><body>{icons}'
        f'<header class="topbar"><div class="bar">{brand}<span class="spacer"></span><nav aria-label="Site">{nav}</nav></div></header>'
        f'<main class="content">{body}'
        f'<footer class="split"><span>Taanviir\'s skills</span><a href="{GITHUB}">github.com/Taanviir/skills</a></footer>'
        '</main></body></html>')


def skill_title(skill, tag="h2"):
    icon = ICONS.get(skill)
    tile = f'<span class="tile"><svg aria-hidden="true"><use href="#{icon}"/></svg></span>' if icon else ""
    return f'<div class="titled">{tile}<{tag}>{esc(skill)}</{tag}></div>'


def stat(label, value):
    return f'<div class="stat"><span class="label">{esc(label)}</span><span class="value">{esc(value)}</span></div>'


def index_page(results_dir, runs, now, older, token_text, compare_name):
    passed = sum(r["pass"] for r in runs)
    seconds = statistics.median(r["seconds"] for r in runs)
    name = os.path.basename(os.path.normpath(results_dir))
    sub = f"Run {esc(name)}" + (f", with costs compared to run {esc(compare_name)}" if compare_name else "") + "."
    body = [
        f'<section class="hero"><span class="overline">Evals</span><h1>Eval results</h1><p>{sub} Each case runs the agent '
        'in a fresh folder with a scripted user, and graders check what it did.</p></section>',
        '<div class="stats">' + stat("Runs passed", f"{passed}/{len(runs)}") + stat("Cases", len(group(runs, "case")))
        + stat("Total cost", f'${sum(r["cost"] for r in runs):.2f}') + stat("Median run", f"{seconds:.0f}s") + "</div>",
    ]
    for skill, skill_runs in group(runs, "skill").items():
        ok = sum(r["pass"] for r in skill_runs)
        tone = "success" if ok == len(skill_runs) else "warning"
        rows = []
        for case, case_runs in group(skill_runs, "case").items():
            cost = now.get(case, 0)
            before = ""
            if older is not None:
                if case in older:
                    was = older[case]
                    change = (cost - was) / was * 100 if was else 0
                    cls = "up" if change > 5 else "down" if change < -5 else "text-secondary"
                    before = (f'<td class="num"><span class="text-secondary">${was:.2f}</span> '
                              f'<span class="{cls}">{change:+.0f}%</span></td>')
                else:
                    before = '<td class="num text-secondary">new</td>'
            chips = "".join(chip(r, f"runs/{quote(run_id(r))}.html") for r in case_runs)
            rows.append(f'<tr><td>{esc(case)}</td><td><div class="runs">{chips}</div></td>'
                        f'<td class="num">${cost:.2f}</td>{before}'
                        f'<td class="num">{statistics.median(r["seconds"] for r in case_runs):.0f}s</td></tr>')
        head = ('<tr><th>Case</th><th>Runs</th><th class="num">Median cost</th>'
                + ('<th class="num">Before</th>' if older is not None else "") + '<th class="num">Median time</th></tr>')
        body.append(
            f'<section class="section"><div class="section-head">{skill_title(skill)}'
            f'<span class="status {tone}">{ok}/{len(skill_runs)} runs passed</span></div>'
            f'<div class="table-wrap"><table class="table"><thead>{head}</thead><tbody>{"".join(rows)}</tbody></table></div></section>')
    body.append(
        '<section class="section"><div class="section-head"><h2>Tokens and cost</h2></div>'
        '<details class="card"><summary class="card-body">Show the token report</summary>'
        f'<div class="card-body"><pre class="report mono">{esc(token_text)}</pre></div></details></section>')
    return "".join(body)


def run_page(results_dir, r, show_outputs):
    status = '<span class="badge success">Passed</span>' if r["pass"] else '<span class="badge danger">Failed</span>'
    turns = len(r["turns"])
    body = [
        f'<section class="hero"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="../">Eval results</a><span>/</span>'
        f'<span aria-current="page">{esc(r["case"])} run {r["run"]}</span></nav>'
        f'{skill_title(r["skill"], "span")}<h1>{esc(r["case"])}, run {r["run"]}</h1>'
        f'<div class="cluster">{status}<span class="text-secondary nums">${r["cost"]:.2f} · {r["seconds"]}s · '
        f'{turns} turn{"s" if turns != 1 else ""}</span></div></section>',
    ]
    rows = []
    for g in r["graders"]:
        tone = "success" if g["pass"] else "danger"
        note = "" if g["pass"] else f'<span class="text">{esc(g.get("note", ""))}</span>'
        rows.append(f'<div class="list-row"><div class="meta"><span>{esc(g["name"])}</span>{note}</div>'
                    f'<span class="status {tone}">{"pass" if g["pass"] else "fail"}</span></div>')
    body.append(f'<section class="section"><div class="section-head"><h2>Graders</h2></div>'
                f'<div class="card"><div class="list graders">{"".join(rows)}</div></div></section>')
    if show_outputs:
        files = outputs(results_dir, r)
        if files:
            links = "".join(f'<a class="btn" href="../../{esc(p)}">{esc(os.path.basename(p))}</a>' for p in files)
            body.append(f'<section class="section"><div class="section-head"><h2>Built files</h2></div>'
                        f'<div class="cluster">{links}</div></section>')
        if not r["pass"]:
            body.append(f'<p class="text-caption text-secondary">Workspace kept at <code>{esc(r["workspace"])}</code></p>')
    for i, t in enumerate(r["turns"], 1):
        calls = t.get("tools", [])
        tools = "".join(f"<div><strong>{esc(n)}</strong> <code>{esc(a)}</code></div>" for n, a in map(tool_line, calls))
        foot = (f'<details class="card-foot tools-foot"><summary class="text-caption">{len(calls)} tool call'
                f'{"s" if len(calls) != 1 else ""}</summary><div class="tools">{tools}</div></details>') if calls else ""
        body.append(
            f'<section class="section"><div class="section-head"><h2>Turn {i}</h2>'
            f'<span class="text-caption text-secondary nums">${t.get("cost", 0):.2f}</span></div>'
            f'<div class="turn"><div class="bubble text">{esc(t["prompt"])}</div>'
            f'<div class="card"><div class="card-body reply"><div class="text">{md(t.get("text", ""))}</div></div>{foot}</div></div></section>')
    return "".join(body)


def write_site(results_dir, out_dir, older_dir=None, root=tokens.ROOT, site=False):
    runs = load(results_dir)
    if not runs:
        sys.exit(f"no run results in {results_dir}")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(os.path.join(out_dir, "runs"))
    scrub = (lambda s: s.replace(os.path.expanduser("~"), "~")) if site else (lambda s: s)
    older = agent_costs(older_dir, root) if older_dir else None
    compare_name = os.path.basename(os.path.normpath(older_dir)) if older_dir else None
    body = index_page(results_dir, runs, agent_costs(results_dir, root), older, tokens.report(results_dir, root), compare_name)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(scrub(shell("Eval results", body, site)))
    for r in runs:
        page = shell(f'{r["case"]} run {r["run"]}', run_page(results_dir, r, not site), site, up="../")
        with open(os.path.join(out_dir, "runs", f"{run_id(r)}.html"), "w", encoding="utf-8") as f:
            f.write(scrub(page))
    if site:
        skills = {s: {"passed": sum(r["pass"] for r in rs), "runs": len(rs), "cases": len(group(rs, "case"))}
                  for s, rs in group(runs, "skill").items()}
        summary = {"run": os.path.basename(os.path.normpath(results_dir)), "passed": sum(r["pass"] for r in runs),
                   "runs": len(runs), "cases": len(group(runs, "case")),
                   "cost": round(sum(r["cost"] for r in runs), 2), "skills": skills}
        with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=1)
    return os.path.join(out_dir, "index.html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results", nargs="?")
    ap.add_argument("--compare")
    ap.add_argument("--out")
    args = ap.parse_args()
    results_dir = args.results or tokens.newest_results()
    if args.out:
        print(write_site(results_dir, args.out, args.compare, site=True))
    else:
        print(write_site(results_dir, os.path.join(results_dir, "report"), args.compare))


if __name__ == "__main__":
    main()
