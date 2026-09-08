#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE = "phase-ib-xau-dataset"
YEARS = (2024, 2025)
RECORD_SIZE = 60


def run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm(s: str) -> str:
    return os.path.normcase(os.path.normpath(str(s)))


def write_progress(path: Path, completed: int, total: int, stage: str, **extra: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "phase": "I-B-HCC-RECOVERY",
        "completed": completed,
        "total": total,
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_policy(path: Path) -> dict[str, Any]:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("schema") != 1 or p.get("phase") != "I-B-HCC-RECOVERY" or p.get("protected_2026_untouched") is not True:
        raise RuntimeError("invalid HCC recovery policy")
    return p


def year_bounds(year: int) -> tuple[int, int]:
    a = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp())
    b = int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp())
    return a, b


def decode_record(data: bytes, pos: int, year: int) -> dict[str, Any] | None:
    if pos < 0 or pos + RECORD_SIZE > len(data):
        return None
    start, end = year_bounds(year)
    try:
        ts = struct.unpack_from("<q", data, pos)[0]
        if ts < start or ts >= end or ts % 60 != 0:
            return None
        o, h, l, c = struct.unpack_from("<dddd", data, pos + 8)
        if not all(math.isfinite(x) for x in (o, h, l, c)):
            return None
        if not (100.0 < o < 100000.0 and 100.0 < h < 100000.0 and 100.0 < l < 100000.0 and 100.0 < c < 100000.0):
            return None
        if h < max(o, c) or l > min(o, c) or h < l:
            return None
        tick_volume = struct.unpack_from("<q", data, pos + 40)[0]
        spread = struct.unpack_from("<i", data, pos + 48)[0]
        real_volume = struct.unpack_from("<q", data, pos + 52)[0]
        if tick_volume < 0 or tick_volume > 10_000_000_000:
            return None
        if spread < -1 or spread > 10_000_000:
            return None
        if real_volume < 0 or real_volume > 10_000_000_000_000:
            return None
    except (struct.error, OverflowError):
        return None
    return {
        "symbol": "XAUUSD",
        "timeframe": "M1",
        "server_time": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S"),
        "server_epoch": ts,
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "tick_volume": int(tick_volume),
        "spread": int(spread),
        "real_volume": int(real_volume),
    }


