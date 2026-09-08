#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FEATURES = [
    "oi_change_15m_pct",
    "oi_change_1h_pct",
    "mark_index_bps",
    "mark_index_bps_change_15m",
    "mark_index_bps_change_1h",
    "premium_index_close",
    "premium_index_change_15m",
    "premium_index_change_1h",
    "funding_last_settled_rate",
    "funding_delta_settlement",
]
LAGS = ((3, "15m"), (12, "1h"))
QPROBS = (0.20, 0.40, 0.60, 0.80)
STEP_MS = 300000

MIN_DISCOVERY_ANNUAL_N = 300
MIN_DISCOVERY_HALF_N = 120
MIN_CONFIRM_ANNUAL_N = 200
MIN_CONFIRM_QUARTER_N = 40
MIN_QUARTER_ELIGIBLE = 6
MIN_QUARTER_MATCH_RATE = 0.75
RETENTION_FRACTION = 0.25
TOP_PER_OUTCOME = 50
BOOTSTRAPS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10
DEDUP_JACCARD = 0.95


def finite(x):
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def quantiles(values):
    s = sorted(values)
    if not s:
        raise ValueError("empty quantile sample")
    n = len(s)
    out = []
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


def qbin(v, cuts):
    b = 1
    for c in cuts:
        if v > c:
            b += 1
        else:
            break
    return b


def ret_1h_atr(row):
    ret = finite(row.get("future_return_1h_pct"))
    close = finite(row.get("close"))
    atr = finite(row.get("atr14"))
    if ret is None or close is None or atr is None or atr <= 0:
        return None
    return (ret / 100.0) * close / atr


def up_first(row):
    t = row.get("future_first_touch_1atr_1h", "")
    if t == "UP":
        return 1.0
    if t == "DOWN":
        return 0.0
    return None


OUTCOME_FUNCS = {
    "direction_1h_atr": ret_1h_atr,
    "up_first_1atr_1h": up_first,
}


def load_rows(path, year):
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("timestamp_utc", "").startswith(f"{year}-"):
                continue
            ts = int(r["timestamp_ms"])
            dt = datetime.fromisoformat(r["timestamp_utc"])
            rows.append({
                "raw": r,
                "timestamp_ms": ts,
                "half": 1 if dt.month <= 6 else 2,
                "quarter": (dt.month - 1) // 3 + 1,
                "day": dt.date().isoformat(),
            })
    return rows


def learn_cuts(rows):
    out = {}
    for feature in FEATURES:
        vals = [v for x in rows if (v := finite(x["raw"].get(feature))) is not None]
        if len(vals) < 1000:
            raise RuntimeError(f"too few 2024 values for {feature}: {len(vals)}")
        out[feature] = quantiles(vals)
    return out


def add_bins(rows, cuts):
    for x in rows:
        bins = {}
        for feature in FEATURES:
            v = finite(x["raw"].get(feature))
            if v is not None:
                bins[feature] = qbin(v, cuts[feature])
        x["bins"] = bins
        x["outcomes"] = {name: fn(x["raw"]) for name, fn in OUTCOME_FUNCS.items()}


def transition_key(feature, lag_tag, q_from, q_to):
    return f"{feature}|{lag_tag}|Q{q_from}->Q{q_to}"


def build_membership(rows):
    by_state = defaultdict(set)
    for i, row in enumerate(rows):
        for lag_bars, lag_tag in LAGS:
            j = i - lag_bars
            if j < 0:
                continue
            if row["timestamp_ms"] - rows[j]["timestamp_ms"] != lag_bars * STEP_MS:
                continue
            for feature in FEATURES:
                q_to = row["bins"].get(feature)
                q_from = rows[j]["bins"].get(feature)
                if q_to is None or q_from is None:
                    continue
                by_state[transition_key(feature, lag_tag, q_from, q_to)].add(i)
    return by_state


def baseline_mean(rows, outcome, subset=None):
    vals = []
    for i, x in enumerate(rows):
        if subset is not None and not subset(i, x):
            continue
        v = x["outcomes"][outcome]
        if v is not None:
            vals.append(v)
    return sum(vals) / len(vals) if vals else None


def effect_for_members(rows, members, outcome, subset=None):
    base = baseline_mean(rows, outcome, subset)
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


