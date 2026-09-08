#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PHASE = "phase-ib-xau-dataset"
TF_NAMES = ("M1", "M5")


def run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout, check=False)


def ensure_mt5_module():
    try:
        import MetaTrader5 as mt5  # type: ignore
        return mt5
    except ImportError:
        cp = run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "MetaTrader5"], timeout=300)
        if cp.returncode != 0:
            raise RuntimeError(f"MetaTrader5 package install failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
        import MetaTrader5 as mt5  # type: ignore
        return mt5


def parse_iso_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_server_wall(s: str) -> datetime:
    return datetime.strptime(s, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)


def derive_server_offset_seconds(ia_summary: dict[str, Any]) -> int:
    manifest = ia_summary.get("terminal_manifest", {})
    exported = manifest.get("exported_at_server_time")
    generated = ia_summary.get("generated_at_utc")
    if not exported or not generated:
        raise RuntimeError("Phase I-A summary lacks export/server timestamp provenance")
    server_wall = parse_server_wall(str(exported))
    generated_utc = parse_iso_utc(str(generated))
    raw = (server_wall - generated_utc).total_seconds()
    rounded = int(round(raw / 3600.0) * 3600)
    residual = abs(raw - rounded)
    if residual > 120:
        raise RuntimeError(f"cannot derive stable server offset: raw={raw:.3f}s rounded={rounded}s residual={residual:.3f}s")
    if abs(rounded) > 14 * 3600:
        raise RuntimeError(f"implausible server offset {rounded}s")
    return rounded


def get_open_terminal_processes() -> list[dict[str, Any]]:
    if os.name != "nt":
        raise RuntimeError("Phase I-B MT5 Python extraction is Windows-only")
    ps = (
        "$p=@(Get-CimInstance Win32_Process -Filter \"Name='terminal64.exe'\" | "
        "Select-Object ProcessId,ExecutablePath,CommandLine); $p | ConvertTo-Json -Compress"
    )
    cp = run(["powershell.exe", "-NoProfile", "-Command", ps], timeout=30)
    if cp.returncode != 0:
        raise RuntimeError(f"cannot inspect MT5 processes: {cp.stderr.strip() or cp.stdout.strip()}")
    text = cp.stdout.strip()
    if not text:
        return []
    obj = json.loads(text)
    return obj if isinstance(obj, list) else [obj]


def norm_path(s: str | None) -> str:
    if not s:
        return ""
    return os.path.normcase(os.path.normpath(str(s)))


def month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=timezone.utc)


