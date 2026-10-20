import math
import unittest
import numpy as np
import pandas as pd
from ml_analysis.util import nk, competition_places, cosine, jaccard, pielou, rank_and_winners, title_words


class UtilTests(unittest.TestCase):
    def test_nk(self):
        self.assertEqual(nk("Beyoncé"), "beyonce")
        self.assertEqual(nk("Mr. Brightside!"), "mrbrightside")

    def test_places_ties_and_skips(self):
        # two songs tie for first on points AND voters -> both 1st, next is 3rd
        self.assertEqual(list(competition_places([5, 5, 3, 1], [2, 2, 2, 1])), [1, 1, 3, 4])
        # same points, more voters wins
        self.assertEqual(list(competition_places([5, 5], [3, 2])), [1, 2])

    def test_cosine_jaccard(self):
        a, b = np.array([1, 0, 2, 0, 0.]), np.array([0, 1, 1, 0, 0.])
        self.assertAlmostEqual(cosine(a, b), 2 / math.sqrt(10))
        self.assertAlmostEqual(jaccard(a, b), 1 / 3)
        self.assertTrue(math.isnan(cosine(np.zeros(3), a[:3])))
        self.assertTrue(math.isnan(jaccard(np.zeros(3), np.zeros(3))))

    def test_pielou(self):
        self.assertAlmostEqual(pielou([5, 5]), 1.0)
        self.assertEqual(pielou([7]), 0.0)
        self.assertTrue(math.isnan(pielou([])))

    def test_ties_are_never_broken_silently(self):
        df = pd.DataFrame({"p": ["x", "y", "z"], "a": [3, 3, 1], "b": [2, 2, 5]})
        ranked, w, status = rank_and_winners(df, [("a", False), ("b", False)])
        self.assertEqual(status, "co-winners")
        self.assertEqual(sorted(w["p"]), ["x", "y"])
        df.loc[1, "b"] = 1
        _, w, status = rank_and_winners(df, [("a", False), ("b", False)])
        self.assertEqual((status, list(w["p"])), ("winner", ["x"]))

    def test_title_words(self):
        self.assertEqual(title_words("Uptown Funk (feat. Bruno Mars)"), ["uptown", "funk"])
        self.assertEqual(title_words("Bohemian Rhapsody - Remastered 2011"), ["bohemian", "rhapsody"])
        self.assertEqual(title_words("Don't Stop Me Now"), ["dont", "stop", "me", "now"])


if __name__ == "__main__":
    unittest.main()
