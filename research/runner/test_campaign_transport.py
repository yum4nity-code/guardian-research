#!/usr/bin/env python3
"""Regression tests for unattended campaign and compact result transport."""

from __future__ import annotations

import unittest

import campaign
import result_transport


class CampaignTransportTests(unittest.TestCase):
    def test_campaign_detects_native_trade_path_from_manifest_contract(self) -> None:
        native = {
            "stages": {
                "smoke": {
                    "gates": {
                        "opened_equals_closed_equals_trade_rows_equals_path_rows": True,
                        "trade_path_fields_present_and_parseable": True,
                    }
                }
            }
        }
        legacy = {"stages": {"smoke": {"gates": {"lifecycle_clean": True}}}}
        self.assertTrue(campaign._path_supported_from_manifest(native))
        self.assertFalse(campaign._path_supported_from_manifest(legacy))

    def test_rich_score_event_payload_is_compacted_but_keeps_core_summary(self) -> None:
        payload = {
            "schema_version": 1,
            "experiment_id": "D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0",
            "stage": "development",
            "role": "DESCRIPTIVE_ANALYTICS_ONLY_DOES_NOT_CHANGE_DECISION_VERDICT",
            "rich_score_path": "D:/rich/rich_score.json",
            "batch_path": "D:/batch/batch.json",
            "analytics": {
                "scope": {"trades": 459},
                "net_r": {
                    "distribution": {"n": 459, "mean": 0.179, "median": -0.039},
                    "profit_factor": {"value": 1.55, "infinite": False},
                    "total_r": 82.38,
                    "win_rate": 0.492,
                },
                "commission_stress_1_5x_r": {
                    "distribution": {"mean": 0.168},
                    "profit_factor": {"value": 1.51, "infinite": False},
                    "total_r": 77.18,
                },
                "trade_path": {
                    "available": True,
                    "trades": 459,
                    "path_ambiguous_rows": 0,
                    "milestone_touch": {"1R": {"n": 150, "rate": 150 / 459}},
                    "very_large_descriptive_tree": {str(i): i for i in range(1000)},
                },
            },
            "compact_trades": {"rows": 459, "path": "D:/rich/trades_compact.csv"},
            "autosync_used": False,
        }
        compact, changed = result_transport._event_payload("rich-score", payload)
        self.assertTrue(changed)
        self.assertNotIn("analytics", compact)
        self.assertEqual(82.38, compact["net_r_summary"]["total_r"])
        self.assertTrue(compact["trade_path_summary"]["available"])
        self.assertEqual(150, compact["trade_path_summary"]["milestone_touch"]["1R"]["n"])

    def test_non_rich_event_payload_is_not_changed(self) -> None:
        payload = {"status": "BATCH_PASS_INTEGRITY", "batch_path": "D:/x/batch.json"}
        out, changed = result_transport._event_payload("batch", payload)
        self.assertFalse(changed)
        self.assertIs(out, payload)


if __name__ == "__main__":
    unittest.main()
