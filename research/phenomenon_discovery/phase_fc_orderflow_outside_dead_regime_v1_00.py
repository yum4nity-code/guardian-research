#!/usr/bin/env python3
"""Phase F-C: order-flow atlas outside the frozen Phase-C low-movement regime.

Scientific intent:
- Reuse the exact Phase-C distinct low-movement states as a fixed exclusion filter.
- Reuse Phase-B 2024 quintile thresholds to reconstruct that filter causally.
- Keep the same univariate Binance order-flow feature family and gates as F-B.
- 2024 discovers/ranks candidates inside the active (non-dead) regime.
- Freeze shortlist before 2025 confirmation.
- 2026 remains untouched.

This is still discovery robustness, not independent validation and not PnL research.
"""
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

FLOW_FEATURES = [
    "spot_taker_imbalance", "perp_taker_imbalance", "taker_imbalance_diff",
    "perp_spot_basis_bps", "log_quote_volume_ratio", "log_trade_count_ratio",
    "spot_taker_imbalance_change_15m", "spot_taker_imbalance_change_1h",
    "perp_taker_imbalance_change_15m", "perp_taker_imbalance_change_1h",
    "taker_imbalance_diff_change_15m", "taker_imbalance_diff_change_1h",
    "perp_spot_basis_bps_change_15m", "perp_spot_basis_bps_change_1h",
    "log_quote_volume_ratio_change_15m", "log_quote_volume_ratio_change_1h",
    "log_trade_count_ratio_change_15m", "log_trade_count_ratio_change_1h",
]
QPROBS = (0.2, 0.4, 0.6, 0.8)
MIN_DISCOVERY_ANNUAL_N = 500
MIN_DISCOVERY_HALF_N = 180
MIN_CONFIRM_ANNUAL_N = 300
MIN_CONFIRM_QUARTER_N = 50
MIN_QUARTER_ELIGIBLE = 6
MIN_QUARTER_MATCH_RATE = 0.75
RETENTION_FRACTION = 0.25
TOP_PER_OUTCOME = 25
BOOTSTRAPS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10
EXPECTED_PHASE_C_PASSES = 18


def finite(x):
    if x in (None, ""):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def quantiles(vals):
    s = sorted(vals)
    if not s:
        raise RuntimeError("empty quantile sample")
    n = len(s)
    out = []
    for p in QPROBS:
        pos = p * (n - 1)
        lo, hi = int(math.floor(pos)), int(math.ceil(pos))
        w = pos - lo
        out.append(s[lo] if lo == hi else s[lo] * (1 - w) + s[hi] * w)
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
    return 1.0 if t == "UP" else 0.0 if t == "DOWN" else None


OUTCOMES = {"direction_1h_atr": ret_1h_atr, "up_first_1atr_1h": up_first}


def parse_state(text):
    parts = []
    for raw in text.split(" & "):
        feature, q = raw.split("=Q", 1)
        parts.append((feature, int(q)))
    return tuple(parts)


def load_phase_c_filter(path: Path):
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != EXPECTED_PHASE_C_PASSES:
        raise RuntimeError(f"Phase-C filter count {len(rows)} != {EXPECTED_PHASE_C_PASSES}")
    states = []
    for r in rows:
        if r.get("outcome") != "move_ge_1atr_1h":
            raise RuntimeError(f"unexpected Phase-C outcome: {r.get('outcome')}")
        if r.get("discovery_sign") not in ("-1", "-1.0"):
            raise RuntimeError(f"unexpected Phase-C sign for {r.get('state')}: {r.get('discovery_sign')}")
        if str(r.get("phase_c_screen_pass", "")).lower() != "true":
            raise RuntimeError(f"non-passing Phase-C row supplied: {r.get('state')}")
        states.append(parse_state(r["state"]))
    return states


