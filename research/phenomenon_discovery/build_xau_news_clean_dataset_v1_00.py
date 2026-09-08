#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

TF_SECONDS = {"M1": 60, "M5": 300}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_kv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def load_mask(path: Path) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            start = int(r["mask_start_server_epoch"])
            end = int(r["mask_end_server_epoch"])
            if start >= end:
                raise RuntimeError(f"invalid news mask interval {start}..{end}")
            out.append((start, end))
    out.sort()
    for i in range(1, len(out)):
        if out[i][0] <= out[i - 1][1]:
            raise RuntimeError("news mask is not strictly merged/non-overlapping")
    if not out:
        raise RuntimeError("empty Phase I-A news mask")
    return out


def normalized_month(server_time: str) -> str:
    return server_time[:7].replace(".", "-")


def process_one(raw_path: Path, clean_path: Path, timeframe: str, mask: list[tuple[int, int]]) -> dict:
    if timeframe not in TF_SECONDS:
        raise ValueError(timeframe)
    step = TF_SECONDS[timeframe]
    clean_path.parent.mkdir(parents=True, exist_ok=True)

    raw_rows = 0
    clean_rows = 0
    excluded_rows = 0
    first_epoch: int | None = None
    last_epoch: int | None = None
    first_clean_epoch: int | None = None
    last_clean_epoch: int | None = None
    raw_by_month: dict[str, int] = defaultdict(int)
    clean_by_month: dict[str, int] = defaultdict(int)
    excluded_by_month: dict[str, int] = defaultdict(int)
    mask_idx = 0

    with raw_path.open("r", newline="", encoding="utf-8-sig") as fi:
        reader = csv.DictReader(fi)
        if not reader.fieldnames:
            raise RuntimeError(f"missing CSV header: {raw_path}")
        required = {"symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise RuntimeError(f"missing raw columns {missing} in {raw_path}")
        with clean_path.open("w", newline="", encoding="utf-8") as fo:
            writer = csv.DictWriter(fo, fieldnames=reader.fieldnames)
            writer.writeheader()
            previous_epoch: int | None = None
            for r in reader:
                raw_rows += 1
                if r["timeframe"] != timeframe:
                    raise RuntimeError(f"unexpected timeframe {r['timeframe']} in {raw_path}")
                server_time = r["server_time"]
                if not (server_time.startswith("2024.") or server_time.startswith("2025.")):
                    raise RuntimeError(f"protected/out-of-window row encountered: {server_time}")
                epoch = int(r["server_epoch"])
                if previous_epoch is not None and epoch <= previous_epoch:
                    raise RuntimeError(f"non-increasing raw timestamp in {raw_path}: {epoch} <= {previous_epoch}")
                previous_epoch = epoch
                if first_epoch is None:
                    first_epoch = epoch
                last_epoch = epoch
                month = normalized_month(server_time)
                raw_by_month[month] += 1

                bar_start = epoch
                bar_end = epoch + step
                while mask_idx < len(mask) and mask[mask_idx][1] < bar_start:
                    mask_idx += 1
                contaminated = False
                j = mask_idx
                while j < len(mask) and mask[j][0] < bar_end:
                    start, end = mask[j]
                    if end >= bar_start:
                        contaminated = True
                        break
                    j += 1

                if contaminated:
                    excluded_rows += 1
                    excluded_by_month[month] += 1
                    continue

                writer.writerow(r)
                clean_rows += 1
                clean_by_month[month] += 1
                if first_clean_epoch is None:
                    first_clean_epoch = epoch
                last_clean_epoch = epoch

    if raw_rows == 0 or clean_rows == 0:
        raise RuntimeError(f"empty raw/clean dataset for {timeframe}")

    return {
        "timeframe": timeframe,
        "bar_seconds": step,
        "raw_rows": raw_rows,
        "clean_rows": clean_rows,
        "news_excluded_rows": excluded_rows,
        "news_excluded_fraction": excluded_rows / raw_rows,
        "first_raw_epoch": first_epoch,
        "last_raw_epoch": last_epoch,
        "first_clean_epoch": first_clean_epoch,
        "last_clean_epoch": last_clean_epoch,
        "raw_rows_by_month": dict(sorted(raw_by_month.items())),
        "clean_rows_by_month": dict(sorted(clean_by_month.items())),
        "news_excluded_rows_by_month": dict(sorted(excluded_by_month.items())),
        "raw_path": str(raw_path),
        "clean_path": str(clean_path),
        "raw_sha256": sha256(raw_path),
        "clean_sha256": sha256(clean_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-m1", required=True)
    ap.add_argument("--raw-m5", required=True)
    ap.add_argument("--ib-terminal-manifest", required=True)
    ap.add_argument("--ia-summary", required=True)
    ap.add_argument("--ia-mask", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    raw_m1 = Path(args.raw_m1)
    raw_m5 = Path(args.raw_m5)
    ib_manifest_path = Path(args.ib_terminal_manifest)
    ia_summary_path = Path(args.ia_summary)
    ia_mask_path = Path(args.ia_mask)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    for p in (raw_m1, raw_m5, ib_manifest_path, ia_summary_path, ia_mask_path):
        if not p.exists():
            raise RuntimeError(f"missing I-B input: {p}")

    ib_manifest = read_kv(ib_manifest_path)
    ia_summary = json.loads(ia_summary_path.read_text(encoding="utf-8"))
    ia_terminal = ia_summary.get("terminal_manifest", {})

    if ib_manifest.get("phase") != "I-B":
        raise RuntimeError("I-B terminal manifest phase mismatch")
    if ib_manifest.get("server") != ia_terminal.get("server"):
        raise RuntimeError(f"server mismatch I-A={ia_terminal.get('server')} I-B={ib_manifest.get('server')}")
    if ib_manifest.get("terminal_data_path", "").rstrip("\\").lower() != str(ia_terminal.get("terminal_data_path", "")).rstrip("\\").lower():
        raise RuntimeError("TERMINAL_DATA_PATH mismatch between I-A and I-B")
    if ib_manifest.get("terminal_path", "").rstrip("\\").lower() != str(ia_terminal.get("terminal_path", "")).rstrip("\\").lower():
        raise RuntimeError("TERMINAL_PATH mismatch between I-A and I-B")
    if ia_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("I-A provenance does not protect 2026")
    if ia_summary.get("research_profile", {}).get("pre_minutes") != 5 or ia_summary.get("research_profile", {}).get("post_minutes") != 5:
        raise RuntimeError("I-A research mask is not the frozen +/-5 minute policy")

    mask = load_mask(ia_mask_path)
    m1_clean = outdir / "xauusd_m1_2024_2025_news_clean.csv"
    m5_clean = outdir / "xauusd_m5_2024_2025_news_clean.csv"
    tf_stats = {
        "M1": process_one(raw_m1, m1_clean, "M1", mask),
        "M5": process_one(raw_m5, m5_clean, "M5", mask),
    }

    months = sorted(set(tf_stats["M1"]["raw_rows_by_month"]) | set(tf_stats["M5"]["raw_rows_by_month"]))
    audit_rows: list[dict] = []
    for month in months:
        for tf in ("M1", "M5"):
            s = tf_stats[tf]
            raw = int(s["raw_rows_by_month"].get(month, 0))
            excluded = int(s["news_excluded_rows_by_month"].get(month, 0))
            clean = int(s["clean_rows_by_month"].get(month, 0))
            audit_rows.append({
                "month": month,
                "timeframe": tf,
                "raw_rows": raw,
                "news_excluded_rows": excluded,
                "clean_rows": clean,
                "news_excluded_fraction": (excluded / raw) if raw else 0.0,
            })
    audit_path = outdir / "phase_ib_news_exclusion_audit.csv"
    with audit_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(audit_rows[0].keys()))
        w.writeheader()
        w.writerows(audit_rows)

    summary = {
        "schema": 1,
        "phase": "I-B",
        "status": "DATA_GATE_READY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "same-open-MT5 XAUUSD history export; conservative Phase I-A high-impact USD +/-5m mask applied before research dataset use",
        "symbol": ib_manifest.get("symbol"),
        "symbol_root": ib_manifest.get("symbol_root"),
        "terminal_server": ib_manifest.get("server"),
        "terminal_path": ib_manifest.get("terminal_path"),
        "terminal_data_path": ib_manifest.get("terminal_data_path"),
        "from_server_time": ib_manifest.get("from_server_time"),
        "to_server_time_exclusive": ib_manifest.get("to_server_time_exclusive"),
        "phase_ia_summary_sha256": sha256(ia_summary_path),
        "phase_ia_mask_sha256": sha256(ia_mask_path),
        "phase_ia_mask_intervals": len(mask),
        "news_policy_pre_minutes": 5,
        "news_policy_post_minutes": 5,
        "timeframes": tf_stats,
        "audit_path": str(audit_path),
        "audit_sha256": sha256(audit_path),
        "same_server_as_phase_ia": True,
        "same_terminal_data_path_as_phase_ia": True,
        "protected_2026_untouched": True,
        "propfirm_tradability_authorized": False,
        "next_gate": "Phase I-C may use only the news-clean I-B datasets after I-B integrity PASS. 2026 remains sealed.",
    }
    summary_path = outdir / "phase_ib_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
