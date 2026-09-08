#!/usr/bin/env python3
"""Phenomenon Discovery Lab Phase C v1.00.

Post-Phase-B robustness screen on already inspected 2024-2025 data.
This stage does NOT create independent validation. 2026 stays untouched.

Goals:
- de-duplicate near-identical state definitions;
- quantify 2025 time-block stability;
- test local quantile-neighbour plateaus;
- apply a conservative multiple-testing screen across all 75 Phase-B candidates;
- reduce the candidate set before a frozen 2026 validation.

No PnL optimisation. No trading rules. No future_* field is a predictor.
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

BOOTSTRAPS = 3000
BLOCK_DAYS = 5
BH_Q_MAX = 0.10
MIN_ANNUAL_N = 300
MIN_QUARTER_N = 50
MIN_QUARTER_ELIGIBLE = 6
MIN_QUARTER_MATCH_RATE = 0.75
MIN_PLATEAU_ELIGIBLE = 2
MIN_PLATEAU_MATCH_RATE = 0.50
DEDUP_JACCARD = 0.98


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


def move_1h(row: dict[str, str]) -> float | None:
    mfe = finite(row.get("future_mfe_1h_atr"))
    mae = finite(row.get("future_mae_1h_atr"))
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


def parse_state(text: str) -> tuple[tuple[str, int], ...]:
    parts = []
    for raw in text.split(" & "):
        feature, q = raw.split("=Q", 1)
        parts.append((feature, int(q)))
    return tuple(parts)


def state_text(parts: tuple[tuple[str, int], ...]) -> str:
    return " & ".join(f"{f}=Q{q}" for f, q in parts)


def match_state(bins: dict[str, int], parts: tuple[tuple[str, int], ...]) -> bool:
    return all(bins.get(f) == q for f, q in parts)


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


def load_candidates(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_symbol(path: Path, cuts: dict[str, list[float]]) -> list[dict]:
    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("timestamp_utc", "").startswith("2025-"):
                continue
            ts = datetime.fromisoformat(r["timestamp_utc"])
            bins = {}
            for feature, fc in cuts.items():
                v = finite(r.get(feature))
                if v is not None:
                    bins[feature] = qbin(v, fc)
            outs = {name: fn(r) for name, fn in OUTCOME_FUNCS.items()}
            rows.append({
                "day": ts.date().isoformat(),
                "quarter": (ts.month - 1) // 3 + 1,
                "bins": bins,
                "outcomes": outs,
            })
    return rows


def state_metrics(rows: list[dict], parts: tuple[tuple[str, int], ...], outcome: str) -> dict:
    valid = [r for r in rows if r["outcomes"][outcome] is not None]
    base_n = len(valid)
    base_sum = sum(r["outcomes"][outcome] for r in valid)
    base_mean = base_sum / base_n if base_n else 0.0
    event_rows = [r for r in valid if match_state(r["bins"], parts)]
    state_n = len(event_rows)
    state_sum = sum(r["outcomes"][outcome] for r in event_rows)
    state_mean = state_sum / state_n if state_n else None
    effect = None if state_mean is None else state_mean - base_mean

    days = sorted({r["day"] for r in valid})
    day_pos = {d: i for i, d in enumerate(days)}
    day_state_sum = [0.0] * len(days)
    day_state_n = [0] * len(days)
    for r in event_rows:
        j = day_pos[r["day"]]
        day_state_sum[j] += r["outcomes"][outcome]
        day_state_n[j] += 1

    q_metrics = []
    for q in range(1, 5):
        qvalid = [r for r in valid if r["quarter"] == q]
        qevent = [r for r in qvalid if match_state(r["bins"], parts)]
        qb = sum(r["outcomes"][outcome] for r in qvalid) / len(qvalid) if qvalid else None
        qe = sum(r["outcomes"][outcome] for r in qevent) / len(qevent) if qevent else None
        q_metrics.append({
            "quarter": q,
            "n": len(qevent),
            "effect": None if qb is None or qe is None else qe - qb,
        })

    return {
        "baseline_mean": base_mean,
        "state_n": state_n,
        "state_mean": state_mean,
        "effect": effect,
        "days": days,
        "day_state_sum": day_state_sum,
        "day_state_n": day_state_n,
        "quarters": q_metrics,
        "membership": {i for i, r in enumerate(rows) if match_state(r["bins"], parts)},
    }


def neighbour_states(parts: tuple[tuple[str, int], ...]) -> list[tuple[tuple[str, int], ...]]:
    out = []
    for i, (f, q) in enumerate(parts):
        for nq in (q - 1, q + 1):
            if 1 <= nq <= 5:
                p = list(parts)
                p[i] = (f, nq)
                out.append(tuple(p))
    return out


def jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return 0.0 if u == 0 else len(a & b) / u


class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\features_v1")
    ap.add_argument("--phase-b-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_b_v1")
    ap.add_argument("--output-dir", default=r"D:\MT5_Backtests\Research\PhenomenonDiscovery\phase_c_v1")
    args = ap.parse_args()

    feat_dir = Path(args.features_dir)
    bdir = Path(args.phase_b_dir)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    summary = json.loads((bdir / "phase_b_summary.json").read_text(encoding="utf-8"))
    candidates = load_candidates(bdir / "phase_b_shortlist_and_confirmation.csv")
    if len(candidates) != 75:
        raise RuntimeError(f"Expected 75 Phase-B shortlist rows, found {len(candidates)}")

    symbol_rows = {}
    for symbol in ("BTCUSDT", "ETHUSDT"):
        matches = sorted(feat_dir.glob(f"{symbol}_bybit_5m_oi_price_*_features_v1.csv"))
        if len(matches) != 1:
            raise RuntimeError(f"Expected one feature file for {symbol}, found {len(matches)}")
        cuts = summary["thresholds_2024_by_symbol"][symbol]
        symbol_rows[symbol] = load_symbol(matches[0], cuts)
        print(f"{symbol}: loaded 2025 rows={len(symbol_rows[symbol])}")

    result_rows = []
    all_metrics: dict[tuple[int, str], dict] = {}

    for idx, c in enumerate(candidates):
        state = c["state"]
        outcome = c["outcome"]
        wanted = int(c["discovery_sign"])
        parts = parse_state(state)
        row = dict(c)
        pvals = []
        quarter_eligible = 0
        quarter_match = 0
        plateau_eligible = 0
        plateau_match = 0

        for symbol in ("BTCUSDT", "ETHUSDT"):
            m = state_metrics(symbol_rows[symbol], parts, outcome)
            all_metrics[(idx, symbol)] = m
            effect = m["effect"]
            if effect is None or m["state_n"] < MIN_ANNUAL_N:
                p = 1.0
            else:
                p = circular_block_pvalue(
                    m["day_state_sum"], m["day_state_n"], m["baseline_mean"], effect, wanted,
                    stable_seed("phase-c", str(idx), symbol, state, outcome),
                )
            pvals.append(p)
            low = symbol.lower()
            row[f"{low}_2025_n_recalc"] = m["state_n"]
            row[f"{low}_2025_effect_recalc"] = effect
            row[f"{low}_block_p"] = p

            for qm in m["quarters"]:
                eff = qm["effect"]
                if qm["n"] >= MIN_QUARTER_N and eff is not None:
                    quarter_eligible += 1
                    if (eff > 0 and wanted > 0) or (eff < 0 and wanted < 0):
                        quarter_match += 1

        # Local plateau: one quantile step in one condition at a time.
        for neigh in neighbour_states(parts):
            same_both = True
            eligible_both = True
            for symbol in ("BTCUSDT", "ETHUSDT"):
                nm = state_metrics(symbol_rows[symbol], neigh, outcome)
                if nm["state_n"] < MIN_ANNUAL_N or nm["effect"] is None:
                    eligible_both = False
                    break
                if not ((nm["effect"] > 0 and wanted > 0) or (nm["effect"] < 0 and wanted < 0)):
                    same_both = False
            if eligible_both:
                plateau_eligible += 1
                if same_both:
                    plateau_match += 1

        row["worst_symbol_p"] = max(pvals)
        row["quarter_eligible"] = quarter_eligible
        row["quarter_match"] = quarter_match
        row["quarter_match_rate"] = quarter_match / quarter_eligible if quarter_eligible else 0.0
        row["plateau_eligible"] = plateau_eligible
        row["plateau_match"] = plateau_match
        row["plateau_match_rate"] = plateau_match / plateau_eligible if plateau_eligible else 0.0
        result_rows.append(row)

    bh = bh_adjust([(i, float(r["worst_symbol_p"])) for i, r in enumerate(result_rows)])
    for i, r in enumerate(result_rows):
        r["worst_symbol_bh_q"] = bh[i]

    # De-duplicate only Phase-B survivors, within the same outcome.
    survivor_indices = [i for i, r in enumerate(result_rows) if r.get("phase_b_survivor") == "True"]
    dsu = DSU(len(result_rows))
    duplicate_pairs = []
    for ai in range(len(survivor_indices)):
        i = survivor_indices[ai]
        for bj in range(ai + 1, len(survivor_indices)):
            j = survivor_indices[bj]
            if result_rows[i]["outcome"] != result_rows[j]["outcome"]:
                continue
            jb = jaccard(all_metrics[(i, "BTCUSDT")]["membership"], all_metrics[(j, "BTCUSDT")]["membership"])
            je = jaccard(all_metrics[(i, "ETHUSDT")]["membership"], all_metrics[(j, "ETHUSDT")]["membership"])
            if min(jb, je) >= DEDUP_JACCARD:
                dsu.union(i, j)
                duplicate_pairs.append((i, j, jb, je))

    clusters: dict[int, list[int]] = defaultdict(list)
    for i in survivor_indices:
        clusters[dsu.find(i)].append(i)

    cluster_rows = []
    for cid_num, members in enumerate(sorted(clusters.values(), key=lambda m: min(m)), start=1):
        # Prefer strongest corrected evidence, then effect retention.
        members_sorted = sorted(
            members,
            key=lambda i: (
                float(result_rows[i]["worst_symbol_bh_q"]),
                -float(result_rows[i].get("confirm_worst_abs_effect") or 0.0),
            ),
        )
        rep = members_sorted[0]
        cluster_id = f"C{cid_num:02d}"
        for i in members:
            result_rows[i]["dedup_cluster"] = cluster_id
            result_rows[i]["cluster_representative"] = (i == rep)
        cluster_rows.append({
            "cluster": cluster_id,
            "outcome": result_rows[rep]["outcome"],
            "representative_state": result_rows[rep]["state"],
            "member_count": len(members),
            "members": " || ".join(result_rows[i]["state"] for i in members),
        })

    for r in result_rows:
        if "dedup_cluster" not in r:
            r["dedup_cluster"] = ""
            r["cluster_representative"] = False
        r["phase_c_screen_pass"] = bool(
            r.get("phase_b_survivor") == "True"
            and bool(r["cluster_representative"])
            and float(r["worst_symbol_bh_q"]) <= BH_Q_MAX
            and int(r["quarter_eligible"]) >= MIN_QUARTER_ELIGIBLE
            and float(r["quarter_match_rate"]) >= MIN_QUARTER_MATCH_RATE
            and int(r["plateau_eligible"]) >= MIN_PLATEAU_ELIGIBLE
            and float(r["plateau_match_rate"]) >= MIN_PLATEAU_MATCH_RATE
        )

    passes = [r for r in result_rows if r["phase_c_screen_pass"]]
    passes.sort(key=lambda r: (float(r["worst_symbol_bh_q"]), -float(r.get("confirm_worst_abs_effect") or 0.0)))

    def write_csv(path: Path, rows: list[dict]) -> None:
        if not rows:
            path.write_text("empty\n", encoding="utf-8")
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

    write_csv(outdir / "phase_c_all_candidates.csv", result_rows)
    write_csv(outdir / "phase_c_distinct_passes.csv", passes)
    write_csv(outdir / "phase_c_dedup_clusters.csv", cluster_rows)

    summary_out = {
        "schema": 1,
        "phase": "C",
        "status": "DISCOVERY_ROBUSTNESS_ONLY",
        "independent_validation": False,
        "protected_2026_untouched": True,
        "phase_b_candidates_tested": len(result_rows),
        "phase_b_survivors": len(survivor_indices),
        "dedup_clusters": len(clusters),
        "near_duplicate_pairs": len(duplicate_pairs),
        "phase_c_distinct_pass_count": len(passes),
        "passes_by_outcome": {o: sum(1 for r in passes if r["outcome"] == o) for o in OUTCOME_FUNCS},
        "gates": {
            "bootstrap_paths": BOOTSTRAPS,
            "circular_block_days": BLOCK_DAYS,
            "multiple_testing": "Benjamini-Hochberg on worst(BTC p, ETH p) across all 75 Phase-B candidates",
            "bh_q_max": BH_Q_MAX,
            "quarter_min_n": MIN_QUARTER_N,
            "quarter_min_eligible_blocks": MIN_QUARTER_ELIGIBLE,
            "quarter_match_rate_min": MIN_QUARTER_MATCH_RATE,
            "plateau_min_eligible_neighbours": MIN_PLATEAU_ELIGIBLE,
            "plateau_match_rate_min": MIN_PLATEAU_MATCH_RATE,
            "dedup_jaccard_both_symbols": DEDUP_JACCARD,
        },
        "warning": "Phase C uses already inspected 2024-2025 data. Passing is not validation. Freeze final candidates before opening any 2026 data.",
    }
    (outdir / "phase_c_summary.json").write_text(json.dumps(summary_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary_out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
