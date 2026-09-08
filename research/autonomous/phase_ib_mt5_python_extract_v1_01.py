#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
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
            raise RuntimeError(f"MetaTrader5 install failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")
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
        raise RuntimeError("Phase I-A lacks server/UTC timestamp provenance")
    raw = (parse_server_wall(str(exported)) - parse_iso_utc(str(generated))).total_seconds()
    rounded = int(round(raw / 3600.0) * 3600)
    if abs(raw - rounded) > 120 or abs(rounded) > 14 * 3600:
        raise RuntimeError(f"unstable/implausible I-A server offset raw={raw:.3f}s rounded={rounded}s")
    return rounded


def get_open_terminal_processes() -> list[dict[str, Any]]:
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
    return os.path.normcase(os.path.normpath(str(s))) if s else ""


def month_start(year: int, month: int) -> datetime:
    return datetime(year, month, 1, tzinfo=timezone.utc)


def next_month(dt: datetime) -> datetime:
    return datetime(dt.year + (1 if dt.month == 12 else 0), 1 if dt.month == 12 else dt.month + 1, 1, tzinfo=timezone.utc)


def resolve_symbol(mt5, root: str) -> str:
    if mt5.symbol_select(root, True):
        return root
    syms = mt5.symbols_get()
    if syms is None:
        raise RuntimeError(f"symbols_get failed: {mt5.last_error()}")
    matches = sorted({str(s.name) for s in syms if str(s.name).startswith(root)})
    if len(matches) != 1 or not mt5.symbol_select(matches[0], True):
        raise RuntimeError(f"symbol root {root} ambiguous/unavailable: {matches[:20]}")
    return matches[0]


def fetch_month(mt5, symbol: str, timeframe: int, utc_from: datetime, utc_to_exclusive: datetime, retries: int = 24):
    # v1.00 mixed a datetime date_from with a floating-point Unix timestamp date_to.
    # The MT5 Python API contract is datetime/int; use timezone-aware datetimes for BOTH ends.
    date_to = utc_to_exclusive - timedelta(seconds=1)
    last_error = None
    for attempt in range(1, retries + 1):
        rates = mt5.copy_rates_range(symbol, timeframe, utc_from, date_to)
        if rates is not None and len(rates) > 0:
            return rates
        last_error = mt5.last_error()
        # Prime the currently selected symbol/timeframe before retrying old history.
        try:
            mt5.copy_rates_from_pos(symbol, timeframe, 0, 512)
        except Exception:
            pass
        time.sleep(min(5.0, 0.5 + attempt * 0.2))
    raise RuntimeError(
        f"copy_rates_range empty after {retries} attempts symbol={symbol} "
        f"from={utc_from.isoformat()} to={date_to.isoformat()} last_error={last_error}"
    )


