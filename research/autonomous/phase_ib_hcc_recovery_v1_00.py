#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE = "phase-ib-xau-dataset"
YEARS = (2024, 2025)


def run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=False)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_progress(path: Path, completed: int, total: int, stage: str, **extra: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "schema": 1,
        "phase": "I-B-HCC-RECOVERY",
        "completed": completed,
        "total": total,
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def ensure_hcc_reader():
    try:
        from hcc_reader import read_hcc  # type: ignore
        return read_hcc
    except ImportError:
        cp = run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "hcc-reader"], timeout=300)
        if cp.returncode != 0:
            raise RuntimeError(f"hcc-reader install failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
        from hcc_reader import read_hcc  # type: ignore
        return read_hcc


def norm(s: str) -> str:
    return os.path.normcase(os.path.normpath(str(s)))


def load_policy(path: Path) -> dict[str, Any]:
    p = json.loads(path.read_text(encoding="utf-8"))
    if p.get("schema") != 1 or p.get("phase") != "I-B-HCC-RECOVERY":
        raise RuntimeError("invalid HCC recovery policy")
    if p.get("protected_2026_untouched") is not True:
        raise RuntimeError("policy does not seal 2026")
    return p


def dt_to_epoch(value: Any) -> int:
    # hcc-reader returns pandas Timestamp/datetime; retain its underlying Unix-second value
    # directly as the MT5 server-time datetime coordinate. No offset transformation here.
    if hasattr(value, "timestamp"):
        return int(value.timestamp())
    s = str(value)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def read_year(read_hcc, path: Path, year: int) -> list[dict[str, Any]]:
    df = read_hcc(str(path))
    if df is None or len(df) == 0:
        raise RuntimeError(f"empty HCC parse for {path}")
    required = {"datetime", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    cols = set(str(c) for c in df.columns)
    missing = sorted(required - cols)
    if missing:
        raise RuntimeError(f"HCC parser missing columns {missing} for {path}")
    out: list[dict[str, Any]] = []
    for row in df.itertuples(index=False):
        d = row._asdict()
        epoch = dt_to_epoch(d["datetime"])
        wall = datetime.fromtimestamp(epoch, tz=timezone.utc)
        if wall.year != year:
            raise RuntimeError(f"out-of-year HCC row in {path}: {wall.isoformat()}")
        o, h, l, c = map(float, (d["open"], d["high"], d["low"], d["close"]))
        if min(o, h, l, c) <= 0 or h < max(o, c) or l > min(o, c) or h < l:
            raise RuntimeError(f"invalid HCC OHLC at {epoch}")
        out.append({
            "symbol": "XAUUSD",
            "timeframe": "M1",
            "server_time": wall.strftime("%Y.%m.%d %H:%M:%S"),
            "server_epoch": epoch,
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "tick_volume": int(d["tick_volume"]),
            "spread": int(d["spread"]),
            "real_volume": int(d["real_volume"]),
        })
    return out


def validate_m1(rows: list[dict[str, Any]]) -> None:
    if len(rows) < 500000:
        raise RuntimeError(f"M1 coverage too small before checker: {len(rows)}")
    prev = None
    seen = set()
    for r in rows:
        t = int(r["server_epoch"])
        if t in seen:
            raise RuntimeError(f"duplicate M1 timestamp {t}")
        seen.add(t)
        if prev is not None and t <= prev:
            raise RuntimeError(f"non-increasing M1 timestamp {t} <= {prev}")
        if t % 60:
            raise RuntimeError(f"M1 timestamp not minute-aligned: {t}")
        prev = t


def aggregate_m5(m1: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    bucket: list[dict[str, Any]] = []
    current = None

    def flush(items: list[dict[str, Any]], key: int) -> None:
        if not items:
            return
        first, last = items[0], items[-1]
        wall = datetime.fromtimestamp(key, tz=timezone.utc)
        out.append({
            "symbol": "XAUUSD",
            "timeframe": "M5",
            "server_time": wall.strftime("%Y.%m.%d %H:%M:%S"),
            "server_epoch": key,
            "open": float(first["open"]),
            "high": max(float(x["high"]) for x in items),
            "low": min(float(x["low"]) for x in items),
            "close": float(last["close"]),
            "tick_volume": sum(int(x["tick_volume"]) for x in items),
            "spread": int(last["spread"]),
            "real_volume": sum(int(x["real_volume"]) for x in items),
        })

    for r in m1:
        key = (int(r["server_epoch"]) // 300) * 300
        if current is None:
            current = key
        if key != current:
            flush(bucket, current)
            bucket = []
            current = key
        bucket.append(r)
    if current is not None:
        flush(bucket, current)
    if len(out) < 100000:
        raise RuntimeError(f"M5 coverage too small before checker: {len(out)}")
    m1_ts = {int(x["server_epoch"]) for x in m1}
    missing = sum(1 for x in out if int(x["server_epoch"]) not in m1_ts)
    if missing:
        raise RuntimeError(f"derived M5 opens missing exact M1 timestamp: {missing}")
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
        raise RuntimeError("policy/I-A terminal data path mismatch")

    allowed = [Path(x) for x in policy.get("allowed_source_files", [])]
    expected = [Path(policy["canonical_terminal_data_path"]) / "Bases" / policy["canonical_server"] / "history" / "XAUUSD" / f"{y}.hcc" for y in YEARS]
    if [norm(x) for x in allowed] != [norm(x) for x in expected]:
        raise RuntimeError("policy allowed HCC files do not exactly match frozen 2024/2025 canonical paths")
    for p in allowed:
        if "2026.hcc" in norm(p):
            raise RuntimeError("protected 2026 path present in allowed sources")
        if not p.exists():
            raise RuntimeError(f"missing canonical HCC file {p}")

    out.mkdir(parents=True, exist_ok=True)
    write_progress(progress, 0, 6, "install_parser")
    read_hcc = ensure_hcc_reader()
    publish(publisher, "RUNNING", "Phase I-B read-only HCC recovery started from exact FundedNext-Server 2 XAUUSD 2024/2025 files; 2026 sealed.", [policy_path], deploy)

    all_m1: list[dict[str, Any]] = []
    source_files = []
    for i, (year, p) in enumerate(zip(YEARS, allowed), start=1):
        write_progress(progress, i - 1, 6, f"parse_{year}", source=str(p))
        rows = read_year(read_hcc, p, year)
        all_m1.extend(rows)
        source_files.append({"year": year, "path": str(p), "sha256": sha256(p), "rows": len(rows), "size_bytes": p.stat().st_size})
        write_progress(progress, i, 6, f"parsed_{year}", rows=len(rows))

    all_m1.sort(key=lambda x: int(x["server_epoch"]))
    validate_m1(all_m1)
    raw_m1 = out / "xauusd_m1_2024_2025_raw.csv"
    raw_m5 = out / "xauusd_m5_2024_2025_raw.csv"
    write_csv(raw_m1, all_m1)
    write_progress(progress, 3, 6, "aggregate_m5", m1_rows=len(all_m1))
    m5 = aggregate_m5(all_m1)
    write_csv(raw_m5, m5)

    ib_manifest = out / "xauusd_history_terminal_manifest.txt"
    ib_manifest.write_text(
        "schema=1\n"
        "phase=I-B\n"
        "symbol=XAUUSD\n"
        "symbol_root=XAUUSD\n"
        f"server={manifest.get('server')}\n"
        f"company={manifest.get('company')}\n"
        f"terminal_path={manifest.get('terminal_path')}\n"
        f"terminal_data_path={manifest.get('terminal_data_path')}\n"
        f"terminal_commondata_path={manifest.get('terminal_commondata_path')}\n"
        "from_server_time=2024.01.01 00:00:00\n"
        "to_server_time_exclusive=2026.01.01 00:00:00\n"
        "source_method=read_only_canonical_hcc_m1\n"
        "timestamp_semantics=direct_mt5_server_datetime_coordinate_no_offset\n"
        f"m1_rows={len(all_m1)}\n"
        f"m5_rows={len(m5)}\n",
        encoding="utf-8",
    )
    source_manifest = out / "phase_ib_hcc_source_manifest.json"
    source_manifest.write_text(json.dumps({
        "schema": 1,
        "phase": "I-B-HCC-RECOVERY",
        "server": manifest.get("server"),
        "terminal_data_path": manifest.get("terminal_data_path"),
        "symbol": "XAUUSD",
        "files": source_files,
        "m1_rows": len(all_m1),
        "m5_rows": len(m5),
        "policy_sha256": sha256(policy_path),
        "protected_2026_untouched": True,
        "propfirm_tradability_authorized": False,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_progress(progress, 4, 6, "build_news_clean")
    cp = run([sys.executable, str(builder), "--raw-m1", str(raw_m1), "--raw-m5", str(raw_m5), "--ib-terminal-manifest", str(ib_manifest), "--ia-summary", str(ia_summary_path), "--ia-mask", str(ia_mask), "--output-dir", str(out)], cwd=deploy, timeout=1200)
    if cp.returncode:
        raise RuntimeError(f"I-B builder failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-6000:]}")

    write_progress(progress, 5, 6, "integrity_check")
    cp = run([sys.executable, str(checker), "--input-dir", str(out), "--ia-mask", str(ia_mask)], cwd=deploy, timeout=1200)
    if cp.returncode:
        raise RuntimeError(f"I-B checker failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-8000:]}")

    summary = out / "phase_ib_summary.json"
    integrity = out / "phase_ib_integrity.json"
    audit = out / "phase_ib_news_exclusion_audit.csv"
    integ = json.loads(integrity.read_text(encoding="utf-8"))
    if integ.get("status") != "PASS" or integ.get("protected_2026_untouched") is not True:
        raise RuntimeError("I-B integrity artifact is not protected PASS")

    write_progress(progress, 6, 6, "PASS", status="PASS", m1_rows=len(all_m1), m5_rows=len(m5))
    publish(
        publisher,
        "PASS",
        f"Phase I-B PASS via read-only canonical HCC recovery: M1={len(all_m1)} M5={len(m5)} from FundedNext-Server 2 XAUUSD 2024/2025 only; frozen +/-5m news mask applied; existing integrity checker PASS; 2026 untouched.",
        [summary, integrity, audit, ib_manifest, source_manifest, policy_path],
        deploy,
    )
    print(json.dumps({"status": "PASS", "m1_rows": len(all_m1), "m5_rows": len(m5), "protected_2026_untouched": True}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PHASE I-B HCC RECOVERY FAIL: {exc}", file=sys.stderr)
        raise
