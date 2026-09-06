#!/usr/bin/env python3
"""Local diagnostics for invalid Guardian Strategy Tester runs.

This module never launches MetaTrader and never changes experiment state. It
inspects immutable run evidence already copied into the local workspace and,
when available, recent portable MT5 tester logs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import runner
import tester


class DiagnosticError(RuntimeError):
    pass


def _decode_log_tail(path: Path, max_bytes: int = 4 * 1024 * 1024) -> str:
    size = path.stat().st_size
    with path.open("rb") as fh:
        if size > max_bytes:
            fh.seek(size - max_bytes)
        raw = fh.read()
    if not raw:
        return ""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", errors="replace")
    sample = raw[:512]
    if sample.count(b"\x00") > max(8, len(sample) // 8):
        return raw.decode("utf-16-le", errors="replace")
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _recent_fatal_lines(config: dict[str, Any], evidence_mtime: float) -> dict[str, Any]:
    root = runner._expand_path(config["mt5_root"])
    candidate_roots = [root / "Tester", root / "MQL5" / "Logs", root / "Logs"]
    log_paths: list[Path] = []
    for base in candidate_roots:
        if not base.exists():
            continue
        for path in base.rglob("*.log"):
            try:
                # Keep a generous window because tester-agent logs can remain open
                # slightly before/after the evidence files are finalized.
                if abs(path.stat().st_mtime - evidence_mtime) <= 6 * 3600:
                    log_paths.append(path)
            except OSError:
                continue

    matches: list[dict[str, str]] = []
    for path in sorted(log_paths, key=lambda p: p.stat().st_mtime):
        try:
            text = _decode_log_tail(path)
        except OSError:
            continue
        for line in text.splitlines():
            if "D037 V101 FATAL" in line:
                matches.append({"log": str(path), "line": line.strip()})

    return {
        "candidate_log_files": len(log_paths),
        "fatal_lines": matches[-20:],
    }


def diagnose_latest_invalid(identifier: str, stage_name: str) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    stage = manifest["stages"].get(stage_name)
    if not stage:
        raise DiagnosticError(f"unknown stage: {stage_name}")

    config = runner.load_config()
    config_errors = tester.validate_test_config(config)
    if config_errors:
        raise DiagnosticError("invalid local config: " + "; ".join(config_errors))

    workspace = runner._expand_path(config["workspace_dir"])
    base = workspace / "runs" / manifest["experiment_id"] / stage_name
    if not base.exists():
        raise DiagnosticError(f"no local run directory exists: {base}")

    candidates = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True)
    for run_dir in candidates:
        for symbol in stage["symbols"]:
            stats_name, trades_name = tester.expected_output_names(manifest, stage_name, symbol)
            stats_path = run_dir / stats_name
            if not stats_path.is_file():
                continue
            try:
                stats = tester.read_semicolon_csv(stats_path)
            except tester.TestError:
                continue
            if not stats:
                continue
            final = stats[-1]
            final_status = final.get("status", "")
            fatal_status = final.get("fatal_status", "")
            if final_status == "FINAL" and not fatal_status:
                continue

            trades_path = run_dir / trades_name
            trade_rows = 0
            trades_encoding = None
            if trades_path.is_file():
                try:
                    trade_rows = len(tester.read_semicolon_csv(trades_path))
                    _, trades_encoding = tester.decode_csv_text(trades_path)
                except tester.TestError:
                    trade_rows = -1

            _, stats_encoding = tester.decode_csv_text(stats_path)
            mtime = max(
                stats_path.stat().st_mtime,
                trades_path.stat().st_mtime if trades_path.is_file() else stats_path.stat().st_mtime,
            )
            counters = {
                key: final.get(key)
                for key in (
                    "bars_seen",
                    "bars_in_stage",
                    "days_initialized",
                    "days_traded",
                    "ambiguous_days",
                    "entry_signals",
                    "trades_opened",
                    "trades_closed",
                    "invalid_price",
                    "invalid_risk",
                    "risk_calc_failures",
                    "pnl_calc_failures",
                    "csv_trade_rows",
                )
            }
            logs = _recent_fatal_lines(config, mtime)
            return {
                "schema_version": 1,
                "status": "INVALID_RUN_DIAGNOSTIC",
                "experiment_id": manifest["experiment_id"],
                "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
                "stage": stage_name,
                "run_dir": str(run_dir),
                "symbol": final.get("symbol") or symbol,
                "final_status": final_status,
                "fatal_status": fatal_status,
                "evidence_mtime_utc": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
                "stats": {
                    "path": str(stats_path),
                    "sha256": runner.sha256_file(stats_path),
                    "encoding": stats_encoding,
                },
                "trades": {
                    "path": str(trades_path) if trades_path.is_file() else None,
                    "sha256": runner.sha256_file(trades_path) if trades_path.is_file() else None,
                    "encoding": trades_encoding,
                    "parsed_rows": trade_rows,
                },
                "counters": counters,
                "mt5_logs": logs,
                "autosync_used": False,
            }

    raise DiagnosticError("no invalid run evidence found in local workspace")


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Diagnose newest invalid Guardian local tester run")
    parser.add_argument("experiment")
    parser.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))
    args = parser.parse_args()
    try:
        result = diagnose_latest_invalid(args.experiment, args.stage)
    except (DiagnosticError, runner.RunnerError, tester.TestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
