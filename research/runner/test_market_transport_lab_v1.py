#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

import market_transport_lab_v1 as mtl


class MarketTransportLabV1Tests(unittest.TestCase):
    def test_materialized_sources_preserve_parent_and_patch_only_transport_contract(self):
        for parent_key, spec in mtl.PARENTS.items():
            parent = mtl.ROOT / spec["source"]
            before = parent.read_bytes()
            generated, generated_sha, provenance = mtl.materialize_transport_source(parent_key)
            self.assertEqual(before, parent.read_bytes())
            self.assertTrue(generated.is_file())
            self.assertEqual(generated_sha, provenance["generated_source_sha256"])
            text = generated.read_text(encoding="utf-8")
            self.assertIn(spec["transport_id"], text)
            self.assertIn(spec["generated_name"], text)
            self.assertIn('string SOURCE_VERSION="1.00-MTL1";', text)
            for symbol in mtl.NEW_SYMBOLS:
                self.assertIn(f'StringFind(_Symbol,"{symbol}")>=0', text)
            self.assertIn('if(c=="INDEX") return 0.0;', text)
            self.assertNotIn('StringFind(_Symbol,"BTCUSD")>=0 || StringFind(_Symbol,"ETHUSD")>=0', text)

    def test_synthetic_manifests_validate_for_smoke_and_development(self):
        for parent_key in mtl.PARENTS:
            generated, generated_sha, _ = mtl.materialize_transport_source(parent_key)
            for stage in ("smoke", "development"):
                path, manifest = mtl._manifest(parent_key, stage, generated, generated_sha)
                self.assertTrue(path.is_file())
                self.assertEqual([], mtl.experiment.validate_manifest(manifest))
                self.assertEqual(stage, manifest["runner_contract"]["default_stage"])

    def _batch(self, root: Path, parent_key: str, rows_per_symbol: int, value: float):
        tests = []
        for symbol in mtl.NEW_SYMBOLS:
            path = root / f"{parent_key}_{symbol}.csv"
            with path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=["net_r", "net_r_commission_x1_5", "entry_time"], delimiter=";")
                writer.writeheader()
                for index in range(rows_per_symbol):
                    year = 2024 if index % 2 == 0 else 2025
                    writer.writerow({
                        "net_r": f"{value:.8f}",
                        "net_r_commission_x1_5": f"{value * 0.9:.8f}",
                        "entry_time": f"{year}.06.01 12:00",
                    })
            tests.append({
                "symbol": symbol,
                "trades": {"path": str(path)},
                "integrity": {"invalid_price": 0, "invalid_risk": 0, "pnl_calc_failures": 0},
            })
        return {"tests": tests}

    def test_primary_broad_pass_requires_all_frozen_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = self._batch(root, "D038", rows_per_symbol=42, value=0.20)
            score = mtl._score("D038", good)
            self.assertTrue(score["all_gates_pass"])
            self.assertEqual("TRANSPORT_CANDIDATE_CONFIRM", score["verdict"])
            self.assertEqual(12, score["metrics"]["positive_symbols_n"])

            bad = self._batch(root, "D038_BAD", rows_per_symbol=42, value=-0.20)
            score_bad = mtl._score("D038", bad)
            self.assertFalse(score_bad["all_gates_pass"])
            self.assertEqual("TRANSPORT_NO_BROAD_PASS", score_bad["verdict"])

    def test_d045_lower_count_gate_is_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = self._batch(root, "D045", rows_per_symbol=10, value=0.15)
            score = mtl._score("D045", batch)
            self.assertEqual(120, score["metrics"]["aggregate_n"])
            self.assertTrue(score["gates"]["aggregate_n_min"])
            self.assertTrue(score["gates"]["qualified_symbols_min"])
            self.assertEqual("TRANSPORT_CANDIDATE_CONFIRM", score["verdict"])

    def test_d040_can_only_emit_comparator_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            batch = self._batch(root, "D040", rows_per_symbol=42, value=0.20)
            score = mtl._score("D040", batch)
            self.assertEqual("COMPARATOR_BROAD_PASS", score["verdict"])
            self.assertTrue(score["parent_verdict_unchanged"])


if __name__ == "__main__":
    unittest.main()