def sign(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("state\n", encoding="utf-8")
        return
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_seed(*parts):
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def circular_block_pvalue(rows, members, outcome, observed_effect, wanted_sign, seed):
    valid = [(i, x) for i, x in enumerate(rows) if x["outcomes"][outcome] is not None]
    if not valid:
        return 1.0
    base = sum(x["outcomes"][outcome] for _, x in valid) / len(valid)
    days = sorted({x["day"] for _, x in valid})
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
    block_num = []
    block_den = []
    for start in range(len(days)):
        num = 0.0
        den = 0
        for k in range(BLOCK_DAYS):
            j = (start + k) % len(days)
            num += centered[j]
            den += day_n[j]
        block_num.append(num)
        block_den.append(den)

    blocks_needed = int(math.ceil(len(days) / BLOCK_DAYS))
    rng = random.Random(seed)
    extreme = 0
    valid_boot = 0
    for _ in range(BOOTSTRAPS):
        num = 0.0
        den = 0
        for _b in range(blocks_needed):
            s = rng.randrange(len(days))
            num += block_num[s]
            den += block_den[s]
        if den <= 0:
            continue
        eff = num / den
        valid_boot += 1
        if wanted_sign > 0:
            extreme += int(eff >= observed_effect)
        else:
            extreme += int(eff <= observed_effect)
    return (extreme + 1.0) / (valid_boot + 1.0)


def bh_adjust(items):
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


def jaccard(a, b):
    if not a and not b:
        return 1.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matrix-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\derivative_matrix_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_eb_v1")
    args = ap.parse_args()

    matrix_dir = Path(args.matrix_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows24 = {}
    rows25 = {}
    cuts = {}
    mem24 = {}
    mem25 = {}

    for symbol in ("BTCUSDT", "ETHUSDT"):
        path = matrix_dir / f"{symbol}_derivative_context_features_v1.csv"
        if not path.exists():
            raise RuntimeError(f"missing matrix: {path}")
        rows24[symbol] = load_rows(path, 2024)
        rows25[symbol] = load_rows(path, 2025)
        cuts[symbol] = learn_cuts(rows24[symbol])
        add_bins(rows24[symbol], cuts[symbol])
        add_bins(rows25[symbol], cuts[symbol])
        mem24[symbol] = build_membership(rows24[symbol])
        mem25[symbol] = build_membership(rows25[symbol])
        print(f"{symbol}: 2024={len(rows24[symbol])} 2025={len(rows25[symbol])} transition_states_2024={len(mem24[symbol])}")

    all_states = sorted(set(mem24["BTCUSDT"]) & set(mem24["ETHUSDT"]))
    universe = []
    eligible_by_outcome = defaultdict(list)

    for state in all_states:
        for outcome in OUTCOME_FUNCS:
            rec = {"state": state, "outcome": outcome}
            effects = []
            annual_ok = True
            half_ok = True
            wanted = None
            for symbol in ("BTCUSDT", "ETHUSDT"):
                n, eff = effect_for_members(rows24[symbol], mem24[symbol][state], outcome)
                rec[f"{symbol.lower()}_2024_n"] = n
                rec[f"{symbol.lower()}_2024_effect"] = eff
                if n < MIN_DISCOVERY_ANNUAL_N or eff is None or sign(eff) == 0:
                    annual_ok = False
                else:
                    effects.append(abs(eff))
                    if wanted is None:
                        wanted = sign(eff)
                    elif sign(eff) != wanted:
                        annual_ok = False
                for half in (1, 2):
                    hn, he = effect_for_members(
                        rows24[symbol], mem24[symbol][state], outcome,
                        subset=lambda _i, x, h=half: x["half"] == h,
                    )
                    rec[f"{symbol.lower()}_2024_h{half}_n"] = hn
                    rec[f"{symbol.lower()}_2024_h{half}_effect"] = he
                    if hn < MIN_DISCOVERY_HALF_N or he is None:
                        half_ok = False
                    elif wanted is not None and sign(he) != wanted:
                        half_ok = False

            rec["discovery_same_sign_both"] = annual_ok
            rec["discovery_half_stable"] = bool(annual_ok and half_ok)
            rec["discovery_sign"] = wanted if annual_ok else None
            rec["discovery_worst_abs_effect"] = min(effects) if annual_ok and len(effects) == 2 else None
            rec["discovery_eligible"] = bool(rec["discovery_half_stable"])
            universe.append(rec)
            if rec["discovery_eligible"]:
                eligible_by_outcome[outcome].append(rec)

    frozen = []
    for outcome, items in eligible_by_outcome.items():
        items = sorted(items, key=lambda r: r["discovery_worst_abs_effect"], reverse=True)
        frozen.extend(dict(r) for r in items[:TOP_PER_OUTCOME])
    frozen.sort(key=lambda r: (r["outcome"], -r["discovery_worst_abs_effect"], r["state"]))

    universe_path = out_dir / "phase_eb_2024_transition_universe.csv"
    frozen_path = out_dir / "phase_eb_frozen_shortlist_2024.csv"
    write_csv(universe_path, universe)
    write_csv(frozen_path, frozen)
    frozen_hash = sha256(frozen_path)
    print(f"Frozen 2024 shortlist: {len(frozen)} sha256={frozen_hash}")

    confirmed = []
    for rec0 in frozen:
        rec = dict(rec0)
        state = rec["state"]
        outcome = rec["outcome"]
        wanted = int(rec["discovery_sign"])
        effects = []
        annual_ok = True
        quarter_eligible = 0
        quarter_match = 0
        ps = []

        for symbol in ("BTCUSDT", "ETHUSDT"):
            members = mem25[symbol].get(state, set())
            n, eff = effect_for_members(rows25[symbol], members, outcome)
            rec[f"{symbol.lower()}_2025_n"] = n
            rec[f"{symbol.lower()}_2025_effect"] = eff
            if n < MIN_CONFIRM_ANNUAL_N or eff is None or sign(eff) != wanted:
                annual_ok = False
            else:
                effects.append(abs(eff))
                p = circular_block_pvalue(
                    rows25[symbol], members, outcome, eff, wanted,
                    stable_seed("phase-eb", state, outcome, symbol),
                )
                ps.append(p)
                rec[f"{symbol.lower()}_block_p"] = p

            for quarter in range(1, 5):
                qn, qe = effect_for_members(
                    rows25[symbol], members, outcome,
                    subset=lambda _i, x, q=quarter: x["quarter"] == q,
                )
                rec[f"{symbol.lower()}_2025_q{quarter}_n"] = qn
                rec[f"{symbol.lower()}_2025_q{quarter}_effect"] = qe
                if qn >= MIN_CONFIRM_QUARTER_N and qe is not None:
                    quarter_eligible += 1
                    quarter_match += int(sign(qe) == wanted)

        worst_effect = min(effects) if annual_ok and len(effects) == 2 else None
        rec["confirm_same_sign_both"] = annual_ok
        rec["confirm_worst_abs_effect"] = worst_effect
        rec["confirm_retains_effect"] = bool(
            worst_effect is not None
            and worst_effect >= RETENTION_FRACTION * rec["discovery_worst_abs_effect"]
        )
        rec["quarter_eligible"] = quarter_eligible
        rec["quarter_match"] = quarter_match
        rec["quarter_match_rate"] = quarter_match / quarter_eligible if quarter_eligible else 0.0
        rec["quarter_stable"] = bool(
            quarter_eligible >= MIN_QUARTER_ELIGIBLE
            and rec["quarter_match_rate"] >= MIN_QUARTER_MATCH_RATE
        )
        rec["worst_symbol_p"] = max(ps) if len(ps) == 2 else 1.0
        confirmed.append(rec)

    qvals = bh_adjust([(i, r["worst_symbol_p"]) for i, r in enumerate(confirmed)]) if confirmed else {}
    for i, rec in enumerate(confirmed):
        rec["worst_symbol_bh_q"] = qvals.get(i, 1.0)
        rec["phase_eb_screen_pass"] = bool(
            rec["confirm_same_sign_both"]
            and rec["confirm_retains_effect"]
            and rec["quarter_stable"]
            and rec["worst_symbol_bh_q"] <= BH_Q_MAX
        )

    screen = [r for r in confirmed if r["phase_eb_screen_pass"]]
    screen.sort(key=lambda r: (r["outcome"], r["worst_symbol_bh_q"], -(r["confirm_worst_abs_effect"] or 0.0)))

    cluster_rows = []
    reps = []
    assigned = set()
    for i, first in enumerate(screen):
        if i in assigned:
            continue
        group = [i]
        assigned.add(i)
        for j in range(i + 1, len(screen)):
            if j in assigned or screen[j]["outcome"] != first["outcome"]:
                continue
            a = first["state"]
            b = screen[j]["state"]
            btc_j = jaccard(mem25["BTCUSDT"].get(a, set()), mem25["BTCUSDT"].get(b, set()))
            eth_j = jaccard(mem25["ETHUSDT"].get(a, set()), mem25["ETHUSDT"].get(b, set()))
            if btc_j >= DEDUP_JACCARD and eth_j >= DEDUP_JACCARD:
                group.append(j)
                assigned.add(j)
        members = [screen[k] for k in group]
        rep = sorted(members, key=lambda r: (r["worst_symbol_bh_q"], -(r["confirm_worst_abs_effect"] or 0.0)))[0]
        cid = f"C{len(reps)+1:02d}"
        for member in members:
            cluster_rows.append({
                "cluster": cid,
                "representative": rep["state"],
                "state": member["state"],
                "outcome": member["outcome"],
            })
        rep2 = dict(rep)
        rep2["dedup_cluster"] = cid
        reps.append(rep2)

    confirm_path = out_dir / "phase_eb_2025_confirmation.csv"
    passes_path = out_dir / "phase_eb_distinct_passes.csv"
    clusters_path = out_dir / "phase_eb_dedup_clusters.csv"
    write_csv(confirm_path, confirmed)
    write_csv(passes_path, reps)
    write_csv(clusters_path, cluster_rows)

    summary = {
        "schema": 1,
        "phase": "E-B",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "independent_validation": False,
        "protected_2026_untouched": True,
        "method": "single-variable quintile transitions only; 2024 discovery with BTC+ETH and H1/H2 sign stability; frozen shortlist before 2025 confirmation; 2025 quarter stability, circular 5-day bootstrap, BH correction; no transition combinations",
        "features": FEATURES,
        "lags": [tag for _, tag in LAGS],
        "transition_states_per_feature_lag": 25,
        "transition_states_tested": len(all_states),
        "universe_tests_total": len(universe),
        "frozen_shortlist_count": len(frozen),
        "frozen_shortlist_sha256": frozen_hash,
        "phase_eb_screen_pass_count": len(screen),
        "phase_eb_distinct_pass_count": len(reps),
        "passes_by_outcome": {o: sum(1 for r in reps if r["outcome"] == o) for o in OUTCOME_FUNCS},
        "gates": {
            "min_2024_annual_n": MIN_DISCOVERY_ANNUAL_N,
            "min_2024_half_n": MIN_DISCOVERY_HALF_N,
            "min_2025_annual_n": MIN_CONFIRM_ANNUAL_N,
            "min_2025_quarter_n": MIN_CONFIRM_QUARTER_N,
            "quarter_min_eligible_blocks": MIN_QUARTER_ELIGIBLE,
            "quarter_match_rate_min": MIN_QUARTER_MATCH_RATE,
            "confirmation_effect_retention_fraction": RETENTION_FRACTION,
            "bootstrap_paths": BOOTSTRAPS,
            "circular_block_days": BLOCK_DAYS,
            "bh_q_max": BH_Q_MAX,
            "dedup_jaccard": DEDUP_JACCARD,
            "top_per_outcome": TOP_PER_OUTCOME,
        },
        "warning": "Phase E-B still uses inspected 2024-2025 data. Passing transitions are candidates only. Freeze any final candidate before opening 2026.",
        "thresholds_2024_by_symbol": cuts,
    }
    summary_path = out_dir / "phase_eb_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "transition_states_tested": summary["transition_states_tested"],
        "frozen_shortlist_count": summary["frozen_shortlist_count"],
        "phase_eb_screen_pass_count": summary["phase_eb_screen_pass_count"],
        "phase_eb_distinct_pass_count": summary["phase_eb_distinct_pass_count"],
        "passes_by_outcome": summary["passes_by_outcome"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
