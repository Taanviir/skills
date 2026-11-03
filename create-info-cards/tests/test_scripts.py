"""Run with: python3 -I -m unittest discover -s create-info-cards/tests"""
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
TEMPLATE = os.path.join(ROOT, "assets", "template.html")


def run(*args, cwd=None):
    return subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=180)


def card(name, body):
    return (
        f'<figure><div class="frame"><article class="card" data-name="{name}">'
        f'<div class="card-top"></div><div class="card-body">{body}</div>'
        f'<div class="card-foot"><span>Source</span><b>1 / 1</b></div>'
        f'</article></div><figcaption><button type="button" class="save">Save PNG</button></figcaption></figure>'
    )


def page(dirname, cards):
    """Writes the template with the given cards in place of its sample card."""
    html = open(TEMPLATE, encoding="utf-8").read()
    start = html.index("    <!-- One <figure> per card.")
    end = html.index("</figure>", start) + len("</figure>")
    html = html[:start] + "\n".join(cards) + html[end:]
    path = os.path.join(dirname, "page.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


FULL = "<h2>Headline</h2>" + "".join(f'<p class="lede">Line {i} of steady text.</p>' for i in range(10))
OVER = "<h2>Headline</h2>" + "".join(f'<p class="lede">Line {i} of steady text.</p>' for i in range(30))
EMPTY = "<h2>Short</h2>"


class CheckFit(unittest.TestCase):
    def test_reports_overflow_loose_and_ok_per_card(self):
        with tempfile.TemporaryDirectory() as d:
            p = page(d, [card("01-full", FULL), card("02-over", OVER), card("03-empty", EMPTY)])
            r = run(sys.executable, "-I", os.path.join(SCRIPTS, "check.py"), p, "fit")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            status = dict(re.findall(r"^(\S+)\s+overflow=.*\s(\S+)$", r.stdout, re.M))
            self.assertEqual(status, {"01-full": "ok", "02-over": "OVERFLOW", "03-empty": "LOOSE"}, r.stdout)
            self.assertIn("2 card(s) need work", r.stdout)

    def test_all_fit_exits_0(self):
        with tempfile.TemporaryDirectory() as d:
            p = page(d, [card("01-full", FULL)])
            r = run(sys.executable, "-I", os.path.join(SCRIPTS, "check.py"), p, "fit")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("ALL CARDS FIT", r.stdout)

    def test_leaves_no_temp_copy_beside_the_page(self):
        with tempfile.TemporaryDirectory() as d:
            p = page(d, [card("01-full", FULL)])
            run(sys.executable, "-I", os.path.join(SCRIPTS, "check.py"), p, "fit")
            self.assertEqual(os.listdir(d), ["page.html"])


class CheckShotAndExport(unittest.TestCase):
    def test_shot_writes_a_png(self):
        with tempfile.TemporaryDirectory() as d:
            p = page(d, [card("01-full", FULL)])
            out = os.path.join(d, "shot.png")
            run(sys.executable, "-I", os.path.join(SCRIPTS, "check.py"), p, "shot", out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    def test_export_renders_card_one(self):
        with tempfile.TemporaryDirectory() as d:
            p = page(d, [card("01-full", FULL)])
            r = run(sys.executable, "-I", os.path.join(SCRIPTS, "check.py"), p, "export")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("'ok': True", r.stdout)


VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000 align:start position:0%
hello<00:00:01.500><c> there</c>

00:00:03.000 --> 00:00:05.000 align:start position:0%
hello there
first point &gt; second

00:01:05.000 --> 00:01:07.000 align:start position:0%
a minute later
"""


class Vtt2Txt(unittest.TestCase):
    def test_strips_tags_dedupes_and_stamps_each_minute(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, "in.vtt"), os.path.join(d, "out.txt")
            with open(src, "w", encoding="utf-8") as f:
                f.write(VTT)
            r = run(sys.executable, "-I", os.path.join(SCRIPTS, "vtt2txt.py"), src, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = open(out, encoding="utf-8").read()
            self.assertEqual(text.count("hello there"), 1)
            self.assertIn("[0:00:01] hello there", text)
            self.assertIn("[0:01:05] a minute later", text)
            self.assertNotIn("<c>", text)


class FetchSource(unittest.TestCase):
    def test_unknown_source_exits_1(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("bash", os.path.join(SCRIPTS, "fetch_source.sh"), "notes.docx", d)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Unknown source type", r.stderr)

    def test_pdf_text_is_extracted(self):
        with tempfile.TemporaryDirectory() as d:
            pdf = os.path.join(d, "doc.pdf")
            fixture = os.path.join(ROOT, "evals", "fixtures", "library-report.pdf")
            self.assertTrue(os.path.exists(fixture), "build the fixture with evals/fixtures/build.sh")
            r = run("bash", os.path.join(SCRIPTS, "fetch_source.sh"), fixture, d)
            self.assertEqual(r.returncode, 0, r.stderr)
            text = open(os.path.join(d, "source.txt"), encoding="utf-8").read()
            self.assertIn("Northbank", text)


if __name__ == "__main__":
    unittest.main()
