"""Run with: python3 -I -m unittest discover -s evals/tests"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run  # noqa: E402

CASE = {"skill": "graphite-ui", "graders": [{"name": "waited", "type": "no_writes", "turn": 0}]}


class NoWrites(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp()
        with open(os.path.join(self.ws, "a.css"), "w") as f:
            f.write(".a {}\n")
        os.makedirs(os.path.join(self.ws, ".claude"))

    def turn(self, before):
        return {"text": "", "files_before": before, "files": run.snapshot(self.ws)}

    def grade(self, turns):
        return run.grade(CASE, self.ws, turns)[0][0]

    def test_a_turn_that_only_reads_passes(self):
        before = run.snapshot(self.ws)
        self.assertTrue(self.grade([self.turn(before)])["pass"])

    def test_an_edit_fails_and_names_the_file(self):
        before = run.snapshot(self.ws)
        with open(os.path.join(self.ws, "a.css"), "a") as f:
            f.write(".b {}\n")
        r = self.grade([self.turn(before)])
        self.assertFalse(r["pass"])
        self.assertIn("a.css", r["note"])

    def test_a_new_file_fails(self):
        before = run.snapshot(self.ws)
        open(os.path.join(self.ws, "cards.html"), "w").close()
        self.assertFalse(self.grade([self.turn(before)])["pass"])

    def test_files_under_claude_are_ignored(self):
        before = run.snapshot(self.ws)
        open(os.path.join(self.ws, ".claude", "notes.md"), "w").close()
        self.assertTrue(self.grade([self.turn(before)])["pass"])

    def test_a_turn_that_never_ran_fails(self):
        self.assertFalse(self.grade([])["pass"])


class MissingTurn(unittest.TestCase):
    def test_a_regex_on_a_turn_that_never_ran_fails_instead_of_reading_the_last_one(self):
        case = {"skill": "graphite-ui", "graders": [
            {"name": "no plan in turn 1", "type": "regex", "turn": 1, "pattern": "plan", "expect": False}]}
        r = run.grade(case, tempfile.mkdtemp(), [{"text": "done"}])[0][0]
        self.assertFalse(r["pass"])
        self.assertIn("turn 1 never ran", r["note"])


if __name__ == "__main__":
    unittest.main()
