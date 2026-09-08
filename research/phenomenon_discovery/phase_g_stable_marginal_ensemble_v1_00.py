#!/usr/bin/env python3
"""Phase G: deterministic stable-marginal ensemble.

Purpose
-------
Test whether many weak but cross-asset/time-stable marginal effects can combine
into a directional score without hand-crafted strategy rules.

Protocol
--------
1) Read ONLY 2024 from the already-built Bybit derivative matrix + Binance
   order-flow matrix.
2) Learn per-symbol 2024 quintile cuts.
3) For each outcome, keep only feature/quintile contributions whose effect sign
   agrees across BTC, ETH, and both 2024 halves with minimum support.
4) Score each bar by an equal-weight vote of those frozen signs.
5) Freeze model JSON + SHA256 BEFORE loading any 2025 rows.
6) Evaluate only the frozen top/bottom score tails on 2025 with cross-asset sign,
   effect-retention, quarter stability, circular 5-day block bootstrap, and BH.

No 2026 data is read. No PnL optimization. No hyperparameter tuning on 2025.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from datetime import datetime
from pathlib import Path

FEATURES = [
    # Base market state (reduced to avoid obvious deterministic duplicates)
    "rsi14",
    "atr_slope_3bar_pct",
    "price_change_5m_pct",
    "price_change_15m_pct",
    "price_change_1h_pct",
    "oi_change_5m_pct",
    "oi_change_15m_pct",
    "oi_change_1h_pct",
    "oi_accel_5m_pctpt",
    "oi_accel_15m_pctpt",
    # Derivative context
    "mark_index_bps",
    "mark_index_bps_change_15m",
    "mark_index_bps_change_1h",
    "premium_index_close",
    "premium_index_change_15m",
    "premium_index_change_1h",
    "funding_last_settled_rate",
    "funding_delta_settlement",
    # Binance order-flow
    "spot_taker_imbalance",
    "perp_taker_imbalance",
    "taker_imbalance_diff",
    "perp_spot_basis_bps",
    "log_quote_volume_ratio",
    "log_trade_count_ratio",
    "spot_taker_imbalance_change_15m",
    "spot_taker_imbalance_change_1h",
    "perp_taker_imbalance_change_15m",
    "perp_taker_imbalance_change_1h",
    "taker_imbalance_diff_change_15m",
    "taker_imbalance_diff_change_1h",
    "perp_spot_basis_bps_change_15m",
    "perp_spot_basis_bps_change_1h",
    "log_quote_volume_ratio_change_15m",
    "log_quote_volume_ratio_change_1h",
    "log_trade_count_ratio_change_15m",
    "log_trade_count_ratio_change_1h",
]

QPROBS = (0.20, 0.40, 0.60, 0.80)
TAIL_Q = 0.10
MIN_DISCOVERY_ANNUAL_N = 500
MIN_DISCOVERY_HALF_N = 180
MIN_CONFIRM_ANNUAL_N = 300
MIN_CONFIRM_QUARTER_N = 50
MIN_QUARTER_ELIGIBLE = 6
MIN_QUARTER_MATCH_RATE = 0.75
RETENTION_FRACTION = 0.25
BOOTSTRAPS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10


def finite(x):
    if x in (None, ""):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def quantiles(values, probs=QPROBS):
    s = sorted(values)
    if not s:
        raise RuntimeError("empty quantile sample")
    n = len(s)
    out = []
    for p in probs:
        pos = p * (n - 1)
        lo = int(math.floor(pos))
        hi = int(math.ceil(pos))
        if lo == hi:
            out.append(s[lo])
        else:
            w = pos - lo
            out.append(s[lo] * (1.0 - w) + s[hi] * w)
    return out


def qbin(v, cuts):
    b = 1
    for c in cuts:
        if v > c:
            b += 1
        else:
            break
    return b


def ret_1h_atr(r):
    ret = finite(r.get("future_return_1h_pct"))
    close = finite(r.get("close"))
    atr = finite(r.get("atr14"))
    if ret is None or close is None or atr is None or atr <= 0:
        return None
    return (ret / 100.0) * close / atr


def up_first(r):
    t = r.get("future_first_touch_1atr_1h", "")
    if t == "UP":
        return 1.0
    if t == "DOWN":
        return 0.0
    return None


OUTCOMES = {
    "direction_1h_atr": ret_1h_atr,
    "up_first_1atr_1h": up_first,
}


def load_joined_year(deriv_path: Path, flow_path: Path, year: int):
    flow = {}
    with flow_path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("timestamp_utc", "").startswith(f"{year}-"):
                flow[int(r["timestamp_ms"])] = r
    rows = []
    with deriv_path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("timestamp_utc", "").startswith(f"{year}-"):
                continue
            ts = int(r["timestamp_ms"])
            fr = flow.get(ts)
            if fr is None:
                continue
            raw = dict(r)
            raw.update(fr)
            dt = datetime.fromisoformat(r["timestamp_utc"])
            rows.append({
                "raw": raw,
                "half": 1 if dt.month <= 6 else 2,
                "quarter": ((dt.month - 1) // 3) + 1,
                "day": dt.date().isoformat(),
            })
    return rows


def learn_cuts(rows):
    cuts = {}
    for feature in FEATURES:
        vals = [v for x in rows if (v := finite(x["raw"].get(feature))) is not None]
        if len(vals) < 1000:
            raise RuntimeError(f"too few values for {feature}: {len(vals)}")
        cuts[feature] = quantiles(vals)
    return cuts


def add_bins_outcomes(rows, cuts):
    for x in rows:
        bins = {}
        for feature in FEATURES:
            v = finite(x["raw"].get(feature))
            if v is not None:
                bins[feature] = qbin(v, cuts[feature])
        x["bins"] = bins
        x["outcomes"] = {name: fn(x["raw"]) for name, fn in OUTCOMES.items()}


def baseline(rows, outcome, subset=None):
    vals = []
    for i, x in enumerate(rows):
        if subset is not None and not subset(i, x):
            continue
        v = x["outcomes"][outcome]
        if v is not None:
            vals.append(v)
    return sum(vals) / len(vals) if vals else None


def effect(rows, members, outcome, subset=None):
    base = baseline(rows, outcome, subset)
    vals = []
    for i in members:
        x = rows[i]
        if subset is not None and not subset(i, x):
            continue
        v = x["outcomes"][outcome]
        if v is not None:
            vals.append(v)
    if base is None or not vals:
        return len(vals), None
    return len(vals), sum(vals) / len(vals) - base


def sgn(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def feature_members(rows, feature, q):
    return {i for i, x in enumerate(rows) if x["bins"].get(feature) == q}


def learn_stable_contributions(rows24):
    contributions = {outcome: {} for outcome in OUTCOMES}
    audit = []
    for outcome in OUTCOMES:
        for feature in FEATURES:
            for q in range(1, 6):
                key = f"{feature}=Q{q}"
                wanted = None
                ok = True
                rec = {"outcome": outcome, "state": key}
                for symbol in ("BTCUSDT", "ETHUSDT"):
                    mem = feature_members(rows24[symbol], feature, q)
                    n, e = effect(rows24[symbol], mem, outcome)
                    rec[f"{symbol.lower()}_annual_n"] = n
                    rec[f"{symbol.lower()}_annual_effect"] = e
                    if n < MIN_DISCOVERY_ANNUAL_N or e is None or sgn(e) == 0:
                        ok = False
                    else:
                        if wanted is None:
                            wanted = sgn(e)
                        elif sgn(e) != wanted:
                            ok = False
                    for half in (1, 2):
                        hn, he = effect(
                            rows24[symbol], mem, outcome,
                            subset=lambda _i, x, h=half: x["half"] == h,
                        )
                        rec[f"{symbol.lower()}_h{half}_n"] = hn
                        rec[f"{symbol.lower()}_h{half}_effect"] = he
                        if hn < MIN_DISCOVERY_HALF_N or he is None or wanted is None or sgn(he) != wanted:
                            ok = False
                rec["stable"] = bool(ok and wanted is not None)
                rec["sign"] = wanted if rec["stable"] else None
                audit.append(rec)
                if rec["stable"]:
                    contributions[outcome][key] = int(wanted)
    return contributions, audit


def score_rows(rows, contribution_map):
    for x in rows:
        total = 0
        used = 0
        for feature in FEATURES:
            q = x["bins"].get(feature)
            if q is None:
                continue
            signv = contribution_map.get(f"{feature}=Q{q}")
            if signv is not None:
                total += signv
                used += 1
        x["score"] = None if used == 0 else total
        x["score_votes"] = used


def pooled_tail_cuts(rows_by_symbol):
    vals = []
    for rows in rows_by_symbol.values():
        vals.extend(x["score"] for x in rows if x.get("score") is not None)
    low, high = quantiles(vals, probs=(TAIL_Q, 1.0 - TAIL_Q))
    return low, high


def tail_members(rows, side, low_cut, high_cut):
    if side == "HIGH":
        return {i for i, x in enumerate(rows) if x.get("score") is not None and x["score"] >= high_cut}
    return {i for i, x in enumerate(rows) if x.get("score") is not None and x["score"] <= low_cut}


def stable_seed(*parts):
    return int(hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16], 16)


def block_p(rows, members, outcome, observed_effect, wanted_sign, seed):
    valid = [x for x in rows if x["outcomes"][outcome] is not None]
    if not valid:
        return 1.0
    base = sum(x["outcomes"][outcome] for x in valid) / len(valid)
    days = sorted({x["day"] for x in valid})
    pos = {d: i for i, d in enumerate(days)}
    day_sum = [0.0] * len(days)
    day_n = [0] * len(days)
    for i in members:
        x = rows[i]
        v = x["outcomes"][outcome]
        if v is None:
            continue
        j = pos[x["day"]]
        day_sum[j] += v
        day_n[j] += 1
    if sum(day_n) == 0:
        return 1.0
    centered = [
        day_sum[i] - day_n[i] * base - observed_effect * day_n[i]
        for i in range(len(days))
    ]
    block_num, block_den = [], []
    for start in range(len(days)):
        num, den = 0.0, 0
        for k in range(BLOCK_DAYS):
            j = (start + k) % len(days)
            num += centered[j]
            den += day_n[j]
        block_num.append(num)
        block_den.append(den)
    need = int(math.ceil(len(days) / BLOCK_DAYS))
    rng = random.Random(seed)
    extreme = valid_boot = 0
    for _ in range(BOOTSTRAPS):
        num, den = 0.0, 0
        for _b in range(need):
            j = rng.randrange(len(days))
            num += block_num[j]
            den += block_den[j]
        if den <= 0:
            continue
        e = num / den
        valid_boot += 1
        extreme += int(e >= observed_effect) if wanted_sign > 0 else int(e <= observed_effect)
    return (extreme + 1.0) / (valid_boot + 1.0)


def bh(items):
    ordered = sorted(items, key=lambda x: x[1])
    m = len(ordered)
    out = {}
    running = 1.0
    for rev in range(m - 1, -1, -1):
        idx, p = ordered[rev]
        rank = rev + 1
        q = min(1.0, p * m / rank)
        running = min(running, q)
        out[idx] = running
    return out


def write_csv(path, rows):
    if not rows:
        path.write_text("hypothesis\n", encoding="utf-8")
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


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--derivative-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1")
    ap.add_argument("--flow-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_g_v1")
    args = ap.parse_args()

    deriv_dir = Path(args.derivative_dir)
    flow_dir = Path(args.flow_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    deriv_paths = {}
    flow_paths = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        dp = deriv_dir / f"{symbol}_derivative_context_features_v1.csv"
        fp = flow_dir / f"{symbol}_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        if not dp.exists() or not fp.exists():
            raise RuntimeError(f"missing Phase G input for {symbol}")
        deriv_paths[symbol] = dp
        flow_paths[symbol] = fp

    # -------------------------- 2024 ONLY --------------------------
    rows24, cuts = {}, {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        rows24[symbol] = load_joined_year(deriv_paths[symbol], flow_paths[symbol], 2024)
        cuts[symbol] = learn_cuts(rows24[symbol])
        add_bins_outcomes(rows24[symbol], cuts[symbol])
        print(f"{symbol}: loaded 2024 rows={len(rows24[symbol])}")

    contributions, contribution_audit = learn_stable_contributions(rows24)
    model = {
        "schema": 1,
        "phase": "G",
        "method": "equal-weight vote of feature/quintile signs stable across BTC+ETH and both 2024 halves; frozen before 2025 read",
        "features": FEATURES,
        "quintile_probs": QPROBS,
        "tail_q": TAIL_Q,
        "cuts_2024_by_symbol": cuts,
        "outcomes": {},
        "protected_2026_untouched": True,
    }

    discovery_rows = []
    for outcome in OUTCOMES:
        score_rows(rows24["BTCUSDT"], contributions[outcome])
        score_rows(rows24["ETHUSDT"], contributions[outcome])
        low_cut, high_cut = pooled_tail_cuts(rows24)
        model["outcomes"][outcome] = {
            "stable_contributions": contributions[outcome],
            "stable_contribution_count": len(contributions[outcome]),
            "score_low_tail_cut": low_cut,
            "score_high_tail_cut": high_cut,
        }
        for side, wanted in (("LOW", -1), ("HIGH", 1)):
            rec = {"hypothesis": f"{outcome}|{side}", "outcome": outcome, "side": side, "expected_sign": wanted}
            ok = True
            worst = None
            for symbol in ("BTCUSDT", "ETHUSDT"):
                mem = tail_members(rows24[symbol], side, low_cut, high_cut)
                n, e = effect(rows24[symbol], mem, outcome)
                rec[f"{symbol.lower()}_2024_n"] = n
                rec[f"{symbol.lower()}_2024_effect"] = e
                if n < MIN_DISCOVERY_ANNUAL_N or e is None or sgn(e) != wanted:
                    ok = False
                else:
                    worst = abs(e) if worst is None else min(worst, abs(e))
                for half in (1, 2):
                    hn, he = effect(rows24[symbol], mem, outcome, subset=lambda _i, x, h=half: x["half"] == h)
                    rec[f"{symbol.lower()}_2024_h{half}_n"] = hn
                    rec[f"{symbol.lower()}_2024_h{half}_effect"] = he
                    if hn < MIN_DISCOVERY_HALF_N or he is None or sgn(he) != wanted:
                        ok = False
            rec["discovery_eligible"] = ok
            rec["discovery_worst_abs_effect"] = worst if ok else None
            discovery_rows.append(rec)
        model["outcomes"][outcome]["discovery_hypotheses"] = [
            r for r in discovery_rows if r["outcome"] == outcome
        ]

    model_path = out_dir / "phase_g_frozen_model_2024.json"
    model_path.write_text(json.dumps(model, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    model_hash = sha256(model_path)
    audit_path = out_dir / "phase_g_2024_contribution_audit.csv"
    write_csv(audit_path, contribution_audit)
    print(f"FROZEN MODEL sha256={model_hash}")

    # -------------------------- ONLY NOW READ 2025 --------------------------
    rows25 = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        rows25[symbol] = load_joined_year(deriv_paths[symbol], flow_paths[symbol], 2025)
        add_bins_outcomes(rows25[symbol], cuts[symbol])
        print(f"{symbol}: loaded 2025 rows={len(rows25[symbol])}")

    confirmations = []
    for drec in discovery_rows:
        rec = dict(drec)
        outcome = rec["outcome"]
        side = rec["side"]
        wanted = int(rec["expected_sign"])
        score_rows(rows25["BTCUSDT"], contributions[outcome])
        score_rows(rows25["ETHUSDT"], contributions[outcome])
        low_cut = model["outcomes"][outcome]["score_low_tail_cut"]
        high_cut = model["outcomes"][outcome]["score_high_tail_cut"]
        annual_ok = bool(rec["discovery_eligible"])
        effects = []
        qelig = qmatch = 0
        ps = []
        for symbol in ("BTCUSDT", "ETHUSDT"):
            mem = tail_members(rows25[symbol], side, low_cut, high_cut)
            n, e = effect(rows25[symbol], mem, outcome)
            rec[f"{symbol.lower()}_2025_n"] = n
            rec[f"{symbol.lower()}_2025_effect"] = e
            if n < MIN_CONFIRM_ANNUAL_N or e is None or sgn(e) != wanted:
                annual_ok = False
            else:
                effects.append(abs(e))
                p = block_p(rows25[symbol], mem, outcome, e, wanted, stable_seed("phase-g", rec["hypothesis"], symbol))
                rec[f"{symbol.lower()}_block_p"] = p
                ps.append(p)
            for quarter in range(1, 5):
                qn, qe = effect(rows25[symbol], mem, outcome, subset=lambda _i, x, q=quarter: x["quarter"] == q)
                rec[f"{symbol.lower()}_2025_q{quarter}_n"] = qn
                rec[f"{symbol.lower()}_2025_q{quarter}_effect"] = qe
                if qn >= MIN_CONFIRM_QUARTER_N and qe is not None:
                    qelig += 1
                    qmatch += int(sgn(qe) == wanted)
        rec["confirm_same_sign_both"] = annual_ok
        rec["confirm_worst_abs_effect"] = min(effects) if annual_ok and len(effects) == 2 else None
        rec["confirm_retains_effect"] = bool(
            rec["confirm_worst_abs_effect"] is not None
            and rec["discovery_worst_abs_effect"] is not None
            and rec["confirm_worst_abs_effect"] >= RETENTION_FRACTION * rec["discovery_worst_abs_effect"]
        )
        rec["quarter_eligible"] = qelig
        rec["quarter_match"] = qmatch
        rec["quarter_match_rate"] = qmatch / qelig if qelig else 0.0
        rec["quarter_stable"] = qelig >= MIN_QUARTER_ELIGIBLE and rec["quarter_match_rate"] >= MIN_QUARTER_MATCH_RATE
        rec["worst_symbol_p"] = max(ps) if len(ps) == 2 else 1.0
        confirmations.append(rec)

    qmap = bh([(i, r["worst_symbol_p"]) for i, r in enumerate(confirmations)])
    passes = []
    for i, r in enumerate(confirmations):
        r["worst_symbol_bh_q"] = qmap[i]
        r["phase_g_screen_pass"] = bool(
            r["discovery_eligible"]
            and r["confirm_same_sign_both"]
            and r["confirm_retains_effect"]
            and r["quarter_stable"]
            and r["worst_symbol_bh_q"] <= BH_Q_MAX
        )
        if r["phase_g_screen_pass"]:
            passes.append(r)

    confirm_path = out_dir / "phase_g_2025_confirmation.csv"
    pass_path = out_dir / "phase_g_distinct_passes.csv"
    write_csv(confirm_path, confirmations)
    write_csv(pass_path, passes)

    summary = {
        "schema": 1,
        "phase": "G",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "method": model["method"],
        "feature_count": len(FEATURES),
        "features": FEATURES,
        "frozen_model_sha256": model_hash,
        "outcomes": {
            outcome: {
                "stable_contribution_count": len(contributions[outcome]),
                "score_low_tail_cut": model["outcomes"][outcome]["score_low_tail_cut"],
                "score_high_tail_cut": model["outcomes"][outcome]["score_high_tail_cut"],
            }
            for outcome in OUTCOMES
        },
        "hypotheses_tested": len(confirmations),
        "phase_g_screen_pass_count": len(passes),
        "passes_by_outcome": {
            outcome: sum(1 for r in passes if r["outcome"] == outcome)
            for outcome in OUTCOMES
        },
        "gates": {
            "tail_q": TAIL_Q,
            "bootstrap_paths": BOOTSTRAPS,
            "circular_block_days": BLOCK_DAYS,
            "bh_q_max": BH_Q_MAX,
            "confirmation_effect_retention_fraction": RETENTION_FRACTION,
            "quarter_match_rate_min": MIN_QUARTER_MATCH_RATE,
            "quarter_min_eligible_blocks": MIN_QUARTER_ELIGIBLE,
        },
        "independent_validation": False,
        "protected_2026_untouched": True,
        "warning": "Phase G still uses inspected 2024-2025 history. Any pass must be frozen again before opening 2026. No PnL claim is authorized.",
    }
    summary_path = out_dir / "phase_g_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
