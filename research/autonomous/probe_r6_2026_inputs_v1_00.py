#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path


START = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
END = int(datetime(2026, 9, 1, tzinfo=timezone.utc).timestamp())
JAN7 = int(datetime(2026, 1, 7, tzinfo=timezone.utc).timestamp())
AUG25 = int(datetime(2026, 8, 25, tzinfo=timezone.utc).timestamp())


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_manifest(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def inspect_csv(path: Path, timeframe: str) -> dict:
    result = {"path": str(path), "exists": path.exists(), "timeframe": timeframe}
    if not path.exists():
        return result
    rows = 0
    first = None
    last = None
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        result["columns"] = sorted(fields)
        if "server_epoch" not in fields:
            result["error"] = "server_epoch column missing"
            return result
        prev = None
        for row in reader:
            t = int(row["server_epoch"])
            if prev is not None and t <= prev:
                result["error"] = "timestamps not strictly increasing"
                return result
            prev = t
            first = t if first is None else first
            last = t
            rows += 1
    result.update(
        {
            "rows": rows,
            "first_epoch": first,
            "last_epoch": last,
            "starts_by_jan7": first is not None and first <= JAN7,
            "ends_after_aug25": last is not None and last >= AUG25,
            "inside_jan_aug_window": first is not None and last is not None and first >= START and last < END,
        }
    )
    if timeframe.lower() == "m1":
        result["complete_enough"] = bool(
            rows >= 150000 and result["starts_by_jan7"] and result["ends_after_aug25"] and result["inside_jan_aug_window"]
        )
    else:
        result["complete_enough"] = bool(
            rows >= 30000 and result["starts_by_jan7"] and result["ends_after_aug25"] and result["inside_jan_aug_window"]
        )
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--m1-csv", required=True)
    ap.add_argument("--m1-manifest", required=True)
    ap.add_argument("--m5-csv", required=True)
    ap.add_argument("--m5-manifest", required=True)
    ap.add_argument("--hcc", required=True)
    ap.add_argument("--news-mask", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    m1_csv = Path(args.m1_csv)
    m5_csv = Path(args.m5_csv)
    m1_manifest = Path(args.m1_manifest)
    m5_manifest = Path(args.m5_manifest)
    hcc = Path(args.hcc)
    news_mask = Path(args.news_mask)

    m1 = inspect_csv(m1_csv, "M1")
    m5 = inspect_csv(m5_csv, "M5")
    m1["manifest"] = parse_manifest(m1_manifest)
    m5["manifest"] = parse_manifest(m5_manifest)

    hcc_info = {"path": str(hcc), "exists": hcc.exists(), "readable": False}
    if hcc.exists():
        hcc_info["size_bytes"] = hcc.stat().st_size
        try:
            with hcc.open("rb") as handle:
                hcc_info["first_byte_hex"] = handle.read(1).hex()
            hcc_info["readable"] = True
        except Exception as exc:
            hcc_info["read_error"] = f"{type(exc).__name__}: {exc}"

    news = {"path": str(news_mask), "exists": news_mask.exists()}
    if news_mask.exists():
        news["size_bytes"] = news_mask.stat().st_size

    status = "PASS"
    recommendation = None
    if m1.get("complete_enough") and m5.get("complete_enough") and news["exists"]:
        recommendation = "USE_EXISTING_VALIDATED_JAN_AUG_SNAPSHOTS"
    elif hcc_info["readable"] and m5.get("complete_enough") and news["exists"]:
        recommendation = "RECOVER_FULL_M1_FROM_HCC_AND_REUSE_VALIDATED_M5"
    elif m5.get("complete_enough") and news["exists"]:
        recommendation = "M1_BLOCKED_HCC_LOCKED_OR_INCOMPLETE"
        status = "BLOCKED"
    else:
        recommendation = "DATASET_NOT_READY"
        status = "BLOCKED"

    out = {
        "schema": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "scope": "infrastructure_only_no_scientific_r6_evaluation",
        "authorized_protected_2026_access": True,
        "frozen_window": {"start": "2026-01-01T00:00:00Z", "end_exclusive": "2026-09-01T00:00:00Z"},
        "m1": m1,
        "m5": m5,
        "hcc": hcc_info,
        "news_mask": news,
        "recommendation": recommendation,
        "retuning_performed": False,
    }
    atomic_json(Path(args.output), out)
    print(json.dumps({"status": status, "recommendation": recommendation, "m1_complete": bool(m1.get("complete_enough")), "m5_complete": bool(m5.get("complete_enough")), "hcc_readable": hcc_info["readable"]}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
