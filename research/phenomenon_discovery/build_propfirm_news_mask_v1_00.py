#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROTECTED_2026_EPOCH = 1767225600
TARGET_SYMBOL = "XAUUSD"
TARGET_CURRENCY = "USD"


def read_manifest(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def merge_intervals(intervals: list[tuple[int, int, list[str]]]) -> list[dict]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: (x[0], x[1]))
    merged: list[dict] = []
    cur_start, cur_end, cur_ids = intervals[0][0], intervals[0][1], list(intervals[0][2])
    for start, end, ids in intervals[1:]:
        if start <= cur_end:
            cur_end = max(cur_end, end)
            cur_ids.extend(ids)
        else:
            merged.append({
                "mask_start_server_epoch": cur_start,
                "mask_end_server_epoch": cur_end,
                "source_event_ids": ";".join(sorted(set(cur_ids))),
            })
            cur_start, cur_end, cur_ids = start, end, list(ids)
    merged.append({
        "mask_start_server_epoch": cur_start,
        "mask_end_server_epoch": cur_end,
        "source_event_ids": ";".join(sorted(set(cur_ids))),
    })
    return merged


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-csv", required=True)
    ap.add_argument("--terminal-manifest", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    raw_path = Path(args.raw_csv)
    manifest_path = Path(args.terminal_manifest)
    policy_path = Path(args.policy)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    research = policy["research_policy"]
    pre = int(research["pre_minutes"]) * 60
    post = int(research["post_minutes"]) * 60
    terminal_manifest = read_manifest(manifest_path)
    rows = load_rows(raw_path)

    seen: set[str] = set()
    normalized: list[dict] = []
    year_counts: dict[str, int] = defaultdict(int)
    month_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        value_id = str(r.get("value_id", "")).strip()
        if not value_id or value_id in seen:
            continue
        seen.add(value_id)
        try:
            epoch = int(r["server_epoch"])
            importance = int(r["importance"])
        except (KeyError, TypeError, ValueError):
            continue
        if epoch >= PROTECTED_2026_EPOCH:
            raise RuntimeError(f"protected 2026 row encountered value_id={value_id} epoch={epoch}")
        if importance != 3:
            continue
        currency = str(r.get("currency", "")).strip().upper()
        if currency != TARGET_CURRENCY:
            continue
        server_time = str(r.get("server_time", "")).strip()
        year = server_time[:4]
        month = server_time[:7]
        year_counts[year] += 1
        month_counts[month] += 1
        normalized.append({
            "value_id": value_id,
            "event_id": r.get("event_id", ""),
            "server_time": server_time,
            "server_epoch": epoch,
            "currency": currency,
            "importance": importance,
            "event_code": r.get("event_code", ""),
            "event_name": r.get("event_name", ""),
            "country_code": r.get("country_code", ""),
            "country_name": r.get("country_name", ""),
            "source_url": r.get("source_url", ""),
            "mask_start_server_epoch": epoch - pre,
            "mask_end_server_epoch": epoch + post,
            "research_profile": research["name"],
            "target_symbol": TARGET_SYMBOL,
        })

    normalized.sort(key=lambda r: (int(r["server_epoch"]), str(r["value_id"])))
    event_fields = [
        "value_id", "event_id", "server_time", "server_epoch", "currency", "importance",
        "event_code", "event_name", "country_code", "country_name", "source_url",
        "mask_start_server_epoch", "mask_end_server_epoch", "research_profile", "target_symbol",
    ]
    events_path = outdir / "phase_ia_xauusd_high_impact_events_2024_2025.csv"
    write_csv(events_path, normalized, event_fields)

    intervals = [
        (int(r["mask_start_server_epoch"]), int(r["mask_end_server_epoch"]), [str(r["value_id"])])
        for r in normalized
    ]
    merged = merge_intervals(intervals)
    for idx, r in enumerate(merged, start=1):
        r["interval_id"] = idx
        r["target_symbol"] = TARGET_SYMBOL
        r["currency"] = TARGET_CURRENCY
        r["research_profile"] = research["name"]
    mask_path = outdir / "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    mask_fields = [
        "interval_id", "target_symbol", "currency", "research_profile",
        "mask_start_server_epoch", "mask_end_server_epoch", "source_event_ids",
    ]
    write_csv(mask_path, merged, mask_fields)

    summary = {
        "schema": 1,
        "phase": "I-A",
        "status": "DATA_GATE_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "MT5 Economic Calendar via same-terminal trade-server time",
        "terminal_manifest": terminal_manifest,
        "research_profile": research,
        "target_symbol": TARGET_SYMBOL,
        "target_currency": TARGET_CURRENCY,
        "raw_rows": len(rows),
        "unique_raw_value_ids": len(seen),
        "xauusd_high_impact_event_rows": len(normalized),
        "merged_mask_intervals": len(merged),
        "event_counts_by_year": dict(sorted(year_counts.items())),
        "event_counts_by_month": dict(sorted(month_counts.items())),
        "protected_2026_untouched": True,
        "same_server_time_required_for_xau_phase_ib": True,
        "propfirm_tradability_authorized": False,
        "promotion_gate": "Phase I-B/I-C may exclude masked rows for research; no live prop-firm promotion is authorized by Phase I-A alone.",
        "official_profiles_reference": policy.get("official_profiles", {}),
    }
    summary_path = outdir / "phase_ia_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
