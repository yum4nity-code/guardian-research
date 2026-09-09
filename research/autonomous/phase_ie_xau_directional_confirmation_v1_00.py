#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

PHASE_PUBLISH = "phase-ie-xau-directional-confirmation"


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def heartbeat(path: Path | None, completed: int, total: int, stage: str) -> None:
    if path:
        atomic_json(path, {
            "completed": int(completed),
            "total": int(total),
            "stage": stage,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        })


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("guardian_phase_ic", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Phase I-C engine: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sign_of(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def holm_adjust(pvalues: list[float]) -> list[float]:
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    out = [1.0] * m
    running = 0.0
    for rank, idx in enumerate(order):
        adjusted = min(1.0, (m - rank) * float(pvalues[idx]))
        running = max(running, adjusted)
        out[idx] = running
    return out


def block_bootstrap_ci(values: np.ndarray, mask: np.ndarray, block_len: int, reps: int, alpha_family: float, family_n: int, seed: int) -> tuple[float, float, int]:
    finite = np.isfinite(values)
    n = len(values)
    blocks = []
    for start in range(0, n, block_len):
        end = min(n, start + block_len)
        v = values[start:end]
        m = mask[start:end]
        f = finite[start:end]
        sf = m & f
        cf = (~m) & f
        blocks.append((float(np.sum(v[sf])), int(np.sum(sf)), float(np.sum(v[cf])), int(np.sum(cf))))
    arr = np.asarray(blocks, dtype=float)
    if len(arr) < 2:
        raise RuntimeError("too few bootstrap blocks")
    rng = np.random.default_rng(seed)
    effects: list[np.ndarray] = []
    batch = 250
    for first in range(0, reps, batch):
        b = min(batch, reps - first)
        idx = rng.integers(0, len(arr), size=(b, len(arr)), endpoint=False)
        sampled = arr[idx].sum(axis=1)
        ns = sampled[:, 1]
        nc = sampled[:, 3]
        ok = (ns > 0) & (nc > 0)
        eff = np.full(b, np.nan, dtype=float)
        eff[ok] = sampled[ok, 0] / ns[ok] - sampled[ok, 2] / nc[ok]
        effects.append(eff)
    boot = np.concatenate(effects)
    boot = boot[np.isfinite(boot)]
    if len(boot) < int(reps * 0.95):
        raise RuntimeError(f"too few valid bootstrap replicates: {len(boot)}/{reps}")
    alpha_each = float(alpha_family) / max(1, int(family_n))
    lo = float(np.quantile(boot, alpha_each / 2.0))
    hi = float(np.quantile(boot, 1.0 - alpha_each / 2.0))
    return lo, hi, int(len(boot))


def publish(publisher: Path | None, status: str, summary: str, artifacts: list[Path], cwd: Path) -> None:
    if publisher is None:
        return
    cmd = [sys.executable, str(publisher), "--phase", PHASE_PUBLISH, "--status", status, "--summary", summary]
    for p in artifacts:
        if p.exists():
            cmd += ["--artifact", str(p)]
    cp = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"publication failed rc={cp.returncode}: {cp.stderr.strip() or cp.stdout.strip()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ib-dir", required=True)
    ap.add_argument("--ic-dir", required=True)
    ap.add_argument("--id-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--deploy", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    ib = Path(args.ib_dir)
    icdir = Path(args.ic_dir)
    iddir = Path(args.id_dir)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    deploy = Path(args.deploy)
    hb = Path(args.progress_file) if args.progress_file else None
    publisher = Path(args.publisher) if args.publisher else None
    policy_path = Path(args.policy)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))

    if policy.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-E policy does not explicitly seal 2026")
    if policy.get("eligible_outcomes") != ["mean_fwd_ret_atr"]:
        raise RuntimeError("Phase I-E eligible outcome family is not the preregistered directional family")

    ib_integrity = json.loads((ib / "phase_ib_integrity.json").read_text(encoding="utf-8"))
    ib_summary = json.loads((ib / "phase_ib_summary.json").read_text(encoding="utf-8"))
    ic_summary = json.loads((icdir / "phase_ic_summary.json").read_text(encoding="utf-8"))
    id_summary = json.loads((iddir / "phase_id_summary.json").read_text(encoding="utf-8"))
    candidates_path = iddir / "phase_id_robust_survivors.csv"
    cuts_path = icdir / "phase_ic_frozen_2024_cutpoints.json"
    data_path = ib / "xauusd_m5_2024_2025_news_clean.csv"
    ic_engine = deploy / "research" / "autonomous" / "phase_ic_xau_phenomenon_atlas_v1_00.py"

    for p in (candidates_path, cuts_path, data_path, ic_engine):
        if not p.exists():
            raise RuntimeError(f"missing required artifact: {p}")
    if ib_integrity.get("status") != "PASS" or ib_integrity.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-B integrity/provenance is not PASS with 2026 sealed")
    if ib_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-B summary does not seal 2026")
    if ic_summary.get("technical_status") != "PASS" or ic_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-C provenance is not a sealed technical PASS")
    if id_summary.get("technical_status") != "PASS" or id_summary.get("scientific_status") != "ROBUST_SURVIVORS_FOUND":
        raise RuntimeError("Phase I-D terminal robust-survivor result is required")
    if id_summary.get("protected_2026_untouched") is not True:
        raise RuntimeError("Phase I-D provenance does not seal 2026")

    heartbeat(hb, 0, 100, "load_frozen_candidates")
    all_id = pd.read_csv(candidates_path)
    if len(all_id) != int(id_summary.get("robust_survivor_count", -1)):
        raise RuntimeError(f"Phase I-D robust survivor count mismatch csv={len(all_id)} summary={id_summary.get('robust_survivor_count')}")
    eligible = all_id[all_id["outcome"].astype(str).isin(policy["eligible_outcomes"])].copy().reset_index(drop=True)
    expected_n = int(id_summary.get("robust_survivors_by_outcome", {}).get("mean_fwd_ret_atr", -1))
    if len(eligible) != expected_n:
        raise RuntimeError(f"directional family count mismatch csv={len(eligible)} summary={expected_n}")
    if len(eligible) == 0:
        raise RuntimeError("Phase I-E was queued without any frozen directional Phase I-D candidate")

    cuts = json.loads(cuts_path.read_text(encoding="utf-8"))
    df = pd.read_csv(data_path)
    if not df["server_time"].astype(str).str.startswith(("2024.", "2025.")).all():
        raise RuntimeError("protected/out-of-window row present in Phase I-B dataset")
    df = df.sort_values("server_epoch").reset_index(drop=True)
    df["year"] = df.server_time.str[:4].astype(int)
    dt = pd.to_datetime(df.server_time, format="%Y.%m.%d %H:%M:%S")
    df["quarter"] = dt.dt.quarter.astype(int)

    ic = load_module(ic_engine)
    heartbeat(hb, 10, 100, "features")
    df = ic.build_features(df)
    horizons = sorted({int(v) for v in eligible["horizon_bars"].tolist()})
    heartbeat(hb, 20, 100, "labels")
    df = ic.add_labels(df, horizons)
    d25 = df[df.year == int(policy["confirmation_year"])].copy().reset_index(drop=True)

    for feature in sorted(set(eligible["feature"].astype(str))):
        if feature not in cuts:
            raise RuntimeError(f"frozen cutpoints absent for directional feature {feature}")
        d25[feature + "__q"] = ic.assign_q(d25[feature], cuts[feature])

    family_n = len(eligible)
    rows: list[dict] = []
    masks: list[np.ndarray] = []
    raw_ps: list[float] = []
    total = max(1, family_n)

    for i, (_, c) in enumerate(eligible.iterrows(), start=1):
        feature = str(c["feature"])
        q = int(c["quintile"]) - 1
        h = int(c["horizon_bars"])
        state = str(c["state"])
        mask = d25[feature + "__q"].to_numpy() == q
        hour_block = c.get("hour_block")
        if pd.notna(hour_block):
            mask &= d25.hour_block.to_numpy() == int(float(hour_block))
        values = d25[f"fwd_ret_atr_h{h}"].to_numpy(float)
        full = ic.continuous_test(values, mask)
        if full is None:
            raise RuntimeError(f"full-2025 continuous test unavailable for {state} h={h}")
        expected_sign = sign_of(float(c["confirmation_effect"]))
        if expected_sign == 0:
            raise RuntimeError(f"zero frozen confirmation sign for {state} h={h}")

        quarter_details: dict[str, dict] = {}
        same_sign_quarters = 0
        quarter_gate = True
        for quarter in (1, 2, 3, 4):
            period = d25.quarter.to_numpy() == quarter
            qr = ic.continuous_test(values[period], mask[period])
            if qr is None:
                quarter_details[str(quarter)] = {"sufficient": False}
                quarter_gate = False
                continue
            qeff = float(qr["effect"])
            sufficient = int(qr["n_state"]) >= int(policy["minimum_quarter_state_n"])
            same = sign_of(qeff) == expected_sign
            magnitude = abs(qeff) >= float(policy["minimum_quarter_effect_atr"])
            same_sign_quarters += int(same and sufficient and magnitude)
            quarter_gate &= sufficient and same and magnitude
            quarter_details[str(quarter)] = {
                "sufficient": bool(sufficient),
                "n_state": int(qr["n_state"]),
                "effect": qeff,
                "same_sign": bool(same),
                "minimum_effect_pass": bool(magnitude),
            }

        key = f"{state}|{h}|{feature}|{q}|{hour_block}"
        digest = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big")
        seed = int(policy["bootstrap_seed"]) ^ digest
        lo, hi, valid_reps = block_bootstrap_ci(
            values,
            mask,
            int(policy["block_length_bars"]),
            int(policy["block_bootstrap_replicates"]),
            float(policy["familywise_alpha"]),
            family_n,
            seed,
        )
        bootstrap_direction_pass = (lo > 0.0) if expected_sign > 0 else (hi < 0.0)

        row = {k: (None if pd.isna(v) else v) for k, v in c.to_dict().items()}
        row.update({
            "phase_ie_full_n_state": int(full["n_state"]),
            "phase_ie_full_n_comp": int(full["n_comp"]),
            "phase_ie_full_effect": float(full["effect"]),
            "phase_ie_raw_p": float(full["p"]),
            "phase_ie_expected_sign": expected_sign,
            "phase_ie_full_sign_pass": sign_of(float(full["effect"])) == expected_sign,
            "phase_ie_full_effect_pass": abs(float(full["effect"])) >= float(policy["minimum_full_effect_atr"]),
            "phase_ie_same_sign_effect_quarters": int(same_sign_quarters),
            "phase_ie_quarter_gate_pass": bool(quarter_gate and same_sign_quarters >= int(policy["required_quarters_same_sign"])),
            "phase_ie_quarter_details": json.dumps(quarter_details, sort_keys=True),
            "phase_ie_bootstrap_ci_low": lo,
            "phase_ie_bootstrap_ci_high": hi,
            "phase_ie_bootstrap_valid_reps": valid_reps,
            "phase_ie_bootstrap_direction_pass": bool(bootstrap_direction_pass),
        })
        rows.append(row)
        masks.append(mask.copy())
        raw_ps.append(float(full["p"]))
        heartbeat(hb, 20 + int(65 * i / total), 100, "directional_confirmation")

    adjusted = holm_adjust(raw_ps)
    for row, p_adj in zip(rows, adjusted):
        row["phase_ie_holm_p"] = float(p_adj)
        row["phase_ie_holm_pass"] = bool(p_adj <= float(policy["familywise_alpha"]))
        row["phase_ie_pass"] = bool(
            row["phase_ie_full_sign_pass"]
            and row["phase_ie_full_effect_pass"]
            and row["phase_ie_quarter_gate_pass"]
            and row["phase_ie_holm_pass"]
            and row["phase_ie_bootstrap_direction_pass"]
        )

    heartbeat(hb, 88, 100, "redundancy_clustering")
    passed_idx = [i for i, r in enumerate(rows) if r["phase_ie_pass"]]
    parent = {i: i for i in passed_idx}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    threshold = float(policy["redundancy_jaccard_threshold"])
    overlap_rows: list[dict] = []
    for pos, a in enumerate(passed_idx):
        for b in passed_idx[pos + 1:]:
            if int(rows[a]["phase_ie_expected_sign"]) != int(rows[b]["phase_ie_expected_sign"]):
                continue
            inter = int(np.sum(masks[a] & masks[b]))
            union_n = int(np.sum(masks[a] | masks[b]))
            j = float(inter / union_n) if union_n else 0.0
            overlap_rows.append({"candidate_a": a, "candidate_b": b, "jaccard": j})
            if j >= threshold:
                union(a, b)

    clusters: dict[int, list[int]] = {}
    for i in passed_idx:
        clusters.setdefault(find(i), []).append(i)
    canonical_indices: list[int] = []
    cluster_records: list[dict] = []
    for cluster_num, members in enumerate(sorted(clusters.values(), key=lambda xs: min(xs)), start=1):
        canonical = min(members, key=lambda i: (str(rows[i].get("state")), int(rows[i].get("horizon_bars")), str(rows[i].get("feature")), str(rows[i].get("hour_block"))))
        canonical_indices.append(canonical)
        for i in members:
            rows[i]["phase_ie_redundancy_cluster"] = cluster_num
            rows[i]["phase_ie_canonical_representative"] = (i == canonical)
        cluster_records.append({
            "cluster": cluster_num,
            "member_count": len(members),
            "canonical_state": rows[canonical].get("state"),
            "canonical_horizon_bars": int(rows[canonical].get("horizon_bars")),
            "canonical_feature": rows[canonical].get("feature"),
            "canonical_hour_block": rows[canonical].get("hour_block"),
        })
    for i, row in enumerate(rows):
        row.setdefault("phase_ie_redundancy_cluster", None)
        row.setdefault("phase_ie_canonical_representative", False)

    result = pd.DataFrame(rows)
    all_path = out / "phase_ie_all_directional_candidates.csv"
    survivors_path = out / "phase_ie_directional_survivors.csv"
    canonical_path = out / "phase_ie_independent_candidates.csv"
    overlap_path = out / "phase_ie_redundancy_pairs.csv"
    result.to_csv(all_path, index=False)
    survivors = result[result.phase_ie_pass == True].copy() if len(result) else result.copy()
    survivors.to_csv(survivors_path, index=False)
    canonical = result[result.phase_ie_canonical_representative == True].copy() if len(result) else result.copy()
    canonical.to_csv(canonical_path, index=False)
    pd.DataFrame(overlap_rows, columns=["candidate_a", "candidate_b", "jaccard"]).to_csv(overlap_path, index=False)

    scientific = "DIRECTIONAL_CANDIDATES_CONFIRMED" if len(canonical_indices) else "NO_DIRECTIONAL_CANDIDATE_SURVIVES"
    summary = {
        "schema": 1,
        "phase": "I-E",
        "technical_status": "PASS",
        "scientific_status": scientific,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_phase_id_robust_survivors": int(len(all_id)),
        "source_phase_id_directional_survivors": int(len(eligible)),
        "source_phase_id_non_directional_move_survivors_classified_non_alpha": int(len(all_id) - len(eligible)),
        "directional_candidates_tested": int(len(result)),
        "phase_ie_candidate_pass_count": int(len(survivors)),
        "independent_directional_cluster_count": int(len(canonical_indices)),
        "redundancy_clusters": cluster_records,
        "policy": policy,
        "protected_2026_untouched": True,
        "propfirm_tradability_authorized": False,
        "next_rule": (
            "At least one independent directional phenomenon survived the frozen Phase I-E gate. Commit the exact protected-2026 final-OOS preregistration without reading 2026, then obtain explicit owner approval before opening 2026."
            if canonical_indices else
            "No frozen XAU directional candidate survived the stricter Phase I-E gate. Close the XAU directional family; do not rescue it with sizing, PnL optimization, or Challenge Lab. The supervisor may preregister a genuinely independent phenomenon family next."
        ),
    }
    summary_path = out / "phase_ie_summary.json"
    atomic_json(summary_path, summary)
    heartbeat(hb, 100, 100, "complete")

    publish(
        publisher,
        "PASS",
        f"Phase I-E technical PASS; scientific={scientific}; directional_tested={len(result)}; raw_passes={len(survivors)}; independent_clusters={len(canonical_indices)}; 2026 untouched.",
        [summary_path, all_path, survivors_path, canonical_path, overlap_path, policy_path],
        deploy,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
