"""Headless dashboard tests (Streamlit AppTest). Builds a tiny analysis output from the synthetic workbook."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in (ROOT, os.path.join(ROOT, "tests"), os.path.join(ROOT, "dashboard")):
    if p not in sys.path:
        sys.path.insert(0, p)

from helpers import write_workbook            # noqa: E402
from ml_analysis.cli import main              # noqa: E402
from streamlit.testing.v1 import AppTest      # noqa: E402

APP = os.path.join(ROOT, "dashboard", "app.py")


def run_app(out_dir):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.sidebar.text_input[0].set_value(out_dir).run()
    return at


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        wb = write_workbook(os.path.join(cls.tmp.name, "t.xlsx"))
        cls.out = os.path.join(cls.tmp.name, "out")
        main(["--workbook", wb, "--out", cls.out, "--leagues", "1"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_renders_synthetic_league(self):
        at = run_app(self.out)
        self.assertEqual(len(at.exception), 0, [e.message for e in at.exception])
        self.assertTrue(any("Test League" in t.value for t in at.title), [t.value for t in at.title])
        self.assertEqual(len(at.tabs), 8)

    def test_missing_output_folder_shows_a_clear_error(self):
        at = run_app(os.path.join(self.tmp.name, "nope"))
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(any("manifest.json" in e.value for e in at.sidebar.error))

    def test_hiding_votes_still_renders_and_explains(self):
        at = run_app(self.out)
        at.sidebar.checkbox[0].uncheck().run()
        self.assertEqual(len(at.exception), 0, [e.message for e in at.exception])
        self.assertTrue(any("hidden" in i.value for i in at.info))

    def test_recap_page_story_and_gallery_on_synthetic_data(self):
        at = run_app(self.out)
        at.switch_page("screens/recap.py").run()
        self.assertEqual(len(at.exception), 0, [e.message for e in at.exception])
        self.assertTrue(any("Music League Wrapped" in t.value for t in at.title))
        steps = 0
        while True:
            nxt = [b for b in at.button if b.label == "Next"]
            if not nxt or nxt[0].disabled:
                break
            nxt[0].click().run(); steps += 1
            self.assertEqual(len(at.exception), 0, (steps, [e.message for e in at.exception]))
        self.assertGreater(steps, 3)
        at.radio[0].set_value("All awards").run()
        self.assertEqual(len(at.exception), 0, [e.message for e in at.exception])

    @unittest.skipUnless(os.environ.get("ML_OUT") and os.path.exists(os.path.join(os.environ.get("ML_OUT", ""), "manifest.json")), "set ML_OUT to run")
    def test_relationship_slide_is_gated_by_the_privacy_switch(self):
        at = run_app(os.environ["ML_OUT"])
        at.switch_page("screens/recap.py").run()
        opts = lambda: [o for sb in at.selectbox for o in sb.options]
        self.assertTrue(any("Biggest fans" in o for o in opts()))
        at.sidebar.checkbox[0].uncheck().run()
        self.assertEqual(len(at.exception), 0)
        self.assertFalse(any("Biggest fans" in o for o in opts()))

    @unittest.skipUnless(os.environ.get("ML_OUT") and os.path.exists(os.path.join(os.environ.get("ML_OUT", ""), "manifest.json")), "set ML_OUT to run")
    def test_every_recap_scope_and_slide_in_real_output(self):
        at = run_app(os.environ["ML_OUT"])
        at.switch_page("screens/recap.py").run()
        for sc in at.sidebar.selectbox[0].options:
            at.sidebar.selectbox[0].select(sc).run()
            while True:
                nxt = [b for b in at.button if b.label == "Next"]
                if not nxt or nxt[0].disabled:
                    break
                nxt[0].click().run()
                self.assertEqual(len(at.exception), 0, (sc, [e.message for e in at.exception]))

    @unittest.skipUnless(os.environ.get("ML_OUT") and os.path.exists(os.path.join(os.environ.get("ML_OUT", ""), "manifest.json")), "set ML_OUT to run")
    def test_every_league_in_real_output(self):
        at = run_app(os.environ["ML_OUT"])
        for o in at.sidebar.selectbox[0].options:
            at.sidebar.selectbox[0].select(o).run()
            self.assertEqual(len(at.exception), 0, (o, [e.message for e in at.exception]))


if __name__ == "__main__":
    unittest.main()
