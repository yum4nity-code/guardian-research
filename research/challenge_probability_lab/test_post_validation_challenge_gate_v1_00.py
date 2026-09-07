#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "post_validation_challenge_gate_v1_00.py"
PROFILE = HERE / "guardian_reference_profile_v1_00.json"


def write_csv(path: Path, *, canonical: bool = True) -> None:
    fields = ["run_stage", "symbol", "entry_time", "exit_time", "net_r"]
    if canonical:
        fields += ["challenge_day", "adverse_r"]
    rows = []
    for i in range(30):
        day = f"202601{(i % 10) + 1:02d}"
        r = 1.2 if i % 3 else -1.0
        row = {
            "run_stage": "CONFIRM",
            "symbol": "EURUSD",
            "entry_time": f"2026.01.{(i % 10) + 1:02d} 10:{i % 60:02d}",
            "exit_time": f"2026.01.{(i % 10) + 1:02d} 11:{i % 60:02d}",
            "net_r": str(r),
        }
        if canonical:
            row["challenge_day"] = day
            row["adverse_r"] = "-0.5"
        rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class GateTests(unittest.TestCase):
    def run_gate(self, td: Path, eligible: bool, *, canonical: bool = True, legacy: bool = False):
        trades = td / "trades.csv"
        decision = td / "decision.json"
        out = td / "out"
        write_csv(trades, canonical=canonical)
        decision.write_text(json.dumps({"challenge_lab_eligible": eligible}), encoding="utf-8")
        cmd = [
            sys.executable, str(SCRIPT),
            "--input", str(trades),
            "--eligibility-json", str(decision),
            "--profile", str(PROFILE),
            "--output-dir", str(out),
            "--stage", "CONFIRM",
            "--paths", "100",
            "--seed", "123",
            "--profit-target-pct", "1",
        ]
        if legacy:
            cmd.append("--allow-legacy-atomic-export")
        return subprocess.run(cmd, text=True, capture_output=True), out

    def test_not_eligible_skips(self):
        with tempfile.TemporaryDirectory() as d:
            r, out = self.run_gate(Path(d), False)
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((out / "challenge_gate_manifest.json").read_text())
            self.assertEqual(m["status"], "SKIPPED_NOT_ALPHA_VALIDATED")
            self.assertFalse(m["lab_ran"])
            self.assertFalse((out / "challenge_probability.json").exists())

    def test_eligible_canonical_runs(self):
        with tempfile.TemporaryDirectory() as d:
            r, out = self.run_gate(Path(d), True)
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((out / "challenge_gate_manifest.json").read_text())
            self.assertEqual(m["status"], "CHALLENGE_LAB_COMPLETE")
            self.assertEqual(m["dd_fidelity"], "ATOMIC_PLUS_INDIVIDUAL_ADVERSE_R")
            self.assertTrue((out / "challenge_probability.json").exists())
            self.assertTrue((out / "challenge_probability.csv").exists())
            self.assertTrue((out / "challenge_probability.md").exists())

    def test_missing_challenge_day_rejected_by_default(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = self.run_gate(Path(d), True, canonical=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("missing canonical 'challenge_day'", r.stderr)

    def test_legacy_atomic_escape_hatch_is_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            r, out = self.run_gate(Path(d), True, canonical=False, legacy=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            m = json.loads((out / "challenge_gate_manifest.json").read_text())
            self.assertEqual(m["dd_fidelity"], "ATOMIC_CLOSED_EQUITY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
