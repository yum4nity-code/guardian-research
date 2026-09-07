#!/usr/bin/env python3
"""Descriptive-only deep audit of already-seen D053 2024-2025 trades.

No MT5 execution. No D053 verdict change. No D054 rule/gate change.
"""
from __future__ import annotations

import contextlib
import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import experiment
import result_transport
import runner
import state_tools
import tester

ROOT = Path(__file__).resolve().parents[2]
D053_ID = "D053-US-INDEX-ORB30-ENTRY-ALPHA-V0"
D053_SOURCE_SHA = "d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad"
SYMBOLS = ["SPX500", "NDX100", "US30", "US2000"]


class AuditError(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def f(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except Exception as exc:
        raise AuditError(f"invalid {key}={row.get(key)!r}") from exc
    if not math.isfinite(value):
        raise AuditError(f"non-finite {key}")
    return value


def pf(values: list[float]) -> float | None:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def summary(values: list[float]) -> dict[str, Any]:
    p = pf(values)
    return {
        "n": len(values),
        "total_r": sum(values),
        "mean_r": statistics.fmean(values) if values else 0.0,
        "median_r": statistics.median(values) if values else 0.0,
        "pf": None if p is None or math.isinf(p) else p,
        "pf_infinite": bool(p is not None and math.isinf(p)),
        "win_rate": (sum(v > 0 for v in values) / len(values)) if values else 0.0,
    }


def parse_day(day_key: str) -> date:
    text = str(day_key)
    if len(text) != 8 or not text.isdigit():
        raise AuditError(f"invalid day_key={text}")
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def parse_time(text: str) -> datetime:
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise AuditError(f"unsupported MT5 datetime={text!r}")


def nth_weekday(year: int, month: int, weekday: int, nth: int) -> date:
    d = date(year, month, 1)
    delta = (weekday - d.weekday()) % 7
    return date(year, month, 1 + delta + 7 * (nth - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    d = date.fromordinal(next_month.toordinal() - 1)
    return date.fromordinal(d.toordinal() - ((d.weekday() - weekday) % 7))


def dst_mismatch_proxy(d: date) -> bool:
    # US: second Sunday Mar -> first Sunday Nov. EU server proxy: last Sunday Mar -> last Sunday Oct.
    us_start = nth_weekday(d.year, 3, 6, 2)
    us_end = nth_weekday(d.year, 11, 6, 1)
    eu_start = last_weekday(d.year, 3, 6)
    eu_end = last_weekday(d.year, 10, 6)
    us_dst = us_start <= d < us_end
    eu_dst = eu_start <= d < eu_end
    return us_dst != eu_dst


def locate_batch() -> tuple[Path, dict[str, Any]]:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    base = workspace / "d053" / "development"
    if not base.exists():
        raise AuditError(f"D053 development workspace missing: {base}")
    candidates = sorted(base.glob("*/batch.json"), reverse=True)
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("status") != "D053_BATCH_PASS_INTEGRITY":
            continue
        if str(payload.get("source_sha256", "")).lower() != D053_SOURCE_SHA:
            continue
        tests = payload.get("tests", [])
        if [t.get("symbol") for t in tests] != SYMBOLS:
            continue
        if all(Path(str(t.get("trades", {}).get("path", ""))).is_file() for t in tests):
            return path, payload
    raise AuditError("no complete local D053 2024-2025 batch with all four trade CSVs found")


def load_rows(batch: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for test in batch["tests"]:
        symbol = test["symbol"]
        path = Path(test["trades"]["path"])
        parsed = tester.read_semicolon_csv(path)
        if len(parsed) != int(test["integrity"]["trades"]):
            raise AuditError(f"{symbol}: trade-row count changed since authoritative batch")
        for row in parsed:
            if symbol not in str(row.get("symbol", "")):
                raise AuditError(f"{symbol}: row symbol mismatch")
            rows.append(row)
    if len(rows) != 2042:
        raise AuditError(f"expected authoritative D053 n=2042, got {len(rows)}")
    return rows


def grouped_stats(rows: list[dict[str, str]], key_fn) -> dict[str, Any]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[str(key_fn(row))].append(f(row, "net_r"))
    return {key: summary(groups[key]) for key in sorted(groups)}


def rolling_months(month_stats: dict[str, dict[str, Any]], window: int) -> dict[str, Any]:
    months = sorted(month_stats)
    out: list[dict[str, Any]] = []
    for i in range(window - 1, len(months)):
        selected = months[i - window + 1:i + 1]
        n = sum(int(month_stats[m]["n"]) for m in selected)
        total = sum(float(month_stats[m]["total_r"]) for m in selected)
        out.append({"from": selected[0], "to": selected[-1], "n": n, "total_r": total, "mean_r": total / n if n else 0.0})
    if not out:
        return {"window_months": window, "series": []}
    return {
        "window_months": window,
        "worst": min(out, key=lambda x: x["mean_r"]),
        "best": max(out, key=lambda x: x["mean_r"]),
        "negative_windows": sum(x["total_r"] < 0 for x in out),
        "positive_windows": sum(x["total_r"] > 0 for x in out),
        "series": out,
    }


def risk_quartiles(rows: list[dict[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for symbol in SYMBOLS:
        items: list[tuple[float, float]] = []
        for row in rows:
            if symbol not in str(row["symbol"]):
                continue
            entry = f(row, "entry")
            stop = f(row, "initial_stop")
            risk_pct = abs(entry - stop) / entry if entry > 0 else 0.0
            items.append((risk_pct, f(row, "net_r")))
        items.sort(key=lambda x: x[0])
        buckets: dict[str, Any] = {}
        n = len(items)
        for q in range(4):
            lo = (n * q) // 4
            hi = (n * (q + 1)) // 4
            chunk = items[lo:hi]
            buckets[f"Q{q+1}"] = {
                "risk_pct_min": chunk[0][0] if chunk else None,
                "risk_pct_max": chunk[-1][0] if chunk else None,
                **summary([x[1] for x in chunk]),
            }
        result[symbol] = buckets
    return result


def build_audit(rows: list[dict[str, str]], batch_path: Path) -> dict[str, Any]:
    net = [f(row, "net_r") for row in rows]
    stress = [f(row, "net_r_spread_x1_5") for row in rows]

    monthly_values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        monthly_values[str(row["day_key"])[:6]].append(f(row, "net_r"))
    month_stats = {month: summary(monthly_values[month]) for month in sorted(monthly_values)}
    ordered_months = sorted(month_stats.items(), key=lambda kv: kv[1]["mean_r"])

    latency_groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        t = parse_time(str(row["entry_time"]))
        mins = (t.hour * 60 + t.minute) - 17 * 60 + t.second / 60.0
        if mins < 15:
            bucket = "00_15m"
        elif mins < 30:
            bucket = "15_30m"
        elif mins < 60:
            bucket = "30_60m"
        elif mins < 120:
            bucket = "60_120m"
        else:
            bucket = "120m_plus"
        latency_groups[bucket].append(f(row, "net_r"))

    dst_groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        mismatch = dst_mismatch_proxy(parse_day(str(row["day_key"])))
        dst_groups["MISMATCH_PROXY" if mismatch else "ALIGNED_PROXY"].append(f(row, "net_r"))

    audit = {
        "schema_version": 1,
        "status": "D053_DESCRIPTIVE_AUDIT_COMPLETE_NO_VERDICT_CHANGE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": D053_ID,
        "source_sha256": D053_SOURCE_SHA,
        "source_batch": str(batch_path),
        "scientific_boundary": {
            "data": "D053 already-seen 2024-2025 only",
            "d053_formal_verdict_unchanged": "D053_REJECT_V0",
            "d054_frozen_before_this_audit": True,
            "no_filter_or_parameter_promotion_from_audit": True,
        },
        "aggregate": {**summary(net), "stress_total_r": sum(stress)},
        "by_symbol": grouped_stats(rows, lambda r: str(r["symbol"])),
        "by_side": grouped_stats(rows, lambda r: str(r["side"])),
        "by_weekday": grouped_stats(rows, lambda r: parse_day(str(r["day_key"])).strftime("%A")),
        "by_exit_reason": grouped_stats(rows, lambda r: str(r["exit_reason"])),
        "entry_latency_from_17_server": {key: summary(values) for key, values in sorted(latency_groups.items())},
        "dst_alignment_proxy": {key: summary(values) for key, values in sorted(dst_groups.items())},
        "monthly": month_stats,
        "positive_months": sum(v["total_r"] > 0 for v in month_stats.values()),
        "negative_months": sum(v["total_r"] < 0 for v in month_stats.values()),
        "worst_5_months": [{"month": m, **s} for m, s in ordered_months[:5]],
        "best_5_months": [{"month": m, **s} for m, s in ordered_months[-5:][::-1]],
        "rolling_3m": rolling_months(month_stats, 3),
        "rolling_6m": rolling_months(month_stats, 6),
        "risk_width_quartiles_by_symbol": risk_quartiles(rows),
        "path": {
            "mean_mfe_r": statistics.fmean(f(r, "mfe_r") for r in rows),
            "mean_mae_r": statistics.fmean(f(r, "mae_r") for r in rows),
            "mean_time_to_mfe_minutes": statistics.fmean(f(r, "time_to_mfe_minutes") for r in rows if str(r.get("time_to_mfe_minutes", "")).strip()),
            "mean_time_to_mae_minutes": statistics.fmean(f(r, "time_to_mae_minutes") for r in rows if str(r.get("time_to_mae_minutes", "")).strip()),
        },
        "session_end_rows": sum(str(r.get("exit_reason")) == "SESSION_END" for r in rows),
        "integrity_events": 0,
        "autosync_used": False,
    }
    return audit


@contextlib.contextmanager
def d053_publish_context() -> Iterator[None]:
    original = runner.load_context
    state = state_tools.load_state()
    manifest_path, manifest = experiment.load_manifest("D053")

    def local_context(identifier: str):
        accepted = {"D053", D053_ID.upper(), str(manifest_path).upper(), str(manifest_path.relative_to(ROOT)).upper()}
        if str(identifier).upper() not in accepted:
            raise runner.RunnerError(f"D053 audit context refuses unrelated identifier: {identifier}")
        return state, manifest_path, manifest

    runner.load_context = local_context
    try:
        yield
    finally:
        runner.load_context = original


def run_audit() -> dict[str, Any]:
    batch_path, batch = locate_batch()
    rows = load_rows(batch)
    audit = build_audit(rows, batch_path)
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    local = workspace / "d053" / "descriptive-audit" / stamp() / "d053-descriptive-audit.json"
    runner.write_receipt(local, audit)
    audit["local_path"] = str(local)
    with d053_publish_context():
        audit["github_transport"] = result_transport.safe_publish_event("D053", "development", "d053-descriptive-audit", audit)
    return audit


def main() -> int:
    audit = run_audit()
    print(json.dumps(audit, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
