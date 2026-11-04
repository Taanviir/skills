"""Run with: python3 -I -m unittest discover -s skills/graphite-ui/tests -p 'test_*.py'"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADER = os.path.join(ROOT, "evals", "graders", "rework.py")
PLAIN = os.path.join(ROOT, "evals", "fixtures", "plain-app")

# A minimal correct rework of plain-app: same ids and text, tokens installed, no literals.
REWORKED_CSS = """\
@import "graphite-ui/tokens.css";
@import "graphite-ui/base.css";
:root { --gr-accent-h: 263; --gr-accent-c: 0.95; }
.layout { display: flex; }
.side-nav { background: var(--gr-bg-surface); padding: var(--gr-space-4); }
.btn { padding: var(--gr-space-2) var(--gr-space-4); border-radius: var(--gr-radius-control); }
.btn-primary { background: var(--gr-accent-solid); color: var(--gr-fg-on-accent); }
"""
REWORKED_JS_HEAD = (
    "const css = getComputedStyle(document.documentElement);\n"
    "const CHART_COLORS = { bar: css.getPropertyValue('--gr-series-1'), grid: css.getPropertyValue('--gr-border-separator'),"
    " label: css.getPropertyValue('--gr-fg-secondary') };\n"
)


def grade(mode, run_dir, *extra):
    r = subprocess.run([sys.executable, "-I", GRADER, mode, run_dir, *extra], capture_output=True, text=True)
    return r.returncode, r.stdout


class ReworkGrader(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.app = os.path.join(self.dir, "app")
        shutil.copytree(PLAIN, self.app)

    def tearDown(self):
        shutil.rmtree(self.dir)

    def rework(self):
        os.makedirs(os.path.join(self.app, "graphite-ui"))
        for f in ("tokens.css", "base.css"):
            shutil.copy(os.path.join(ROOT, "assets", f), os.path.join(self.app, "graphite-ui", f))
        with open(os.path.join(self.app, "style.css"), "w") as f:
            f.write(REWORKED_CSS)
        js = open(os.path.join(PLAIN, "app.js")).read().split("\n", 1)[1]
        with open(os.path.join(self.app, "app.js"), "w") as f:
            f.write(REWORKED_JS_HEAD + js.replace("document.body.classList.toggle('dark');", "document.documentElement.dataset.theme = 'dark';"))

    def test_unchanged_passes_on_a_copy_and_fails_on_an_edit(self):
        self.assertEqual(grade("unchanged", self.app, PLAIN)[0], 0)
        with open(os.path.join(self.app, "style.css"), "a") as f:
            f.write("\n.x {}\n")
        code, out = grade("unchanged", self.app, PLAIN)
        self.assertEqual(code, 1)
        self.assertIn("style.css", out)

    def test_untouched_app_is_not_a_rework(self):
        self.assertEqual(grade("reworked", self.app, PLAIN)[0], 1)

    def test_a_correct_rework_passes(self):
        self.rework()
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 0, out)

    def test_a_lost_element_id_fails(self):
        self.rework()
        page = os.path.join(self.app, "index.html")
        html = open(page).read().replace('id="late-alert"', "")
        open(page, "w").write(html)
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 1)
        self.assertIn("late-alert", out)

    def test_lost_visible_text_fails(self):
        self.rework()
        page = os.path.join(self.app, "index.html")
        html = open(page).read().replace("Keep it", "Keep")
        open(page, "w").write(html)
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 1)
        self.assertIn("Keep it", out)

    def test_text_kept_as_an_aria_label_passes(self):
        self.rework()
        page = os.path.join(self.app, "index.html")
        html = open(page).read().replace('id="keep">Keep it</button>', 'id="keep" aria-label="Keep it"></button>')
        open(page, "w").write(html)
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 0, out)

    def test_a_leftover_old_token_fails(self):
        self.rework()
        with open(os.path.join(self.app, "style.css"), "a") as f:
            f.write(":root { --primary: var(--gr-accent-solid); }\n")
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 1)
        self.assertIn("--primary", out)

    def test_a_hex_left_in_js_fails(self):
        self.rework()
        with open(os.path.join(self.app, "app.js"), "a") as f:
            f.write("\nconst EXTRA = '#ff0000';\n")
        code, out = grade("reworked", self.app, PLAIN)
        self.assertEqual(code, 1)
        self.assertIn("script-color", out)

    def test_knobs(self):
        self.rework()
        self.assertEqual(grade("knobs", self.app, "263", "6")[0], 0)
        self.assertEqual(grade("knobs", self.app, "150", "6")[0], 1)
        self.assertEqual(grade("knobs", self.app, "260", "6")[0], 0)


if __name__ == "__main__":
    unittest.main()
