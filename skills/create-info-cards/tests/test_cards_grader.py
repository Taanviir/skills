"""Run with: python3 -I -m unittest discover -s skills/create-info-cards/tests"""
import os
import subprocess
import sys
import tempfile
import unittest

from test_scripts import card, page

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADER = os.path.join(ROOT, "evals", "graders", "cards.py")
HARBOR = os.path.join(ROOT, "evals", "fixtures", "harbor-article.html")
LIBRARY = os.path.join(ROOT, "evals", "fixtures", "library-report.pdf")

TRUE_LINE = '<p class="lede">1,850 workers, 3 berths, 38% less emissions, 19 months.</p>'


def grade(cards, *args):
    with tempfile.TemporaryDirectory() as d:
        if cards:
            page(d, cards)
        r = subprocess.run([sys.executable, "-I", GRADER, *args[:1], d, *args[1:]], capture_output=True, text=True)
        return r.returncode, r.stdout


def body(line=TRUE_LINE):
    return "<h2>Harbor rebuilt for $412 million</h2>" + line * 6


class CardsGrader(unittest.TestCase):
    def test_numbers_from_the_source_pass(self):
        code, out = grade([card("01", body()), card("02", body())], "built", HARBOR, "2", "4")
        self.assertEqual(code, 0, out)

    def test_an_invented_number_fails(self):
        code, out = grade([card("01", body(TRUE_LINE.replace("38%", "977%")))], "built", HARBOR, "1", "4")
        self.assertEqual(code, 1)
        self.assertIn("977", out)

    def test_spelled_out_numbers_count(self):
        code, out = grade([card("01", body())], "built", HARBOR, "1", "4")
        self.assertNotIn("'3'", out)

    def test_card_count_out_of_range_fails(self):
        code, out = grade([card("01", body())], "built", HARBOR, "2", "4")
        self.assertEqual(code, 1)
        self.assertIn("1 cards", out)

    def test_pdf_source_is_read(self):
        line = '<p class="lede">1.42 million visits, up 18 percent, 7 branches.</p>'
        code, out = grade([card("01", "<h2>Northbank 2025</h2>" + line * 10)], "built", LIBRARY, "1", "2")
        self.assertEqual(code, 0, out)

    def test_dash_skips_number_tracing(self):
        code, out = grade([card("01", body(TRUE_LINE.replace("38%", "977%")))], "built", "-", "1", "2")
        self.assertEqual(code, 0, out)

    def test_cards_with_extra_classes_are_counted(self):
        two = card("01", body()) + card("02", body()).replace('class="card"', 'class="card big"')
        code, out = grade([two], "built", HARBOR, "2", "2")
        self.assertEqual(code, 0, out)

    def test_numbers_from_the_confirmed_replies_count(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("Fact sheet: 48 berths now, 40 before.")
        line = '<p class="lede">40 fishing berths before, 48 now.</p>'
        code, out = grade([card("01", "<h2>North basin</h2>" + line * 10)], "built", HARBOR, "1", "2", f.name)
        os.unlink(f.name)
        self.assertEqual(code, 0, out)

    def test_a_difference_of_source_numbers_passes_as_derived(self):
        line = '<p class="lede">210 more permanent jobs, 620 in all.</p>'
        code, out = grade([card("01", "<h2>Jobs</h2>" + line * 10)], "built", HARBOR, "1", "2")
        self.assertEqual(code, 0, out)
        self.assertIn("derived: 210", out)

    def test_the_top_strip_is_not_checked(self):
        top = card("01", body()).replace('<div class="card-top"></div>', '<div class="card-top"><span>027.4</span></div>')
        code, out = grade([top], "built", HARBOR, "1", "2")
        self.assertEqual(code, 0, out)

    def test_no_page(self):
        self.assertEqual(grade([], "no-page")[0], 0)
        self.assertEqual(grade([card("01", body())], "no-page")[0], 1)


if __name__ == "__main__":
    unittest.main()
