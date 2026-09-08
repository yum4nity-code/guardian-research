import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("phase_ic", HERE / "phase_ic_xau_phenomenon_atlas_v1_00.py")
mod = importlib.util.module_from_spec(SPEC)
sys.modules["phase_ic"] = mod
SPEC.loader.exec_module(mod)


class TestPhaseIC(unittest.TestCase):
    def test_bh_adjust(self):
        rows = [{"p": 0.001}, {"p": 0.02}, {"p": 0.5}]
        mod.bh_adjust(rows)
        self.assertLessEqual(rows[0]["q"], rows[1]["q"])
        self.assertLessEqual(rows[1]["q"], rows[2]["q"])
        self.assertAlmostEqual(rows[0]["q"], 0.003, places=6)

    def test_continuous_state_effect(self):
        values = np.array([2.0, 2.0, 0.0, 0.0])
        mask = np.array([True, True, False, False])
        r = mod.continuous_test(values, mask)
        self.assertAlmostEqual(r["effect"], 2.0)
        self.assertEqual(r["n_state"], 2)

    def test_binary_state_effect(self):
        values = np.array([1.0, 1.0, 0.0, 0.0])
        mask = np.array([True, True, False, False])
        r = mod.binary_test(values, mask)
        self.assertAlmostEqual(r["effect"], 1.0)

    def test_future_labels_do_not_cross_gap_segment(self):
        # Index 1 would see a +1 ATR move at index 2 if labels were allowed to jump
        # across the explicit segment boundary. It must remain NaN instead.
        df = pd.DataFrame({
            "segment": [1, 1, 2, 2],
            "close": [100.0, 100.0, 103.0, 103.0],
            "high": [100.2, 100.2, 103.5, 103.5],
            "low": [99.8, 99.8, 102.5, 102.5],
            "atr14": [1.0, 1.0, 1.0, 1.0],
        })
        out = mod.add_labels(df.copy(), [1])
        self.assertTrue(np.isnan(out.loc[1, "fwd_ret_atr_h1"]))
        self.assertTrue(np.isnan(out.loc[1, "move_ge_1atr_h1"]))
        self.assertAlmostEqual(out.loc[0, "fwd_ret_atr_h1"], 0.0)


if __name__ == "__main__":
    unittest.main()
