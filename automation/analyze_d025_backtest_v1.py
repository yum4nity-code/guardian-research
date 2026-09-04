#!/usr/bin/env python3
import argparse
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

HORIZONS = ["1H", "4H", "8H", "24H", "48H"]
HORIZON_RANK = {h: i for i, h in enumerate(HORIZONS)}


def read_csv(path: Path):
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def is_nonzero(v):
    try:
        return int(float(v or 0)) != 0
    except Exception:
        return False


def safe_mean(xs):
    xs = [x for x in xs if x is not None]
    return statistics.mean(xs) if xs else None


def safe_median(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def pct(n, d):
    return round(100.0 * n / d, 3) if d else None


def sha256(path: Path):
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--from-date", required=True)
    ap.add_argument("--to-date", required=True)
    ap.add_argument("--host-symbol", required=True)
    ap.add_argument("--symbol1", required=True)
    ap.add_argument("--symbol2", required=True)
    ap.add_argument("--terminal-label", default="FundedNext")
    ap.add_argument("--model", default="4")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    events_path = run_dir / "events.csv"
    trades_path = run_dir / "virtual_trades.csv"
    outcomes_path = run_dir / "outcomes.csv"
    events = read_csv(events_path)
    trades = read_csv(trades_path)
    outcomes = read_csv(outcomes_path)

    event_map = defaultdict(list)
    for row in events:
        eid = (row.get("event_id") or "").strip()
        if eid:
            event_map[eid].append(row)

    trade_by_event = {}
    for row in trades:
        eid = (row.get("event_id") or "").strip()
        if eid:
            trade_by_event[eid] = row

    outcomes_by_event = defaultdict(list)
    for row in outcomes:
        eid = (row.get("event_id") or "").strip()
        if eid:
            outcomes_by_event[eid].append(row)

    stage_counts = Counter()
    failure_counts = Counter()
    valid_ids = set()
    for eid, rows in event_map.items():
        transitions = [r.get("transition", "") for r in rows]
        for stage in ["SWEEP", "CASCADE", "EXHAUSTION", "RECLAIM"]:
            if stage in transitions:
                stage_counts[stage] += 1
        if any(t.startswith("VALID_SIGNAL") and "REJECTED" not in t for t in transitions):
            stage_counts["VALID_SIGNAL"] += 1
            valid_ids.add(eid)
        for t in transitions:
            if t.startswith("FAILED_"):
                failure_counts[t] += 1

    # Ensure every actual virtual trade is considered a valid signal even if an event CSV line is missing.
    valid_ids.update(trade_by_event.keys())

    horizon_stats = {}
    for h in HORIZONS:
        rows = [r for r in outcomes if r.get("horizon") == h]
        n = len(rows)
        horizon_stats[h] = {
            "n": n,
            "mfe_r_mean": safe_mean([fnum(r.get("mfe_r")) for r in rows]),
            "mfe_r_median": safe_median([fnum(r.get("mfe_r")) for r in rows]),
            "mae_r_mean": safe_mean([fnum(r.get("mae_r")) for r in rows]),
            "mae_r_median": safe_median([fnum(r.get("mae_r")) for r in rows]),
            "stop_touched": sum(is_nonzero(r.get("stop_utc")) for r in rows),
            "ambiguous_same_m1": sum((r.get("ambiguous_same_m1") or "").upper() == "YES" for r in rows),
        }
        for level in range(1, 6):
            key = f"hit{level}_utc"
            hits = sum(is_nonzero(r.get(key)) for r in rows)
            horizon_stats[h][f"hit_{level}r"] = hits
            horizon_stats[h][f"hit_{level}r_pct"] = pct(hits, n)

    latest_outcome = {}
    for eid, rows in outcomes_by_event.items():
        latest_outcome[eid] = max(rows, key=lambda r: HORIZON_RANK.get(r.get("horizon"), -1))

    by_symbol = defaultdict(lambda: Counter())
    by_level = defaultdict(lambda: Counter())
    compact_rows = []
    for eid, rows in event_map.items():
        first = rows[0]
        transitions = [r.get("transition", "") for r in rows]
        symbol = first.get("symbol", "")
        level = first.get("level_family", "")
        if "SWEEP" in transitions:
            by_symbol[symbol]["sweeps"] += 1
            by_level[level]["sweeps"] += 1
        if eid in valid_ids:
            by_symbol[symbol]["valid_signals"] += 1
            by_level[level]["valid_signals"] += 1
        for t in transitions:
            if t.startswith("FAILED_"):
                by_symbol[symbol]["failed"] += 1
                by_level[level]["failed"] += 1

        out = latest_outcome.get(eid, {})
        trade = trade_by_event.get(eid, {})
        reached = "SWEEP"
        for s in ["CASCADE", "EXHAUSTION", "RECLAIM"]:
            if s in transitions:
                reached = s
        if eid in valid_ids:
            reached = "VALID_SIGNAL"
        failure = next((t for t in transitions if t.startswith("FAILED_")), "")
        compact_rows.append({
            "event_id": eid,
            "symbol": symbol,
            "side": first.get("side", ""),
            "level": level,
            "sweep_utc": next((r.get("utc_text", "") for r in rows if r.get("transition") == "SWEEP"), ""),
            "reached": reached,
            "failure": failure,
            "entry": trade.get("entry", ""),
            "virtual_sl": trade.get("virtual_sl", ""),
            "risk": trade.get("risk", ""),
            "latest_horizon": out.get("horizon", ""),
            "mfe_r": out.get("mfe_r", ""),
            "mae_r": out.get("mae_r", ""),
            "hit1": out.get("hit1_utc", ""),
            "hit2": out.get("hit2_utc", ""),
            "hit3": out.get("hit3_utc", ""),
            "hit4": out.get("hit4_utc", ""),
            "hit5": out.get("hit5_utc", ""),
            "stop": out.get("stop_utc", ""),
            "ambiguous": out.get("ambiguous_same_m1", ""),
        })

    complete_48 = {r.get("event_id") for r in outcomes if r.get("horizon") == "48H" and r.get("event_id")}
    total_trades = len(trade_by_event)
    censored_48 = max(0, total_trades - len(complete_48))

    summary = {
        "schema": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_id": args.run_id,
        "terminal_label": args.terminal_label,
        "tester": {
            "host_symbol": args.host_symbol,
            "symbol1": args.symbol1,
            "symbol2": args.symbol2,
            "period": "M1",
            "model": int(args.model),
            "model_label": "Every tick based on real ticks" if str(args.model) == "4" else str(args.model),
            "from_date": args.from_date,
            "to_date": args.to_date,
            "optimization": False,
        },
        "d025": {
            "research_generation": "V0",
            "mt5_version": "1.00",
            "rules_locked": True,
            "trading_orders": False,
        },
        "raw_counts": {
            "event_rows": len(events),
            "unique_events": len(event_map),
            "virtual_trades": total_trades,
            "outcome_rows": len(outcomes),
            "complete_48h": len(complete_48),
            "censored_before_48h": censored_48,
        },
        "funnel": {
            "sweep": stage_counts["SWEEP"],
            "cascade": stage_counts["CASCADE"],
            "exhaustion": stage_counts["EXHAUSTION"],
            "reclaim": stage_counts["RECLAIM"],
            "valid_signal": len(valid_ids),
            "sweep_to_cascade_pct": pct(stage_counts["CASCADE"], stage_counts["SWEEP"]),
            "cascade_to_exhaustion_pct": pct(stage_counts["EXHAUSTION"], stage_counts["CASCADE"]),
            "exhaustion_to_reclaim_pct": pct(stage_counts["RECLAIM"], stage_counts["EXHAUSTION"]),
            "sweep_to_valid_pct": pct(len(valid_ids), stage_counts["SWEEP"]),
        },
        "failures": dict(failure_counts.most_common()),
        "horizons": horizon_stats,
        "by_symbol": {k: dict(v) for k, v in sorted(by_symbol.items())},
        "by_level": {k: dict(v) for k, v in sorted(by_level.items())},
        "files": {
            "events_sha256": sha256(events_path),
            "virtual_trades_sha256": sha256(trades_path),
            "outcomes_sha256": sha256(outcomes_path),
        },
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    compact_path = out_dir / "events_compact.csv"
    with compact_path.open("w", encoding="utf-8", newline="") as f:
        fields = list(compact_rows[0].keys()) if compact_rows else ["event_id","symbol","side","level","sweep_utc","reached","failure","entry","virtual_sl","risk","latest_horizon","mfe_r","mae_r","hit1","hit2","hit3","hit4","hit5","stop","ambiguous"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(compact_rows)

    md = []
    md.append(f"# D025 LER V0 — FundedNext backtest — {args.run_id}")
    md.append("")
    md.append(f"Period: **{args.from_date} -> {args.to_date}**  ")
    md.append(f"Symbols: **{args.symbol1} + {args.symbol2}**  ")
    md.append("Model: **Every tick based on real ticks (Model=4)**  ")
    md.append("Orders: **NONE — virtual research only**")
    md.append("")
    md.append("## Funnel")
    md.append("")
    md.append("| Stage | Unique events |")
    md.append("|---|---:|")
    for label, key in [("SWEEP","sweep"),("CASCADE","cascade"),("EXHAUSTION","exhaustion"),("RECLAIM","reclaim"),("VALID_SIGNAL","valid_signal")]:
        md.append(f"| {label} | {summary['funnel'][key]} |")
    md.append("")
    md.append(f"Virtual trades: **{total_trades}**; complete 48h: **{len(complete_48)}**; censored before 48h: **{censored_48}**.")
    md.append("")
    md.append("## Outcome snapshots")
    md.append("")
    md.append("| Horizon | N | Median MFE (R) | Median MAE (R) | 1R hit | 2R hit | 3R hit | 4R hit | 5R hit | Stop touched |")
    md.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for h in HORIZONS:
        s = horizon_stats[h]
        def fmt(x): return "" if x is None else f"{x:.3f}"
        md.append(f"| {h} | {s['n']} | {fmt(s['mfe_r_median'])} | {fmt(s['mae_r_median'])} | {s['hit_1r']} | {s['hit_2r']} | {s['hit_3r']} | {s['hit_4r']} | {s['hit_5r']} | {s['stop_touched']} |")
    md.append("")
    md.append("## Failure reasons")
    md.append("")
    if failure_counts:
        for k, v in failure_counts.most_common():
            md.append(f"- `{k}`: {v}")
    else:
        md.append("- None recorded.")
    md.append("")
    md.append("## Scientific note")
    md.append("")
    md.append("This run does not tune any D025 threshold. It evaluates the preregistered Core MT5 V0 rules only. Binance/Bybit features are not used by the signal state machine in this backtest.")
    (out_dir / "SUMMARY.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "run_id": args.run_id,
        "sweeps": stage_counts["SWEEP"],
        "valid_signals": len(valid_ids),
        "virtual_trades": total_trades,
        "complete_48h": len(complete_48),
        "summary": str(out_dir / "summary.json"),
    }))


if __name__ == "__main__":
    main()
