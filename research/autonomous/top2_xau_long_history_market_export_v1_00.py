#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

TF_MAP = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5"}


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def hb(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if not path:
        return
    obj = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        obj.update(extra)
    atomic_json(path, obj)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def month_windows(start: pd.Timestamp, end: pd.Timestamp):
    cur = start
    while cur < end:
        nxt = min(cur + pd.offsets.MonthBegin(1), end)
        if nxt <= cur:
            nxt = min(cur + pd.DateOffset(months=1), end)
        yield cur, nxt
        cur = nxt


def normalize_rates(arr, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if arr is None or len(arr) == 0:
        return pd.DataFrame()
    z = pd.DataFrame(arr)
    if "time" not in z:
        raise RuntimeError("MT5 rates missing time")
    z["server_epoch"] = pd.to_numeric(z["time"], errors="raise").astype("int64")
    z = z[(z.server_epoch >= int(start.timestamp())) & (z.server_epoch < int(end.timestamp()))].copy()
    keep = ["server_epoch", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]
    for col in keep:
        if col not in z:
            if col in ("real_volume", "spread", "tick_volume"):
                z[col] = 0
            else:
                raise RuntimeError(f"MT5 rates missing {col}")
    z = z[keep]
    z["server_time"] = pd.to_datetime(z.server_epoch, unit="s", utc=True).dt.strftime("%Y.%m.%d %H:%M:%S")
    z = z[["server_time", *keep]].sort_values("server_epoch").drop_duplicates("server_epoch", keep="last").reset_index(drop=True)
    return z


def load_canonical(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise RuntimeError(f"canonical file missing: {path}")
    z = pd.read_csv(path)
    if "server_epoch" not in z.columns:
        if "time" in z.columns:
            z["server_epoch"] = (pd.to_datetime(z["time"], utc=True).astype("int64") // 1_000_000_000).astype("int64")
        elif "server_time" in z.columns:
            z["server_epoch"] = (pd.to_datetime(z["server_time"], utc=True).astype("int64") // 1_000_000_000).astype("int64")
        else:
            raise RuntimeError(f"cannot resolve canonical epoch: {path}")
    req = {"server_epoch", "open", "high", "low", "close"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"canonical columns invalid: {path}")
    for c in ("open", "high", "low", "close"):
        z[c] = pd.to_numeric(z[c], errors="raise")
    z["server_epoch"] = pd.to_numeric(z.server_epoch, errors="raise").astype("int64")
    return z[["server_epoch", "open", "high", "low", "close"]].sort_values("server_epoch").drop_duplicates("server_epoch")


def reconcile(exported: pd.DataFrame, canonical: pd.DataFrame, label: str) -> dict:
    if canonical.empty:
        raise RuntimeError(f"{label}: empty canonical overlap")
    merged = canonical.merge(exported[["server_epoch", "open", "high", "low", "close"]], on="server_epoch", how="left", suffixes=("_c", "_e"), indicator=True)
    matched = int((merged["_merge"] == "both").sum())
    coverage = matched / len(canonical)
    mismatch = 0
    if matched:
        m = merged["_merge"] == "both"
        for c in ("open", "high", "low", "close"):
            mismatch += int((~np.isclose(merged.loc[m, c + "_c"].to_numpy(float), merged.loc[m, c + "_e"].to_numpy(float), rtol=0.0, atol=1e-8)).sum())
    if coverage < 0.9999 or mismatch != 0:
        raise RuntimeError(f"{label}: canonical reconciliation failed coverage={coverage:.8f} mismatched_ohlc_cells={mismatch}")
    return {"canonical_rows": int(len(canonical)), "matched_rows": matched, "coverage": coverage, "mismatched_ohlc_cells": mismatch}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--terminal-exe", required=True)
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--required-server", default="FundedNext-Server 2")
    ap.add_argument("--start", default="2017-01-01T00:00:00Z")
    ap.add_argument("--end-exclusive", default="2026-08-01T00:00:00Z")
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--phase-ib-root", required=True)
    ap.add_argument("--phase-if-common", required=True)
    ap.add_argument("--progress-file")
    args = ap.parse_args()

    start = pd.Timestamp(args.start)
    end = pd.Timestamp(args.end_exclusive)
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    if start != pd.Timestamp("2017-01-01T00:00:00Z") or end != pd.Timestamp("2026-08-01T00:00:00Z"):
        raise RuntimeError("long-history window drift")

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    phase_ib = Path(args.phase_ib_root)
    phase_if = Path(args.phase_if_common)
    terminal = Path(args.terminal_exe)
    if not terminal.exists():
        raise RuntimeError(f"terminal missing: {terminal}")

    import MetaTrader5 as mt5

    if not mt5.initialize(str(terminal), timeout=60000, portable=True):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    manifest = {
        "schema": 1,
        "phase": "top2-xau-long-history-market-export",
        "window": {"start": start.isoformat(), "end_exclusive": end.isoformat()},
        "terminal_exe": str(terminal),
        "symbol": args.symbol,
        "timeframes": {},
        "reconciliation": {},
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        ai = mt5.account_info()
        ti = mt5.terminal_info()
        if ai is None or ti is None:
            raise RuntimeError(f"MT5 terminal/account unavailable: {mt5.last_error()}")
        if str(ai.server) != args.required_server:
            raise RuntimeError(f"wrong MT5 server: {ai.server!r} != {args.required_server!r}")
        if not mt5.symbol_select(args.symbol, True):
            raise RuntimeError(f"cannot select {args.symbol}: {mt5.last_error()}")
        manifest["server"] = str(ai.server)
        manifest["company"] = str(ai.company)
        manifest["terminal_maxbars"] = int(getattr(ti, "maxbars", 0) or 0)

        windows = list(month_windows(start, end))
        total_steps = len(windows) * 2
        completed = 0

        exported_all = {}
        for tf_name, attr in TF_MAP.items():
            tf = getattr(mt5, attr)
            by_year: dict[int, list[pd.DataFrame]] = {}
            for a, b in windows:
                hb(progress, completed, total_steps, f"export_{tf_name}", {"month": a.strftime("%Y-%m")})
                arr = mt5.copy_rates_range(args.symbol, tf, a.to_pydatetime(), b.to_pydatetime())
                if arr is None or len(arr) == 0:
                    raise RuntimeError(f"{tf_name} no data for {a}..{b}: {mt5.last_error()}")
                z = normalize_rates(arr, a, b)
                if z.empty:
                    raise RuntimeError(f"{tf_name} normalized empty for {a}..{b}")
                for year, yz in z.groupby(pd.to_datetime(z.server_epoch, unit="s", utc=True).dt.year):
                    by_year.setdefault(int(year), []).append(yz.copy())
                completed += 1

            tf_meta = {}
            full_parts = []
            for year in range(2017, 2027):
                if year not in by_year:
                    raise RuntimeError(f"{tf_name} missing entire year {year}")
                yz = pd.concat(by_year[year], ignore_index=True).sort_values("server_epoch").drop_duplicates("server_epoch").reset_index(drop=True)
                y_end = pd.Timestamp(f"{year+1}-01-01T00:00:00Z") if year < 2026 else end
                yz = yz[(yz.server_epoch >= int(pd.Timestamp(f"{year}-01-01T00:00:00Z").timestamp())) & (yz.server_epoch < int(y_end.timestamp()))]
                min_rows = (150000 if tf_name == "M1" else 30000) if year < 2026 else (100000 if tf_name == "M1" else 20000)
                if len(yz) < min_rows:
                    raise RuntimeError(f"{tf_name} {year} too few rows: {len(yz)} < {min_rows}")
                if not yz.server_epoch.is_monotonic_increasing or yz.server_epoch.duplicated().any():
                    raise RuntimeError(f"{tf_name} {year} timestamps invalid")
                yp = out / f"xauusd_{tf_name.lower()}_{year}.csv"
                yz.to_csv(yp, index=False)
                tf_meta[str(year)] = {
                    "path": str(yp),
                    "sha256": sha256(yp),
                    "rows": int(len(yz)),
                    "first_epoch": int(yz.server_epoch.iloc[0]),
                    "last_epoch": int(yz.server_epoch.iloc[-1]),
                }
                full_parts.append(yz)
            exported_all[tf_name] = pd.concat(full_parts, ignore_index=True).sort_values("server_epoch").drop_duplicates("server_epoch").reset_index(drop=True)
            manifest["timeframes"][tf_name] = tf_meta

        # Fail closed unless the long export reconciles with the frozen data already used today.
        for tf_name in ("M1", "M5"):
            low = tf_name.lower()
            can_2425 = load_canonical(phase_ib / f"xauusd_{low}_2024_2025_raw.csv")
            exp_2425 = exported_all[tf_name][
                (exported_all[tf_name].server_epoch >= int(pd.Timestamp("2024-01-01T00:00:00Z").timestamp()))
                & (exported_all[tf_name].server_epoch < int(pd.Timestamp("2026-01-01T00:00:00Z").timestamp()))
            ]
            manifest["reconciliation"][f"{tf_name}_2024_2025"] = reconcile(exp_2425, can_2425, f"{tf_name} 2024-2025")

            can_2026 = load_canonical(phase_if / f"xauusd_{low}_2026_jan_aug.csv")
            can_2026 = can_2026[can_2026.server_epoch < int(end.timestamp())]
            exp_2026 = exported_all[tf_name][
                (exported_all[tf_name].server_epoch >= int(pd.Timestamp("2026-01-01T00:00:00Z").timestamp()))
                & (exported_all[tf_name].server_epoch < int(end.timestamp()))
            ]
            manifest["reconciliation"][f"{tf_name}_2026_jan_jul"] = reconcile(exp_2026, can_2026, f"{tf_name} 2026 Jan-Jul")

        manifest["status"] = "PASS"
        manifest["read_only_market_access"] = True
        mp = out / "top2_long_history_market_manifest.json"
        atomic_json(mp, manifest)
        hb(progress, total_steps, total_steps, "complete", {"status": "PASS"})
        print(json.dumps({"status": "PASS", "years": "2017-2026-07", "server": manifest["server"], "manifest": str(mp)}))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
