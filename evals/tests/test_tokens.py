"""Run with: python3 -I -m unittest discover -s evals/tests"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tokens  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def make_root():
    root = tempfile.mkdtemp()
    write(os.path.join(root, "skills", "demo", "SKILL.md"), "---\nname: demo\ndescription: A demo skill.\n---\n" + "x" * 400)
    write(os.path.join(root, "skills", "demo", "references", "a.md"), "a" * 300)
    write(os.path.join(root, "skills", "demo", "references", "b.md"), "b" * 200)
    write(os.path.join(root, "skills", "demo", "assets", "t.html"), "<p>" * 100)
    cases = [
        {"name": "demo-task", "turns": ["go"], "graders": [{"name": "fired", "type": "skill_used"}]},
        {"name": "demo-skip", "turns": ["no"], "graders": [{"name": "quiet", "type": "skill_used", "expect": False}]},
    ]
    write(os.path.join(root, "skills", "demo", "evals", "cases.json"), json.dumps(cases))
    return root


class Session:
    """Builds a stream-json event list one API call at a time."""

    def __init__(self, sid="s1"):
        self.events, self.sid, self.n, self.cost = [], sid, 0, 0.0

    def call(self, ctx, *blocks, results=()):
        self.n += 1
        usage = {"input_tokens": 2, "cache_creation_input_tokens": 100, "cache_read_input_tokens": ctx - 102, "output_tokens": 10}
        self.events.append({"type": "assistant", "message": {"id": f"m{self.n}", "content": list(blocks), "usage": usage}})
        for tool_id, text in results:
            self.events.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": text}]}})

    def end(self, cost, prompt, output, thinking=0, ms=1000):
        self.cost += cost
        self.events.append({"type": "result", "session_id": self.sid, "total_cost_usd": self.cost, "duration_ms": ms,
                            "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": prompt,
                                      "output_tokens": output, "output_tokens_details": {"thinking_tokens": thinking}}})


def tool(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def save_run(results, case, n, session):
    write(os.path.join(results, f"{case}-{n}.json"), json.dumps({"case": case, "skill": "demo", "run": n}))
    write(os.path.join(results, f"{case}-{n}.events.jsonl"), "\n".join(json.dumps(e) for e in session.events))


def fired_run(prompt, cost, read_b=False):
    s = Session()
    s.call(20000, tool("t1", "Skill", skill="demo"), results=[("t1", "Launching skill: demo")])
    command = "cd /tmp/w/.claude/skills/demo && cat references/a.md"
    if read_b:
        command += " references/b.md"
    s.call(20300, tool("t2", "Bash", command=command), results=[("t2", "a" * 300)])
    s.call(20500, {"type": "text", "text": "done"})
    s.end(cost, prompt, 500, thinking=50)
    return s


class Aggregation(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.results = tempfile.mkdtemp()
        save_run(self.results, "demo-task", 1, fired_run(100, 0.10))
        save_run(self.results, "demo-task", 2, fired_run(300, 0.30, read_b=True))
        save_run(self.results, "demo-task", 3, fired_run(200, 0.20))
        skip = Session()
        skip.call(20000, {"type": "text", "text": "fixed"})
        skip.end(0.05, 50, 20)
        save_run(self.results, "demo-skip", 1, skip)
        self.skills = tokens.load_skills(self.root)
        self.runs = tokens.load_results(self.results, self.skills)

    def by_case(self, case):
        return [r for r in self.runs if r["case"] == case]

    def test_median_and_max_over_runs(self):
        mm = tokens.med_max(self.by_case("demo-task"))
        self.assertEqual(mm["cost"], (0.20, 0.30))
        self.assertEqual(mm["prompt"], (200, 300))
        self.assertEqual(mm["calls"], (3, 3))
        self.assertEqual(mm["peak"], (20500, 20500))
        self.assertEqual(mm["thinking"], (50, 50))

    def test_fired_and_baseline_are_told_apart(self):
        cases = tokens.load_cases(self.root, self.skills)
        self.assertTrue(cases["demo-skip"]["baseline"])
        self.assertFalse(cases["demo-task"]["baseline"])
        self.assertTrue(all(r["fired"] for r in self.by_case("demo-task")))
        self.assertFalse(self.by_case("demo-skip")[0]["fired"])

    def test_file_reads_are_counted_per_run(self):
        counts = tokens.read_counts(self.runs)
        self.assertEqual(counts[("demo", "SKILL.md")], {"demo-task": [3, 0]})
        self.assertEqual(counts[("demo", "references/a.md")], {"demo-task": [3, 0]})
        self.assertEqual(counts[("demo", "references/b.md")], {"demo-task": [1, 0]})
        self.assertNotIn(("demo", "assets/t.html"), counts)

    def test_cost_of_a_resumed_turn_excludes_earlier_turns(self):
        s = Session()
        s.call(20000, {"type": "text", "text": "plan"})
        s.end(0.10, 100, 10)
        s.call(21000, {"type": "text", "text": "built"})
        s.end(0.25, 200, 10)
        turns, _ = tokens.parse_events([json.dumps(e) for e in s.events], self.skills)
        self.assertEqual([round(t["cost"], 2) for t in turns], [0.10, 0.25])

    def test_report_renders(self):
        text = tokens.report(self.results, self.root)
        for heading in ("== 1.", "== 2.", "== 3.", "== 4."):
            self.assertIn(heading, text)
        self.assertIn("overhead (median)", text)


class BashReads(unittest.TestCase):
    def setUp(self):
        self.skills = tokens.load_skills(make_root())

    def reads(self, command):
        return sorted(tokens.bash_reads(command, self.skills)[0])

    def test_cd_then_relative_cat(self):
        self.assertEqual(self.reads("cd /tmp/w/.claude/skills/demo && cat references/a.md SKILL.md"),
                         [("demo", "SKILL.md", True), ("demo", "references/a.md", True)])

    def test_variable_and_braces(self):
        self.assertEqual(self.reads("G=.claude/skills/demo; cat $G/references/{a,b}.md"),
                         [("demo", "references/a.md", True), ("demo", "references/b.md", True)])

    def test_piped_or_ranged_reads_are_partial(self):
        self.assertEqual(self.reads("cat .claude/skills/demo/references/a.md | head -20"),
                         [("demo", "references/a.md", False)])
        self.assertEqual(self.reads("sed -n '1,5p' .claude/skills/demo/assets/t.html"),
                         [("demo", "assets/t.html", False)])

    def test_quoted_pipe_in_a_grep_pattern(self):
        self.assertEqual(self.reads("grep -n 'a|b' .claude/skills/demo/references/b.md"),
                         [("demo", "references/b.md", False)])

    def test_copies_redirects_and_heredocs_load_nothing(self):
        self.assertEqual(self.reads("cp .claude/skills/demo/assets/t.html out.html"), [])
        self.assertEqual(self.reads("sed -n '1,$p' .claude/skills/demo/assets/t.html > /tmp/x"), [])
        self.assertEqual(self.reads("python3 - <<'EOF'\nopen('.claude/skills/demo/assets/t.html')\nEOF"), [])


if __name__ == "__main__":
    unittest.main()