def load_phase_b_thresholds(path: Path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    thresholds = obj.get("thresholds_2024_by_symbol")
    if not isinstance(thresholds, dict):
        raise RuntimeError("Phase-B summary missing thresholds_2024_by_symbol")
    return thresholds


def load_joined(flow_path, feat_path, year):
    feat = {}
    with feat_path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("timestamp_utc", "").startswith(f"{year}-"):
                feat[int(r["timestamp_ms"])] = r
    rows = []
    with flow_path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("timestamp_utc", "").startswith(f"{year}-"):
                continue
            ts = int(r["timestamp_ms"])
            fr = feat.get(ts)
            if fr is None:
                continue
            raw = dict(fr)
            raw.update(r)
            dt = datetime.fromisoformat(r["timestamp_utc"])
            rows.append({
                "raw": raw,
                "half": 1 if dt.month <= 6 else 2,
                "quarter": ((dt.month - 1) // 3) + 1,
                "day": dt.date().isoformat(),
            })
    return rows


def learn_flow_cuts(rows):
    out = {}
    for feature in FLOW_FEATURES:
        vals = [v for x in rows if (v := finite(x["raw"].get(feature))) is not None]
        if len(vals) < 1000:
            raise RuntimeError(f"too few 2024 values for {feature}: {len(vals)}")
        out[feature] = quantiles(vals)
    return out


def reconstruct_phase_c_bins(row, thresholds):
    bins = {}
    for feature, cuts in thresholds.items():
        v = finite(row["raw"].get(feature))
        if v is not None:
            bins[feature] = qbin(v, cuts)
    return bins


def matches(parts, bins):
    return all(bins.get(feature) == q for feature, q in parts)


def annotate(rows, flow_cuts, phase_b_thresholds, dead_states):
    for x in rows:
        phase_bins = reconstruct_phase_c_bins(x, phase_b_thresholds)
        x["dead_regime"] = any(matches(parts, phase_bins) for parts in dead_states)
        x["flow_bins"] = {
            f: qbin(v, flow_cuts[f])
            for f in FLOW_FEATURES
            if (v := finite(x["raw"].get(f))) is not None
        }
        x["outcomes"] = {name: fn(x["raw"]) for name, fn in OUTCOMES.items()}


def active_subset(_i, x):
    return not x["dead_regime"]


def members(rows, feature, q):
    return {i for i, x in enumerate(rows) if not x["dead_regime"] and x["flow_bins"].get(feature) == q}


def baseline(rows, outcome, subset=None):
    vals = [
        x["outcomes"][outcome]
        for i, x in enumerate(rows)
        if (subset is None or subset(i, x)) and x["outcomes"][outcome] is not None
    ]
    return sum(vals) / len(vals) if vals else None


def effect(rows, mem, outcome, subset=None):
    base = baseline(rows, outcome, subset)
    vals = []
    for i in mem:
        x = rows[i]
        if subset is not None and not subset(i, x):
            continue
        v = x["outcomes"][outcome]
        if v is not None:
            vals.append(v)
    return len(vals), None if base is None or not vals else sum(vals) / len(vals) - base


def sgn(x):
    return 1 if x > 0 else -1 if x < 0 else 0


def stable_seed(*parts):
    return int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:16], 16)


def block_p(rows, mem, outcome, obs, wanted, seed):
    valid = [x for x in rows if not x["dead_regime"] and x["outcomes"][outcome] is not None]
    if not valid:
        return 1.0
    base = sum(x["outcomes"][outcome] for x in valid) / len(valid)
    days = sorted({x["day"] for x in valid})
    pos = {d: i for i, d in enumerate(days)}
    ds, dn = [0.0] * len(days), [0] * len(days)
    for i in mem:
        x = rows[i]
        if x["dead_regime"]:
            continue
        v = x["outcomes"][outcome]
        if v is None:
            continue
        j = pos[x["day"]]
        ds[j] += v
        dn[j] += 1
    centered = [ds[i] - dn[i] * base - obs * dn[i] for i in range(len(days))]
    bn, bd = [], []
    for start in range(len(days)):
        num, den = 0.0, 0
        for k in range(BLOCK_DAYS):
            j = (start + k) % len(days)
            num += centered[j]
            den += dn[j]
        bn.append(num)
        bd.append(den)
    rng = random.Random(seed)
    need = int(math.ceil(len(days) / BLOCK_DAYS))
    extreme = validn = 0
    for _ in range(BOOTSTRAPS):
        num, den = 0.0, 0
        for _b in range(need):
            j = rng.randrange(len(days))
            num += bn[j]
            den += bd[j]
        if den <= 0:
            continue
        e = num / den
        validn += 1
        extreme += int(e >= obs) if wanted > 0 else int(e <= obs)
    return (extreme + 1) / (validn + 1)


