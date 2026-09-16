#!/usr/bin/env python3
"""R21-R25 XAUUSD discovery engine v1.02 — second-audit corrective wrapper.

v1.02 intentionally reuses only the already-reviewed phenomenon definitions from
v1.01 while replacing the remaining defective surfaces:
- no arbitrary CSV input path: CLI accepts only the immutable R15 master index;
- discovery CSV is generated internally by the sealed discovery builder;
- absolute M5 grid is enforced before any event logic;
- R22 complete-estimator jackknife fails closed if any required delete-one-day
  replication is undefined.

No confirmation, 2025 pre-OOS, 2026+, PnL optimisation, or live logic exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import build_xau_m5_discovery_slice_v1_01 as sealed_builder
import xau_edge_discovery_r21_r25_v1_01 as base

Bar = base.Bar
DISCOVERY_START = base.DISCOVERY_START
DISCOVERY_END = base.DISCOVERY_END
PROTECTED_START = base.PROTECTED_START
POST_BARS = base.POST_BARS
POST_MINUTES = base.POST_MINUTES

# Trust anchor from the R15 PASS union manifest generated 2026-09-14T11:53:03Z.
# Neither the path nor the digest can be supplied through CLI/environment input.
# Relocating/rebuilding this immutable index requires a reviewed code change.
CANONICAL_R15_INDEX = Path(
    "D:/MT5_Backtests/Research/Autonomous/r15_dukascopy_xauusd_union_v1/"
    "xauusd_dukascopy_master_payload_index.csv"
)
CANONICAL_R15_INDEX_SHA256 = "d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"

# Reuse only phenomenon definitions that the second independent audit found
# coherent on valid M5 input.
r21_comex_unconditional_drift = base.r21_comex_unconditional_drift
r22_volatility_compression = base.r22_volatility_compression
r23_overnight_to_ny = base.r23_overnight_to_ny
r24_comex_opening_range_breakout = base.r24_comex_opening_range_breakout
r25_ny_gap_previous_close = base.r25_ny_gap_previous_close
signed_stats = base.signed_stats
cluster_stats = base.cluster_stats
yearly_stability = base.yearly_stability
_metric_summary = base._metric_summary
_r25_fill_summary = base._r25_fill_summary


def _read_canonical_r15_index(index_path: Path) -> bytes:
    """Admit only the pinned metadata file, before opening any user path.

    Compare the lexical absolute path first, then reject symlink/junction
    redirection. Read the admitted index once; the builder receives a private
    snapshot of precisely the bytes whose digest was checked.
    """
    trusted = CANONICAL_R15_INDEX.absolute()
    if index_path.absolute() != trusted:
        raise RuntimeError("refusing to open non-canonical R15 index path")
    if index_path.resolve(strict=True) != trusted:
        raise RuntimeError("refusing redirected canonical R15 index path")
    content = index_path.read_bytes()
    if hashlib.sha256(content).hexdigest() != CANONICAL_R15_INDEX_SHA256:
        raise RuntimeError("canonical R15 index SHA256 mismatch; builder not called")
    return content


def load_generated_discovery_bars(path: Path) -> list[Bar]:
    """Load only a builder-generated discovery CSV and enforce absolute M5 grid."""
    out: list[Bar] = []
    prev: int | None = None
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        need = {"timeframe", "server_epoch", "open", "high", "low", "close"}
        missing = need - set(r.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")
        for row in r:
            epoch = int(row["server_epoch"])
            if epoch % 300 != 0:
                raise RuntimeError(f"off-grid M5 timestamp: {epoch}")
            if prev is not None and epoch <= prev:
                raise RuntimeError(f"non-increasing timestamp: {epoch} <= {prev}")
            prev = epoch
            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if not DISCOVERY_START <= dt.date() <= DISCOVERY_END:
                raise RuntimeError(f"generated discovery CSV escaped frozen window: {dt.isoformat()}")
            tf = row["timeframe"].strip().upper()
            if tf != "M5":
                raise RuntimeError(f"R21-R25 v1.02 requires M5, got {tf}")
            o, h, l, c = map(float, (row["open"], row["high"], row["low"], row["close"]))
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                raise RuntimeError(f"invalid OHLC at {dt.isoformat()}")
            if h < max(o, c) or l > min(o, c) or h < l:
                raise RuntimeError(f"invalid OHLC geometry at {dt.isoformat()}")
            out.append(Bar(epoch, dt, tf, o, h, l, c))
    if not out:
        raise RuntimeError("no usable generated discovery rows")
    return out


def _validate_builder_receipt(receipt: dict, generated_csv: Path) -> None:
    expected = {
        "status": "PASS",
        "stage": "discovery",
        "stage_start": DISCOVERY_START.isoformat(),
        "stage_end_inclusive": DISCOVERY_END.isoformat(),
        "confirmation_opened": False,
        "pre_oos_2025_opened": False,
        "protected_2026_opened": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RuntimeError(f"sealed builder receipt mismatch {key}: {receipt.get(key)!r} != {value!r}")
    if Path(str(receipt.get("output", ""))).resolve() != generated_csv.resolve():
        raise RuntimeError("sealed builder receipt output path mismatch")
    if receipt.get("last_opened_payload_date") and receipt["last_opened_payload_date"] > DISCOVERY_END.isoformat():
        raise RuntimeError("sealed builder claims a post-discovery payload was opened")


def r22_complete_estimator_day_jackknife(
    bars: Sequence[Bar], events: Sequence[dict], state: str, horizon: int
) -> dict:
    """Delete-one-UTC-day jackknife of the complete R22 estimator, fail-closed.

    Every day in the union of baseline days and event days is a required
    replication. If deleting any required day makes the estimator undefined
    (for example, it removes all events), inference is unavailable rather than
    silently dropping that replication.
    """
    metric = f"abs_fwd_{horizon}b"
    ev = [
        e
        for e in events
        if e.get("compression_state") == state
        and isinstance(e.get(metric), (int, float))
        and isinstance(e.get("utc_minute"), int)
    ]
    method = "delete_one_utc_day_complete_estimator_fail_closed"
    event_days = sorted({str(e["cluster_day"]) for e in ev})
    base_obs = base._baseline_observations(bars, horizon)
    baseline_days_set = {day for day, _, _ in base_obs}
    if not ev:
        # With no events, deleting any baseline day also leaves no events:
        # every required replication is analytically undefined, not absent.
        days = sorted(baseline_days_set)
        return {
            "n": 0,
            "clusters": 0,
            "baseline_days": len(days),
            "event_days": 0,
            "required_replicates": len(days),
            "valid_replicates": 0,
            "undefined_delete_days": days,
            "mean": None,
            "cluster_se": None,
            "cluster_t": None,
            "method": method,
            "reason": "no qualifying events",
        }

    total_base_count: dict[int, int] = defaultdict(int)
    total_base_sum: dict[int, float] = defaultdict(float)
    day_base_count: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    day_base_sum: dict[str, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for day, clock, y in base_obs:
        total_base_count[clock] += 1
        total_base_sum[clock] += y
        day_base_count[day][clock] += 1
        day_base_sum[day][clock] += y

    event_count_clock: dict[int, int] = defaultdict(int)
    day_event_count_clock: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    day_event_n: dict[str, int] = defaultdict(int)
    day_event_sum: dict[str, float] = defaultdict(float)
    event_sum = 0.0
    for e in ev:
        day = str(e["cluster_day"])
        clock = int(e["utc_minute"])
        y = float(e[metric])
        event_count_clock[clock] += 1
        day_event_count_clock[day][clock] += 1
        day_event_n[day] += 1
        day_event_sum[day] += y
        event_sum += y

    def estimate(
        n_event: int,
        sum_event: float,
        counts_event_clock: dict[int, int],
        removed_day: str | None,
    ) -> float | None:
        if n_event <= 0:
            return None
        weighted_base = 0.0
        for clock, ec in counts_event_clock.items():
            if ec <= 0:
                continue
            bc = total_base_count[clock]
            bs = total_base_sum[clock]
            if removed_day is not None:
                bc -= day_base_count[removed_day].get(clock, 0)
                bs -= day_base_sum[removed_day].get(clock, 0.0)
            if bc <= 0:
                return None
            weighted_base += ec * (bs / bc)
        return sum_event / n_event - weighted_base / n_event

    n = len(ev)
    full = estimate(n, event_sum, dict(event_count_clock), None)
    days = sorted(baseline_days_set | set(event_days))
    common = {
        "n": n,
        "clusters": len(event_days),
        "baseline_days": len(baseline_days_set),
        "event_days": len(event_days),
        "required_replicates": len(days),
        "method": method,
    }
    if full is None:
        return {
            **common,
            "valid_replicates": 0,
            "undefined_delete_days": [],
            "mean": None,
            "cluster_se": None,
            "cluster_t": None,
            "reason": "full estimator undefined",
        }

    loo: list[float] = []
    undefined_days: list[str] = []
    for day in days:
        n2 = n - day_event_n.get(day, 0)
        sum2 = event_sum - day_event_sum.get(day, 0.0)
        counts2 = dict(event_count_clock)
        for clock, count in day_event_count_clock.get(day, {}).items():
            counts2[clock] = counts2.get(clock, 0) - count
        est = estimate(n2, sum2, counts2, day)
        if est is None:
            undefined_days.append(day)
        else:
            loo.append(est)

    if undefined_days:
        return {
            **common,
            "valid_replicates": len(loo),
            "undefined_delete_days": undefined_days,
            "mean": full,
            "cluster_se": None,
            "cluster_t": None,
            "reason": "at least one required delete-one-day replication is undefined",
        }

    g = len(loo)
    if g < 2:
        return {
            **common,
            "valid_replicates": g,
            "undefined_delete_days": [],
            "mean": full,
            "cluster_se": None,
            "cluster_t": None,
            "reason": "fewer than two valid required replications",
        }

    mean_loo = statistics.fmean(loo)
    var = ((g - 1) / g) * sum((x - mean_loo) ** 2 for x in loo)
    se = math.sqrt(max(var, 0.0))
    return {
        **common,
        "valid_replicates": g,
        "undefined_delete_days": [],
        "mean": full,
        "cluster_se": se,
        "cluster_t": full / se if se > 0 else None,
        "reason": None,
    }


def summarize(name: str, events: Sequence[dict], bars: Sequence[Bar]) -> dict:
    prefixes = ("post_", "excess_abs_", "continuation_", "reversal_", "toward_", "away_")
    out: dict = {
        "research": name,
        "event_count": len(events),
        "day_count": len({e["cluster_day"] for e in events}),
    }
    if name == "R22":
        out["states"] = {}
        for state in ("bottom10", "bottom20"):
            xs = [e for e in events if e.get("compression_state") == state]
            metrics = _metric_summary(xs, prefixes)
            for h in POST_BARS:
                key = f"excess_abs_{h}b"
                if key in metrics:
                    metrics[key]["clustered"] = r22_complete_estimator_day_jackknife(
                        bars, events, state, h
                    )
            out["states"][state] = {
                "event_count": len(xs),
                "day_count": len({e["cluster_day"] for e in xs}),
                "metrics": metrics,
            }
    else:
        out["metrics"] = _metric_summary(events, prefixes)
        if name == "R25":
            out["fill_probability_descriptive"] = _r25_fill_summary(events)
    return out


def run_from_index(index_path: Path, selected: Sequence[str]) -> dict:
    """Build the discovery slice internally, then analyze it. No external CSV accepted."""
    index_content = _read_canonical_r15_index(index_path)
    with tempfile.TemporaryDirectory(prefix="guardian_r21r25_v102_") as td:
        verified_index = Path(td) / "verified_r15_index.csv"
        verified_index.write_bytes(index_content)
        generated_csv = Path(td) / "sealed_discovery_m5.csv"
        receipt = sealed_builder.build(verified_index, generated_csv)
        _validate_builder_receipt(receipt, generated_csv)
        bars = load_generated_discovery_bars(generated_csv)

        funcs = {
            "R21": r21_comex_unconditional_drift,
            "R22": r22_volatility_compression,
            "R23": r23_overnight_to_ny,
            "R24": r24_comex_opening_range_breakout,
            "R25": r25_ny_gap_previous_close,
        }
        results: dict = {}
        for name in selected:
            ev = funcs[name](bars)
            results[name] = {"summary": summarize(name, ev, bars), "events": ev}

        return {
            "schema": 1,
            "batch": "R21-R25",
            "version": "1.02",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "discovery",
            "source_contract": "sealed_builder_from_canonical_sha256_pinned_r15_index",
            "source_index": str(index_path),
            "source_index_sha256": CANONICAL_R15_INDEX_SHA256,
            "builder_receipt": receipt,
            "rows": len(bars),
            "first_epoch": bars[0].epoch,
            "last_epoch": bars[-1].epoch,
            "stage_boundaries": {
                "discovery_start": DISCOVERY_START.isoformat(),
                "discovery_end": DISCOVERY_END.isoformat(),
                "confirmation": "INACCESSIBLE_IN_V1_02",
                "preoos_2025": "INACCESSIBLE_IN_V1_02",
                "protected_2026_plus": "HARD_SEALED",
            },
            "confirmation_opened": False,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "doctrine": "preregistered discovery only; sealed builder input; no PnL optimization",
            "results": results,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--index",
        required=True,
        type=Path,
        help="Canonical R15 index only; fixed path and SHA256 checked before building discovery.",
    )
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument(
        "--research",
        nargs="+",
        choices=("R21", "R22", "R23", "R24", "R25"),
        default=["R21", "R22", "R23", "R24", "R25"],
    )
    a = ap.parse_args()
    if a.output.resolve() == CANONICAL_R15_INDEX.absolute():
        raise RuntimeError("output must not overwrite the canonical R15 index")
    payload = run_from_index(a.index, a.research)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "results"}, indent=2, sort_keys=True))
    for name, item in payload["results"].items():
        print(f"{name}: events={item['summary']['event_count']} days={item['summary']['day_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
