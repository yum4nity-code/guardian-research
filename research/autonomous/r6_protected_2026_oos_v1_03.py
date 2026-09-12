#!/usr/bin/env python3
from __future__ import annotations

"""Execution-only repair for authorized R6 Jan-Aug 2026 protected OOS.

R6 OOS r4 was invalid because the inherited R5 pre-OOS replay intentionally
rejects every signal_year outside (2024, 2025) and every exit >= 2026-01-01.
This wrapper preserves the frozen R6 signal, entry timing, horizon, overlap,
costs, candidates, window and gates, while replacing only those pre-OOS
eligibility guards with explicit Jan-Aug 2026 window guards.

No candidate parameter, statistical gate, cost profile, source selection,
news-mask rule, temporal split or live-deployment rule is changed.
"""

import json
from typing import Any

import numpy as np
import pandas as pd

import r6_protected_2026_oos_v1_02 as transport


base = transport.base
r6 = base.r6
econ = base.econ

START = base.START
SPLIT = base.SPLIT
END = base.END
START_NS = int(START.value)
END_NS = int(END.value)


def _ts(ns: int) -> pd.Timestamp:
    return pd.Timestamp(int(ns), unit="ns", tz="UTC")


def authorized_replay(
    source: pd.DataFrame,
    raw_m1: pd.DataFrame,
    signals: np.ndarray,
    horizon: int,
    direction: int,
    tf_seconds: int,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Chronological one-position replay inside the frozen Jan-Aug 2026 window.

    Semantics deliberately mirror the pre-OOS replay except for eligibility:
    2026 is explicitly authorized and the hard boundary is END (2026-09-01),
    not the old PROTECTED=2026-01-01 threshold.
    """
    source_ns = source.time.array.as_unit("ns").asi8
    raw_ns = raw_m1.time.array.as_unit("ns").asi8
    raw_open = raw_m1.open.to_numpy(dtype=float)
    signals = np.asarray(signals, dtype=bool)

    if len(source_ns) == 0 or len(raw_ns) == 0:
        raise RuntimeError("authorized replay received empty source")
    if int(source_ns[0]) < START_NS or int(source_ns[-1]) >= END_NS:
        raise RuntimeError("source outside frozen Jan-Aug 2026 window")
    if int(raw_ns[0]) < START_NS or int(raw_ns[-1]) >= END_NS:
        raise RuntimeError("raw M1 outside frozen Jan-Aug 2026 window")

    ledger: list[dict[str, Any]] = []
    state: dict[str, Any] | None = None
    counts = {
        "signals_total": int(signals.sum()),
        "ignored_overlap_signals": 0,
        "excluded_oos_boundary_signals": 0,
        "missing_reference_trades": 0,
        "executable_trades": 0,
    }
    n = len(source)

    def close_state(s: dict[str, Any]) -> None:
        exit_idx = int(np.searchsorted(raw_ns, s["exit_available_ns"], side="left"))
        if s["entry_idx"] >= len(raw_ns) or exit_idx >= len(raw_ns):
            counts["missing_reference_trades"] += 1
            return
        entry_ns = int(raw_ns[s["entry_idx"]])
        exit_ns = int(raw_ns[exit_idx])
        if not (START_NS <= entry_ns < exit_ns < END_NS):
            counts["excluded_oos_boundary_signals"] += 1
            return
        oe = float(raw_open[s["entry_idx"]])
        ox = float(raw_open[exit_idx])
        ledger.append(
            {
                "signal_index": s["signal_index"],
                "signal_time": _ts(s["signal_ns"]).isoformat(),
                "entry_time": _ts(entry_ns).isoformat(),
                "exit_time": _ts(exit_ns).isoformat(),
                "entry_open": oe,
                "exit_open": ox,
                "direction": int(direction),
                "profiles": {p: econ.cost(oe, ox, direction, p) for p in econ.PROFILES},
            }
        )

    for i in range(n):
        available_ns = int(source_ns[i] + tf_seconds * 1_000_000_000)

        # Preserve inherited ordering: process an exit before considering a new
        # signal that becomes available at the same timestamp.
        if state is not None and available_ns >= int(state["exit_available_ns"]):
            close_state(state)
            state = None

        if not signals[i]:
            continue
        if state is not None:
            counts["ignored_overlap_signals"] += 1
            continue

        exit_source_index = i + int(horizon) + 1
        if exit_source_index >= n:
            counts["excluded_oos_boundary_signals"] += 1
            continue

        signal_ns = int(source_ns[i])
        exit_available_ns = int(source_ns[exit_source_index])
        if not (START_NS <= signal_ns < END_NS):
            counts["excluded_oos_boundary_signals"] += 1
            continue
        if available_ns >= END_NS or exit_available_ns >= END_NS:
            counts["excluded_oos_boundary_signals"] += 1
            continue

        entry_idx = int(np.searchsorted(raw_ns, available_ns, side="left"))
        if entry_idx >= len(raw_ns):
            counts["missing_reference_trades"] += 1
            continue
        entry_ns = int(raw_ns[entry_idx])
        if not (START_NS <= entry_ns < END_NS):
            counts["excluded_oos_boundary_signals"] += 1
            continue

        state = {
            "signal_index": int(i),
            "signal_ns": signal_ns,
            "entry_idx": entry_idx,
            "exit_available_ns": exit_available_ns,
        }

    if state is not None:
        close_state(state)

    counts["executable_trades"] = len(ledger)
    return ledger, counts


def evaluate_year_authorized(rule: dict, source: pd.DataFrame, raw: pd.DataFrame, year: int):
    if int(year) != 2026:
        raise RuntimeError(f"authorized R6 OOS evaluator only permits year 2026, got {year}")
    atr = r6.atr14(source)
    sig = r6.breakout_signal(
        source,
        atr,
        rule["lookback_bars"],
        rule["buffer_atr"],
        rule["direction"],
        rule["session_start"],
        rule["session_end"],
    )
    ledger, accounting = authorized_replay(
        source,
        raw,
        sig,
        rule["horizon_bars"],
        rule["direction"],
        300,
    )
    full = [
        t
        for t in ledger
        if START <= pd.Timestamp(t["entry_time"]) and pd.Timestamp(t["exit_time"]) < END
    ]
    return ledger, accounting, {p: econ.stats(full, p) for p in econ.PROFILES}


# Mechanical runtime patch only. transport/base retain every other frozen rule.
base.apply_news_mask = transport.apply_news_mask
base.r6.evaluate_year = evaluate_year_authorized


def main() -> int:
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
