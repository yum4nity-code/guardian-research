#!/usr/bin/env python3
"""Read-only Edge Atlas data preflight. No strategy or historical calculation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from data_loader_v1 import (
    AdmissionError, BINANCE_COLUMNS, PROTECTED_START, decode_dukascopy_m1_day,
    iter_binance_spot_m5, load_dukascopy_index,
)

PINNED_MANIFEST_SHA256 = "67c602f2a42ef09c60c6ca86eca7b876e5af6bc3a81e053a29a545be0fd2c75c"
EXPECTED_IDS = {
    "DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025",
    "BINANCE_SPOT_BTCUSDT_M5_2024_2025",
    "BINANCE_SPOT_ETHUSDT_M5_2024_2025",
}


def canonical_manifest_sha256(path: Path) -> str:
    import hashlib
    obj = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def validate_manifest(manifest: dict) -> dict[str, dict]:
    if manifest.get("schema_version") != 1 or manifest.get("campaign_id") != "EDGE-ATLAS-2026-09-17" or manifest.get("verdict") != "READY_FOR_READ_ONLY_CHEAP_FAIL":
        raise AdmissionError("manifest identity/status mismatch")
    rules = manifest.get("global_rules")
    required_rules = {
        "read_only": True, "maximum_year_exclusive": 2026,
        "reject_path_containing_2026": True,
        "reject_row_at_or_after": "2026-01-01T00:00:00Z",
        "reject_unlisted_source": True, "fundednext_xau_forbidden": True,
        "derived_dukascopy_yearly_csv_forbidden": True,
        "open_interest_available": False, "derivative_context_available": False,
    }
    if not isinstance(rules, dict) or any(rules.get(k) != v for k, v in required_rules.items()):
        raise AdmissionError("manifest global fail-closed rules mismatch")
    datasets = manifest.get("datasets")
    if not isinstance(datasets, list) or len(datasets) != 3:
        raise AdmissionError("manifest must contain exactly three admitted datasets")
    by_id = {item.get("dataset_id"): item for item in datasets if isinstance(item, dict)}
    if set(by_id) != EXPECTED_IDS or len(by_id) != len(datasets):
        raise AdmissionError("manifest dataset IDs are incomplete, duplicate or unexpected")
    duka = by_id["DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025"]
    if not (
        duka.get("status") == "ADMITTED_READ_ONLY" and duka.get("asset") == "XAUUSD"
        and duka.get("source") == "Dukascopy public XAUUSD BID_candles_min_1.bi5"
        and duka.get("format") == "LZMA-compressed 24-byte M1 candle records"
        and duka.get("granularity") == "M1" and duka.get("timezone") == "UTC"
        and isinstance(duka.get("cache_roots"), list) and len(duka["cache_roots"]) == 2
        and duka.get("payload_count") == 5518 and duka.get("first_date") == "2004-11-08"
        and duka.get("last_date") == "2025-12-31" and duka.get("missing_weekday_payloads") == 0
        and duka.get("duplicate_dates") == 0
    ):
        raise AdmissionError("Dukascopy provenance/coverage metadata mismatch")
    for dataset_id, asset in (
        ("BINANCE_SPOT_BTCUSDT_M5_2024_2025", "BTCUSDT"),
        ("BINANCE_SPOT_ETHUSDT_M5_2024_2025", "ETHUSDT"),
    ):
        item = by_id[dataset_id]
        if not (
            item.get("status") == "ADMITTED_READ_ONLY" and item.get("asset") == asset
            and item.get("source") == "Binance public monthly spot klines"
            and item.get("granularity") == "M5 OHLCV" and item.get("timezone") == "UTC"
            and item.get("admitted_first_timestamp") == "2024-01-01T00:00:00Z"
            and item.get("admitted_last_timestamp") == "2025-12-31T23:55:00Z"
            and item.get("admitted_rows") == 210528 and item.get("expected_full_grid_rows") == 210528
            and item.get("duplicates") == item.get("nonmonotonic_rows") == item.get("non_300_second_deltas") == item.get("off_grid_rows") == 0
            and item.get("open_interest") is False and item.get("derivatives") is False
        ):
            raise AdmissionError(f"Binance provenance/coverage metadata mismatch: {dataset_id}")
    return by_id


def run_preflight(manifest_path: Path, expected_manifest_sha256: str = PINNED_MANIFEST_SHA256) -> dict:
    result = {
        "schema_version": 1,
        "status": "PREFLIGHT_FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(manifest_path),
        "files_inspected": 1,
        "files_admitted": [],
        "files_rejected": [],
        "rejection_causes": [],
        "datasets": [],
        "presence_2026": False,
        "causal_availability": "NOT_CHECKED",
        "historical_strategy_run": False,
        "payload_files_admitted": 0,
        "payload_hashes": "NOT_CHECKED",
    }
    current_file = str(manifest_path)
    try:
        if canonical_manifest_sha256(manifest_path) != expected_manifest_sha256:
            raise AdmissionError("admitted manifest SHA-256 mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        by_id = validate_manifest(manifest)
        for dataset_id in sorted(EXPECTED_IDS):
            dataset = by_id[dataset_id]
            if dataset_id.startswith("DUKASCOPY_"):
                index_path = Path(dataset["payload_index"])
                current_file = str(index_path)
                rows = load_dukascopy_index(index_path, dataset["payload_index_sha256"])
                result["files_inspected"] += 1
                count = 0
                first = last = None
                for row in rows:
                    count += 1
                    first = first or row["date"]
                    last = row["date"]
                    current_file = row["path"]
                    # Exhaust one day, then release it before opening the next.
                    for _ in decode_dukascopy_m1_day(row):
                        pass
                    result["files_inspected"] += 1
                if count != dataset["payload_count"] or first != dataset["first_date"] or last != dataset["last_date"]:
                    raise AdmissionError("Dukascopy coverage mismatch")
                result["files_admitted"].append({"path": str(index_path), "payload_files": count})
                result["payload_files_admitted"] = count
                result["payload_hashes"] = f"VERIFIED_AGAINST_INDEX:{dataset['payload_index_sha256']}"
                result["datasets"].append({"id": dataset_id, "coverage": [first, last], "granularity": "M1", "timezone": "UTC", "hash": dataset["payload_index_sha256"], "files": count})
            elif dataset_id.startswith("BINANCE_SPOT_"):
                path = Path(dataset["path"])
                current_file = str(path)
                start = datetime.fromisoformat(dataset["admitted_first_timestamp"].replace("Z", "+00:00"))
                end = PROTECTED_START
                count = 0
                first = last = None
                for bar in iter_binance_spot_m5(path, dataset["file_sha256"], start, end):
                    count += 1
                    first = first or bar.timestamp
                    last = bar.timestamp
                result["files_inspected"] += 1
                if first is None or last is None or count != dataset["admitted_rows"] or first.isoformat().replace("+00:00", "Z") != dataset["admitted_first_timestamp"] or last.isoformat().replace("+00:00", "Z") != dataset["admitted_last_timestamp"]:
                    raise AdmissionError("Binance coverage mismatch")
                result["files_admitted"].append(str(path))
                result["datasets"].append({"id": dataset_id, "coverage": [dataset["admitted_first_timestamp"], dataset["admitted_last_timestamp"]], "granularity": "M5", "timezone": "UTC", "hash": dataset["file_sha256"], "files": 1})
            else:
                raise AdmissionError(f"unknown dataset type: {dataset_id}")
        result["causal_availability"] = "PASS_BAR_CLOSE_AVAILABLE_AT"
        result["status"] = "PREFLIGHT_PASS_NO_RUN"
    except AdmissionError as exc:
        result["status"] = "BLOCKED_DATA"
        result["rejection_causes"].append(str(exc))
        result["files_rejected"].append({"path": current_file, "cause": str(exc)})
        result["presence_2026"] = "2026" in str(exc)
    except Exception as exc:  # infrastructure/programming errors must still return a prescribed status
        result["status"] = "INFRASTRUCTURE_ERROR"
        result["rejection_causes"].append(repr(exc))
        result["files_rejected"].append({"path": current_file, "cause": repr(exc)})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_preflight(args.manifest)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            raise SystemExit("refusing to overwrite preflight output")
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["status"] == "PREFLIGHT_PASS_NO_RUN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
