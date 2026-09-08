#!/usr/bin/env python3
"""Phenomenon Discovery Lab Phase D v1.00.

Deterministic exhaustive search over all exact three-feature quintile states.
2024 creates/fixes the candidate universe and shortlist. 2025 is internal
confirmation only. 2026 remains untouched.

This is not PnL optimization and not independent validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path

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
OUTCOMES = ("direction_1h_atr", "up_first_1atr_1h")
TOP_PER_OUTCOME = 50
MIN_2024_ANNUAL_N = 500
MIN_2024_HALF_N = 180
MIN_2025_ANNUAL_N = 300
MIN_2025_QUARTER_N = 50
MIN_QUARTER_ELIGIBLE = 6
MIN_QUARTER_MATCH_RATE = 0.75
RETENTION_FRACTION = 0.25
BOOTSTRAPS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10
DEDUP_JACCARD = 0.95
EXPECTED_RULES = math.comb(len(FEATURES), 3) * 125


def finite(x: str | None) -> float | None:
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def qbin(v: float, cuts: list[float]) -> int:
    out = 1
    for c in cuts:
        if v > c:
            out += 1
        else:
            break
    return out


def ret_1h_atr(row: dict[str, str]) -> float | None:
    ret = finite(row.get("future_return_1h_pct"))
    close = finite(row.get("close"))
    atr = finite(row.get("atr14"))
    if ret is None or close is None or atr is None or atr <= 0:
        return None
    return (ret / 100.0) * close / atr


def up_first(row: dict[str, str]) -> float | None:
    t = row.get("future_first_touch_1atr_1h", "")
    if t == "UP":
        return 1.0
    if t == "DOWN":
        return 0.0
    return None


def sign(v: float | None) -> int:
    if v is None:
        return 0
    return 1 if v > 0 else -1 if v < 0 else 0


def state_text(parts: tuple[tuple[str, int], ...]) -> str:
    return " & ".join(f"{f}=Q{q}" for f, q in parts)


def parse_state(text: str) -> tuple[tuple[str, int], ...]:
    out = []
    for raw in text.split(" & "):
        f, q = raw.split("=Q", 1)
        out.append((f, int(q)))
    return tuple(out)


def stable_seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def bh_adjust(items: list[tuple[int, float]]) -> dict[int, float]:
    ordered = sorted(items, key=lambda x: x[1])
    m = len(ordered)
    out: dict[int, float] = {}
    running = 1.0
    for rank_rev in range(m - 1, -1, -1):
        idx, p = ordered[rank_rev]
        rank = rank_rev + 1
        q = min(1.0, p * m / rank)
        running = min(running, q)
        out[idx] = running
    return out


def circular_block_pvalue(
    day_state_sum: list[float],
    day_state_n: list[int],
    baseline_mean: float,
    observed_effect: float,
    wanted_sign: int,
    seed: int,
) -> float:
    n_days = len(day_state_sum)
    if n_days == 0 or sum(day_state_n) == 0:
        return 1.0
    centered = [
        day_state_sum[i] - day_state_n[i] * baseline_mean - observed_effect * day_state_n[i]
        for i in range(n_days)
    ]
    block_num = []
    block_den = []
    for start in range(n_days):
        num = 0.0
        den = 0
        for k in range(BLOCK_DAYS):
            j = (start + k) % n_days
            num += centered[j]
            den += day_state_n[j]
        block_num.append(num)
        block_den.append(den)
    blocks_needed = int(math.ceil(n_days / BLOCK_DAYS))
    rng = random.Random(seed)
    extreme = 0
    valid = 0
    for _ in range(BOOTSTRAPS):
        num = 0.0
        den = 0
        for _b in range(blocks_needed):
            s = rng.randrange(n_days)
            num += block_num[s]
            den += block_den[s]
        if den <= 0:
            continue
        boot_effect = num / den
        valid += 1
        if wanted_sign > 0:
            if boot_effect >= observed_effect:
                extreme += 1
        else:
            if boot_effect <= observed_effect:
                extreme += 1
    return (extreme + 1.0) / (valid + 1.0)


def load_rows(path: Path, year: int, cuts: dict[str, list[float]]) -> list[dict]:
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f):
            if raw.get("timestamp_utc", "")[:4] != str(year):
                continue
            ts = datetime.fromisoformat(raw["timestamp_utc"])
            bins = []
            good = True
            for feature in FEATURES:
                v = finite(raw.get(feature))
                if v is None:
                    good = False
                    break
                bins.append(qbin(v, cuts[feature]))
            if not good:
                continue
            rows.append({
                "bins": tuple(bins),
                "half": 1 if ts.month <= 6 else 2,
                "quarter": (ts.month - 1) // 3 + 1,
                "day": ts.date().isoformat(),
                "direction_1h_atr": ret_1h_atr(raw),
                "up_first_1atr_1h": up_first(raw),
            })
    return rows


def baselines(rows: list[dict], outcome: str) -> dict:
    out = {}
    for label, pred in (
        ("all", lambda r: True),
        ("h1", lambda r: r["half"] == 1),
        ("h2", lambda r: r["half"] == 2),
    ):
        vals = [r[outcome] for r in rows if pred(r) and r[outcome] is not None]
        out[label] = sum(vals) / len(vals) if vals else None
    return out


def aggregate_combo(rows: list[dict], combo: tuple[int, int, int]) -> dict[str, dict[str, list]]:
    result = {}
    for outcome in OUTCOMES:
        result[outcome] = {
            "all_n": [0] * 125,
            "all_sum": [0.0] * 125,
            "h1_n": [0] * 125,
            "h1_sum": [0.0] * 125,
            "h2_n": [0] * 125,
            "h2_sum": [0.0] * 125,
        }
    i, j, k = combo
    for r in rows:
        b = r["bins"]
        idx = (b[i] - 1) * 25 + (b[j] - 1) * 5 + (b[k] - 1)
        half = r["half"]
        for outcome in OUTCOMES:
            v = r[outcome]
            if v is None:
                continue
            rec = result[outcome]
            rec["all_n"][idx] += 1
            rec["all_sum"][idx] += v
            hk = "h1" if half == 1 else "h2"
            rec[f"{hk}_n"][idx] += 1
            rec[f"{hk}_sum"][idx] += v
    return result


def cell_effect(rec: dict[str, list], base: dict, idx: int, block: str) -> tuple[int, float | None]:
    n = rec[f"{block}_n"][idx]
    if n <= 0 or base[block] is None:
        return n, None
    mean = rec[f"{block}_sum"][idx] / n
    return n, mean - base[block]


def discover_2024(symbol_rows: dict[str, list[dict]]) -> tuple[list[dict], list[dict]]:
    bases = {s: {o: baselines(rows, o) for o in OUTCOMES} for s, rows in symbol_rows.items()}
    universe = []
    eligible = {o: [] for o in OUTCOMES}
    feature_combos = list(itertools.combinations(range(len(FEATURES)), 3))
    print(f"Phase D deterministic universe: feature triples={len(feature_combos)} exact rules={EXPECTED_RULES}")

    for combo_pos, combo in enumerate(feature_combos, 1):
        aggs = {s: aggregate_combo(rows, combo) for s, rows in symbol_rows.items()}
        fparts = tuple(FEATURES[x] for x in combo)
        for cell in range(125):
            q1 = cell // 25 + 1
            q2 = (cell % 25) // 5 + 1
            q3 = cell % 5 + 1
            parts = ((fparts[0], q1), (fparts[1], q2), (fparts[2], q3))
            state = state_text(parts)
            for outcome in OUTCOMES:
                row = {"state": state, "outcome": outcome}
                effects = []
                counts_ok = True
                signs = []
                for symbol in ("BTCUSDT", "ETHUSDT"):
                    rec = aggs[symbol][outcome]
                    base = bases[symbol][outcome]
                    for block in ("all", "h1", "h2"):
                        n, eff = cell_effect(rec, base, cell, block)
                        row[f"{symbol.lower()}_2024_{block}_n"] = n
                        row[f"{symbol.lower()}_2024_{block}_effect"] = eff
                        if block == "all":
                            counts_ok = counts_ok and n >= MIN_2024_ANNUAL_N
                        else:
                            counts_ok = counts_ok and n >= MIN_2024_HALF_N
                        if eff is not None:
                            effects.append(abs(eff))
                            signs.append(sign(eff))
                        else:
                            signs.append(0)
                same_sign = bool(signs and signs[0] != 0 and all(x == signs[0] for x in signs))
                row["discovery_counts_ok"] = counts_ok
                row["discovery_same_sign_all_blocks"] = same_sign
                row["discovery_sign"] = signs[0] if same_sign else 0
                row["discovery_worst_abs_effect"] = min(effects) if effects else None
                row["discovery_eligible"] = bool(counts_ok and same_sign)
                universe.append(row)
                if row["discovery_eligible"]:
                    eligible[outcome].append(row.copy())
        if combo_pos % 25 == 0 or combo_pos == len(feature_combos):
            print(f"2024 discovery feature triples {combo_pos}/{len(feature_combos)}")

    frozen = []
    for outcome in OUTCOMES:
        ranked = sorted(
            eligible[outcome],
            key=lambda r: (r["discovery_worst_abs_effect"] or 0.0),
            reverse=True,
        )[:TOP_PER_OUTCOME]
        for rank, r in enumerate(ranked, 1):
            r["discovery_rank"] = rank
            frozen.append(r)
    return universe, frozen


def match_parts(bins: tuple[int, ...], parts: tuple[tuple[str, int], ...]) -> bool:
    for feature, q in parts:
        if bins[FEATURES.index(feature)] != q:
            return False
    return True


def confirm_metrics(rows: list[dict], parts: tuple[tuple[str, int], ...], outcome: str, wanted_sign: int, seed: int) -> dict:
    valid = [r for r in rows if r[outcome] is not None]
    base_mean = sum(r[outcome] for r in valid) / len(valid)
    event = [r for r in valid if match_parts(r["bins"], parts)]
    n = len(event)
    mean = sum(r[outcome] for r in event) / n if n else None
    effect = None if mean is None else mean - base_mean

    qmetrics = []
    for q in range(1, 5):
        qvalid = [r for r in valid if r["quarter"] == q]
        qevent = [r for r in qvalid if match_parts(r["bins"], parts)]
        qb = sum(r[outcome] for r in qvalid) / len(qvalid) if qvalid else None
        qe = sum(r[outcome] for r in qevent) / len(qevent) if qevent else None
        qmetrics.append({
            "quarter": q,
            "n": len(qevent),
            "effect": None if qb is None or qe is None else qe - qb,
        })

    days = sorted({r["day"] for r in valid})
    dpos = {d: i for i, d in enumerate(days)}
    dsum = [0.0] * len(days)
    dn = [0] * len(days)
    for r in event:
        p = dpos[r["day"]]
        dsum[p] += r[outcome]
        dn[p] += 1
    pval = 1.0
    if effect is not None and sign(effect) == wanted_sign:
        pval = circular_block_pvalue(dsum, dn, base_mean, effect, wanted_sign, seed)
    membership = {i for i, r in enumerate(rows) if match_parts(r["bins"], parts)}
    return {"n": n, "effect": effect, "quarters": qmetrics, "p": pval, "membership": membership}


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def confirm_2025(frozen: list[dict], symbol_rows: dict[str, list[dict]]) -> tuple[list[dict], list[dict], list[dict]]:
    checked = []
    combined_memberships = []
    offset = len(symbol_rows["BTCUSDT"]) + 1000

    for idx, src in enumerate(frozen):
        row = src.copy()
        parts = parse_state(row["state"])
        wanted = int(row["discovery_sign"])
        quarter_eligible = 0
        quarter_match = 0
        total_effects = []
        total_sign_ok = True
        ps = []
        memberships = set()
        for symbol in ("BTCUSDT", "ETHUSDT"):
            met = confirm_metrics(
                symbol_rows[symbol], parts, row["outcome"], wanted,
                stable_seed("phase-d", row["state"], row["outcome"], symbol),
            )
            row[f"{symbol.lower()}_2025_n"] = met["n"]
            row[f"{symbol.lower()}_2025_effect"] = met["effect"]
            row[f"{symbol.lower()}_2025_block_p"] = met["p"]
            ps.append(met["p"])
            if met["effect"] is None or sign(met["effect"]) != wanted or met["n"] < MIN_2025_ANNUAL_N:
                total_sign_ok = False
            else:
                total_effects.append(abs(met["effect"]))
            for qm in met["quarters"]:
                if qm["n"] >= MIN_2025_QUARTER_N and qm["effect"] is not None:
                    quarter_eligible += 1
                    if sign(qm["effect"]) == wanted:
                        quarter_match += 1
            if symbol == "BTCUSDT":
                memberships |= met["membership"]
            else:
                memberships |= {offset + x for x in met["membership"]}

        row["worst_symbol_p"] = max(ps)
        row["quarter_eligible"] = quarter_eligible
        row["quarter_match"] = quarter_match
        row["quarter_match_rate"] = quarter_match / quarter_eligible if quarter_eligible else 0.0
        row["confirm_same_sign_both"] = total_sign_ok
        row["confirm_worst_abs_effect"] = min(total_effects) if len(total_effects) == 2 else None
        floor = RETENTION_FRACTION * (row["discovery_worst_abs_effect"] or 0.0)
        row["confirm_retains_25pct_effect"] = bool(
            row["confirm_worst_abs_effect"] is not None and row["confirm_worst_abs_effect"] >= floor
        )
        checked.append(row)
        combined_memberships.append(memberships)
        print(f"2025 confirm {idx + 1}/{len(frozen)} {row['outcome']} rank={row.get('discovery_rank')}")

    qvals = bh_adjust([(i, float(r["worst_symbol_p"])) for i, r in enumerate(checked)])
    for i, row in enumerate(checked):
        row["worst_symbol_bh_q"] = qvals[i]
        row["phase_d_screen_pass"] = bool(
            row["confirm_same_sign_both"]
            and row["confirm_retains_25pct_effect"]
            and row["quarter_eligible"] >= MIN_QUARTER_ELIGIBLE
            and row["quarter_match_rate"] >= MIN_QUARTER_MATCH_RATE
            and row["worst_symbol_bh_q"] <= BH_Q_MAX
        )

    pass_indices = [i for i, r in enumerate(checked) if r["phase_d_screen_pass"]]
    parent = {i: i for i in pass_indices}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    near_pairs = []
    for pos, a in enumerate(pass_indices):
        for b in pass_indices[pos + 1:]:
            if checked[a]["outcome"] != checked[b]["outcome"]:
                continue
            jac = jaccard(combined_memberships[a], combined_memberships[b])
            if jac >= DEDUP_JACCARD:
                union(a, b)
                near_pairs.append({"a": checked[a]["state"], "b": checked[b]["state"], "outcome": checked[a]["outcome"], "jaccard": jac})

    clusters = defaultdict(list)
    for i in pass_indices:
        clusters[find(i)].append(i)
    distinct = []
    cluster_rows = []
    for cnum, members in enumerate(clusters.values(), 1):
        members_sorted = sorted(
            members,
            key=lambda i: (
                checked[i]["worst_symbol_bh_q"],
                -(checked[i]["confirm_worst_abs_effect"] or 0.0),
            ),
        )
        rep = members_sorted[0]
        cid = f"D{cnum:02d}"
        for i in members:
            checked[i]["dedup_cluster"] = cid
            checked[i]["cluster_representative"] = i == rep
            cluster_rows.append({
                "cluster": cid,
                "representative": checked[rep]["state"],
                "member": checked[i]["state"],
                "outcome": checked[i]["outcome"],
            })
        distinct.append(checked[rep].copy())
    distinct.sort(key=lambda r: (r["outcome"], r["worst_symbol_bh_q"], -(r["confirm_worst_abs_effect"] or 0.0)))
    return checked, distinct, cluster_rows + near_pairs


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("empty\n", encoding="utf-8")
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--phase-b-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_d_v1")
    args = ap.parse_args()

    feat = Path(args.features_dir)
    phase_b = Path(args.phase_b_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    summary_b = json.loads((phase_b / "phase_b_summary.json").read_text(encoding="utf-8"))
    cuts_all = summary_b["thresholds_2024_by_symbol"]

    files = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        matches = sorted(feat.glob(f"{symbol}_bybit_5m_oi_price_*_features_v1.csv"))
        if len(matches) != 1:
            raise RuntimeError(f"expected exactly one {symbol} feature file, found {len(matches)}")
        files[symbol] = matches[0]

    rows24 = {s: load_rows(files[s], 2024, cuts_all[s]) for s in files}
    print("Loaded 2024:", {s: len(v) for s, v in rows24.items()})
    universe, frozen = discover_2024(rows24)
    if len(universe) != EXPECTED_RULES * len(OUTCOMES):
        raise RuntimeError(f"unexpected universe rows {len(universe)} expected {EXPECTED_RULES * len(OUTCOMES)}")

    universe_path = out / "phase_d_2024_full_universe.csv"
    frozen_path = out / "phase_d_frozen_shortlist_2024.csv"
    write_csv(universe_path, universe)
    write_csv(frozen_path, frozen)
    frozen_hash = sha256(frozen_path)

    rows25 = {s: load_rows(files[s], 2025, cuts_all[s]) for s in files}
    print("Loaded 2025:", {s: len(v) for s, v in rows25.items()})
    checked, distinct, clusters = confirm_2025(frozen, rows25)

    checked_path = out / "phase_d_2025_confirmation.csv"
    distinct_path = out / "phase_d_distinct_passes.csv"
    clusters_path = out / "phase_d_dedup_clusters.csv"
    write_csv(checked_path, checked)
    write_csv(distinct_path, distinct)
    write_csv(clusters_path, clusters)

    summary = {
        "schema": 1,
        "phase": "D",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "method": "deterministic exhaustive exact three-feature quintile states; 2024 generation with BTC+ETH and H1/H2 sign stability; frozen top 50 per directional outcome; 2025 internal confirmation with quarter stability, circular 5-day block bootstrap and BH correction; 2026 untouched",
        "features": FEATURES,
        "outcomes": list(OUTCOMES),
        "exact_three_clause_rules": EXPECTED_RULES,
        "universe_tests_total": EXPECTED_RULES * len(OUTCOMES),
        "frozen_shortlist_count": len(frozen),
        "frozen_shortlist_sha256": frozen_hash,
        "phase_d_screen_pass_count": sum(1 for r in checked if r["phase_d_screen_pass"]),
        "phase_d_distinct_pass_count": len(distinct),
        "passes_by_outcome": {o: sum(1 for r in distinct if r["outcome"] == o) for o in OUTCOMES},
        "gates": {
            "min_2024_annual_n": MIN_2024_ANNUAL_N,
            "min_2024_half_n": MIN_2024_HALF_N,
            "top_per_outcome": TOP_PER_OUTCOME,
            "min_2025_annual_n": MIN_2025_ANNUAL_N,
            "min_2025_quarter_n": MIN_2025_QUARTER_N,
            "quarter_min_eligible_blocks": MIN_QUARTER_ELIGIBLE,
            "quarter_match_rate_min": MIN_QUARTER_MATCH_RATE,
            "confirmation_effect_retention_fraction": RETENTION_FRACTION,
            "bootstrap_paths": BOOTSTRAPS,
            "circular_block_days": BLOCK_DAYS,
            "bh_q_max": BH_Q_MAX,
            "dedup_jaccard": DEDUP_JACCARD,
        },
        "protected_2026_untouched": True,
        "independent_validation": False,
        "warning": "Phase D still uses inspected historical data. Any final candidate must be frozen before 2026 is opened. No PnL claim is authorized.",
    }
    (out / "phase_d_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("exact_three_clause_rules", "frozen_shortlist_count", "phase_d_screen_pass_count", "phase_d_distinct_pass_count", "passes_by_outcome")}, indent=2))
    print(f"Output: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
