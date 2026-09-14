#!/usr/bin/env python3
"""Cluster-robust audit for R16-R20 discovery outputs.

Reads the existing discovery JSON only. It does not touch confirmation/pre-OOS data.
Computes cluster-robust standard errors for the mean with one cluster per event day.
This is intended to correct the naive t-stat inflation caused by overlapping intraday events.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import fmean

DAY_KEYS = ("day_london", "day_new_york", "day")
METRIC_PREFIXES = ("continuation_", "reversal_", "breakout_", "rejection_", "post_")


def _day_key(event: dict) -> str:
    for key in DAY_KEYS:
        value = event.get(key)
        if value:
            return str(value)
    raise RuntimeError(f"event has no day key: {event}")


def _finite_number(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def cluster_stats(events: list[dict], metric: str) -> dict:
    rows = [(float(e[metric]), _day_key(e)) for e in events if _finite_number(e.get(metric))]
    if not rows:
        return {"n": 0, "clusters": 0, "mean": None, "cluster_se": None, "cluster_t": None}

    xs = [x for x, _ in rows]
    mean = fmean(xs)
    by_cluster: dict[str, list[float]] = defaultdict(list)
    for x, day in rows:
        by_cluster[day].append(x)

    n = len(xs)
    g = len(by_cluster)
    if g < 2:
        return {"n": n, "clusters": g, "mean": mean, "cluster_se": None, "cluster_t": None}

    # Cluster-robust variance of the sample mean. For each cluster g,
    # S_g = sum_i(x_ig - mean). Finite-cluster correction G/(G-1).
    ss = 0.0
    for vals in by_cluster.values():
        s = sum(v - mean for v in vals)
        ss += s * s
    var_mean = (g / (g - 1.0)) * ss / (n * n)
    se = math.sqrt(var_mean) if var_mean >= 0 else None
    t = mean / se if se and se > 0 else None
    return {"n": n, "clusters": g, "mean": mean, "cluster_se": se, "cluster_t": t}


def run(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("stage") != "discovery":
        raise RuntimeError(f"refusing non-discovery input: stage={payload.get('stage')!r}")
    if payload.get("protected_2026_opened") is not False:
        raise RuntimeError("protected 2026 flag is not false")
    if payload.get("pre_oos_2025_opened") is not False:
        raise RuntimeError("pre-OOS 2025 flag is not false")

    out = {
        "schema": 1,
        "audit": "R16-R20 discovery cluster-robust mean audit",
        "source": str(path),
        "stage": "discovery",
        "protected_2026_opened": False,
        "pre_oos_2025_opened": False,
        "results": {},
    }
    for name, item in payload["results"].items():
        events = item.get("events", [])
        metrics = sorted({
            key
            for event in events
            for key in event
            if key.startswith(METRIC_PREFIXES)
        })
        out["results"][name] = {
            "event_count": len(events),
            "metrics": {metric: cluster_stats(events, metric) for metric in metrics},
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output")
    args = ap.parse_args()

    result = run(Path(args.input))
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for name in ("R16", "R17", "R18", "R19", "R20"):
        print(f"\n===== {name} CLUSTERED =====")
        metrics = result["results"].get(name, {}).get("metrics", {})
        for metric, s in metrics.items():
            mean = s["mean"]
            t = s["cluster_t"]
            print(
                f"{metric:20s} n={s['n']:6d} days={s['clusters']:5d} "
                f"mean={mean:+.12g} cluster_t={t:+.6f}" if mean is not None and t is not None
                else f"{metric:20s} n={s['n']:6d} days={s['clusters']:5d} mean={mean} cluster_t={t}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
