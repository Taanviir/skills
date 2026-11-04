"""Run with: python3 -I -m unittest discover -s skills/project-presentation/tests"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADER = os.path.join(ROOT, "evals", "graders", "deck.py")
TEMPLATE = os.path.join(ROOT, "assets", "template.html")


def filled_template():
    html = open(TEMPLATE, encoding="utf-8").read()
    return re.sub(r"\{\{[A-Z0-9_]+\}\}", "Tidepool", html).replace("</style>", ".brand { color: #0f766e; }</style>")


def grade(html, name="tidepool-presentation.html", brand="#0f766e"):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(html)
        r = subprocess.run([sys.executable, "-I", GRADER, "built", d, "tidepool", brand], capture_output=True, text=True)
        return r.returncode, r.stdout


def phone(html):
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "x-presentation.html"), "w", encoding="utf-8") as f:
            f.write(html)
        r = subprocess.run([sys.executable, "-I", GRADER, "phone", d], capture_output=True, text=True)
        return r.returncode, r.stdout


class DeckGrader(unittest.TestCase):
    def test_filled_template_passes(self):
        code, out = grade(filled_template())
        self.assertEqual(code, 0, out)

    def test_left_placeholder_fails(self):
        code, out = grade(filled_template().replace("Tidepool", "{{PROJECT_NAME}}", 1))
        self.assertEqual(code, 1)
        self.assertIn("unfilled placeholders", out)

    def test_cdn_stylesheet_fails(self):
        html = filled_template().replace("</head>", '<link rel="stylesheet" href="https://cdn.example.com/x.css"></head>')
        code, out = grade(html)
        self.assertEqual(code, 1)
        self.assertIn("network", out)

    def test_too_few_slides_fails(self):
        html = filled_template()
        sections = re.findall(r'<section class="slide[\s\S]*?</section>', html)
        for s in sections[3:]:
            html = html.replace(s, "")
        code, out = grade(html)
        self.assertEqual(code, 1)
        self.assertIn("slides", out)

    def test_wrong_name_and_missing_brand_fail(self):
        self.assertEqual(grade(filled_template(), name="deck-presentation.html")[0], 1)
        self.assertEqual(grade(filled_template().replace("#0f766e", "#123456"))[0], 1)

    def test_no_brand_check_with_dash(self):
        self.assertEqual(grade(filled_template().replace("#0f766e", "#123456"), brand="-")[0], 0)

    def test_broken_script_fails(self):
        code, out = grade(filled_template().replace("</body>", "<script>function (</script></body>"))
        self.assertEqual(code, 1)
        self.assertIn("parse", out)

class PhoneWidth(unittest.TestCase):
    """Needs headless Chromium from Playwright's cache."""

    def test_template_with_a_long_title_fits(self):
        code, out = phone(re.sub(r"\{\{[A-Z0-9_]+\}\}", "ledgerline", open(TEMPLATE, encoding="utf-8").read()))
        self.assertEqual(code, 0, out)

    def test_fixed_width_content_fails(self):
        html = filled_template().replace("</style>", ".cover h1 { width: 600px; }</style>")
        code, out = phone(html)
        self.assertEqual(code, 1)
        self.assertIn("slide 1", out)


if __name__ == "__main__":
    unittest.main()
