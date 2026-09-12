#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import r5_pre_oos_economic_robustness_v1_00 as econ
import r6_xau_low_turnover_breakout_v1_00 as r6

START = pd.Timestamp("2017-01-01T00:00:00Z")
END = pd.Timestamp("2026-08-01T00:00:00Z")


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def hb(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if not path:
        return
    obj = {"completed": int(completed), "total": int(total), "stage": stage, "updated_at_utc": datetime.now(timezone.utc).isoformat()}
    if extra:
        obj.update(extra)
    atomic_json(path, obj)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def load_rates(data_dir: Path, tf: str) -> pd.DataFrame:
    parts = []
    for year in range(2017, 2027):
        p = data_dir / f"xauusd_{tf.lower()}_{year}.csv"
        if not p.exists():
            raise RuntimeError(f"missing long-history {tf} file: {p}")
        z = pd.read_csv(p)
        req = {"server_epoch", "open", "high", "low", "close"}
        if not req.issubset(z.columns):
            raise RuntimeError(f"{tf} invalid columns in {p}")
        t = pd.to_datetime(pd.to_numeric(z.server_epoch, errors="raise").astype("int64"), unit="s", utc=True)
        part = pd.DataFrame({
            "time": t,
            "open": pd.to_numeric(z.open, errors="raise"),
            "high": pd.to_numeric(z.high, errors="raise"),
            "low": pd.to_numeric(z.low, errors="raise"),
            "close": pd.to_numeric(z.close, errors="raise"),
        })
        parts.append(part)
    out = pd.concat(parts, ignore_index=True).sort_values("time").drop_duplicates("time").reset_index(drop=True)
    out = out[(out.time >= START) & (out.time < END)].reset_index(drop=True)
    if out.empty or not out.time.is_monotonic_increasing or out.time.duplicated().any():
        raise RuntimeError(f"{tf} long-history sequence invalid")
    return out


def load_mask(path: Path) -> list[tuple[int, int]]:
    if not path.exists():
        raise RuntimeError(f"news mask missing: {path}")
    z = pd.read_csv(path)
    req = {"mask_start_server_epoch", "mask_end_server_epoch"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"mask invalid: {path}")
    ints = sorted((int(a), int(b)) for a, b in zip(z.mask_start_server_epoch, z.mask_end_server_epoch))
    return ints


def epoch_seconds(series: pd.Series) -> np.ndarray:
    return np.fromiter((int(pd.Timestamp(v).value // 1_000_000_000) for v in series), dtype=np.int64, count=len(series))


def apply_mask(source: pd.DataFrame, intervals: list[tuple[int, int]], tf_seconds: int = 300) -> pd.DataFrame:
    epochs = epoch_seconds(source.time)
    keep = np.ones(len(source), dtype=bool)
    j = 0
    for i, bar_start in enumerate(epochs):
        bar_end = int(bar_start) + tf_seconds
        while j < len(intervals) and intervals[j][1] < bar_start:
            j += 1
        k = j
        while k < len(intervals) and intervals[k][0] < bar_end:
            s, e = intervals[k]
            if e >= bar_start:
                keep[i] = False
                break
            k += 1
    return source.loc[keep].reset_index(drop=True)


def _ts(ns: int) -> pd.Timestamp:
    return pd.Timestamp(int(ns), unit="ns", tz="UTC")


def replay_window(source: pd.DataFrame, raw_m1: pd.DataFrame, signals: np.ndarray, horizon: int, direction: int, start: pd.Timestamp, end: pd.Timestamp):
    s_ns = source.time.array.as_unit("ns").asi8
    r_ns = raw_m1.time.array.as_unit("ns").asi8
    r_open = raw_m1.open.to_numpy(float)
    start_ns, end_ns = int(start.value), int(end.value)
    signals = np.asarray(signals, dtype=bool)
    ledger = []
    state = None
    counts = {"signals_total": int(signals.sum()), "ignored_overlap_signals": 0, "excluded_boundary_signals": 0, "missing_reference_trades": 0, "executable_trades": 0}

    def close_state(st):
        xi = int(np.searchsorted(r_ns, st["exit_available_ns"], side="left"))
        if st["entry_idx"] >= len(r_ns) or xi >= len(r_ns):
            counts["missing_reference_trades"] += 1
            return
        en = int(r_ns[st["entry_idx"]]); ex = int(r_ns[xi])
        if not (start_ns <= en < ex < end_ns):
            counts["excluded_boundary_signals"] += 1
            return
        oe, ox = float(r_open[st["entry_idx"]]), float(r_open[xi])
        ledger.append({
            "signal_time": _ts(st["signal_ns"]).isoformat(),
            "entry_time": _ts(en).isoformat(),
            "exit_time": _ts(ex).isoformat(),
            "entry_open": oe,
            "exit_open": ox,
            "direction": int(direction),
            "profiles": {p: econ.cost(oe, ox, direction, p) for p in econ.PROFILES},
        })

    for i in range(len(source)):
        available_ns = int(s_ns[i] + 300 * 1_000_000_000)
        if state is not None and available_ns >= state["exit_available_ns"]:
            close_state(state)
            state = None
        if not signals[i]:
            continue
        if state is not None:
            counts["ignored_overlap_signals"] += 1
            continue
        exit_idx = i + int(horizon) + 1
        if exit_idx >= len(source):
            counts["excluded_boundary_signals"] += 1
            continue
        sig_ns = int(s_ns[i]); exit_available_ns = int(s_ns[exit_idx])
        if not (start_ns <= sig_ns < end_ns) or available_ns >= end_ns or exit_available_ns >= end_ns:
            counts["excluded_boundary_signals"] += 1
            continue
        ei = int(np.searchsorted(r_ns, available_ns, side="left"))
        if ei >= len(r_ns) or not (start_ns <= int(r_ns[ei]) < end_ns):
            counts["missing_reference_trades"] += 1
            continue
        state = {"signal_ns": sig_ns, "entry_idx": ei, "exit_available_ns": exit_available_ns}

    if state is not None:
        close_state(state)
    counts["executable_trades"] = len(ledger)
    return ledger, counts


def signal(rule: dict, source: pd.DataFrame) -> np.ndarray:
    atr = r6.atr14(source)
    return r6.breakout_signal(source, atr, int(rule["lookback_bars"]), float(rule["buffer_atr"]), int(rule["direction"]), rule["session_start"], rule["session_end"])


def metric(ledger, profile: str):
    return econ.stats(ledger, profile)


def filter_ledger(ledger, start: pd.Timestamp, end: pd.Timestamp):
    return [t for t in ledger if start <= pd.Timestamp(t["entry_time"]) and pd.Timestamp(t["exit_time"]) < end]


def max_streak(vals, predicate) -> int:
    best = cur = 0
    for x in vals:
        if predicate(x):
            cur += 1; best = max(best, cur)
        else:
            cur = 0
    return best


def concentration(ledger, profile: str) -> dict:
    vals = [float(t["profiles"][profile]["net"]) for t in ledger]
    pos = sorted((x for x in vals if x > 0), reverse=True)
    total_pos = float(sum(pos))
    return {
        "top1_share_positive_gains": (pos[0] / total_pos) if pos and total_pos else None,
        "top3_share_positive_gains": (sum(pos[:3]) / total_pos) if pos and total_pos else None,
        "top5_share_positive_gains": (sum(pos[:5]) / total_pos) if pos and total_pos else None,
        "max_win_streak": max_streak(vals, lambda x: x > 0),
        "max_loss_streak": max_streak(vals, lambda x: x < 0),
    }


def isolated_year(rule: dict, source: pd.DataFrame, raw: pd.DataFrame, year: int):
    a = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    b = END if year == 2026 else pd.Timestamp(f"{year+1}-01-01T00:00:00Z")
    s = source[(source.time >= a) & (source.time < b)].reset_index(drop=True)
    r = raw[(raw.time >= a) & (raw.time < b)].reset_index(drop=True)
    sig = signal(rule, s)
    led, acc = replay_window(s, r, sig, int(rule["horizon_bars"]), int(rule["direction"]), a, b)
    return led, acc


def compare_known(year_metrics: dict, survivor: dict, cid: str) -> None:
    for year in (2024, 2025):
        got = year_metrics[str(year)]
        exp = survivor[f"y{year}"]
        for profile in ("E1", "STRESS"):
            for key in ("trades", "net", "PF"):
                gv = got[profile][key]; ev = exp[profile][key]
                if key == "trades":
                    ok = int(gv) == int(ev)
                elif gv is None or ev is None:
                    ok = gv is ev
                else:
                    ok = math.isclose(float(gv), float(ev), rel_tol=0.0, abs_tol=1e-7)
                if not ok:
                    raise RuntimeError(f"{cid} canonical replay mismatch {year} {profile} {key}: {gv} != {ev}")


def publish(pub: str | None, status: str, summary: str, artifacts):
    if not pub:
        return
    cmd = ["python", pub, "--phase", "top2-xau-long-history-characterization", "--status", status, "--summary", summary]
    for p in artifacts:
        cmd += ["--artifact", str(p)]
    subprocess.run(cmd, check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preregistration", required=True)
    ap.add_argument("--market-dir", required=True)
    ap.add_argument("--market-manifest", required=True)
    ap.add_argument("--mask-2024-2025", required=True)
    ap.add_argument("--mask-2026", required=True)
    ap.add_argument("--r6-result", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    prereg_path = Path(args.preregistration)
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg["window"]["start"] != "2017-01-01T00:00:00Z" or prereg["window"]["end_exclusive"] != "2026-08-01T00:00:00Z":
        raise RuntimeError("prereg window drift")
    if len(prereg["candidates"]) != 2 or {x["candidate_id"] for x in prereg["candidates"]} != {"R6B-347", "R6B-307"}:
        raise RuntimeError("top-two candidate drift")

    manifest = json.loads(Path(args.market_manifest).read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS" or manifest.get("server") != "FundedNext-Server 2":
        raise RuntimeError("market export not provenance-clean")

    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None
    hb(progress, 0, 6, "load_long_history")
    raw_m1 = load_rates(Path(args.market_dir), "M1")
    raw_m5 = load_rates(Path(args.market_dir), "M5")

    mask2425 = load_mask(Path(args.mask_2024_2025))
    mask26 = [(a, b) for a, b in load_mask(Path(args.mask_2026)) if a < int(END.timestamp())]
    hybrid = apply_mask(raw_m5, sorted(mask2425 + mask26))
    variants = {"RAW_FULL_HISTORY": raw_m5, "HYBRID_CANONICAL": hybrid}

    published = json.loads(Path(args.r6_result).read_text(encoding="utf-8"))
    published_by_id = {x["candidate_id"]: x for x in published.get("survivors", [])}

    result = {
        "schema": 1,
        "phase": "top2-xau-long-history-characterization",
        "status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window": prereg["window"],
        "post_selection_characterization": True,
        "independent_validation": False,
        "retuning_performed": False,
        "live_deployment_authorized": False,
        "market_manifest_sha256": sha256(Path(args.market_manifest)),
        "mask_sha256": {"2024_2025": sha256(Path(args.mask_2024_2025)), "2026": sha256(Path(args.mask_2026))},
        "candidates": {},
    }
    yearly_rows = []
    monthly_rows = []
    hybrid_monthly_by_candidate = {}

    step = 0
    for rule in prereg["candidates"]:
        cid = rule["candidate_id"]
        result["candidates"][cid] = {}
        for variant_name, source in variants.items():
            step += 1
            hb(progress, step, 6, "evaluate", {"candidate_id": cid, "variant": variant_name})
            sig = signal(rule, source)
            ledger, accounting = replay_window(source, raw_m1, sig, int(rule["horizon_bars"]), int(rule["direction"]), START, END)
            full = {p: metric(ledger, p) for p in econ.PROFILES}

            yearly = {}
            for year in range(2017, 2027):
                led_y, acc_y = isolated_year(rule, source, raw_m1, year)
                yearly[str(year)] = {p: metric(led_y, p) for p in econ.PROFILES}
                yearly[str(year)]["accounting"] = acc_y
                for p in econ.PROFILES:
                    yearly_rows.append({"candidate_id": cid, "variant": variant_name, "year": year, "profile": p, **yearly[str(year)][p]})

            if variant_name == "HYBRID_CANONICAL":
                if cid not in published_by_id:
                    raise RuntimeError(f"published R6 survivor missing: {cid}")
                compare_known(yearly, published_by_id[cid], cid)

            monthly = {}
            cur = START
            while cur < END:
                nxt = min(cur + pd.offsets.MonthBegin(1), END)
                if nxt <= cur:
                    nxt = min(cur + pd.DateOffset(months=1), END)
                key = cur.strftime("%Y-%m")
                led_m = filter_ledger(ledger, cur, nxt)
                monthly[key] = {p: metric(led_m, p) for p in econ.PROFILES}
                for p in econ.PROFILES:
                    monthly_rows.append({"candidate_id": cid, "variant": variant_name, "month": key, "profile": p, **monthly[key][p]})
                cur = nxt

            rolling = {}
            month_keys = sorted(monthly)
            for width in (6, 12):
                rows = []
                for i in range(width - 1, len(month_keys)):
                    end_month = pd.Timestamp(month_keys[i] + "-01", tz="UTC") + pd.offsets.MonthBegin(1)
                    start_month = end_month - pd.DateOffset(months=width)
                    led_r = filter_ledger(ledger, start_month, end_month)
                    rows.append({"end_month": month_keys[i], "months": width, **{p: metric(led_r, p) for p in econ.PROFILES}})
                rolling[f"{width}m"] = rows

            full_years = [str(y) for y in range(2017, 2026)]
            e1_pos = sum(yearly[y]["E1"]["net"] > 0 for y in full_years)
            st_pos = sum(yearly[y]["STRESS"]["net"] > 0 for y in full_years)
            positive_year_nets = [max(0.0, float(yearly[y]["E1"]["net"])) for y in full_years]
            pos_sum = sum(positive_year_nets)
            max_share = max(positive_year_nets) / pos_sum if pos_sum > 0 else None
            screen_cfg = prereg["operational_screen"]
            screen = {
                "full_e1_net": full["E1"]["net"] > screen_cfg["full_e1_net_gt"],
                "full_stress_net": full["STRESS"]["net"] > screen_cfg["full_stress_net_gt"],
                "full_e1_ex_best": full["E1"]["ex_best_positive_net"] > screen_cfg["full_e1_ex_best_gt"],
                "positive_year_fraction_e1": (e1_pos / len(full_years)) >= screen_cfg["minimum_positive_full_year_fraction_e1"],
                "positive_year_fraction_stress": (st_pos / len(full_years)) >= screen_cfg["minimum_positive_full_year_fraction_stress"],
                "2026_jan_jul_e1": yearly["2026"]["E1"]["net"] > screen_cfg["2026_jan_jul_e1_net_gt"],
                "2026_jan_jul_stress": yearly["2026"]["STRESS"]["net"] > screen_cfg["2026_jan_jul_stress_net_gt"],
                "single_year_concentration": max_share is not None and max_share <= screen_cfg["maximum_single_year_share_of_positive_e1_net"],
            }
            screen["all_descriptive_gates"] = all(screen.values())
            rec = {
                "definition": rule,
                "signal_accounting": accounting,
                "full": full,
                "concentration": {p: concentration(ledger, p) for p in econ.PROFILES},
                "yearly": yearly,
                "monthly": monthly,
                "rolling": rolling,
                "positive_full_years": {"E1": e1_pos, "STRESS": st_pos, "denominator": len(full_years)},
                "max_single_year_share_positive_e1": max_share,
                "operational_screen": screen,
            }
            result["candidates"][cid][variant_name] = rec
            if variant_name == "HYBRID_CANONICAL":
                hybrid_monthly_by_candidate[cid] = {m: monthly[m]["E1"]["net"] for m in monthly}

    # Pair diagnostics on the more faithful hybrid variant.
    ids = ["R6B-347", "R6B-307"]
    common_months = sorted(set(hybrid_monthly_by_candidate[ids[0]]) & set(hybrid_monthly_by_candidate[ids[1]]))
    a = np.array([hybrid_monthly_by_candidate[ids[0]][m] for m in common_months], float)
    b = np.array([hybrid_monthly_by_candidate[ids[1]][m] for m in common_months], float)
    corr = float(np.corrcoef(a, b)[0, 1]) if len(a) >= 2 and np.std(a) > 0 and np.std(b) > 0 else None
    combined = a + b
    result["pair_diagnostics"] = {
        "variant": "HYBRID_CANONICAL",
        "months": len(common_months),
        "monthly_e1_net_correlation": corr,
        "simple_combined_e1_net": float(combined.sum()),
        "positive_combined_month_fraction": float((combined > 0).mean()) if len(combined) else None,
        "note": "Simple sum only; does not model shared margin or cross-strategy position conflicts."
    }

    rp = out / "top2_xau_long_history_result.json"
    yp = out / "top2_xau_long_history_yearly.csv"
    mp = out / "top2_xau_long_history_monthly.csv"
    atomic_json(rp, result)
    pd.DataFrame(yearly_rows).to_csv(yp, index=False)
    pd.DataFrame(monthly_rows).to_csv(mp, index=False)
    hb(progress, 6, 6, "complete", {"status": "PASS"})
    summary_bits = []
    for cid in ids:
        h = result["candidates"][cid]["HYBRID_CANONICAL"]
        summary_bits.append(f"{cid} E1={h['full']['E1']['net']:.2f} STRESS={h['full']['STRESS']['net']:.2f} years+={h['positive_full_years']['E1']}/9 screen={h['operational_screen']['all_descriptive_gates']}")
    summary = "Top2 XAU 2017-Jul2026 characterization complete: " + "; ".join(summary_bits)
    publish(args.publisher, "PASS", summary, [rp, yp, mp, prereg_path, Path(args.market_manifest)])
    print(json.dumps({"status": "PASS", "summary": summary, "pair_monthly_correlation": corr}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
