"""End-to-end eval runner for the skills in this repo.

Each case copies a fixture into a fresh workspace, installs every skill in the repo as a
project skill, runs one or more prompts through `claude -p` (later prompts resume the same
session, so a case can answer a skill that stops for approval), then grades the workspace.

Usage:
  python3 -I evals/run.py [--skill NAME] [--case GLOB] [--runs N] [-j N] [--budget USD] [--keep]

Cases live in <skill>/evals/cases.json. Results and transcripts go to evals/results/<timestamp>/.
"""
import argparse
import concurrent.futures as cf
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill", "WebFetch", "TodoWrite"]
JUDGE_MODEL = "haiku"


def skills():
    return sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(REPO, "*", "SKILL.md")))


def load_cases(only_skill, pattern):
    cases = []
    for skill in skills():
        if only_skill and skill != only_skill:
            continue
        path = os.path.join(REPO, skill, "evals", "cases.json")
        if not os.path.exists(path):
            continue
        for case in json.load(open(path, encoding="utf-8")):
            if pattern and not any(fnmatch.fnmatch(case["name"], p) for p in pattern.split(",")):
                continue
            case["skill"] = skill
            cases.append(case)
    return cases


def workspace(case):
    ws = tempfile.mkdtemp(prefix=f"eval-{case['name']}-")
    fixture = case.get("fixture")
    if fixture:
        src = os.path.join(REPO, case["skill"], "evals", fixture)
        if os.path.isdir(src):
            shutil.copytree(src, ws, dirs_exist_ok=True)
        else:
            shutil.copy(src, ws)
    os.makedirs(os.path.join(ws, ".claude", "skills"))
    for s in skills():
        os.symlink(os.path.join(REPO, s), os.path.join(ws, ".claude", "skills", s))
    return ws


def run_turn(ws, prompt, session, budget, timeout):
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--max-budget-usd", str(budget), "--allowedTools", *TOOLS]
    if session:
        cmd += ["--resume", session]
    try:
        out = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    events, result = [], {}
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        events.append(ev)
        if ev.get("type") == "result":
            result = ev
    tools = []
    for ev in events:
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    tools.append({"name": block.get("name"), "input": block.get("input", {})})
    return {
        "prompt": prompt,
        "session": result.get("session_id", session),
        "text": result.get("result", ""),
        "cost": result.get("total_cost_usd", 0) or 0,
        "error": result.get("is_error", not result),
        "tools": tools,
        "events": events,
    }


def skill_fired(turns, skill):
    for t in turns:
        for call in t["tools"]:
            blob = json.dumps(call["input"])
            if call["name"] == "Skill" and skill in blob:
                return True
            if call["name"] == "Read" and f"/{skill}/SKILL.md" in blob:
                return True
    return False


def judge(criteria, material, what):
    prompt = (
        "You are grading the output of an AI agent. Read the material and decide whether it meets "
        "the criteria. Reply with PASS or FAIL on the first line, then one sentence of reason.\n\n"
        f"Criteria:\n{criteria}\n\nMaterial ({what}):\n{material[:60000]}"
    )
    out = subprocess.run(["claude", "-p", prompt, "--model", JUDGE_MODEL, "--output-format", "json", "--tools", ""],
                         capture_output=True, text=True, timeout=300)
    try:
        res = json.loads(out.stdout)
        text, cost = res.get("result", ""), res.get("total_cost_usd", 0) or 0
    except ValueError:
        text, cost = out.stdout + out.stderr, 0
    return text.strip().upper().startswith("PASS"), text.strip(), cost