def parse_hcc(path: Path, year: int, progress: Path, progress_base: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = path.read_bytes()
    if len(data) < 512:
        raise RuntimeError(f"HCC file too small: {path}")
    header_size = struct.unpack_from("<I", data, 0)[0]
    if not (128 <= header_size <= 8192):
        raise RuntimeError(f"implausible HCC header size/magic {header_size} in {path}")

    records: list[dict[str, Any]] = []
    seen: set[int] = set()
    pos = int(header_size)
    n = len(data)
    blocks = 0
    scan_checkpoint = pos

    while pos + RECORD_SIZE <= n:
        found = None
        search_end = min(n - RECORD_SIZE, pos + 250_000)
        i = pos
        while i <= search_end:
            r = decode_record(data, i, year)
            if r is not None:
                nxt = decode_record(data, i + RECORD_SIZE, year)
                if nxt is not None:
                    dt = int(nxt["server_epoch"]) - int(r["server_epoch"])
                    if 0 <= dt <= 14 * 86400:
                        found = i
                        break
            i += 1
        if found is None:
            pos = search_end + 1
            if pos - scan_checkpoint >= 2_000_000:
                write_progress(progress, progress_base, 7, f"scan_{year}", bytes_scanned=pos, file_bytes=n, records=len(records))
                scan_checkpoint = pos
            continue

        blocks += 1
        pos = found
        previous = None
        while pos + RECORD_SIZE <= n:
            r = decode_record(data, pos, year)
            if r is None:
                break
            t = int(r["server_epoch"])
            if previous is not None:
                delta = t - previous
                if delta < 0 or delta > 14 * 86400:
                    break
            previous = t
            if t not in seen:
                records.append(r)
                seen.add(t)
            pos += RECORD_SIZE
        pos += 1

    records.sort(key=lambda x: int(x["server_epoch"]))
    meta = {
        "year": year,
        "path": str(path),
        "sha256": sha256(path),
        "size_bytes": len(data),
        "header_size": header_size,
        "blocks_found": blocks,
        "rows": len(records),
    }
    if len(records) < 100000:
        raise RuntimeError(f"HCC parser recovered too few rows for {year}: {len(records)} meta={meta}")
    return records, meta


def validate_m1(rows: list[dict[str, Any]]) -> None:
    if len(rows) < 500000:
        raise RuntimeError(f"M1 total coverage too small before checker: {len(rows)}")
    prev = None
    for r in rows:
        t = int(r["server_epoch"])
        if prev is not None and t <= prev:
            raise RuntimeError(f"non-increasing/duplicate M1 timestamp {t} <= {prev}")
        prev = t


def aggregate_m5(m1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    current_key = None
    bucket: list[dict[str, Any]] = []

    def flush(key: int, items: list[dict[str, Any]]) -> None:
        if not items:
            return
        wall = datetime.fromtimestamp(key, tz=timezone.utc)
        out.append({
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "server_time": wall.strftime("%Y.%m.%d %H:%M:%S"),
            "server_epoch": key,
            "open": float(items[0]["open"]),
            "high": max(float(x["high"]) for x in items),
            "low": min(float(x["low"]) for x in items),
            "close": float(items[-1]["close"]),
            "tick_volume": sum(int(x["tick_volume"]) for x in items),
            "spread": int(items[-1]["spread"]),
            "real_volume": sum(int(x["real_volume"]) for x in items),
        })

    for r in m1:
        key = (int(r["server_epoch"]) // 300) * 300
        if current_key is None:
            current_key = key
        if key != current_key:
            flush(current_key, bucket)
            bucket = []
            current_key = key
        bucket.append(r)
    if current_key is not None:
        flush(current_key, bucket)
    if len(out) < 100000:
        raise RuntimeError(f"M5 total coverage too small before checker: {len(out)}")
    m1_ts = {int(x["server_epoch"]) for x in m1}
    bad = sum(1 for x in out if int(x["server_epoch"]) not in m1_ts)
    if bad:
        raise RuntimeError(f"derived M5 exact-open timestamps absent from M1: {bad}")
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def publish(publisher: Path, status: str, summary: str, artifacts: list[Path], cwd: Path) -> None:
    cmd = [sys.executable, str(publisher), "--phase", PHASE, "--status", status, "--summary", summary]
    for p in artifacts:
        if p.exists():
            cmd += ["--artifact", str(p)]
    cp = run(cmd, cwd=cwd, timeout=300)
    if cp.returncode:
        raise RuntimeError(f"publication failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ia-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--deploy", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--progress-file", required=True)
    args = ap.parse_args()

    deploy = Path(args.deploy)
    ia_dir = Path(args.ia_dir)
    out = Path(args.output_dir)
    policy_path = Path(args.policy)
    progress = Path(args.progress_file)
    policy = load_policy(policy_path)

    ia_summary_path = ia_dir / "phase_ia_summary.json"
    ia_mask = ia_dir / "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    builder = deploy / "research" / "phenomenon_discovery" / "build_xau_news_clean_dataset_v1_00.py"
    checker = deploy / "research" / "phenomenon_discovery" / "check_xau_news_clean_dataset_v1_00.py"
    publisher = deploy / "research" / "phenomenon_discovery" / "publish_phase_result_v1_00.py"
    for p in (ia_summary_path, ia_mask, builder, checker, publisher, policy_path):
        if not p.exists():
            raise RuntimeError(f"missing dependency {p}")

    ia = json.loads(ia_summary_path.read_text(encoding="utf-8"))
    manifest = ia.get("terminal_manifest", {})
    if ia.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-A does not prove 2026 sealed")
    if manifest.get("server") != policy.get("canonical_server"):
        raise RuntimeError("policy/I-A server mismatch")
    if norm(manifest.get("terminal_data_path", "")) != norm(policy.get("canonical_terminal_data_path", "")):
        raise RuntimeError("policy/I-A terminal path mismatch")

    allowed = [Path(x) for x in policy.get("allowed_source_files", [])]
    expected = [Path(policy["canonical_terminal_data_path"]) / "Bases" / policy["canonical_server"] / "history" / "XAUUSD" / f"{y}.hcc" for y in YEARS]
    if [norm(x) for x in allowed] != [norm(x) for x in expected]:
        raise RuntimeError("allowed HCC paths differ from frozen exact 2024/2025 paths")
    for p in allowed:
        if "2026.hcc" in norm(p):
            raise RuntimeError("protected 2026 path would be opened")
        if not p.exists():
            raise RuntimeError(f"missing HCC source {p}")

    out.mkdir(parents=True, exist_ok=True)
    publish(publisher, "RUNNING", "Phase I-B deterministic built-in HCC recovery r2 started on exact FundedNext-Server 2 XAUUSD 2024/2025 files only; 2026 sealed.", [policy_path], deploy)
    write_progress(progress, 0, 7, "parse_2024")

    m1_2024, meta24 = parse_hcc(allowed[0], 2024, progress, 0)
    write_progress(progress, 1, 7, "parse_2025", rows_2024=len(m1_2024))
    m1_2025, meta25 = parse_hcc(allowed[1], 2025, progress, 1)
    all_m1 = sorted(m1_2024 + m1_2025, key=lambda x: int(x["server_epoch"]))
    validate_m1(all_m1)
    write_progress(progress, 2, 7, "write_m1", m1_rows=len(all_m1))

    raw_m1 = out / "xauusd_m1_2024_2025_raw.csv"
    raw_m5 = out / "xauusd_m5_2024_2025_raw.csv"
    write_csv(raw_m1, all_m1)
    write_progress(progress, 3, 7, "aggregate_m5")
    m5 = aggregate_m5(all_m1)
    write_csv(raw_m5, m5)

    ib_manifest = out / "xauusd_history_terminal_manifest.txt"
    ib_manifest.write_text(
        "schema=1\nphase=I-B\nsymbol=XAUUSD\nsymbol_root=XAUUSD\n"
        f"server={manifest.get('server')}\ncompany={manifest.get('company')}\n"
        f"terminal_path={manifest.get('terminal_path')}\nterminal_data_path={manifest.get('terminal_data_path')}\n"
        f"terminal_commondata_path={manifest.get('terminal_commondata_path')}\n"
        "from_server_time=2024.01.01 00:00:00\nto_server_time_exclusive=2026.01.01 00:00:00\n"
        "source_method=read_only_canonical_hcc_m1_builtin_parser\n"
        "timestamp_semantics=direct_mt5_server_datetime_coordinate_no_offset\n"
        f"m1_rows={len(all_m1)}\nm5_rows={len(m5)}\n",
        encoding="utf-8",
    )
    source_manifest = out / "phase_ib_hcc_source_manifest.json"
    source_manifest.write_text(json.dumps({
        "schema": 1,
        "phase": "I-B-HCC-RECOVERY",
        "parser_version": "1.01-built-in",
        "server": manifest.get("server"),
        "terminal_data_path": manifest.get("terminal_data_path"),
        "symbol": "XAUUSD",
        "files": [meta24, meta25],
        "m1_rows": len(all_m1),
        "m5_rows": len(m5),
        "policy_sha256": sha256(policy_path),
        "protected_2026_untouched": True,
        "propfirm_tradability_authorized": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_progress(progress, 4, 7, "build_news_clean")
    cp = run([sys.executable, str(builder), "--raw-m1", str(raw_m1), "--raw-m5", str(raw_m5), "--ib-terminal-manifest", str(ib_manifest), "--ia-summary", str(ia_summary_path), "--ia-mask", str(ia_mask), "--output-dir", str(out)], cwd=deploy, timeout=1200)
    if cp.returncode:
        raise RuntimeError(f"I-B builder failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-6000:]}")

    write_progress(progress, 5, 7, "integrity_check")
    cp = run([sys.executable, str(checker), "--input-dir", str(out), "--ia-mask", str(ia_mask)], cwd=deploy, timeout=1200)
    if cp.returncode:
        raise RuntimeError(f"I-B checker failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-8000:]}")

    summary = out / "phase_ib_summary.json"
    integrity = out / "phase_ib_integrity.json"
    audit = out / "phase_ib_news_exclusion_audit.csv"
    integ = json.loads(integrity.read_text(encoding="utf-8"))
    if integ.get("status") != "PASS" or integ.get("protected_2026_untouched") is not True:
        raise RuntimeError("I-B integrity artifact is not protected PASS")

    write_progress(progress, 7, 7, "PASS", status="PASS", m1_rows=len(all_m1), m5_rows=len(m5))
    publish(publisher, "PASS", f"Phase I-B PASS via built-in read-only HCC parser: M1={len(all_m1)} M5={len(m5)} from exact FundedNext-Server 2 XAUUSD 2024/2025 HCC only; frozen news mask applied; integrity PASS; 2026 untouched.", [summary, integrity, audit, ib_manifest, source_manifest, policy_path], deploy)
    print(json.dumps({"status": "PASS", "m1_rows": len(all_m1), "m5_rows": len(m5), "protected_2026_untouched": True}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PHASE I-B HCC RECOVERY v1.01 FAIL: {exc}", file=sys.stderr)
        raise
