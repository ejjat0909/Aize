"""Tests for the screenshot comparison itself.

A visual-regression harness that cannot fail is worse than none: it produces a green tick and a false sense of
having looked. These tests make synthetic changes of known sizes and assert the comparator reacts, so the
thresholds are a measured decision rather than a number someone picked.

Run with:  python3 -m unittest discover -s scripts -p "test_*.py"
"""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import screenshot_catalogue as sc  # noqa: E402

BACKGROUND = (243, 241, 247)
INK = (24, 20, 33)
PURPLE = (137, 55, 241)


def page(ink=INK, box=None):
    """A synthetic catalogue page: a header block, a button, and optionally one small square."""
    im = Image.new("RGB", (1080, 1920), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, 1080, 1848], fill=BACKGROUND)
    draw.rectangle([60, 120, 1020, 400], fill=ink)
    draw.rectangle([60, 500, 600, 700], fill=PURPLE)
    if box is not None:
        draw.rectangle(box, fill=(200, 40, 40))
    return im


class ComparisonTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.golden = self.dir / "page.png"
        page().save(self.golden)

    def test_an_identical_capture_matches(self):
        mean, pct, verdict = sc.compare(page(), self.golden)
        self.assertEqual("ok", verdict)
        self.assertLess(mean, 0.01)
        self.assertLess(pct, 0.01)

    def test_a_missing_golden_is_a_failure_not_a_pass(self):
        _, pct, verdict = sc.compare(page(), self.dir / "nope.png")
        self.assertEqual("missing golden", verdict)
        self.assertEqual(100.0, pct)

    def test_a_size_change_is_a_failure(self):
        _, _, verdict = sc.compare(page().resize((1080, 1600)), self.golden)
        self.assertIn("size", verdict)

    def test_a_colour_change_on_a_component_is_caught(self):
        # A button changing colour is a 400x200 patch: under 1% of the screen, so the mean barely notices it and
        # the pixel count does. This is why the gate reports both numbers.
        mean, pct, verdict = sc.compare(page(ink=(120, 40, 200)), self.golden)
        self.assertEqual("differs", verdict)
        self.assertGreater(pct, sc.MAX_DIFF_PIXEL_PCT)

    def test_a_moved_element_is_caught(self):
        moved = page()
        ImageDraw.Draw(moved).rectangle([60, 500, 600, 700], fill=BACKGROUND)
        ImageDraw.Draw(moved).rectangle([60, 520, 600, 720], fill=PURPLE)
        _, _, verdict = sc.compare(moved, self.golden)
        self.assertEqual("differs", verdict)

    def test_one_glyph_changing_is_caught(self):
        # 24 dp at 420 dpi is ~63 px square: a single icon in a 61-icon grid. If this passes, the gate is not
        # watching the glyphs it exists for.
        _, pct, verdict = sc.compare(page(box=(200, 1500, 263, 1563)), self.golden)
        self.assertEqual("differs", verdict)
        self.assertGreater(pct, sc.MAX_DIFF_PIXEL_PCT)

    def test_antialiasing_noise_is_not_a_failure(self):
        # A handful of edge pixels is what two runs on the same emulator actually produce.
        noisy = page()
        ImageDraw.Draw(noisy).point([(500 + i, 900) for i in range(40)], fill=(210, 210, 210))
        _, _, verdict = sc.compare(noisy, self.golden)
        self.assertEqual("ok", verdict)

    def test_the_system_navigation_bar_is_outside_the_comparison(self):
        # The gesture pill fades in and out on its own; that is not the app's pixels and must not fail a page.
        shot = page()
        ImageDraw.Draw(shot).rectangle([400, sc.CONTENT_HEIGHT + 2, 680, 1900], fill=(255, 255, 255))
        _, _, verdict = sc.compare(shot, self.golden)
        self.assertEqual("ok", verdict)

    def test_the_section_list_matches_the_enum_in_the_app(self):
        # The script hard-codes the page ids so it can run without compiling Kotlin; this keeps the two lists
        # from drifting apart silently.
        source = (Path(sc.REPO) / "app/src/debug/kotlin/app/aize/catalogue/CatalogueSection.kt").read_text()
        declared = [
            line.split('"')[1]
            for line in source.splitlines()
            if line.strip().startswith(("Colour(", "Type(", "Icon(", "Button(", "Control(", "Surface(", "Shape(", "Motion("))
        ]
        self.assertEqual(declared, sc.SECTIONS)


if __name__ == "__main__":
    unittest.main()
