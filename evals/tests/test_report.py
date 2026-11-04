"""Run with: python3 -I -m unittest discover -s evals/tests"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import report  # noqa: E402
from test_tokens import fired_run, make_root, write  # noqa: E402


def save(results, n, cost, passed, note="", reply="done"):
    session = fired_run(100, cost)
    record = {
        "case": "demo-task", "skill": "demo", "run": n, "workspace": f"/tmp/w{n}", "seconds": 10, "cost": cost,
        "pass": passed, "graders": [{"name": "page builds", "pass": passed, "note": note}],
        "turns": [{"prompt": "make <it>", "text": reply, "cost": cost,
                   "tools": [{"name": "Bash", "input": {"command": "cat references/a.md"}}]}],
    }
    write(os.path.join(results, f"demo-task-{n}.json"), json.dumps(record))
    write(os.path.join(results, f"demo-task-{n}.events.jsonl"), "\n".join(json.dumps(e) for e in session.events))


def read(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return f.read()


class LocalReport(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.now, self.before = tempfile.mkdtemp(), tempfile.mkdtemp()
        save(self.now, 1, 0.10, True, reply="**Built** the `cards.html` page")
        save(self.now, 2, 0.30, False, note="export check: <did not report>")
        write(os.path.join(self.now, "demo-task-1", "out", "cards.html"), "<p>x</p>")
        save(self.before, 1, 0.50, True)
        self.out = os.path.join(self.now, "report")
        report.write_report(self.now, self.out, self.before, root=self.root)
        self.index = read(self.out, "index.html")

    def test_index_counts_and_links_each_run(self):
        self.assertIn("1/2", self.index)
        self.assertIn('href="runs/demo-task-2.html"', self.index)

    def test_compare_shows_the_older_cost(self):
        self.assertIn('<td class="num">$0.20</td><td class="num">$0.50</td>', self.index)

    def test_failed_run_link_says_so(self):
        self.assertIn('class="fail">2 failed</a>', self.index)

    def test_run_page_escapes_and_shows_the_failure(self):
        page = read(self.out, "runs", "demo-task-2.html")
        self.assertIn("export check: &lt;did not report&gt;", page)
        self.assertIn("make &lt;it&gt;", page)
        self.assertIn("Failed", page)

    def test_reply_markdown_bold_and_code(self):
        page = read(self.out, "runs", "demo-task-1.html")
        self.assertIn("<strong>Built</strong> the <code>cards.html</code> page", page)

    def test_local_run_page_links_built_files(self):
        self.assertIn('href="../../demo-task-1/out/cards.html"', read(self.out, "runs", "demo-task-1.html"))


if __name__ == "__main__":
    unittest.main()