def grade(case, ws, turns):
    results, cost = [], 0
    fd, replies = tempfile.mkstemp(suffix=".txt", prefix="eval-replies-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n\n".join(t["text"] for t in turns))
    subs = {"{ws}": ws, "{skill_dir}": os.path.join(REPO, case["skill"]),
            "{evals}": os.path.join(REPO, case["skill"], "evals"), "{replies}": replies}
    last = turns[-1]["text"] if turns else ""
    for g in case["graders"]:
        kind = g["type"]
        if kind == "skill_used":
            fired = skill_fired(turns, g.get("skill", case["skill"]))
            ok, note = fired == g.get("expect", True), f"skill fired: {fired}"
        elif kind == "cmd":
            argv = [re.sub(r"\{(?:ws|skill_dir|evals|replies)\}", lambda m: subs[m.group(0)], a) for a in g["argv"]]
            p = subprocess.run(argv, capture_output=True, text=True, timeout=g.get("timeout", 600))
            ok, note = p.returncode == 0, (p.stdout + p.stderr).strip()[-1500:]
        elif kind == "regex":
            turn_text = turns[g["turn"]]["text"] if "turn" in g and g["turn"] < len(turns) else last
            found = re.search(g["pattern"], turn_text, re.I | re.S) is not None
            ok, note = found == g.get("expect", True), f"pattern {'found' if found else 'not found'}: {g['pattern']}"
        elif kind == "judge":
            if g.get("file"):
                paths = [p for p in glob.glob(os.path.join(ws, g["file"]), recursive=True) if "/.claude/" not in p]
                material = "\n\n".join(f"--- {os.path.relpath(p, ws)}\n" + open(p, encoding="utf-8", errors="ignore").read() for p in paths) or "(no file matched)"
                what = "files the agent wrote"
            else:
                material = turns[g["turn"]]["text"] if "turn" in g and g["turn"] < len(turns) else last
                what = "the agent's reply to the user, not the user's request"
            ok, note, c = judge(g["criteria"], material, what)
            cost += c
        else:
            ok, note = False, f"unknown grader type {kind}"
        results.append({"name": g["name"], "pass": ok, "note": note})
    os.unlink(replies)
    return results, cost


def run_case(case, run_no, args, out_dir):
    ws = workspace(case)
    turns, session, started = [], None, time.time()
    for prompt in case["turns"]:
        t = run_turn(ws, prompt, session, args.budget, case.get("timeout", 1800))
        turns.append(t)
        session = t["session"]
        if t["error"] or not session:
            break
    graders, judge_cost = grade(case, ws, turns)
    record = {
        "case": case["name"], "skill": case["skill"], "run": run_no, "workspace": ws,
        "seconds": round(time.time() - started), "cost": round(sum(t["cost"] for t in turns) + judge_cost, 4),
        "pass": all(g["pass"] for g in graders), "graders": graders,
        "turns": [{k: v for k, v in t.items() if k != "events"} for t in turns],
    }
    with open(os.path.join(out_dir, f"{case['name']}-{run_no}.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    with open(os.path.join(out_dir, f"{case['name']}-{run_no}.events.jsonl"), "w", encoding="utf-8") as f:
        for t in turns:
            for ev in t["events"]:
                f.write(json.dumps(ev) + "\n")
    shutil.copytree(ws, os.path.join(out_dir, f"{case['name']}-{run_no}"), symlinks=True,
                    ignore=shutil.ignore_patterns(".claude", "node_modules", ".git"))
    if not args.keep and record["pass"]:
        shutil.rmtree(ws, ignore_errors=True)
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill")
    ap.add_argument("--case", help="comma-separated name globs")
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("-j", type=int, default=1)
    ap.add_argument("--budget", type=float, default=5.0, help="max USD per claude -p turn")
    ap.add_argument("--keep", action="store_true", help="keep workspaces of passing runs too")
    args = ap.parse_args()

    cases = load_cases(args.skill, args.case)
    if not cases:
        sys.exit("no cases matched")
    out_dir = os.path.join(REPO, "evals", "results", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_dir)

    jobs = [(c, r) for c in cases for r in range(1, args.runs + 1)]
    with cf.ThreadPoolExecutor(max_workers=args.j) as pool:
        records = list(pool.map(lambda job: run_case(job[0], job[1], args, out_dir), jobs))

    width = max(len(r["case"]) for r in records)
    for r in records:
        print(f"{'PASS' if r['pass'] else 'FAIL'}  {r['case']:<{width}}  run {r['run']}  ${r['cost']:.2f}  {r['seconds']}s")
        for g in r["graders"]:
            if not g["pass"]:
                print(f"        x {g['name']}: {g['note'][:400]}")
        if not r["pass"]:
            print(f"        workspace kept at {r['workspace']}")
    passed = sum(r["pass"] for r in records)
    print(f"\n{passed}/{len(records)} runs passed, ${sum(r['cost'] for r in records):.2f} total. Results in {out_dir}")
    sys.exit(0 if passed == len(records) else 1)


if __name__ == "__main__":
    main()
