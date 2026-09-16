#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import test_xau_edge_discovery_r21_r25_v1_02 as regression_v102
import xau_edge_discovery_r21_r25_v1_03 as m


def B(dt, o=100.0, h=101.0, l=99.0, c=100.0):
    return m.Bar(int(dt.timestamp()), dt, "M5", o, h, l, c)


def test_v102_regression_suite_still_passes():
    regression_v102.main()


def test_progress_json_is_atomic_and_guarded():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "progress.json"
        m._write_progress(p, phase="build_m5", fraction=0.25, completed=10, total=40)
        obj = m.json.loads(p.read_text(encoding="utf-8"))
        assert obj["status"] == "RUNNING"
        assert obj["phase"] == "build_m5"
        assert obj["fraction"] == 0.25
        assert obj["completed"] == 10
        assert obj["protected_2026_opened"] is False
        assert not p.with_suffix(".json.tmp").exists()


def test_cleanup_removes_only_transient_r21_r25_state():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        legacy = root / "v102"
        current = root / "v103"
        audit = root / "receipts"
        legacy.mkdir(); current.mkdir(); audit.mkdir()
        for d in (legacy, current):
            (d / "discovery.json").write_text("stale", encoding="utf-8")
            (d / "progress.json").write_text("stale", encoding="utf-8")
        audit_file = audit / "R21-R25-XAU-DISCOVERY__r5.json"
        audit_file.write_text("KEEP", encoding="utf-8")
        stale_tmp = root / "guardian_r21r25_v102_dead"
        stale_tmp.mkdir()
        (stale_tmp / "partial.csv").write_text("x", encoding="utf-8")

        with patch.object(m, "LEGACY_OUTPUT_DIR", legacy), \
             patch.object(m, "CANONICAL_OUTPUT_DIR", current), \
             patch.object(m.tempfile, "gettempdir", return_value=str(root)):
            removed = m._cleanup_stale_transients()

        assert not (legacy / "discovery.json").exists()
        assert not (legacy / "progress.json").exists()
        assert not (current / "discovery.json").exists()
        assert not (current / "progress.json").exists()
        assert not stale_tmp.exists()
        assert audit_file.read_text(encoding="utf-8") == "KEEP"
        assert removed


def test_output_and_progress_are_confined():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "r21_r25_xau_v103"
        root.parent.mkdir(parents=True, exist_ok=True)
        output = root / "discovery.json"
        progress = root / "progress.json"
        with patch.object(m, "CANONICAL_OUTPUT_DIR", root), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress):
            assert m._validate_output_path(output) == output.absolute()
            assert m._validate_progress_path(progress) == progress.absolute()
            for bad in (root / "other.json", root.parent / "payload.bi5"):
                try:
                    m._validate_output_path(bad)
                except RuntimeError:
                    pass
                else:
                    raise AssertionError(f"unsafe output accepted: {bad}")


def test_run_from_index_emits_live_build_heartbeat_and_analysis_progress():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        index = root / "master_index.csv"
        index.write_bytes(b"metadata only")
        outdir = root / "r21_r25_xau_v103"
        output = outdir / "discovery.json"
        progress = outdir / "progress.json"
        legacy = root / "r21_r25_xau_v102"
        seen = []

        def fake_build(index_path: Path, generated_csv: Path, progress_callback=None):
            assert index_path.read_bytes() == b"metadata only"
            start = datetime(2019, 1, 15, 13, 20, tzinfo=timezone.utc)
            with generated_csv.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=["symbol","timeframe","server_time","server_epoch","open","high","low","close"],
                )
                w.writeheader()
                for i, price in enumerate([100, 101, 102, 103]):
                    dt = start + timedelta(minutes=5*i)
                    w.writerow({
                        "symbol":"XAUUSD","timeframe":"M5","server_time":dt.isoformat(),
                        "server_epoch":int(dt.timestamp()),"open":price,"high":price+.1,
                        "low":price-.1,"close":price,
                    })
            for n in (1, 5, 10):
                if progress_callback:
                    progress_callback({
                        "completed":n,"total":10,"last_opened_payload_date":"2019-01-15",
                        "decoded_m1":n*100,"emitted_m5":n*20,
                    })
            return {
                "status":"PASS","stage":"discovery",
                "stage_start":m.DISCOVERY_START.isoformat(),
                "stage_end_inclusive":m.DISCOVERY_END.isoformat(),
                "confirmation_opened":False,"pre_oos_2025_opened":False,
                "protected_2026_opened":False,
                "output":str(generated_csv.resolve()),
                "last_opened_payload_date":"2019-01-15",
            }

        original_write = m._write_progress

        def observe(path, **kwargs):
            seen.append((kwargs["phase"], kwargs["fraction"]))
            return original_write(path, **kwargs)

        digest = hashlib.sha256(b"metadata only").hexdigest()
        with patch.object(m, "CANONICAL_R15_INDEX", index), \
             patch.object(m, "CANONICAL_R15_INDEX_SHA256", digest), \
             patch.object(m, "_validate_pin_attestation", return_value={}), \
             patch.object(m, "CANONICAL_OUTPUT_DIR", outdir), \
             patch.object(m, "CANONICAL_OUTPUT", output), \
             patch.object(m, "CANONICAL_PROGRESS", progress), \
             patch.object(m, "LEGACY_OUTPUT_DIR", legacy), \
             patch.object(m.sealed_builder, "build", side_effect=fake_build), \
             patch.object(m, "_write_progress", side_effect=observe):
            payload = m.run_from_index(index, ["R21"], progress)

        phases = [x[0] for x in seen]
        assert phases[0] == "starting"
        assert phases.count("build_m5") == 3
        assert "load_m5" in phases
        assert "analyze_R21" in phases
        assert "analyze_R21_done" in phases
        assert phases[-1] == "serialize"
        fractions = [x[1] for x in seen]
        assert fractions == sorted(fractions)
        assert payload["version"] == "1.03"
        assert payload["protected_2026_opened"] is False
        obj = m.json.loads(progress.read_text(encoding="utf-8"))
        assert obj["phase"] == "serialize"
        assert obj["fraction"] == 0.99


def test_off_grid_still_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.csv"
        dt = datetime(2019, 1, 15, 13, 20, 30, tzinfo=timezone.utc)
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["timeframe","server_epoch","open","high","low","close"])
            w.writeheader()
            w.writerow({"timeframe":"M5","server_epoch":int(dt.timestamp()),"open":100,"high":101,"low":99,"close":100})
        try:
            m.load_generated_discovery_bars(p)
        except RuntimeError as e:
            assert "off-grid M5 timestamp" in str(e)
        else:
            raise AssertionError("off-grid bar accepted")


def main():
    test_v102_regression_suite_still_passes()
    test_progress_json_is_atomic_and_guarded()
    test_cleanup_removes_only_transient_r21_r25_state()
    test_output_and_progress_are_confined()
    test_run_from_index_emits_live_build_heartbeat_and_analysis_progress()
    test_off_grid_still_rejected()
    print("PASS: R21-R25 v1.03 heartbeat/cleanup regression tests")


if __name__ == "__main__":
    main()
