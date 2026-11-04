# Evals

Two layers of checks for the skills in this repo.

## Script tests

Fast and deterministic. They cover the scripts each skill ships.

```sh
node --test skills/graphite-ui/tests/*.test.mjs
python3 -I -m unittest discover -s skills/create-info-cards/tests
```

`skills/create-info-cards/tests` needs headless Chromium from Playwright's cache, `pdftotext` and `uvx`. The deck grader's phone check needs the same Chromium. Rebuild the PDF fixture with `skills/create-info-cards/evals/fixtures/build.sh` after editing `library-report.html`.

## End-to-end evals

`run.py` runs each case through `claude -p` in a fresh workspace and grades what the agent left behind.

```sh
python3 -I evals/run.py                         # every case, once
python3 -I evals/run.py --skill graphite-ui     # one skill
python3 -I evals/run.py --case 'cards-*' --runs 3 -j 4
```

For each case the runner:
1. Copies the case's fixture into a temp workspace and links every skill in the repo into `.claude/skills/`, so the agent has to pick the right one.
2. Sends each prompt in `turns`. The second prompt resumes the same session, which is how a case answers a skill that stops for approval.
3. Runs the graders and writes a JSON record, the full event stream and a copy of the finished workspace to `evals/results/<timestamp>/`. A failing run also keeps its temp workspace.

Runs use your own Claude Code login, settings and `~/.claude/CLAUDE.md`, with Bash, file edits and WebFetch allowed. `--budget` caps the spend of each `claude -p` call (default $5).

### Cases

Each skill keeps its cases in `<skill>/evals/cases.json`, its fixtures in `<skill>/evals/fixtures/` and its grader scripts in `<skill>/evals/graders/`. The fixtures are invented content written for these evals.

| Grader type | Passes when |
|---|---|
| `skill_used` | the agent loaded the skill, or did not when `"expect": false` |
| `cmd` | the command exits 0. `{ws}`, `{evals}`, `{skill_dir}` and `{replies}` (a file with the agent's replies) are filled in |
| `no_writes` | no file in the workspace changed during turn `"turn": n` (default 0), such as a turn that should stop for approval |
| `regex` | the pattern is found in the final reply, or in turn `"turn": n` |
| `judge` | Haiku answers PASS to the criteria, given the final reply or the files matching `"file"` |

A run passes when every grader passes.

### Why not `claude plugin eval`

Its graders cannot run scripts, a case cannot send a follow-up message, and runs get a temporary home directory without the Chromium that `create-info-cards` checks with.

## HTML report

`report.py` turns a results directory into a few local pages styled with Graphite UI: `<results-dir>/report/index.html` and one page per run. Open it in a browser; no server is needed.

```sh
python3 -I evals/report.py                                   # newest results dir
python3 -I evals/report.py evals/results/20261104-111416 --compare evals/results/20261103-010024
```

The index has a table per skill: passes, a link to each run, median cost and time, and the token report at the end. A run page has its graders, each turn's prompt and reply, the tool calls, and links to the files it built. `--compare` adds each case's median agent cost from an older run, taken from the event streams the same way the token report does.

## Token report

`tokens.py` reads a results directory that `run.py` already wrote and prints what each skill costs. It starts no sessions.

```sh
python3 -I evals/tokens.py                                  # newest results dir
python3 -I evals/tokens.py evals/results/20261103-010024
```

It prints four sections:
1. Static footprint: bytes and tokens of each skill file. Token counts come from the event streams: the growth of the prompt after a tool call that loaded one file, or a bytes/token ratio measured the same way.
2. Which skill files the agent loaded in each case, in full or in part.
3. Median and max per case of prompt tokens, output, thinking, API calls, cost, time and peak context. Runs that loaded the skill are set against runs that did not.
4. Where the tokens go: cache reads against cache writes, cost per token type (prices fitted to the logged costs), how much of the prompt is skill text, and the context size at the end of each turn.

Per-turn cost is the difference between consecutive `total_cost_usd` values, because that field keeps counting across a resumed session. Judge calls are left out.
