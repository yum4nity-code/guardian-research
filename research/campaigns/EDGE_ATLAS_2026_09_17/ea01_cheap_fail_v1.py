#!/usr/bin/env python3
"""Frozen EA01 discovery-only engine. It streams one BI5 day at a time."""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from data_loader_v1 import AdmissionError, Bar, aggregate_m1_to_m5, decode_dukascopy_m1_day, load_dukascopy_index
from preflight_v1 import PINNED_MANIFEST_SHA256, canonical_manifest_sha256, validate_manifest

ID = "EDGE-ATLAS-2026-09-17-EA01-CHEAPFAIL-V0"
START = datetime(2017, 1, 1, tzinfo=timezone.utc)
END_EXCLUSIVE = datetime(2023, 1, 1, tzinfo=timezone.utc)
VARIANTS = ("reversal", "continuation")


@dataclass(frozen=True)
class Trade:
    variant: str
    signal_close: str
    entry_time: str
    exit_time: str
    side: int
    entry: float
    stop: float
    exit: float
    exit_reason: str
    pnl: float
    r_multiple: float


def atomic_json(path: Path, obj: object) -> None:
    if path.exists():
        raise AdmissionError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if tmp.exists():
        raise AdmissionError(f"stale temporary output exists: {tmp}")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def admitted_discovery_rows(manifest_path: Path):
    if not manifest_path.is_file():
        raise AdmissionError("manifest absent")
    if "production" in {part.lower() for part in manifest_path.resolve().parts}:
        raise AdmissionError("production input path forbidden")
    if canonical_manifest_sha256(manifest_path) != PINNED_MANIFEST_SHA256:
        raise AdmissionError("manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    datasets = validate_manifest(manifest)
    duka = datasets["DUKASCOPY_XAUUSD_BID_M1_BI5_2004_2025"]
    if duka["asset"] != "XAUUSD" or duka["timezone"] != "UTC" or duka["granularity"] != "M1":
        raise AdmissionError("EA01 requires XAUUSD UTC M1")
    rows = load_dukascopy_index(Path(duka["payload_index"]), duka["payload_index_sha256"])
    for row in rows:
        day = datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc)
        if START <= day < END_EXCLUSIVE:
            yield row


def true_range(bar: Bar, previous_close: float) -> float:
    return max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))


def summarize(trades: list[Trade]) -> dict:
    wins = sum(max(t.pnl, 0.0) for t in trades)
    losses = -sum(min(t.pnl, 0.0) for t in trades)
    return {"trades": len(trades), "net_pnl_points": sum(t.pnl for t in trades),
            "mean_r": (sum(t.r_multiple for t in trades) / len(trades)) if trades else None,
            "profit_factor": (wins / losses) if losses else (math.inf if wins else None)}


def evaluate_bars(bars) -> tuple[dict, list[Trade]]:
    """Evaluate exactly two frozen variants without future-bar access."""
    window: deque[Bar] = deque(maxlen=4)
    atr: float | None = None
    initial_trs: deque[float] = deque(maxlen=14)
    previous: Bar | None = None
    pending: list[dict] = []
    trades: list[Trade] = []
    for bar in bars:
        if not START <= bar.timestamp < END_EXCLUSIVE:
            raise AdmissionError("bar outside discovery period")
        if len(window) == 4 and atr is not None:
            directions = [1 if window[i].close > window[i - 1].close else -1 if window[i].close < window[i - 1].close else 0 for i in range(1, 4)]
            if directions[0] and len(set(directions)) == 1:
                signal_direction = directions[0]
                for variant, side in (("reversal", -signal_direction), ("continuation", signal_direction)):
                    risk = 1.5 * atr
                    pending.append({"variant": variant, "side": side, "entry": bar.open,
                                    "entry_time": bar.timestamp.isoformat(), "signal_close": window[-1].available_at.isoformat(),
                                    "stop": bar.open - side * risk, "risk": risk, "held": 0})
        survivors = []
        for pos in pending:
            pos["held"] += 1
            stop_hit = bar.low <= pos["stop"] if pos["side"] > 0 else bar.high >= pos["stop"]
            if stop_hit or pos["held"] == 3:
                exit_price = pos["stop"] if stop_hit else bar.close
                pnl = pos["side"] * (exit_price - pos["entry"])
                trades.append(Trade(pos["variant"], pos["signal_close"], pos["entry_time"],
                                    bar.available_at.isoformat(), pos["side"], pos["entry"], pos["stop"],
                                    exit_price, "STOP" if stop_hit else "TIME_3_BARS", pnl, pnl / pos["risk"]))
            else:
                survivors.append(pos)
        pending = survivors
        if previous is not None:
            tr = true_range(bar, previous.close)
            if atr is None:
                initial_trs.append(tr)
                if len(initial_trs) == 14:
                    atr = sum(initial_trs) / 14.0
            else:
                atr = ((atr * 13.0) + tr) / 14.0
        previous = bar
        window.append(bar)
    metrics = {variant: summarize([t for t in trades if t.variant == variant]) for variant in VARIANTS}
    return metrics, trades


def iter_discovery_m5(manifest_path: Path):
    for row in admitted_discovery_rows(manifest_path):
        yield from aggregate_m1_to_m5(decode_dukascopy_m1_day(row))


def run(manifest: Path, output: Path) -> dict:
    metrics, trades = evaluate_bars(iter_discovery_m5(manifest))
    result = {"schema": 1, "job_id": ID, "status": "COMPLETE", "discovery_start": START.isoformat(),
              "discovery_end_exclusive": END_EXCLUSIVE.isoformat(), "variants": list(VARIANTS),
              "metrics": metrics, "trades": [asdict(t) for t in trades], "protected_2026_opened": False}
    atomic_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    list(admitted_discovery_rows(args.manifest))
    if not args.execute:
        print(json.dumps({"status": "PREFLIGHT_ONLY", "id": ID}))
        return 0
    result = run(args.manifest, args.output)
    print(json.dumps({"status": result["status"], "id": ID}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
