#!/usr/bin/env python3
import math
import unittest

import numpy as np
import pandas as pd

import r4_causal_capture_forensic_audit_v1_00 as audit


def frame(epochs, opens, highs, lows, closes):
    return pd.DataFrame({
        "time": pd.to_datetime(np.asarray(epochs, dtype=np.int64), unit="s", utc=True),
        "open": np.asarray(opens, dtype=float),
        "high": np.asarray(highs, dtype=float),
        "low": np.asarray(lows, dtype=float),
        "close": np.asarray(closes, dtype=float),
        "volume": np.ones(len(epochs), dtype=float),
    })


class ForensicAuditPreflight(unittest.TestCase):
    def test_decomposition_identity(self):
        audit.self_test()
        for d in (-1, 1):
            cs, ce, oe, ox = 100.0, 103.0, 100.5, 102.25
            b = d * (ce - cs)
            entry = d * (cs - oe)
            exit_ = d * (ox - ce)
            c = d * (ox - oe)
            self.assertTrue(math.isclose(c, b + entry + exit_, abs_tol=1e-12))

    def test_first_available_reference_after_gap(self):
        raw = np.array([60, 120, 240, 300], dtype=np.int64)
        idx, ok = audit.ref_indices(raw, np.array([60, 121, 240, 301], dtype=np.int64))
        self.assertEqual(idx.tolist(), [0, 2, 2, 4])
        self.assertEqual(ok.tolist(), [True, True, True, False])

    def test_timestamp_membership(self):
        base = np.array([60, 120, 240], dtype=np.int64)
        vals = np.array([60, 180, 240], dtype=np.int64)
        self.assertEqual(audit.member(base, vals).tolist(), [True, False, True])

    def test_exact_m5_mapping_and_one_incomplete_bucket(self):
        # Two M5 buckets. Second bucket is missing minute +180 and must be
        # reported incomplete, never counted as an OHLC mismatch.
        ep = [0,60,120,180,240, 300,360,420,540]
        o  = [10,11,12,13,14, 20,21,22,24]
        h  = [11,12,13,14,15, 21,22,23,25]
        l  = [ 9,10,11,12,13, 19,20,21,23]
        c  = [10.5,11.5,12.5,13.5,14.5, 20.5,21.5,22.5,24.5]
        m1 = frame(ep,o,h,l,c)
        m5 = frame(
            [0,300],
            [10,20],
            [15,25],
            [9,19],
            [14.5,24.5],
        )
        r = audit.audit_m5(m5, m1, "synthetic")
        self.assertEqual(r["complete_buckets"], 1)
        self.assertEqual(r["incomplete_buckets"], 1)
        self.assertEqual(r["mismatch_buckets"], 0)
        self.assertEqual(r["status"], "PASS")

    def test_m5_mapping_detects_real_ohlc_mismatch(self):
        ep = [0,60,120,180,240]
        m1 = frame(ep,[10,11,12,13,14],[11,12,13,14,15],[9,10,11,12,13],[10.5,11.5,12.5,13.5,14.5])
        m5 = frame([0],[10],[15.25],[9],[14.5])
        r = audit.audit_m5(m5, m1, "synthetic_bad")
        self.assertEqual(r["complete_buckets"], 1)
        self.assertEqual(r["mismatch_buckets"], 1)
        self.assertEqual(r["field_mismatch_counts"]["high"], 1)
        self.assertEqual(r["status"], "DATA_MAPPING_BLOCKED")

    def test_clean_subset(self):
        raw = frame([0,60,120],[10,11,12],[11,12,13],[9,10,11],[10.5,11.5,12.5])
        clean = raw.iloc[[0,2]].reset_index(drop=True)
        self.assertEqual(audit.clean_subset(raw, clean)["status"], "PASS")
        bad = clean.copy()
        bad.loc[1,"close"] += 0.01
        self.assertEqual(audit.clean_subset(raw, bad)["status"], "DATA_MAPPING_BLOCKED")

    def test_feature_family_is_descriptive_only(self):
        expected = {"ret3":"ret","sma20":"sma","rsi14":"rsi","body":"body"}
        self.assertEqual({k:audit.family(k) for k in expected}, expected)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ForensicAuditPreflight)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
