#!/usr/bin/env python3
"""Phenomenon Discovery Lab Phase B v1.00.

Build a coarse, interpretable market-state atlas before any trading rule search.
2024 is discovery. 2025 is internal confirmation. 2026 remains untouched.

No PnL optimization. No BUY/SELL rules. No future_* field is used as a predictor.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

FEATURES = [
    "rsi14",
    "atr_slope_1bar_pct",
    "atr_slope_3bar_pct",
    "price_change_5m_pct",
    "price_change_15m_pct",
    "price_change_1h_pct",
    "oi_change_5m_pct",
    "oi_change_15m_pct",
    "oi_change_1h_pct",
    "oi_accel_5m_pctpt",
    "oi_accel_15m_pctpt",
    "range_atr",
    "body_atr",
]
QPROBS = (0.20, 0.40, 0.60, 0.80)
MIN_DISCOVERY_N = 500
MIN_CONFIRM_N = 300
TOP_PER_OUTCOME = 25


def finite(x: str) -> float | None:
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    return v if math.isfinite(v) else None


def quantiles(values: list[float]) -> list[float]:
    s = sorted(values)
    if not s:
        raise ValueError("empty values")
    out = []
    n = len(s)
    for p in QPROBS:
        pos = p * (n - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            out.append(s[lo])
        else:
            w = pos - lo
            out.append(s[lo] * (1.0 - w) + s[hi] * w)
    return out


def qbin(v: float, cuts: list[float]) -> int:
    b = 1
    for c in cuts:
        if v > c:
            b += 1
        else:
            break
    return b


def ret_1h_atr(row: dict[str, str]) -> float | None:
    ret = finite(row.get("future_return_1h_pct", ""))
    close = finite(row.get("close", ""))
    atr = finite(row.get("atr14", ""))
    if ret is None or close is None or atr is None or atr <= 0:
        return None
    return (ret / 100.0) * close / atr


def move_1h(row: dict[str, str]) -> float | None:
    mfe = finite(row.get("future_mfe_1h_atr", ""))
    mae = finite(row.get("future_mae_1h_atr", ""))
    if mfe is None or mae is None:
        return None
    return 1.0 if max(mfe, abs(mae)) >= 1.0 else 0.0


def up_first(row: dict[str, str]) -> float | None:
    t = row.get("future_first_touch_1atr_1h", "")
    if t == "UP":
        return 1.0
    if t == "DOWN":
        return 0.0
    return None

OUTCOME_FUNCS = {
    "direction_1h_atr": ret_1h_atr,
    "move_ge_1atr_1h": move_1h,
    "up_first_1atr_1h": up_first,
}


def load_year(path: Path, year: int) -> list[dict[str, str]]:
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("timestamp_utc", "")[:4] == str(year):
                rows.append(r)
    return rows


def learn_cuts(rows: list[dict[str, str]]) -> dict[str, list[float]]:
    out = {}
    for feature in FEATURES:
        vals = [v for r in rows if (v := finite(r.get(feature, ""))) is not None]
        if len(vals) < 1000:
            raise RuntimeError(f"too few values for {feature}: {len(vals)}")
        out[feature] = quantiles(vals)
    return out


def state_key(parts: list[tuple[str, int]]) -> str:
    return " & ".join(f"{f}=Q{b}" for f, b in parts)


def aggregate(rows: list[dict[str, str]], cuts: dict[str, list[float]]) -> dict:
    base = {name: [0, 0.0] for name in OUTCOME_FUNCS}
    stats: dict[str, dict[str, list[float]]] = defaultdict(lambda: {name: [0, 0.0] for name in OUTCOME_FUNCS})

    for r in rows:
        bins = {}
        for f in FEATURES:
            v = finite(r.get(f, ""))
            if v is not None:
                bins[f] = qbin(v, cuts[f])

        outs = {name: fn(r) for name, fn in OUTCOME_FUNCS.items()}
        for name, val in outs.items():
            if val is not None:
                base[name][0] += 1
                base[name][1] += val

        singles = [(f, bins[f]) for f in FEATURES if f in bins]
        keys = [state_key([x]) for x in singles]
        for i in range(len(singles)):
            for j in range(i + 1, len(singles)):
                keys.append(state_key([singles[i], singles[j]]))

        for key in keys:
            rec = stats[key]
            for name, val in outs.items():
                if val is not None:
                    rec[name][0] += 1
                    rec[name][1] += val

    baseline = {name: (s / n if n else None) for name, (n, s) in base.items()}
    states = {}
    for key, rec in stats.items():
        states[key] = {}
        for name, (n, s) in rec.items():
            mean = s / n if n else None
            states[key][name] = {
                "n": int(n),
                "mean": mean,
                "effect_vs_baseline": None if mean is None or baseline[name] is None else mean - baseline[name],
            }
    return {"baseline": baseline, "states": states}


def sign(x: float) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def discovery_shortlist(blocks: dict, outcome: str) -> list[dict]:
    btc = blocks["BTCUSDT_2024"]["states"]
    eth = blocks["ETHUSDT_2024"]["states"]
    common = set(btc).intersection(eth)
    scored = []
    for key in common:
        a = btc[key][outcome]
        b = eth[key][outcome]
        if a["n"] < MIN_DISCOVERY_N or b["n"] < MIN_DISCOVERY_N:
            continue
        ea = a["effect_vs_baseline"]
        eb = b["effect_vs_baseline"]
        if ea is None or eb is None or sign(ea) == 0 or sign(ea) != sign(eb):
            continue
        worst = min(abs(ea), abs(eb))
        scored.append({
            "state": key,
            "outcome": outcome,
            "discovery_sign": sign(ea),
            "discovery_worst_abs_effect": worst,
            "btc_2024_n": a["n"], "btc_2024_effect": ea,
            "eth_2024_n": b["n"], "eth_2024_effect": eb,
        })
    scored.sort(key=lambda x: x["discovery_worst_abs_effect"], reverse=True)
    return scored[:TOP_PER_OUTCOME]


def confirm(candidate: dict, blocks: dict) -> dict:
    outcome = candidate["outcome"]
    key = candidate["state"]
    wanted = candidate["discovery_sign"]
    effects = []
    ok = True
    for symbol in ("BTCUSDT", "ETHUSDT"):
        rec = blocks[f"{symbol}_2025"]["states"].get(key, {}).get(outcome)
        if not rec or rec["n"] < MIN_CONFIRM_N or rec["effect_vs_baseline"] is None:
            ok = False
            n = 0 if not rec else rec["n"]
            eff = None if not rec else rec["effect_vs_baseline"]
        else:
            n = rec["n"]
            eff = rec["effect_vs_baseline"]
            if sign(eff) != wanted:
                ok = False
            else:
                effects.append(abs(eff))
        candidate[f"{symbol.lower()}_2025_n"] = n
        candidate[f"{symbol.lower()}_2025_effect"] = eff
    candidate["confirm_same_sign_both"] = ok
    candidate["confirm_worst_abs_effect"] = min(effects) if ok and len(effects) == 2 else None
    floor = 0.25 * candidate["discovery_worst_abs_effect"]
    candidate["confirm_retains_25pct_effect"] = bool(ok and candidate["confirm_worst_abs_effect"] is not None and candidate["confirm_worst_abs_effect"] >= floor)
    candidate["phase_b_survivor"] = bool(candidate["confirm_same_sign_both"] and candidate["confirm_retains_25pct_effect"])
    return candidate


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("state,outcome,phase_b_survivor\n", encoding="utf-8")
        return
    fields = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1")
    args = ap.parse_args()

    feat = Path(args.features_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    files = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        matches = sorted(feat.glob(f"{symbol}_bybit_5m_oi_price_*_features_v1.csv"))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one {symbol} feature file, found {len(matches)}")
        files[symbol] = matches[0]

    blocks = {}
    cuts_all = {}
    for symbol, path in files.items():
        rows24 = load_year(path, 2024)
        rows25 = load_year(path, 2025)
        cuts = learn_cuts(rows24)
        cuts_all[symbol] = cuts
        blocks[f"{symbol}_2024"] = aggregate(rows24, cuts)
        blocks[f"{symbol}_2025"] = aggregate(rows25, cuts)
        print(f"{symbol}: 2024 rows={len(rows24)} 2025 rows={len(rows25)} states={len(blocks[f'{symbol}_2024']['states'])}")

    candidates = []
    for outcome in OUTCOME_FUNCS:
        short = discovery_shortlist(blocks, outcome)
        for c in short:
            candidates.append(confirm(c, blocks))

    survivors = [c for c in candidates if c["phase_b_survivor"]]
    survivors.sort(key=lambda x: (x["outcome"], -(x["confirm_worst_abs_effect"] or 0.0)))

    write_csv(out / "phase_b_shortlist_and_confirmation.csv", candidates)
    write_csv(out / "phase_b_survivors.csv", survivors)

    summary = {
        "schema": 1,
        "phase": "B",
        "method": "coarse quintile state atlas; single and two-feature states; 2024 discovery; 2025 internal confirmation; BTC+ETH same-sign requirement",
        "future_predictors_forbidden": True,
        "features": FEATURES,
        "quantile_probs": QPROBS,
        "min_discovery_n_per_symbol": MIN_DISCOVERY_N,
        "min_confirmation_n_per_symbol": MIN_CONFIRM_N,
        "top_per_outcome": TOP_PER_OUTCOME,
        "outcomes": list(OUTCOME_FUNCS),
        "shortlist_count": len(candidates),
        "survivor_count": len(survivors),
        "survivors_by_outcome": {o: sum(1 for c in survivors if c["outcome"] == o) for o in OUTCOME_FUNCS},
        "warning": "Phase B survivors are discovery candidates, not validated trading alpha. No strategy sizing or PnL inference is authorized.",
        "thresholds_2024_by_symbol": cuts_all,
    }
    (out / "phase_b_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({k: summary[k] for k in ("shortlist_count", "survivor_count", "survivors_by_outcome")}, indent=2))
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
