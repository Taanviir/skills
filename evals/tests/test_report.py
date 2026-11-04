"""Run with: python3 -I -m unittest discover -s evals/tests"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402
from test_tokens import fired_run, make_root, write  # noqa: E402


def save(results, n, cost, passed, note=""):
    session = fired_run(100, cost)
    record = {
        "case": "demo-task", "skill": "demo", "run": n, "workspace": f"/tmp/w{n}", "seconds": 10, "cost": cost,
        "pass": passed, "graders": [{"name": "page builds", "pass": passed, "note": note}],
        "turns": [{"prompt": "make <it>", "text": "done", "cost": cost,
                   "tools": [{"name": "Bash", "input": {"command": "cat references/a.md"}}]}],
    }
    write(os.path.join(results, f"demo-task-{n}.json"), json.dumps(record))
    write(os.path.join(results, f"demo-task-{n}.events.jsonl"), "\n".join(json.dumps(e) for e in session.events))


class Report(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.now, self.before = tempfile.mkdtemp(), tempfile.mkdtemp()
        save(self.now, 1, 0.10, True)
        save(self.now, 2, 0.30, False, note="export check: <did not report>")
        write(os.path.join(self.now, "demo-task-1", "out", "cards.html"), "<p>x</p>")
        save(self.before, 1, 0.50, True)
        self.page = report.build(self.now, self.before, root=self.root)

    def test_counts_and_cells(self):
        self.assertIn("1/2 runs passed", self.page)
        self.assertIn('href="#demo-task-2">fail 2</a>', self.page)

    def test_failed_run_is_open_with_escaped_reason(self):
        self.assertIn('id="demo-task-2" open', self.page)
        self.assertIn("export check: &lt;did not report&gt;", self.page)
        self.assertIn("make &lt;it&gt;", self.page)

    def test_compare_uses_costs_from_events(self):
        self.assertIn('<td class="nums">$0.20</td><td class="nums delta-down">$0.50</td>', self.page)

    def test_output_pages_are_linked(self):
        self.assertIn('href="demo-task-1/out/cards.html"', self.page)


if __name__ == "__main__":
    unittest.main()
