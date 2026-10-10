import unittest

import numpy as np

from ladder import simulate, summarise


class LadderTests(unittest.TestCase):
    def run_sim(self, R, risk_pct=30.0, tickets=500, seed=1):
        rng = np.random.default_rng(seed)
        sim = simulate(R=np.array(R), gaps=np.array([0.5, 1.0]), start=200.0, target=3000.0,
                       floor=80.0, risk_pct=risk_pct, time_box_days=30, tickets=tickets, rng=rng)
        return sim, summarise(sim, 200.0)

    def test_all_wins_reach_target(self):
        sim, s = self.run_sim([1.0, 2.0])
        self.assertEqual(s["p_target"], 1.0)
        self.assertEqual(s["p_ruin"], 0.0)
        self.assertTrue((sim["final"] >= 3000.0).all())

    def test_all_losses_hit_floor(self):
        sim, s = self.run_sim([-1.0])
        self.assertEqual(s["p_ruin"], 1.0)
        self.assertEqual(s["p_target"], 0.0)
        self.assertTrue((sim["final"] <= 80.0).all())
        # 200 * 0.7^3 = 68.6 < 80, so death on the 3rd trade
        self.assertTrue((sim["n_trades"] == 3).all())
        self.assertIsNotNone(s["median_days_to_death"])

    def test_equity_never_negative(self):
        sim, _ = self.run_sim([-1.6], risk_pct=100.0)
        self.assertTrue((sim["final"] >= 0.0).all())

    def test_seed_reproducible(self):
        _, a = self.run_sim([-1.0, 0.5, 3.0], seed=7)
        _, b = self.run_sim([-1.0, 0.5, 3.0], seed=7)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
