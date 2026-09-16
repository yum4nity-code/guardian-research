#!/usr/bin/env python3
"""R28 XAUUSD compression-state directional-drift discovery v1.00.

Preregistered study:
- exact reviewed R22 bottom10 compression event definition
- discovery only: 2004-11-08 through 2019-06-30
- primary signed horizons: 4b and 8b
- estimator: event signed forward return minus event-frequency-weighted
  same-clock unconditional signed forward-return baseline
- inference: complete-estimator delete-one-UTC-day jackknife, fail closed
- discovery survives only if both horizons share one sign and both |t| > 2.0

Confirmation, 2025 and 2026+ are inaccessible.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import statistics
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import build_xau_m5_discovery_slice_v1_02 as sealed_builder
import xau_edge_discovery_r21_r25_v1_03 as discovery

Bar = discovery.Bar
r28_event_extractor = discovery.r22_volatility_compression
forward_return = discovery.base.forward_return
signed_stats = discovery.signed_stats

PRIMARY_HORIZONS = (4, 8)
PRIMARY_STATE = "bottom10"

CANONICAL_OUTPUT_DIR = Path(
    "D:/MT5_Backtests/Research/Autonomous/r28_xau_discovery_v100"
)
CANONICAL_OUTPUT = CANONICAL_OUTPUT_DIR / "discovery.json"
CANONICAL_PROGRESS = CANONICAL_OUTPUT_DIR / "progress.json"


def _validate_artifact_path(path: Path, expected: Path, label: str) -> Path:
    if not path.is_absolute() or path.absolute() != expected.absolute():
        raise RuntimeError(f"{label} must use its canonical R28 discovery path")

    root = CANONICAL_OUTPUT_DIR.absolute()
    if root.parent.resolve(strict=True) != root.parent.absolute():
        raise RuntimeError("canonical R28 discovery output parent is redirected")

    root.mkdir(parents=True, exist_ok=True)
    if root.resolve(strict=True) != root:
        raise RuntimeError("canonical R28 discovery output directory is redirected")

    if path.is_symlink() or (
        path.exists() and path.resolve(strict=True) != path.absolute()
    ):
        raise RuntimeError(f"canonical R28 discovery {label} file is redirected")

    return path.absolute()


def _validate_output_path(path: Path) -> Path:
    return _validate_artifact_path(path, CANONICAL_OUTPUT, "output")


def _validate_progress_path(path: Path) -> Path:
    return _validate_artifact_path(path, CANONICAL_PROGRESS, "progress")


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _write_progress(progress_path: Path, *, phase: str, fraction: float, **extra) -> None:
    fraction = max(0.0, min(1.0, float(fraction)))
    _atomic_json(
        progress_path,
        {
            "schema": 1,
            "research": "R28",
            "version": "1.00",
            "stage": "discovery",
            "status": "PASS" if phase == "complete" else "RUNNING",
            "phase": phase,
            "fraction": fraction,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "confirmation_opened": False,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            **extra,
        },
    )


def _cleanup_stale_transients() -> list[str]:
    removed: list[str] = []
    root = CANONICAL_OUTPUT_DIR

    try:
        if root.exists() and root.resolve(strict=True) == root.absolute():
            for name in (
                "progress.json",
                "progress.json.tmp",
                "discovery.json.tmp",
            ):
                p = root / name
                if (
                    p.exists()
                    and not p.is_symlink()
                    and p.resolve(strict=True).parent == root.absolute()
                ):
                    p.unlink()
                    removed.append(str(p))
    except OSError:
        pass

    temp_base = Path(tempfile.gettempdir())
    temp_root = temp_base.resolve()
    for p in temp_base.glob("guardian_r28_discovery_v100_*"):
        try:
            if p.is_symlink():
                continue
            resolved = p.resolve(strict=True)
            if resolved.parent != temp_root:
                continue
            if p.is_dir():
                shutil.rmtree(p)
                removed.append(str(p))
        except OSError:
            pass

    return removed


def _signed_baseline_observations(
    bars: Sequence[Bar],
    horizon: int,
) -> list[tuple[str, int, float]]:
    out: list[tuple[str, int, float]] = []
    for i, b in enumerate(bars):
        r = forward_return(bars, i, horizon)
        if r is not None:
            out.append((b.utc_day, b.utc_minute, float(r)))
    return out


def _event_signed_forward_returns(
    bars: Sequence[Bar],
    raw_events: Sequence[dict],
) -> list[dict]:
    by_epoch = {b.epoch: i for i, b in enumerate(bars)}
    out: list[dict] = []

    for raw in raw_events:
        if raw.get("compression_state") != PRIMARY_STATE:
            continue
        i = by_epoch.get(int(raw["epoch"]))
        if i is None:
            raise RuntimeError(f"R28 event epoch absent from M5 bars: {raw['epoch']}")

        event = {
            **raw,
            "research": "R28",
            "origin_research": "R22",
        }
        for h in PRIMARY_HORIZONS:
            event[f"signed_fwd_{h}b"] = forward_return(bars, i, h)
        out.append(event)

    return out


def complete_signed_excess_day_jackknife(
    bars: Sequence[Bar],
    events: Sequence[dict],
    horizon: int,
) -> dict:
    """Complete event-minus-same-clock-signed-baseline estimator.

    Every day in the union of baseline and event days is a required delete-one
    replication. Any undefined replication makes SE/t unavailable.
    """
    metric = f"signed_fwd_{horizon}b"
    ev = [
        e
        for e in events
        if isinstance(e.get(metric), (int, float))
        and math.isfinite(float(e[metric]))
        and isinstance(e.get("utc_minute"), int)
    ]
    base_obs = _signed_baseline_observations(bars, horizon)
    method = "delete_one_utc_day_complete_signed_same_clock_estimator_fail_closed"

    baseline_days_set = {day for day, _, _ in base_obs}
    event_days = sorted({str(e["cluster_day"]) for e in ev})
    all_days = sorted(baseline_days_set | set(event_days))

    if not ev:
        return {
            "n": 0,
            "clusters": 0,
            "baseline_days": len(baseline_days_set),
            "event_days": 0,
            "required_replicates": len(all_days),
            "valid_replicates": 0,
            "undefined_delete_days": all_days,
            "mean": None,
            "cluster_se": None,
            "cluster_t": None,
            "method": method,
            "reason": "no qualifying bottom10 signed events",
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
    common = {
        "n": n,
        "clusters": len(event_days),
        "baseline_days": len(baseline_days_set),
        "event_days": len(event_days),
        "required_replicates": len(all_days),
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

    for day in all_days:
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
            "reason": (
                "at least one required delete-one-day replication is undefined"
            ),
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


def _attach_full_sample_baselines(
    bars: Sequence[Bar],
    events: list[dict],
) -> None:
    for h in PRIMARY_HORIZONS:
        obs = _signed_baseline_observations(bars, h)
        by_clock: dict[int, list[float]] = defaultdict(list)
        for _, clock, y in obs:
            by_clock[clock].append(y)
        means = {clock: statistics.fmean(xs) for clock, xs in by_clock.items() if xs}

        for event in events:
            r = event.get(f"signed_fwd_{h}b")
            baseline = means.get(int(event["utc_minute"]))
            event[f"baseline_signed_{h}b"] = baseline
            event[f"directional_excess_{h}b"] = (
                float(r) - baseline
                if isinstance(r, (int, float)) and baseline is not None
                else None
            )


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def discovery_gate(primary: dict) -> dict:
    observed = {}
    signs: list[int] = []
    passed = True

    for h in PRIMARY_HORIZONS:
        name = f"directional_excess_{h}b"
        stats = primary[name]
        mean = stats.get("mean")
        t = stats.get("cluster_t")

        mean_ok = isinstance(mean, (int, float)) and math.isfinite(float(mean)) and float(mean) != 0.0
        t_ok = isinstance(t, (int, float)) and math.isfinite(float(t)) and abs(float(t)) > 2.0
        sign = _sign(float(mean)) if mean_ok else 0
        signs.append(sign)

        observed[name] = {
            "mean": mean,
            "complete_jackknife_t": t,
            "nonzero_mean": mean_ok,
            "abs_t_above_2": t_ok,
            "sign": sign,
            "reason": stats.get("reason"),
            "required_replicates": stats.get("required_replicates"),
            "valid_replicates": stats.get("valid_replicates"),
            "undefined_delete_days": stats.get("undefined_delete_days"),
        }
        passed = passed and mean_ok and t_ok

    same_nonzero_sign = len(set(signs)) == 1 and signs[0] != 0
    passed = passed and same_nonzero_sign
    frozen_sign = signs[0] if passed else None

    return {
        "primary_state": PRIMARY_STATE,
        "primary_metrics": [
            "directional_excess_4b",
            "directional_excess_8b",
        ],
        "joint_gate": "ALL_REQUIRED",
        "requirements": {
            "both_means_nonzero": True,
            "same_sign_4b_8b": True,
            "each_abs_complete_jackknife_t_gt": 2.0,
        },
        "observed": observed,
        "same_nonzero_sign": same_nonzero_sign,
        "status": "PASS" if passed else "FAIL",
        "frozen_confirmation_sign": frozen_sign,
    }


def run_from_index(index_path: Path, progress_path: Path) -> dict:
    progress_path = _validate_progress_path(progress_path)
    if CANONICAL_OUTPUT.exists():
        raise RuntimeError(
            "existing R28 discovery result detected; refusing scientific overwrite"
        )

    cleaned = _cleanup_stale_transients()

    _write_progress(
        progress_path,
        phase="starting",
        fraction=0.0,
        cleaned_transients=cleaned,
    )

    index_content = discovery._read_canonical_r15_index(index_path)

    def builder_progress(state: dict) -> None:
        completed = int(state["completed"])
        total = int(state["total"])
        fraction = 0.72 * (completed / total if total else 0.0)
        _write_progress(
            progress_path,
            phase="build_m5",
            fraction=fraction,
            completed=completed,
            total=total,
            last_opened_payload_date=state.get("last_opened_payload_date"),
            decoded_m1=state.get("decoded_m1"),
            emitted_m5=state.get("emitted_m5"),
        )
        print(
            f"progress build days={completed}/{total} "
            f"m5={state.get('emitted_m5', 0)} fraction={fraction:.6f}",
            flush=True,
        )

    with tempfile.TemporaryDirectory(prefix="guardian_r28_discovery_v100_") as td:
        verified_index = Path(td) / "verified_r15_index.csv"
        verified_index.write_bytes(index_content)

        generated_csv = Path(td) / "sealed_discovery_m5.csv"
        receipt = sealed_builder.build(
            verified_index,
            generated_csv,
            progress_callback=builder_progress,
        )
        discovery._validate_builder_receipt(receipt, generated_csv)

        _write_progress(
            progress_path,
            phase="load_m5",
            fraction=0.75,
            builder_receipt=receipt,
        )
        bars = discovery.load_generated_discovery_bars(generated_csv)

        _write_progress(
            progress_path,
            phase="extract_bottom10",
            fraction=0.80,
            rows=len(bars),
        )
        raw_events = r28_event_extractor(bars)
        events = _event_signed_forward_returns(bars, raw_events)
        _attach_full_sample_baselines(bars, events)

        _write_progress(
            progress_path,
            phase="jackknife_4b",
            fraction=0.86,
            rows=len(bars),
            event_count=len(events),
        )
        j4 = complete_signed_excess_day_jackknife(bars, events, 4)

        _write_progress(
            progress_path,
            phase="jackknife_8b",
            fraction=0.93,
            rows=len(bars),
            event_count=len(events),
        )
        j8 = complete_signed_excess_day_jackknife(bars, events, 8)

        primary = {
            "directional_excess_4b": j4,
            "directional_excess_8b": j8,
        }
        gate = discovery_gate(primary)

        naive = {}
        for h in PRIMARY_HORIZONS:
            naive[f"signed_fwd_{h}b"] = signed_stats(
                e[f"signed_fwd_{h}b"]
                for e in events
                if isinstance(e.get(f"signed_fwd_{h}b"), (int, float))
            )
            naive[f"directional_excess_{h}b"] = signed_stats(
                e[f"directional_excess_{h}b"]
                for e in events
                if isinstance(e.get(f"directional_excess_{h}b"), (int, float))
            )

        _write_progress(
            progress_path,
            phase="serialize",
            fraction=0.99,
            rows=len(bars),
            event_count=len(events),
            gate_status=gate["status"],
            frozen_confirmation_sign=gate["frozen_confirmation_sign"],
        )

        return {
            "schema": 1,
            "research": "R28",
            "version": "1.00",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "discovery",
            "source_contract": (
                "sealed discovery builder + canonical pinned R15 index"
            ),
            "source_index": str(index_path),
            "source_index_sha256": discovery.CANONICAL_R15_INDEX_SHA256,
            "builder_receipt": receipt,
            "rows": len(bars),
            "first_epoch": bars[0].epoch,
            "last_epoch": bars[-1].epoch,
            "stage_boundaries": {
                "discovery_start": discovery.DISCOVERY_START.isoformat(),
                "discovery_end": discovery.DISCOVERY_END.isoformat(),
                "confirmation": "INACCESSIBLE_IN_V1_00",
                "preoos_2025": "INACCESSIBLE_IN_V1_00",
                "protected_2026_plus": "HARD_SEALED",
            },
            "confirmation_opened": False,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "conditioning_state": "exact R22/R27 bottom10 compression state",
            "doctrine": (
                "signed discovery only; joint 4b+8b same-sign complete-jackknife "
                "gate; sign frozen only after PASS; no PnL optimization"
            ),
            "cleaned_transients": cleaned,
            "event_count": len(events),
            "primary_complete_jackknife": primary,
            "naive_descriptive": naive,
            "discovery_gate": gate,
            "events": events,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--index",
        required=True,
        type=Path,
        help="Canonical R15 index only; discovery admission is enforced.",
    )
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--progress", required=True, type=Path)
    a = ap.parse_args()

    output = _validate_output_path(a.output)
    progress_path = _validate_progress_path(a.progress)

    payload = run_from_index(a.index, progress_path)
    _atomic_json(output, payload)
    _write_progress(
        progress_path,
        phase="complete",
        fraction=1.0,
        output=str(output),
        rows=payload["rows"],
        event_count=payload["event_count"],
        gate_status=payload["discovery_gate"]["status"],
        frozen_confirmation_sign=payload["discovery_gate"][
            "frozen_confirmation_sign"
        ],
    )

    print(
        json.dumps(
            {
                "research": "R28",
                "stage": "discovery",
                "gate_status": payload["discovery_gate"]["status"],
                "frozen_confirmation_sign": payload["discovery_gate"][
                    "frozen_confirmation_sign"
                ],
                "directional_excess_4b": payload["discovery_gate"]["observed"][
                    "directional_excess_4b"
                ],
                "directional_excess_8b": payload["discovery_gate"]["observed"][
                    "directional_excess_8b"
                ],
                "events": payload["event_count"],
                "rows": payload["rows"],
                "confirmation_opened": False,
                "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