def next_month(dt: datetime) -> datetime:
    if dt.month == 12:
        return datetime(dt.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(dt.year, dt.month + 1, 1, tzinfo=timezone.utc)


def shifted_server_time(utc_epoch: int, offset_seconds: int) -> tuple[int, str]:
    server_epoch = int(utc_epoch) + int(offset_seconds)
    server_time = datetime.fromtimestamp(server_epoch, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
    return server_epoch, server_time


def resolve_symbol(mt5, root: str) -> str:
    if mt5.symbol_select(root, True):
        return root
    syms = mt5.symbols_get()
    if syms is None:
        raise RuntimeError(f"symbols_get failed: {mt5.last_error()}")
    matches = sorted({s.name for s in syms if str(s.name).startswith(root)})
    if len(matches) != 1:
        raise RuntimeError(f"symbol root {root} resolved to {len(matches)} candidates: {matches[:20]}")
    if not mt5.symbol_select(matches[0], True):
        raise RuntimeError(f"symbol_select({matches[0]}) failed: {mt5.last_error()}")
    return matches[0]


def fetch_month(mt5, symbol: str, timeframe: int, utc_from: datetime, utc_to_exclusive: datetime, retries: int = 36):
    last_error = None
    for attempt in range(1, retries + 1):
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, utc_to_exclusive.timestamp() - 1)
        if rates is not None and len(rates) > 0:
            return rates
        last_error = mt5.last_error()
        time.sleep(min(5, 0.5 + attempt * 0.15))
    raise RuntimeError(
        f"copy_rates_range returned no data after {retries} attempts symbol={symbol} "
        f"from={utc_from.isoformat()} to={utc_to_exclusive.isoformat()} last_error={last_error}"
    )


def export_timeframe(mt5, symbol: str, tf_name: str, tf_value: int, out_path: Path, offset_seconds: int, progress_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    rows = 0
    first_epoch = None
    last_epoch = None
    months_done = 0
    total_months = 24 * len(TF_NAMES)

    server_cursor = month_start(2024, 1)
    server_end = month_start(2026, 1)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        while server_cursor < server_end:
            server_next = next_month(server_cursor)
            utc_from = server_cursor.timestamp() - offset_seconds
            utc_to = server_next.timestamp() - offset_seconds
            utc_from_dt = datetime.fromtimestamp(utc_from, tz=timezone.utc)
            utc_to_dt = datetime.fromtimestamp(utc_to, tz=timezone.utc)
            rates = fetch_month(mt5, symbol, tf_value, utc_from_dt, utc_to_dt)
            prev_server_epoch = None
            for r in rates:
                utc_epoch = int(r["time"])
                server_epoch, server_time = shifted_server_time(utc_epoch, offset_seconds)
                if not (server_cursor.timestamp() <= server_epoch < server_next.timestamp()):
                    continue
                if prev_server_epoch is not None and server_epoch <= prev_server_epoch:
                    raise RuntimeError(f"non-increasing {tf_name} timestamps within {server_cursor:%Y-%m}")
                prev_server_epoch = server_epoch
                if first_epoch is None:
                    first_epoch = server_epoch
                last_epoch = server_epoch
                w.writerow({
                    "symbol": symbol,
                    "timeframe": tf_name,
                    "server_time": server_time,
                    "server_epoch": server_epoch,
                    "open": repr(float(r["open"])),
                    "high": repr(float(r["high"])),
                    "low": repr(float(r["low"])),
                    "close": repr(float(r["close"])),
                    "tick_volume": int(r["tick_volume"]),
                    "spread": int(r["spread"]),
                    "real_volume": int(r["real_volume"]),
                })
                rows += 1
            months_done += 1
            progress = {
                "schema": 1,
                "phase": "I-B-AUTO",
                "timeframe": tf_name,
                "month": server_cursor.strftime("%Y-%m"),
                "completed": months_done + (0 if tf_name == "M1" else 24),
                "total": total_months,
                "rows_written": rows,
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            progress_path.parent.mkdir(parents=True, exist_ok=True)
            progress_path.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            server_cursor = server_next

    if rows == 0:
        raise RuntimeError(f"empty {tf_name} export")
    return {"rows": rows, "first_epoch": first_epoch, "last_epoch": last_epoch}


def write_manifest(path: Path, ia_summary: dict[str, Any], terminal_info, account_info, symbol: str, m1: dict[str, Any], m5: dict[str, Any], offset_seconds: int):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = {
        "schema": "1",
        "phase": "I-B",
        "symbol": symbol,
        "symbol_root": "XAUUSD",
        "server": str(account_info.server),
        "company": str(account_info.company),
        "terminal_path": str(terminal_info.path),
        "terminal_data_path": str(terminal_info.data_path),
        "terminal_commondata_path": str(terminal_info.commondata_path),
        "from_server_time": "2024.01.01 00:00:00",
        "to_server_time_exclusive": "2026.01.01 00:00:00",
        "exported_at_server_time": datetime.fromtimestamp(time.time() + offset_seconds, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S"),
        "python_api_utc_to_server_offset_seconds": str(offset_seconds),
        "python_api_source": "MetaTrader5.copy_rates_range",
        "m1_rows": str(m1["rows"]),
        "m1_first_epoch": str(m1["first_epoch"]),
        "m1_last_epoch": str(m1["last_epoch"]),
        "m5_rows": str(m5["rows"]),
        "m5_first_epoch": str(m5["first_epoch"]),
        "m5_last_epoch": str(m5["last_epoch"]),
    }
    path.write_text("".join(f"{k}={v}\n" for k, v in lines.items()), encoding="utf-8")


def publish(publisher: Path, status: str, summary: str, artifacts: list[Path], cwd: Path):
    cmd = [sys.executable, str(publisher), "--phase", PHASE, "--status", status, "--summary", summary]
    for p in artifacts:
        if p.exists():
            cmd += ["--artifact", str(p)]
    cp = run(cmd, cwd=cwd, timeout=300)
    if cp.returncode != 0:
        raise RuntimeError(f"publication failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ia-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ia_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_ib_v1")
    ap.add_argument("--terminal-exe", default=r"D:\MT5_FundedNext\terminal64.exe")
    ap.add_argument("--deploy", default=os.environ.get("GUARDIAN_DEPLOY_ROOT", r"D:\MT5_Backtests\guardian-autonomous-main"))
    ap.add_argument("--progress-file", default=os.path.join(os.environ.get("GUARDIAN_AUTONOMOUS_ROOT", r"D:\MT5_Backtests\Research\Autonomous"), "progress", "PHASE-IB-AUTO-PYTHON-EXTRACT.json"))
    args = ap.parse_args()

    deploy = Path(args.deploy)
    ia_dir = Path(args.ia_dir)
    out = Path(args.output_dir)
    progress_path = Path(args.progress_file)
    ia_summary_path = ia_dir / "phase_ia_summary.json"
    ia_mask = ia_dir / "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    builder = deploy / "research" / "phenomenon_discovery" / "build_xau_news_clean_dataset_v1_00.py"
    checker = deploy / "research" / "phenomenon_discovery" / "check_xau_news_clean_dataset_v1_00.py"
    publisher = deploy / "research" / "phenomenon_discovery" / "publish_phase_result_v1_00.py"
    for p in (ia_summary_path, ia_mask, builder, checker, publisher):
        if not p.exists():
            raise RuntimeError(f"missing Phase I-B dependency: {p}")

    out.mkdir(parents=True, exist_ok=True)
    ia_summary = json.loads(ia_summary_path.read_text(encoding="utf-8"))
    ia_terminal = ia_summary.get("terminal_manifest", {})
    if ia_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-A provenance does not protect 2026")
    offset_seconds = derive_server_offset_seconds(ia_summary)

    terminal_exe = Path(args.terminal_exe)
    if not terminal_exe.exists():
        raise RuntimeError(f"canonical terminal exe missing: {terminal_exe}")
    procs = get_open_terminal_processes()
    if len(procs) != 1:
        raise RuntimeError(f"Phase I-B auto requires exactly one open terminal64.exe; found {len(procs)}")
    p0 = procs[0]
    exe_path = norm_path(p0.get("ExecutablePath"))
    if exe_path != norm_path(str(terminal_exe)):
        raise RuntimeError(f"sole open MT5 is not canonical FundedNext terminal: {p0.get('ExecutablePath')}")
    original_pid = int(p0.get("ProcessId"))

    mt5 = ensure_mt5_module()
    publish(publisher, "RUNNING", f"Phase I-B automatic Python extraction starting from sole open MT5 PID {original_pid}; no GUI script required; 2026 protected.", [], deploy)
    initialized = False
    try:
        initialized = bool(mt5.initialize(str(terminal_exe), timeout=60000, portable=True))
        if not initialized:
            raise RuntimeError(f"MetaTrader5.initialize failed: {mt5.last_error()}")
        after = get_open_terminal_processes()
        if len(after) != 1 or int(after[0].get("ProcessId")) != original_pid:
            raise RuntimeError("MT5 process set changed during Python initialize; refusing to use a newly launched/alternate terminal")
        ti = mt5.terminal_info()
        ai = mt5.account_info()
        if ti is None or ai is None:
            raise RuntimeError(f"terminal/account info unavailable: {mt5.last_error()}")
        if str(ai.server) != str(ia_terminal.get("server")):
            raise RuntimeError(f"server mismatch I-A={ia_terminal.get('server')} Python={ai.server}")
        if norm_path(str(ti.path)) != norm_path(str(ia_terminal.get("terminal_path"))):
            raise RuntimeError(f"terminal_path mismatch I-A={ia_terminal.get('terminal_path')} Python={ti.path}")
        if norm_path(str(ti.data_path)) != norm_path(str(ia_terminal.get("terminal_data_path"))):
            raise RuntimeError(f"data_path mismatch I-A={ia_terminal.get('terminal_data_path')} Python={ti.data_path}")

        symbol = resolve_symbol(mt5, "XAUUSD")
        raw_m1 = out / "xauusd_m1_2024_2025_raw.csv"
        raw_m5 = out / "xauusd_m5_2024_2025_raw.csv"
        manifest = out / "xauusd_history_terminal_manifest.txt"
        m1 = export_timeframe(mt5, symbol, "M1", mt5.TIMEFRAME_M1, raw_m1, offset_seconds, progress_path)
        m5 = export_timeframe(mt5, symbol, "M5", mt5.TIMEFRAME_M5, raw_m5, offset_seconds, progress_path)
        write_manifest(manifest, ia_summary, ti, ai, symbol, m1, m5, offset_seconds)
    finally:
        if initialized:
            mt5.shutdown()

    cp = run([sys.executable, str(builder), "--raw-m1", str(out / "xauusd_m1_2024_2025_raw.csv"), "--raw-m5", str(out / "xauusd_m5_2024_2025_raw.csv"), "--ib-terminal-manifest", str(out / "xauusd_history_terminal_manifest.txt"), "--ia-summary", str(ia_summary_path), "--ia-mask", str(ia_mask), "--output-dir", str(out)], cwd=deploy, timeout=900)
    if cp.returncode != 0:
        raise RuntimeError(f"I-B news-clean builder failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-4000:]}")
    cp = run([sys.executable, str(checker), "--input-dir", str(out), "--ia-mask", str(ia_mask)], cwd=deploy, timeout=900)
    if cp.returncode != 0:
        raise RuntimeError(f"I-B integrity checker failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-6000:]}")

    summary = out / "phase_ib_summary.json"
    integrity = out / "phase_ib_integrity.json"
    audit = out / "phase_ib_news_exclusion_audit.csv"
    manifest = out / "xauusd_history_terminal_manifest.txt"
    data = json.loads(integrity.read_text(encoding="utf-8"))
    if data.get("status") != "PASS":
        raise RuntimeError("I-B checker returned non-PASS integrity despite exit code 0")
    publish(
        publisher,
        "PASS",
        "Phase I-B PASS via automatic MetaTrader5 Python API on the sole pre-existing FundedNext terminal. M1/M5 2024-2025 exported without GUI script; UTC bars were mapped into the exact Phase I-A server-time coordinate using the I-A export-proven offset; conservative +/-5m news mask applied; 2026 untouched.",
        [summary, integrity, audit, manifest],
        deploy,
    )
    progress_path.write_text(json.dumps({"schema": 1, "phase": "I-B-AUTO", "completed": 48, "total": 48, "status": "PASS", "updated_at_utc": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "phase": "I-B", "server": data.get("terminal_server"), "offset_seconds": offset_seconds}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PHASE I-B AUTO FAIL: {exc}", file=sys.stderr)
        raise
