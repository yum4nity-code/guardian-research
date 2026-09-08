#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

PROTECTED_2026_EPOCH = 1767225600
MIN_USD_HIGH_IMPACT_PER_YEAR = 60
MIN_USD_HIGH_IMPACT_PER_MONTH = 3


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def canonical_month(server_time: str) -> str:
    """Return YYYY-MM from MT5 TimeToString output or ISO-like input.

    MT5 TimeToString uses YYYY.MM.DD, while earlier integrity code expected
    YYYY-MM. Normalize only the date separator; do not alter the timestamp or
    server-time semantics used by the research artifacts.
    """
    prefix = server_time.strip()[:7]
    return prefix.replace(".", "-")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    args = ap.parse_args()
    d = Path(args.input_dir)
    summary_path = d / "phase_ia_summary.json"
    events_path = d / "phase_ia_xauusd_high_impact_events_2024_2025.csv"
    mask_path = d / "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    for p in (summary_path, events_path, mask_path):
        if not p.exists():
            raise RuntimeError(f"missing Phase I-A artifact: {p}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    events = load_csv(events_path)
    masks = load_csv(mask_path)
    errors: list[str] = []

    if summary.get("protected_2026_untouched") is not True:
        errors.append("summary does not protect 2026")
    if summary.get("same_server_time_required_for_xau_phase_ib") is not True:
        errors.append("same-server-time requirement missing")
    terminal = summary.get("terminal_manifest", {})
    if not terminal.get("server"):
        errors.append("terminal server is blank")
    if not terminal.get("terminal_path"):
        errors.append("terminal path is blank")

    ids = [r.get("value_id", "") for r in events]
    dup_ids = sum(c - 1 for c in Counter(ids).values() if c > 1)
    if dup_ids:
        errors.append(f"duplicate normalized value ids: {dup_ids}")

    by_year = Counter()
    by_month = Counter()
    opened_2026 = 0
    wrong_currency = 0
    wrong_importance = 0
    malformed_windows = 0
    for r in events:
        epoch = int(r["server_epoch"])
        start = int(r["mask_start_server_epoch"])
        end = int(r["mask_end_server_epoch"])
        if epoch >= PROTECTED_2026_EPOCH:
            opened_2026 += 1
        if r.get("currency") != "USD":
            wrong_currency += 1
        if int(r.get("importance", "0")) != 3:
            wrong_importance += 1
        if not start < epoch < end:
            malformed_windows += 1
        server_time = r.get("server_time", "")
        month_key = canonical_month(server_time)
        by_year[month_key[:4]] += 1
        by_month[month_key] += 1

    if opened_2026:
        errors.append(f"opened 2026 event rows: {opened_2026}")
    if wrong_currency:
        errors.append(f"non-USD XAU event rows: {wrong_currency}")
    if wrong_importance:
        errors.append(f"non-high-impact rows: {wrong_importance}")
    if malformed_windows:
        errors.append(f"malformed event windows: {malformed_windows}")
    for year in ("2024", "2025"):
        if by_year[year] < MIN_USD_HIGH_IMPACT_PER_YEAR:
            errors.append(f"insufficient USD high-impact events {year}: {by_year[year]}")
        for month in range(1, 13):
            key = f"{year}-{month:02d}"
            if by_month[key] < MIN_USD_HIGH_IMPACT_PER_MONTH:
                errors.append(f"calendar coverage too sparse {key}: {by_month[key]}")

    mask_overlap_violations = 0
    mask_order_violations = 0
    previous_end = None
    total_mask_seconds = 0
    for r in masks:
        start = int(r["mask_start_server_epoch"])
        end = int(r["mask_end_server_epoch"])
        if start >= end:
            mask_order_violations += 1
        if previous_end is not None and start <= previous_end:
            mask_overlap_violations += 1
        previous_end = end
        total_mask_seconds += max(0, end - start)
    if mask_order_violations:
        errors.append(f"invalid merged mask intervals: {mask_order_violations}")
    if mask_overlap_violations:
        errors.append(f"merged mask overlap violations: {mask_overlap_violations}")
    if len(masks) < 50:
        errors.append(f"too few merged mask intervals: {len(masks)}")

    integrity = {
        "schema": 1,
        "checker_version": "1.01",
        "phase": "I-A",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "event_rows": len(events),
        "merged_mask_intervals": len(masks),
        "duplicate_value_ids": dup_ids,
        "opened_2026_rows": opened_2026,
        "wrong_currency_rows": wrong_currency,
        "wrong_importance_rows": wrong_importance,
        "malformed_event_windows": malformed_windows,
        "mask_order_violations": mask_order_violations,
        "mask_overlap_violations": mask_overlap_violations,
        "total_mask_seconds": total_mask_seconds,
        "event_counts_by_year": dict(sorted(by_year.items())),
        "event_counts_by_month": dict(sorted(by_month.items())),
        "terminal_server": terminal.get("server", ""),
        "terminal_path": terminal.get("terminal_path", ""),
        "research_window_pre_minutes": summary.get("research_profile", {}).get("pre_minutes"),
        "research_window_post_minutes": summary.get("research_profile", {}).get("post_minutes"),
        "protected_2026_untouched": opened_2026 == 0 and summary.get("protected_2026_untouched") is True,
        "propfirm_tradability_authorized": False,
        "month_key_normalization": "MT5 YYYY.MM normalized to YYYY-MM for coverage gate only",
    }
    out = d / "phase_ia_integrity.json"
    out.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(integrity, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
