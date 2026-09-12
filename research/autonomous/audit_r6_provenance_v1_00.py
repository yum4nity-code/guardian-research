#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import r6_xau_low_turnover_breakout_v1_00 as r6


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def publish(publisher: str | None, output: Path, status: str, summary: str) -> None:
    if not publisher:
        return
    subprocess.run(
        [
            "python",
            publisher,
            "--phase",
            "r6-provenance-integrity-audit",
            "--status",
            status,
            "--summary",
            summary,
            "--artifact",
            str(output),
        ],
        check=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--r6-result", required=True)
    ap.add_argument("--r6-receipt", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--publisher")
    args = ap.parse_args()

    root = Path(args.phase_ib_root)
    result_path = Path(args.r6_result)
    receipt_path = Path(args.r6_receipt)
    output = Path(args.output)

    result = load_json(result_path)
    receipt = load_json(receipt_path)

    if receipt.get("status") != "PASS":
        fail(f"R6 receipt not PASS: {receipt.get('status')}")
    if result.get("protected_2026_opened") is not False:
        fail("R6 result does not certify protected_2026_opened=false")
    if int(result.get("discovery_pass_count", -1)) != 15:
        fail("unexpected R6 discovery pass count")
    if int(result.get("survivor_count", -1)) != 12:
        fail("unexpected R6 survivor count")

    expected = dict(r6.EXPECTED)
    if result.get("source_hashes") != expected:
        fail("R6 result source hashes differ from frozen source contract")

    inspected = {}
    for name, expected_sha in expected.items():
        path = root / name
        if not path.exists():
            fail(f"missing frozen input: {name}")
        got_sha = r6.sha256_file(path)
        if got_sha != expected_sha:
            fail(f"hash mismatch for frozen input {name}: {got_sha}")
        df = r6.load_exact(path)
        if len(df) == 0:
            fail(f"empty frozen input: {name}")
        max_time = df.time.max()
        min_time = df.time.min()
        if max_time >= r6.PROTECTED:
            fail(f"protected 2026 row observed in {name}: {max_time}")
        years = sorted(int(x) for x in df.time.dt.year.unique())
        if not set(years).issubset({2024, 2025}):
            fail(f"unexpected years in {name}: {years}")
        inspected[name] = {
            "sha256": got_sha,
            "rows": int(len(df)),
            "min_time": min_time.isoformat(),
            "max_time": max_time.isoformat(),
            "years": years,
        }

    source = Path(r6.__file__).read_text(encoding="utf-8")
    required_source_contracts = [
        "if (df.time>=PROTECTED).any(): raise RuntimeError",
        "issubset({2024,2025})",
        "source24=year_slice(source_all,2024)",
        "source25=year_slice(source_all,2025)",
        "'protected_2026_opened':False",
    ]
    missing = [x for x in required_source_contracts if x not in source]
    if missing:
        fail(f"R6 source contract missing: {missing}")

    receipt_flag = receipt.get("protected_2026_untouched")
    metadata_mapping_defect = receipt_flag is False
    if receipt_flag not in (False, True, None):
        fail("invalid protected_2026_untouched receipt value")

    verdict = "PASS_METADATA_MAPPING_DEFECT" if metadata_mapping_defect else "PASS_PROVENANCE_CLEAN"
    audit = {
        "schema": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "verdict": verdict,
        "r6_receipt_status": receipt.get("status"),
        "r6_receipt_main_commit": receipt.get("main_commit"),
        "receipt_protected_2026_untouched": receipt_flag,
        "scientific_protected_2026_opened": False,
        "metadata_mapping_defect": metadata_mapping_defect,
        "scientific_run_reexecuted": False,
        "oos_2026_authorized": False,
        "discovery_passes": 15,
        "survivors_frozen": 12,
        "inputs": inspected,
        "interpretation": "Frozen R6 2024/2025 provenance verified. This audit does not authorize or open protected 2026 OOS and does not retune or rerun R6 science.",
    }
    atomic_json(output, audit)
    summary = (
        f"R6 provenance {verdict}: exact frozen 2024/2025 inputs verified; "
        "12 survivors frozen; protected 2026 not opened or authorized."
    )
    publish(args.publisher, output, "PASS", summary)
    print(json.dumps({"status": "PASS", "verdict": verdict, "survivors_frozen": 12, "protected_2026_opened": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
