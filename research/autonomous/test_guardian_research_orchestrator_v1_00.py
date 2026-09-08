import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("orch", HERE / "guardian_research_orchestrator_v1_00.py")
orch = importlib.util.module_from_spec(SPEC)
sys.modules["orch"] = orch
SPEC.loader.exec_module(orch)


class TestOrchestrator(unittest.TestCase):
    def test_rejects_2026_without_human_approval(self):
        q = {"schema": 1, "human_approved_2026": False, "jobs": [{
            "id": "X", "revision": 1, "enabled": True,
            "executor": {"kind": "noop"},
            "data_window": {"end_exclusive": "2026-02-01T00:00:00Z"}
        }]}
        with self.assertRaises(ValueError):
            orch.validate_queue(q)

    def test_allows_pre_2026(self):
        q = {"schema": 1, "human_approved_2026": False, "jobs": [{
            "id": "X", "revision": 1, "enabled": True,
            "executor": {"kind": "noop"},
            "data_window": {"end_exclusive": "2026-01-01T00:00:00Z"}
        }]}
        orch.validate_queue(q)

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            orch.normalize_rel_path("../evil.py")

    def test_p95(self):
        self.assertAlmostEqual(orch.percentile95([10, 20, 30, 40]), 38.5)

    def test_adaptive_timeout_uses_eta(self):
        p = {"min_seconds": 100, "eta_multiplier": 2.5, "history_p95_multiplier": 3}
        self.assertAlmostEqual(orch.adaptive_hard_limit(p, [], 50, 0.25), 500)

    def test_adaptive_timeout_uses_history(self):
        p = {"min_seconds": 100, "eta_multiplier": 2.5, "history_p95_multiplier": 3}
        self.assertGreaterEqual(orch.adaptive_hard_limit(p, [100, 120, 140], 0, None), 3 * orch.percentile95([100, 120, 140]))

    def test_receipt_dependency(self):
        with tempfile.TemporaryDirectory() as td:
            r = Path(td)
            (r / "A__r1.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
            ok, why = orch.dependency_satisfied({"kind": "receipt", "job_id": "A", "revision": 1}, Path(td), r)
            self.assertTrue(ok, why)

    def test_noop_job(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            deploy = Path(td) / "deploy"
            deploy.mkdir()
            res = orch.execute_job({"id": "N", "revision": 1, "executor": {"kind": "noop"}}, deploy, root, root / "history.jsonl")
            self.assertEqual(res.status, "PASS")

    def test_codex_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            deploy = Path(td) / "deploy"
            deploy.mkdir()
            res = orch.execute_job({"id": "C", "revision": 1, "executor": {"kind": "codex_assist"}}, deploy, root, root / "history.jsonl")
            self.assertEqual(res.status, "BLOCKED")


if __name__ == "__main__":
    unittest.main()
