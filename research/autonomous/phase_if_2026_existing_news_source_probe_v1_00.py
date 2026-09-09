#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

WINDOW_START = datetime(2026, 1, 1)
WINDOW_END = datetime(2026, 9, 1)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_dt(value: str) -> datetime | None:
    s = value.strip().strip('"').strip("'")
    if not s:
        return None
    s = s.replace("T", " ").replace("Z", "")
    fmts = (
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    m = re.match(r"^(\d{4})[-./](\d{1,2})[-./](\d{1,2})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?", s)
    if m:
        try:
            return datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0),
            )
        except ValueError:
            return None
    return None


def sniff(path: Path) -> tuple[str, list[list[str]]]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delim = dialect.delimiter
    except csv.Error:
        delim = ";" if sample.count(";") >= sample.count(",") else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    return delim, rows


def analyse_csv(path: Path) -> dict:
    out = {
        "path": str(path),
        "exists": path.exists(),
        "content_opened": False,
    }
    if not path.exists():
        return out
    out.update({
        "size_bytes": path.stat().st_size,
        "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(path),
    })
    delim, rows = sniff(path)
    out["content_opened"] = True
    out["delimiter"] = delim
    out["row_count_including_header"] = len(rows)
    if not rows:
        out["status"] = "EMPTY"
        return out

    header = [x.strip().lower() for x in rows[0]]
    out["header"] = rows[0]
    data = rows[1:] if any(re.search(r"[a-zA-Z]", x) for x in rows[0]) else rows

    date_idxs = [i for i, h in enumerate(header) if any(k in h for k in ("time", "date", "datetime"))]
    currency_idxs = [i for i, h in enumerate(header) if "currency" in h or h in {"ccy", "curr"}]
    impact_idxs = [i for i, h in enumerate(header) if any(k in h for k in ("impact", "importance", "priority"))]
    source_idxs = [i for i, h in enumerate(header) if any(k in h for k in ("server", "broker", "source"))]

    parsed_dates: list[datetime] = []
    window_rows = 0
    usd_rows = 0
    high_rows = 0
    usd_high_rows = 0
    source_values = set()

    def cell(row: list[str], i: int) -> str:
        return row[i].strip() if i < len(row) else ""

    for row in data:
        dt = None
        for i in date_idxs:
            dt = parse_dt(cell(row, i))
            if dt:
                break
        if dt is None:
            for v in row[:3]:
                dt = parse_dt(v)
                if dt:
                    break
        if dt:
            parsed_dates.append(dt)
        in_window = bool(dt and WINDOW_START <= dt < WINDOW_END)
        if in_window:
            window_rows += 1

        currency = " ".join(cell(row, i) for i in currency_idxs).upper() if currency_idxs else " ".join(row).upper()
        is_usd = bool(re.search(r"(^|[^A-Z])USD([^A-Z]|$)", currency))
        if in_window and is_usd:
            usd_rows += 1

        impact_text = " ".join(cell(row, i) for i in impact_idxs).strip().lower() if impact_idxs else ""
        is_high = impact_text in {"3", "high", "high impact", "important", "importance_high"} or "high" in impact_text
        if in_window and is_high:
            high_rows += 1
        if in_window and is_usd and is_high:
            usd_high_rows += 1

        for i in source_idxs:
            v = cell(row, i)
            if v:
                source_values.add(v)

    out.update({
        "data_row_count": len(data),
        "parsed_datetime_count": len(parsed_dates),
        "min_datetime": min(parsed_dates).isoformat(sep=" ") if parsed_dates else None,
        "max_datetime": max(parsed_dates).isoformat(sep=" ") if parsed_dates else None,
        "jan_aug_2026_rows": window_rows,
        "jan_aug_2026_usd_rows": usd_rows,
        "jan_aug_2026_high_rows": high_rows,
        "jan_aug_2026_usd_high_rows": usd_high_rows,
        "source_values": sorted(source_values)[:20],
        "has_explicit_currency_column": bool(currency_idxs),
        "has_explicit_impact_column": bool(impact_idxs),
        "has_explicit_source_or_server_column": bool(source_idxs),
    })
    out["status"] = "COVERS_FROZEN_WINDOW" if parsed_dates and min(parsed_dates) <= WINDOW_START and max(parsed_dates) >= datetime(2026, 8, 31) else "INSUFFICIENT_OR_UNPROVEN_COVERAGE"
    return out


def analyse_news_dat(path: Path) -> dict:
    out = {"path": str(path), "exists": path.exists(), "content_opened": False}
    if not path.exists():
        return out
    raw = path.read_bytes()
    out.update({
        "content_opened": True,
        "size_bytes": len(raw),
        "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "looks_like_sqlite": raw.startswith(b"SQLite format 3\x00"),
        "contains_2026_ascii": b"2026" in raw,
        "reason": "Canonical server news.dat inspected only as a source-capability artifact; no market HCC opened.",
    })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--common-files", required=True)
    ap.add_argument("--canonical-news-dat", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    common = Path(args.common_files)
    candidates = [
        common / "Guardian_PropFirm_NewsCalendar.csv",
        common / "FTMO_Guardian_NewsCalendar.csv",
        common / "Guardian" / "phase_if" / "mt5_high_impact_calendar_2026_jan_aug.csv",
        common / "Guardian" / "phase_ia" / "mt5_high_impact_calendar_2024_2025.csv",
    ]
    csv_reports = [analyse_csv(p) for p in candidates]
    news_dat = analyse_news_dat(Path(args.canonical_news_dat))

    generated = datetime.now(timezone.utc).isoformat()
    usable = [r for r in csv_reports if r.get("status") == "COVERS_FROZEN_WINDOW" and r.get("jan_aug_2026_usd_high_rows", 0) > 0]
    result = {
        "schema": 1,
        "phase": "I-F-2026-EXISTING-NEWS-SOURCE-PROBE",
        "generated_at_utc": generated,
        "status": "PASS",
        "scientific_hypothesis_changed": False,
        "protected_market_content_opened": False,
        "protected_news_content_opened": True,
        "frozen_window": {"start": "2026-01-01", "end_exclusive": "2026-09-01"},
        "csv_candidates": csv_reports,
        "canonical_news_dat": news_dat,
        "usable_existing_csv_candidate_count": len(usable),
        "decision": "EXISTING_SOURCE_REQUIRES_PROVENANCE_REVIEW" if usable else "NO_PROVEN_EXISTING_CSV_SOURCE",
        "reason": "Read only pre-existing news/calendar candidate files after committed preregistration and standing 2026 authorization; protected XAU market HCC remains unopened.",
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
