import math
import os
import tempfile
import unittest
import numpy as np
import pandas as pd

from ml_analysis.config import Config
from ml_analysis.data import DataError, load_dataset
from ml_analysis.league import analyze_league
from ml_analysis.recap import build_recap
from ml_analysis.cli import main
from helpers import write_workbook, songs_rows, votes_rows


def cfg(**kw):
    base = dict(min_league_rounds=2, twin_min_shared_rounds=2, min_submissions_award=2, min_submissions_average=2,
                min_ballots=2, min_shared_rounds_pair=2)
    base.update(kw)
    return Config(**base)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = write_workbook(os.path.join(self.tmp.name, "t.xlsx"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_statuses_places_and_eligibility(self):
        ds = load_dataset(self.path, cfg())
        s = ds.songs.set_index("song")
        self.assertEqual(s.loc["sD", "status"], "Forfeited")
        self.assertEqual(s.loc["sE2", "status"], "Zero-vote")
        self.assertEqual(sum(s["status"] == "OK"), 7)
        self.assertEqual(list(s.loc[["sA2", "sB2", "sC2", "sD2", "sE2"], "place"]), [1, 2, 2, 4, 5])
        self.assertEqual((s.loc["sA", "elig"], s.loc["sD", "elig"], s.loc["sE2", "elig"]), (2, 3, 4))
        self.assertTrue(ds.rounds["league_complete"].all())

    def test_mismatch_is_flagged_not_hidden(self):
        rows = songs_rows(); rows[0] = rows[0][:5] + (9,) + rows[0][6:]   # typed 9 points but votes sum to 3
        ds = load_dataset(write_workbook(os.path.join(self.tmp.name, "m.xlsx"), songs=rows), cfg())
        self.assertEqual(ds.songs.set_index("song").loc["sA", "status"], "Mismatch")

    def test_unjoined_votes_halt_with_a_clear_message(self):
        votes = votes_rows() + [(1, "A", "u:NOPE", 1)]
        p = write_workbook(os.path.join(self.tmp.name, "u.xlsx"), votes=votes)
        with self.assertRaises(DataError) as cm:
            load_dataset(p, cfg())
        self.assertIn("do not join", str(cm.exception))

    def test_self_votes_and_duplicates_are_dropped_and_reported(self):
        votes = votes_rows() + [(1, "A", "u:A1", 1), (1, "A", "u:B1", 2)]   # self-vote + duplicate of an existing row
        ds = load_dataset(write_workbook(os.path.join(self.tmp.name, "d.xlsx"), votes=votes), cfg())
        v = ds.validation.set_index("check")
        self.assertEqual(v.loc["Self-votes (dropped)", "value"], 1)
        self.assertEqual(v.loc["Duplicate vote rows (dropped)", "value"], 1)
        self.assertEqual(len(ds.votes), len(votes_rows()))

    def test_league_fans_twins_and_qc(self):
        c = cfg(); ds = load_dataset(self.path, c); r = analyze_league(ds, 1, c)
        fans = r["fans"].set_index("submitter")
        self.assertEqual((fans.loc["A", "biggest_fan"], fans.loc["A", "fan_points"]), ("B", 4))
        self.assertEqual(fans.loc["D", "biggest_fan"], "C")
        self.assertNotIn("E", fans.index)                                   # nobody voted for E
        self.assertTrue((r["qc"]["status"] == "PASS").all())
        tw = r["twins"].set_index("voter")
        self.assertEqual(tw.loc["A", "twin"], "B")
        a, b = np.array([1, 0, 2, 0, 0.]), np.array([0, 1, 1, 0, 0.])      # hand-built jointly eligible vectors
        expected = 0.7 * (2 / math.sqrt(10)) + 0.3 * (1 / 3)
        self.assertAlmostEqual(tw.loc["A", "twin_combined"], expected, places=6)
        self.assertEqual(r["twin_pairs"].query("voter == 'A' and other == 'D'")["status"].iloc[0], "insufficient shared rounds")

    def test_leaderboard_uses_official_points(self):
        c = cfg(); r = analyze_league(load_dataset(self.path, c), 1, c)
        lb = r["leaderboard"].set_index("submitter")
        self.assertEqual(lb.loc["A", "official_points"], 7)
        self.assertEqual(lb.loc["D", "points_lost_to_forfeits"], 3)

    def test_recap_awards_run_and_pick_expected_winners(self):
        c = cfg(); ds = load_dataset(self.path, c); res = build_recap(ds, [1], c)
        aw = {a.key: a for a in res["awards"]}
        self.assertEqual(aw["overall_champion"].winners, ["A"])
        self.assertEqual(aw["podium_throne"].winners, ["A"])
        self.assertEqual(len(aw), 15)

    def test_default_thresholds_do_not_crash_on_tiny_data(self):
        c = Config(min_league_rounds=2, twin_min_shared_rounds=2); ds = load_dataset(self.path, c)
        res = build_recap(ds, [1], c)
        statuses = {a.key: a.status for a in res["awards"]}
        self.assertEqual(statuses["consistency"], "no eligible players")

    def test_cli_writes_manifest_and_files(self):
        out = os.path.join(self.tmp.name, "out")
        code = main(["--workbook", self.path, "--out", out, "--leagues", "1"])
        # default thresholds -> some awards have no eligible players, but the run must still finish cleanly
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(out, "manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(out, "league_1", "songs.csv")))
        self.assertTrue(os.path.exists(os.path.join(out, "recap", "custom", "awards.json")))

    def test_recap_scopes_all_leagues_and_named_periods(self):
        import json
        cfgp = os.path.join(self.tmp.name, "c.json")
        with open(cfgp, "w") as fh:
            json.dump({"min_league_rounds": 2, "recap_periods": {"Year One": [1]}}, fh)
        out = os.path.join(self.tmp.name, "out2")
        self.assertEqual(main(["--workbook", self.path, "--out", out, "--config", cfgp]), 0)
        m = json.load(open(os.path.join(out, "manifest.json")))
        self.assertEqual([x["key"] for x in m["recap_scopes"]], ["all", "league_1", "period_year_one"])
        self.assertEqual(m["schema_version"], 2)
        self.assertTrue(os.path.exists(os.path.join(out, "recap", "period_year_one", "award_overall_champion.csv")))
        bad = os.path.join(self.tmp.name, "bad.json")
        with open(bad, "w") as fh:
            json.dump({"min_league_rounds": 2, "recap_periods": {"Oops": [9]}}, fh)
        self.assertEqual(main(["--workbook", self.path, "--out", os.path.join(self.tmp.name, "o3"), "--config", bad]), 2)


class RealWorkbookTests(unittest.TestCase):
    """Runs only if the real tracker is next to the tests (set ML_WORKBOOK to its path)."""
    path = os.environ.get("ML_WORKBOOK")

    @unittest.skipUnless(path and os.path.exists(path or ""), "set ML_WORKBOOK to run")
    def test_known_numbers(self):
        c = Config(); ds = load_dataset(self.path, c)
        self.assertEqual((len(ds.votes), int(ds.votes["points"].sum())), (5288, 7375))
        self.assertEqual(ds.songs["status"].value_counts().to_dict(), {"OK": 738, "Forfeited": 40, "Unscored": 30, "Zero-vote": 8})
        self.assertTrue((ds.validation["status"] != "FAIL").all())
        r = analyze_league(ds, 4, c)
        kc = r["twins"].set_index("voter").loc["Kelsey"]
        self.assertEqual(kc["twin"], "Colleen")
        self.assertAlmostEqual(kc["twin_combined"], 0.586778, places=5)
        aw = {a.key: a for a in build_recap(ds, [1, 2, 3, 4, 5, 6, 7], c)["awards"]}
        self.assertEqual(aw["overall_champion"].winners, ["Kelsey"])
        top = aw["overall_champion"].table.iloc[0]
        self.assertEqual((top["total_points"], top["submissions"]), (655, 56))
        pt = aw["podium_throne"].table.iloc[0]
        self.assertEqual((pt["gold"], pt["silver"], pt["bronze"]), (12, 5, 5))


if __name__ == "__main__":
    unittest.main()
