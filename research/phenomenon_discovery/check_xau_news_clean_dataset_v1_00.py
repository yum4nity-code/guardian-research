#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

TF_SECONDS = {"M1": 60, "M5": 300}
MIN_MONTH_ROWS = {"M1": 10000, "M5": 2000}
MIN_TOTAL_ROWS = {"M1": 500000, "M5": 100000}
MAX_NEWS_EXCLUDED_FRACTION = 0.10


def load_mask(path: Path) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out.append((int(r["mask_start_server_epoch"]), int(r["mask_end_server_epoch"])))
    out.sort()
    return out


def overlaps_mask(epoch: int, step: int, mask: list[tuple[int, int]], start_idx: int) -> tuple[bool, int]:
    while start_idx < len(mask) and mask[start_idx][1] < epoch:
        start_idx += 1
    bar_end = epoch + step
    j = start_idx
    while j < len(mask) and mask[j][0] < bar_end:
        if mask[j][1] >= epoch:
            return True, start_idx
        j += 1
    return False, start_idx


def scan(path: Path, timeframe: str, mask: list[tuple[int, int]], require_clean: bool) -> dict:
    step = TF_SECONDS[timeframe]
    rows = 0
    duplicate_timestamps = 0
    non_increasing = 0
    timeframe_mismatch = 0
    out_of_window = 0
    invalid_ohlc = 0
    invalid_price = 0
    mask_overlap_rows = 0
    misaligned_seconds = 0
    gap_count = 0
    largest_gap_seconds = 0
    by_month: dict[str, int] = defaultdict(int)
    timestamps: list[int] = []
    seen: set[int] = set()
    previous: int | None = None
    mask_idx = 0

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows += 1
            if r.get("timeframe") != timeframe:
                timeframe_mismatch += 1
            server_time = r.get("server_time", "")
            if not (server_time.startswith("2024.") or server_time.startswith("2025.")):
                out_of_window += 1
            month = server_time[:7].replace(".", "-")
            by_month[month] += 1
            epoch = int(r["server_epoch"])
            timestamps.append(epoch)
            if epoch in seen:
                duplicate_timestamps += 1
            seen.add(epoch)
            if epoch % 60 != 0:
                misaligned_seconds += 1
            if previous is not None:
                if epoch <= previous:
                    non_increasing += 1
                delta = epoch - previous
                if delta > step:
                    gap_count += 1
                    largest_gap_seconds = max(largest_gap_seconds, delta)
            previous = epoch

            try:
                o = float(r["open"])
                h = float(r["high"])
                l = float(r["low"])
                c = float(r["close"])
            except (KeyError, TypeError, ValueError):
                invalid_price += 1
                continue
            if min(o, h, l, c) <= 0:
                invalid_price += 1
            if h < max(o, c) or l > min(o, c) or h < l:
                invalid_ohlc += 1

            contaminated, mask_idx = overlaps_mask(epoch, step, mask, mask_idx)
            if contaminated:
                mask_overlap_rows += 1

    if require_clean and mask_overlap_rows:
        pass

    return {
        "rows": rows,
        "duplicate_timestamps": duplicate_timestamps,
        "non_increasing_timestamps": non_increasing,
        "timeframe_mismatch_rows": timeframe_mismatch,
        "out_of_window_rows": out_of_window,
        "invalid_ohlc_rows": invalid_ohlc,
        "invalid_price_rows": invalid_price,
        "mask_overlap_rows": mask_overlap_rows,
        "misaligned_seconds_rows": misaligned_seconds,
        "gap_count_including_normal_market_closures": gap_count,
        "largest_gap_seconds": largest_gap_seconds,
        "rows_by_month": dict(sorted(by_month.items())),
        "first_epoch": timestamps[0] if timestamps else None,
        "last_epoch": timestamps[-1] if timestamps else None,
        "timestamp_set": seen,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True)
    ap.add_argument("--ia-mask", required=True)
    args = ap.parse_args()

    d = Path(args.input_dir)
    summary_path = d / "phase_ib_summary.json"
    mask_path = Path(args.ia_mask)
    raw_paths = {
        "M1": d / "xauusd_m1_2024_2025_raw.csv",
        "M5": d / "xauusd_m5_2024_2025_raw.csv",
    }
    clean_paths = {
        "M1": d / "xauusd_m1_2024_2025_news_clean.csv",
        "M5": d / "xauusd_m5_2024_2025_news_clean.csv",
    }
    for p in [summary_path, mask_path, *raw_paths.values(), *clean_paths.values()]:
        if not p.exists():
            raise RuntimeError(f"missing Phase I-B artifact: {p}")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    mask = load_mask(mask_path)
    errors: list[str] = []
    scans: dict[str, dict] = {}

    for tf in ("M1", "M5"):
        raw = scan(raw_paths[tf], tf, mask, False)
        clean = scan(clean_paths[tf], tf, mask, True)
        scans[tf] = {"raw": raw, "clean": clean}

        if raw["rows"] < MIN_TOTAL_ROWS[tf]:
            errors.append(f"{tf} raw total coverage too small: {raw['rows']}")
        if raw["duplicate_timestamps"]:
            errors.append(f"{tf} raw duplicate timestamps: {raw['duplicate_timestamps']}")
        if raw["non_increasing_timestamps"]:
            errors.append(f"{tf} raw non-increasing timestamps: {raw['non_increasing_timestamps']}")
        if raw["timeframe_mismatch_rows"]:
            errors.append(f"{tf} raw timeframe mismatch rows: {raw['timeframe_mismatch_rows']}")
        if raw["out_of_window_rows"]:
            errors.append(f"{tf} raw out-of-window rows: {raw['out_of_window_rows']}")
        if raw["invalid_ohlc_rows"] or raw["invalid_price_rows"]:
            errors.append(f"{tf} raw invalid prices/OHLC: {raw['invalid_price_rows']}/{raw['invalid_ohlc_rows']}")
        if raw["misaligned_seconds_rows"]:
            errors.append(f"{tf} raw second-alignment errors: {raw['misaligned_seconds_rows']}")

        if clean["duplicate_timestamps"] or clean["non_increasing_timestamps"]:
            errors.append(f"{tf} clean timestamp integrity failed")
        if clean["out_of_window_rows"]:
            errors.append(f"{tf} clean out-of-window rows: {clean['out_of_window_rows']}")
        if clean["invalid_ohlc_rows"] or clean["invalid_price_rows"]:
            errors.append(f"{tf} clean invalid prices/OHLC")
        if clean["mask_overlap_rows"]:
            errors.append(f"{tf} clean rows still overlap Phase I-A news mask: {clean['mask_overlap_rows']}")

        excluded = raw["rows"] - clean["rows"]
        if excluded <= 0:
            errors.append(f"{tf} news mask excluded no rows")
        frac = excluded / raw["rows"] if raw["rows"] else 1.0
        if frac > MAX_NEWS_EXCLUDED_FRACTION:
            errors.append(f"{tf} news exclusion fraction implausibly high: {frac:.4f}")

        frozen = summary.get("timeframes", {}).get(tf, {})
        if int(frozen.get("raw_rows", -1)) != raw["rows"]:
            errors.append(f"{tf} summary/raw row-count mismatch")
        if int(frozen.get("clean_rows", -1)) != clean["rows"]:
            errors.append(f"{tf} summary/clean row-count mismatch")
        if int(frozen.get("news_excluded_rows", -1)) != excluded:
            errors.append(f"{tf} summary/news-excluded row-count mismatch")

        for year in (2024, 2025):
            for month in range(1, 13):
                key = f"{year}-{month:02d}"
                n = int(raw["rows_by_month"].get(key, 0))
                if n < MIN_MONTH_ROWS[tf]:
                    errors.append(f"{tf} monthly coverage too sparse {key}: {n}")

    m1_ts = scans["M1"]["raw"]["timestamp_set"]
    m5_ts = scans["M5"]["raw"]["timestamp_set"]
    m5_missing_in_m1 = sum(1 for t in m5_ts if t not in m1_ts)

    compact_scans: dict[str, dict] = {}
    for tf in ("M1", "M5"):
        compact_scans[tf] = {}
        for stage in ("raw", "clean"):
            compact_scans[tf][stage] = {k: v for k, v in scans[tf][stage].items() if k != "timestamp_set"}

    integrity = {
        "schema": 1,
        "phase": "I-B",
        "checker_version": "1.00",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "symbol": summary.get("symbol"),
        "terminal_server": summary.get("terminal_server"),
        "terminal_data_path": summary.get("terminal_data_path"),
        "phase_ia_mask_intervals": len(mask),
        "same_server_as_phase_ia": summary.get("same_server_as_phase_ia") is True,
        "same_terminal_data_path_as_phase_ia": summary.get("same_terminal_data_path_as_phase_ia") is True,
        "protected_2026_untouched": summary.get("protected_2026_untouched") is True and all(compact_scans[tf][stage]["out_of_window_rows"] == 0 for tf in ("M1", "M5") for stage in ("raw", "clean")),
        "propfirm_tradability_authorized": False,
        "m5_timestamps_without_exact_m1_open_timestamp": m5_missing_in_m1,
        "note_on_gaps": "Weekend/session/holiday gaps are expected for XAUUSD and are reported, not treated as defects. Monthly coverage is the continuity gate.",
        "timeframes": compact_scans,
    }
    out = d / "phase_ib_integrity.json"
    out.write_text(json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(integrity, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