def bh(items):
    ordered = sorted(items, key=lambda x: x[1])
    m = len(ordered)
    out = {}
    run = 1.0
    for rev in range(m - 1, -1, -1):
        idx, p = ordered[rev]
        rank = rev + 1
        q = min(1.0, p * m / rank)
        run = min(run, q)
        out[idx] = run
    return out


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("state\n", encoding="utf-8")
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\binance_orderflow_v1")
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--phase-b-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1")
    ap.add_argument("--phase-c-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_c_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_fc_v1")
    a = ap.parse_args()

    flow, feat, pb, pc, out = map(Path, (a.flow_dir, a.features_dir, a.phase_b_dir, a.phase_c_dir, a.output_dir))
    out.mkdir(parents=True, exist_ok=True)
    phase_c_path = pc / "phase_c_distinct_passes.csv"
    phase_b_path = pb / "phase_b_summary.json"
    if not phase_c_path.exists() or not phase_b_path.exists():
        raise RuntimeError("missing Phase-B thresholds or Phase-C distinct-pass artifact")
    dead_states = load_phase_c_filter(phase_c_path)
    thresholds = load_phase_b_thresholds(phase_b_path)

    r24, r25, flow_cuts = {}, {}, {}
    audit = {
        "schema": 1,
        "phase": "F-C",
        "phase_c_filter_state_count": len(dead_states),
        "phase_c_filter_sha256": sha(phase_c_path),
        "phase_b_summary_sha256": sha(phase_b_path),
        "symbols": {},
    }

    for sym in ("BTCUSDT", "ETHUSDT"):
        ff = flow / f"{sym}_binance_spot_um_5m_orderflow_2024-01-01_2026-01-01.csv"
        ffs = sorted(feat.glob(f"{sym}_bybit_5m_oi_price_*_features_v1.csv"))
        if not ff.exists() or len(ffs) != 1:
            raise RuntimeError(f"missing F-A/features inputs for {sym}")
        r24[sym] = load_joined(ff, ffs[0], 2024)
        r25[sym] = load_joined(ff, ffs[0], 2025)
        flow_cuts[sym] = learn_flow_cuts(r24[sym])  # same full-2024 basis as F-B
        annotate(r24[sym], flow_cuts[sym], thresholds[sym], dead_states)
        annotate(r25[sym], flow_cuts[sym], thresholds[sym], dead_states)
        d24 = sum(1 for x in r24[sym] if x["dead_regime"])
        d25 = sum(1 for x in r25[sym] if x["dead_regime"])
        audit["symbols"][sym] = {
            "rows_2024": len(r24[sym]), "dead_2024": d24, "active_2024": len(r24[sym]) - d24,
            "dead_pct_2024": d24 / len(r24[sym]) if r24[sym] else None,
            "rows_2025": len(r25[sym]), "dead_2025": d25, "active_2025": len(r25[sym]) - d25,
            "dead_pct_2025": d25 / len(r25[sym]) if r25[sym] else None,
        }
        print(f"{sym}: 2024 active={len(r24[sym])-d24}/{len(r24[sym])} 2025 active={len(r25[sym])-d25}/{len(r25[sym])}")

    audit_path = out / "phase_fc_filter_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    universe, eligible = [], defaultdict(list)
    for feature in FLOW_FEATURES:
        for q in range(1, 6):
            state = f"{feature}=Q{q}"
            for outcome in OUTCOMES:
                rec = {"state": state, "outcome": outcome, "feature": feature, "q": q}
                effects, wanted, ok, halfok = [], None, True, True
                for sym in ("BTCUSDT", "ETHUSDT"):
                    mem = members(r24[sym], feature, q)
                    n, e = effect(r24[sym], mem, outcome, active_subset)
                    rec[f"{sym.lower()}_2024_active_n"] = n
                    rec[f"{sym.lower()}_2024_active_effect"] = e
                    if n < MIN_DISCOVERY_ANNUAL_N or e is None or sgn(e) == 0:
                        ok = False
                    else:
                        effects.append(abs(e))
                        if wanted is None:
                            wanted = sgn(e)
                        elif sgn(e) != wanted:
                            ok = False
                    for h in (1, 2):
                        hn, he = effect(
                            r24[sym], mem, outcome,
                            lambda _i, x, h=h: (not x["dead_regime"]) and x["half"] == h,
                        )
                        rec[f"{sym.lower()}_2024_h{h}_active_n"] = hn
                        rec[f"{sym.lower()}_2024_h{h}_active_effect"] = he
                        if hn < MIN_DISCOVERY_HALF_N or he is None or (wanted is not None and sgn(he) != wanted):
                            halfok = False
                rec["discovery_sign"] = wanted if ok else None
                rec["discovery_worst_abs_effect"] = min(effects) if ok and len(effects) == 2 else None
                rec["discovery_eligible"] = bool(ok and halfok)
                universe.append(rec)
                if rec["discovery_eligible"]:
                    eligible[outcome].append(rec)

    frozen = []
    for outcome, items in eligible.items():
        frozen += [dict(x) for x in sorted(items, key=lambda r: r["discovery_worst_abs_effect"], reverse=True)[:TOP_PER_OUTCOME]]
    frozen.sort(key=lambda r: (r["outcome"], -r["discovery_worst_abs_effect"], r["state"]))
    up = out / "phase_fc_2024_universe.csv"
    fp = out / "phase_fc_frozen_shortlist_2024.csv"
    write_csv(up, universe)
    write_csv(fp, frozen)
    frozen_hash = sha(fp)

    conf = []
    for rec0 in frozen:
        rec = dict(rec0)
        wanted = int(rec["discovery_sign"])
        feature, q, outcome = rec["feature"], int(rec["q"]), rec["outcome"]
        effects, annual, qelig, qmatch, ps = [], True, 0, 0, []
        for sym in ("BTCUSDT", "ETHUSDT"):
            mem = members(r25[sym], feature, q)
            n, e = effect(r25[sym], mem, outcome, active_subset)
            rec[f"{sym.lower()}_2025_active_n"] = n
            rec[f"{sym.lower()}_2025_active_effect"] = e
            if n < MIN_CONFIRM_ANNUAL_N or e is None or sgn(e) != wanted:
                annual = False
            else:
                effects.append(abs(e))
                p = block_p(r25[sym], mem, outcome, e, wanted, stable_seed("phase-fc", rec["state"], outcome, sym))
                ps.append(p)
                rec[f"{sym.lower()}_block_p"] = p
            for qq in range(1, 5):
                qn, qe = effect(
                    r25[sym], mem, outcome,
                    lambda _i, x, qq=qq: (not x["dead_regime"]) and x["quarter"] == qq,
                )
                rec[f"{sym.lower()}_2025_q{qq}_active_n"] = qn
                rec[f"{sym.lower()}_2025_q{qq}_active_effect"] = qe
                if qn >= MIN_CONFIRM_QUARTER_N and qe is not None:
                    qelig += 1
                    qmatch += int(sgn(qe) == wanted)
        rec["confirm_same_sign_both"] = annual
        rec["confirm_worst_abs_effect"] = min(effects) if annual and len(effects) == 2 else None
        rec["confirm_retains_effect"] = bool(
            rec["confirm_worst_abs_effect"] is not None
            and rec["confirm_worst_abs_effect"] >= RETENTION_FRACTION * rec["discovery_worst_abs_effect"]
        )
        rec["quarter_eligible"] = qelig
        rec["quarter_match"] = qmatch
        rec["quarter_match_rate"] = qmatch / qelig if qelig else 0.0
        rec["quarter_stable"] = qelig >= MIN_QUARTER_ELIGIBLE and rec["quarter_match_rate"] >= MIN_QUARTER_MATCH_RATE
        rec["worst_symbol_p"] = max(ps) if len(ps) == 2 else 1.0
        conf.append(rec)

    qmap = bh([(i, r["worst_symbol_p"]) for i, r in enumerate(conf)]) if conf else {}
    passes = []
    for i, r in enumerate(conf):
        r["worst_symbol_bh_q"] = qmap.get(i, 1.0)
        r["phase_fc_screen_pass"] = bool(
            r["confirm_same_sign_both"] and r["confirm_retains_effect"]
            and r["quarter_stable"] and r["worst_symbol_bh_q"] <= BH_Q_MAX
        )
        if r["phase_fc_screen_pass"]:
            passes.append(r)

    cp = out / "phase_fc_2025_confirmation.csv"
    pp = out / "phase_fc_distinct_passes.csv"
    write_csv(cp, conf)
    write_csv(pp, passes)
    summary = {
        "schema": 1,
        "phase": "F-C",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "method": "F-B univariate order-flow atlas conditioned on the complement of the exact frozen 18-state Phase-C low-movement union; Phase-B 2024 thresholds reused unchanged",
        "phase_c_filter_state_count": len(dead_states),
        "phase_c_filter_sha256": sha(phase_c_path),
        "phase_b_summary_sha256": sha(phase_b_path),
        "features": FLOW_FEATURES,
        "states_tested": len(FLOW_FEATURES) * 5,
        "universe_tests_total": len(FLOW_FEATURES) * 5 * len(OUTCOMES),
        "frozen_shortlist_count": len(frozen),
        "frozen_shortlist_sha256": frozen_hash,
        "phase_fc_screen_pass_count": len(passes),
        "passes_by_outcome": {o: sum(1 for r in passes if r["outcome"] == o) for o in OUTCOMES},
        "protected_2026_untouched": True,
        "independent_validation": False,
        "gates": {
            "top_per_outcome": TOP_PER_OUTCOME,
            "bootstrap_paths": BOOTSTRAPS,
            "circular_block_days": BLOCK_DAYS,
            "bh_q_max": BH_Q_MAX,
            "confirmation_effect_retention_fraction": RETENTION_FRACTION,
            "quarter_match_rate_min": MIN_QUARTER_MATCH_RATE,
            "quarter_min_eligible_blocks": MIN_QUARTER_ELIGIBLE,
            "same_gates_as_phase_fb": True,
        },
        "warning": "Phase F-C uses inspected 2024-2025 data. Any pass remains a discovery candidate only. Freeze before opening 2026.",
    }
    (out / "phase_fc_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