def write_progress(path: Path, tf: str, month: str, completed: int, total: int, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "schema": 1,
        "phase": "I-B-AUTO",
        "timeframe": tf,
        "month": month,
        "completed": completed,
        "total": total,
        "rows_written": rows,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_timeframe(mt5, symbol: str, tf_name: str, tf_value: int, out_path: Path, offset_seconds: int, progress_path: Path) -> dict[str, Any]:
    fields = ["symbol", "timeframe", "server_time", "server_epoch", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    rows = 0
    first_epoch: int | None = None
    last_epoch: int | None = None
    month_index = 0
    total = 48
    cursor = month_start(2024, 1)
    end = month_start(2026, 1)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        while cursor < end:
            nxt = next_month(cursor)
            server_start = int(cursor.timestamp())
            server_end = int(nxt.timestamp())
            utc_from = datetime.fromtimestamp(server_start - offset_seconds, tz=timezone.utc)
            utc_to = datetime.fromtimestamp(server_end - offset_seconds, tz=timezone.utc)
            rates = fetch_month(mt5, symbol, tf_value, utc_from, utc_to)

            raw_first = int(rates[0]["time"])
            raw_last = int(rates[-1]["time"])
            kept = 0
            previous: int | None = None
            for r in rates:
                # MetaTrader5 Python bars are UTC. Convert once into the Phase I-A server-wall coordinate.
                server_epoch = int(r["time"]) + offset_seconds
                if not (server_start <= server_epoch < server_end):
                    continue
                if previous is not None and server_epoch <= previous:
                    raise RuntimeError(f"non-increasing {tf_name} timestamps in {cursor:%Y-%m}")
                previous = server_epoch
                server_time = datetime.fromtimestamp(server_epoch, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
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
                kept += 1
                rows += 1
                if first_epoch is None:
                    first_epoch = server_epoch
                last_epoch = server_epoch

            if kept == 0:
                raise RuntimeError(
                    f"{tf_name} {cursor:%Y-%m} returned {len(rates)} bars but none mapped into the requested "
                    f"server month; raw_first={raw_first} raw_last={raw_last} offset={offset_seconds} "
                    f"requested_utc={utc_from.isoformat()}..{utc_to.isoformat()}"
                )
            month_index += 1
            completed = month_index if tf_name == "M1" else 24 + month_index
            write_progress(progress_path, tf_name, cursor.strftime("%Y-%m"), completed, total, rows)
            cursor = nxt

    if rows == 0:
        raise RuntimeError(f"empty {tf_name} export")
    return {"rows": rows, "first_epoch": first_epoch, "last_epoch": last_epoch}


def write_manifest(path: Path, ti, ai, symbol: str, m1: dict[str, Any], m5: dict[str, Any], offset_seconds: int) -> None:
    values = {
        "schema": "1", "phase": "I-B", "symbol": symbol, "symbol_root": "XAUUSD",
        "server": str(ai.server), "company": str(ai.company), "terminal_path": str(ti.path),
        "terminal_data_path": str(ti.data_path), "terminal_commondata_path": str(ti.commondata_path),
        "from_server_time": "2024.01.01 00:00:00", "to_server_time_exclusive": "2026.01.01 00:00:00",
        "exported_at_server_time": datetime.fromtimestamp(time.time() + offset_seconds, tz=timezone.utc).strftime("%Y.%m.%d %H:%M:%S"),
        "python_api_utc_to_server_offset_seconds": str(offset_seconds),
        "python_api_source": "MetaTrader5.copy_rates_range_datetime_bounds_v1_01",
        "m1_rows": str(m1["rows"]), "m1_first_epoch": str(m1["first_epoch"]), "m1_last_epoch": str(m1["last_epoch"]),
        "m5_rows": str(m5["rows"]), "m5_first_epoch": str(m5["first_epoch"]), "m5_last_epoch": str(m5["last_epoch"]),
    }
    path.write_text("".join(f"{k}={v}\n" for k, v in values.items()), encoding="utf-8")


def publish(publisher: Path, status: str, summary: str, artifacts: list[Path], cwd: Path) -> None:
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

    deploy, ia_dir, out = Path(args.deploy), Path(args.ia_dir), Path(args.output_dir)
    progress = Path(args.progress_file)
    summary_path = ia_dir / "phase_ia_summary.json"
    mask = ia_dir / "phase_ia_xauusd_merged_news_mask_2024_2025.csv"
    builder = deploy / "research" / "phenomenon_discovery" / "build_xau_news_clean_dataset_v1_00.py"
    checker = deploy / "research" / "phenomenon_discovery" / "check_xau_news_clean_dataset_v1_00.py"
    publisher = deploy / "research" / "phenomenon_discovery" / "publish_phase_result_v1_00.py"
    out.mkdir(parents=True, exist_ok=True)
    for p in (summary_path, mask, builder, checker, publisher):
        if not p.exists():
            raise RuntimeError(f"missing Phase I-B dependency: {p}")

    ia = json.loads(summary_path.read_text(encoding="utf-8"))
    ia_terminal = ia.get("terminal_manifest", {})
    if ia.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-A provenance does not protect 2026")
    offset = derive_server_offset_seconds(ia)
    terminal_exe = Path(args.terminal_exe)

    try:
        procs = get_open_terminal_processes()
        if len(procs) != 1:
            raise RuntimeError(f"exactly one open terminal64.exe required; found {len(procs)}")
        original_pid = int(procs[0]["ProcessId"])
        if norm_path(procs[0].get("ExecutablePath")) != norm_path(str(terminal_exe)):
            raise RuntimeError(f"sole open MT5 is not canonical FundedNext: {procs[0].get('ExecutablePath')}")

        mt5 = ensure_mt5_module()
        publish(publisher, "RUNNING", f"Phase I-B automatic extractor v1.01 starting on sole open MT5 PID {original_pid}; no GUI script; 2026 protected.", [], deploy)
        initialized = False
        try:
            initialized = bool(mt5.initialize(str(terminal_exe), timeout=60000, portable=True))
            if not initialized:
                raise RuntimeError(f"MetaTrader5.initialize failed: {mt5.last_error()}")
            after = get_open_terminal_processes()
            if len(after) != 1 or int(after[0]["ProcessId"]) != original_pid:
                raise RuntimeError("MT5 process set changed during initialize")
            ti, ai = mt5.terminal_info(), mt5.account_info()
            if ti is None or ai is None:
                raise RuntimeError(f"terminal/account info unavailable: {mt5.last_error()}")
            if str(ai.server) != str(ia_terminal.get("server")):
                raise RuntimeError(f"server mismatch I-A={ia_terminal.get('server')} Python={ai.server}")
            if norm_path(str(ti.path)) != norm_path(str(ia_terminal.get("terminal_path"))):
                raise RuntimeError("terminal_path mismatch vs Phase I-A")
            if norm_path(str(ti.data_path)) != norm_path(str(ia_terminal.get("terminal_data_path"))):
                raise RuntimeError("terminal_data_path mismatch vs Phase I-A")

            symbol = resolve_symbol(mt5, "XAUUSD")
            raw_m1, raw_m5 = out / "xauusd_m1_2024_2025_raw.csv", out / "xauusd_m5_2024_2025_raw.csv"
            manifest = out / "xauusd_history_terminal_manifest.txt"
            m1 = export_timeframe(mt5, symbol, "M1", mt5.TIMEFRAME_M1, raw_m1, offset, progress)
            m5 = export_timeframe(mt5, symbol, "M5", mt5.TIMEFRAME_M5, raw_m5, offset, progress)
            write_manifest(manifest, ti, ai, symbol, m1, m5, offset)
        finally:
            if initialized:
                mt5.shutdown()

        cp = run([sys.executable, str(builder), "--raw-m1", str(out / "xauusd_m1_2024_2025_raw.csv"), "--raw-m5", str(out / "xauusd_m5_2024_2025_raw.csv"), "--ib-terminal-manifest", str(out / "xauusd_history_terminal_manifest.txt"), "--ia-summary", str(summary_path), "--ia-mask", str(mask), "--output-dir", str(out)], cwd=deploy, timeout=900)
        if cp.returncode != 0:
            raise RuntimeError(f"I-B builder failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-5000:]}")
        cp = run([sys.executable, str(checker), "--input-dir", str(out), "--ia-mask", str(mask)], cwd=deploy, timeout=900)
        if cp.returncode != 0:
            raise RuntimeError(f"I-B checker failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout[-7000:]}")

        ib_summary, integrity, audit, manifest = out / "phase_ib_summary.json", out / "phase_ib_integrity.json", out / "phase_ib_news_exclusion_audit.csv", out / "xauusd_history_terminal_manifest.txt"
        integ = json.loads(integrity.read_text(encoding="utf-8"))
        if integ.get("status") != "PASS":
            raise RuntimeError("I-B integrity is not PASS")
        publish(publisher, "PASS", "Phase I-B PASS via automatic MT5 Python API v1.01; XAUUSD M1/M5 2024-2025, exact Phase I-A terminal/server, news mask applied, 2026 untouched.", [ib_summary, integrity, audit, manifest], deploy)
        write_progress(progress, "DONE", "2025-12", 48, 48, int(integ.get("timeframes", {}).get("M1", {}).get("raw", {}).get("rows", 0)))
        return 0
    except Exception as exc:
        failure = out / "phase_ib_auto_failure_v1_01.json"
        failure.write_text(json.dumps({"schema": 1, "status": "FAIL", "error": repr(exc), "updated_at_utc": datetime.now(timezone.utc).isoformat(), "protected_2026_untouched": True}, indent=2) + "\n", encoding="utf-8")
        try:
            publish(publisher, "FAIL", f"Phase I-B automatic extractor v1.01 failed: {exc}", [failure], deploy)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PHASE I-B AUTO v1.01 FAIL: {exc}", file=sys.stderr)
        raise
