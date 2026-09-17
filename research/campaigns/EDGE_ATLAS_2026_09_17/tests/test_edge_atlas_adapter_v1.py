import sys
import tempfile
import unittest
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

CAMPAIGN = Path(__file__).parents[1]
sys.path.insert(0, str(CAMPAIGN))

from data_loader_v1 import AdmissionError
from edge_atlas_cheap_fail_adapter_v1 import ID, TYPE, file_sha256, atomic_status, claim_attempt, recover_stale_running, validate_job, validate_output_dir


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        files = {"manifest": "research/campaigns/EDGE_ATLAS_2026_09_17/ADMITTED_DATA_MANIFEST.json",
                 "runner": "research/campaigns/EDGE_ATLAS_2026_09_17/ea01_cheap_fail_v1.py",
                 "preregistration": "research/campaigns/EDGE_ATLAS_2026_09_17/EA01_CHEAP_FAIL_PREREGISTRATION.md",
                 "launch_authorization": "research/campaigns/EDGE_ATLAS_2026_09_17/EA01_LAUNCH_AUTHORIZATION.json"}
        for rel in files.values():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")
        self.job = {"id": ID, "revision": 1, "type": TYPE, "status": "WAITING_CODEX", "enabled": False,
                    "protected_2026_opened": False, "estimated_duration_seconds": 240,
                    "data_window": {"start": "2017-01-01T00:00:00Z", "end_exclusive": "2023-01-01T00:00:00Z", "partition": "discovery"},
                    "executor": {"kind": "python", "path": "research/campaigns/EDGE_ATLAS_2026_09_17/edge_atlas_cheap_fail_adapter_v1.py"}, **files}
        self.job["runner_sha256"] = file_sha256(self.repo / files["runner"])
        self.job["preregistration_sha256"] = file_sha256(self.repo / files["preregistration"])

    def tearDown(self):
        self.temp.cleanup()

    def admit(self, job=None):
        fake = {"DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025": {"asset": "XAUUSD", "timezone": "UTC", "granularity": "M1"}}
        with patch("edge_atlas_cheap_fail_adapter_v1.canonical_manifest_sha256", return_value="67c602f2a42ef09c60c6ca86eca7b876e5af6bc3a81e053a29a545be0fd2c75c"), patch("edge_atlas_cheap_fail_adapter_v1.validate_manifest", return_value=fake):
            return validate_job(job or self.job, self.repo)

    def test_valid_waiting_job_matches_guardian_python_dispatch(self):
        self.assertEqual(set(self.admit()), {"manifest", "runner", "preregistration", "launch_authorization"})

    def test_generation_115_proposal_is_accepted_by_real_dispatch_validator(self):
        repo = CAMPAIGN.parents[2]
        source = repo / "research/autonomous/guardian_research_orchestrator_v1_00.py"
        spec = importlib.util.spec_from_file_location("guardian_orchestrator_under_test", source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        base = json.loads((repo / "research/autonomous/RESEARCH_QUEUE.json").read_text(encoding="utf-8"))
        proposal = json.loads((repo / "research/autonomous/RESEARCH_QUEUE_APPEND_EDGE_ATLAS_115_PROPOSAL.json").read_text(encoding="utf-8"))
        self.assertEqual(proposal["supersedes_generation"], base["generation"])
        merged = dict(base, generation=proposal["generation"], jobs=proposal["jobs"], human_approved_2026=False)
        module.validate_queue(merged)
        self.assertTrue(any(job.get("enabled") and job.get("status") == "READY" for job in merged["jobs"]))

    def test_rejects_ready_or_enabled(self):
        with self.assertRaises(AdmissionError): self.admit(dict(self.job, status="READY", enabled=True))

    def test_execute_rejects_disabled_job_even_when_called_manually(self):
        with self.assertRaises(AdmissionError):
            fake = {"DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025": {"asset": "XAUUSD", "timezone": "UTC", "granularity": "M1"}}
            with patch("edge_atlas_cheap_fail_adapter_v1.canonical_manifest_sha256", return_value="67c602f2a42ef09c60c6ca86eca7b876e5af6bc3a81e053a29a545be0fd2c75c"), patch("edge_atlas_cheap_fail_adapter_v1.validate_manifest", return_value=fake):
                validate_job(self.job, self.repo, execution_requested=True)

    def test_rejects_over_five_minutes(self):
        with self.assertRaises(AdmissionError): self.admit(dict(self.job, estimated_duration_seconds=301))

    def test_rejects_period_outside_discovery(self):
        bad = dict(self.job, data_window={"start":"2017-01-01T00:00:00Z","end_exclusive":"2024-01-01T00:00:00Z","partition":"confirmation"})
        with self.assertRaises(AdmissionError): self.admit(bad)

    def test_rejects_production_path(self):
        production = self.repo / "production" / "m.json"
        production.parent.mkdir()
        production.write_text("{}")
        with self.assertRaises(AdmissionError): self.admit(dict(self.job, manifest="production/m.json"))

    def test_rejects_manifest_hash(self):
        with patch("edge_atlas_cheap_fail_adapter_v1.canonical_manifest_sha256", return_value="0" * 64):
            with self.assertRaises(AdmissionError): validate_job(self.job, self.repo)

    def test_rejects_runner_hash(self):
        with self.assertRaises(AdmissionError): self.admit(dict(self.job, runner_sha256="0" * 64))

    def test_output_is_confined_to_guardian_root(self):
        root = self.repo / "runtime"
        expected = root / "edge_atlas" / ID
        with patch.dict("os.environ", {"GUARDIAN_AUTONOMOUS_ROOT": str(root)}):
            self.assertEqual(validate_output_dir(expected), expected.resolve())
            with self.assertRaises(AdmissionError): validate_output_dir(self.repo / "elsewhere")

    def test_rejects_non_xau_or_ambiguous_timezone(self):
        fake = {"DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025": {"asset": "EURUSD", "timezone": "LOCAL", "granularity": "M1"}}
        with patch("edge_atlas_cheap_fail_adapter_v1.canonical_manifest_sha256", return_value="67c602f2a42ef09c60c6ca86eca7b876e5af6bc3a81e053a29a545be0fd2c75c"), patch("edge_atlas_cheap_fail_adapter_v1.validate_manifest", return_value=fake):
            with self.assertRaises(AdmissionError): validate_job(self.job, self.repo)

    def _receipt(self, root, finished="2026-09-17T12:30:00+00:00", status="FAIL"):
        path = root / "receipts" / f"{ID}__r1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"job_id": ID, "revision": 1, "status": status, "finished_at_utc": finished}), encoding="utf-8")

    def test_running_active_pid_is_refused(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"RUNNING","job_id":ID,"pid":__import__("os").getpid(),"recorded_at":"2026-09-17T12:00:00+00:00"}), encoding="utf-8")
        with self.assertRaises(AdmissionError): recover_stale_running(marker, out, self.repo / "runtime", ID, 1, processes_absent=True)
        self.assertTrue(marker.exists())

    def test_running_stale_without_process_is_quarantined(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"RUNNING","job_id":ID,"recorded_at":"2026-09-17T12:00:00+00:00"}), encoding="utf-8")
        self._receipt(self.repo / "runtime")
        event = recover_stale_running(marker, out, self.repo / "runtime", ID, 1, processes_absent=True)
        self.assertEqual(event["status"], "RECOVERY_QUARANTINED")
        self.assertFalse(marker.exists())
        archived = Path(event["quarantine"])
        self.assertTrue(archived.exists())
        self.assertEqual(event["sha256"], __import__("hashlib").sha256(archived.read_bytes()).hexdigest())

    def test_incoherent_running_marker_is_blocked(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"COMPLETE","job_id":ID}), encoding="utf-8")
        with self.assertRaises(AdmissionError): recover_stale_running(marker, out, self.repo / "runtime", ID, 1)
        self.assertTrue(marker.exists())

    def test_existing_quarantine_destination_is_not_overwritten(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"RUNNING","job_id":ID,"recorded_at":"2026-09-17T12:00:00+00:00"}), encoding="utf-8")
        self._receipt(self.repo / "runtime")
        destination = out / "quarantine" / f"status_RUNNING_{file_sha256(marker)}.json"
        destination.parent.mkdir(parents=True)
        destination.write_text("sentinel", encoding="utf-8")
        with self.assertRaises(AdmissionError): recover_stale_running(marker, out, self.repo / "runtime", ID, 1, processes_absent=True)
        self.assertEqual(destination.read_text(encoding="utf-8"), "sentinel")
        self.assertTrue(marker.exists())

    def test_missing_pid_is_not_absence_evidence(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"RUNNING","job_id":ID,"recorded_at":"2026-09-17T12:00:00+00:00"}))
        self._receipt(self.repo / "runtime")
        for evidence in (None, False):
            with self.assertRaises(AdmissionError):
                recover_stale_running(marker, out, self.repo / "runtime", ID, 1, processes_absent=evidence)
        self.assertTrue(marker.exists())

    def test_old_receipt_cannot_recover_new_marker(self):
        out = self.repo / "runtime" / "edge_atlas" / ID
        out.mkdir(parents=True)
        marker = out / "status_RUNNING.json"
        marker.write_text(json.dumps({"status":"RUNNING","job_id":ID,"recorded_at":"2026-09-17T13:00:00+00:00"}))
        self._receipt(self.repo / "runtime")
        with self.assertRaises(AdmissionError):
            recover_stale_running(marker, out, self.repo / "runtime", ID, 1, processes_absent=True)
        self.assertTrue(marker.exists())

    def test_exclusive_status_preserves_existing_bytes(self):
        p = self.repo / "status.json"
        p.write_bytes(b"sentinel")
        with self.assertRaises(AdmissionError): atomic_status(p, {"new": True})
        self.assertEqual(p.read_bytes(), b"sentinel")

    def test_attempt_cannot_be_consumed_twice(self):
        claim_attempt(self.repo)
        original = (self.repo / "status_ATTEMPT_CONSUMED.json").read_bytes()
        with self.assertRaises(AdmissionError): claim_attempt(self.repo)
        self.assertEqual((self.repo / "status_ATTEMPT_CONSUMED.json").read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
