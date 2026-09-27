from pathlib import Path
import argparse, hashlib, json, time
import numpy as np
import pandas as pd

ENGINE_VERSION = "M5-MOTION-TOPOLOGY-M09-M10-CENSUS-1.0"
DISCOVERY_START = pd.Timestamp("2012-01-01")
FORBIDDEN_DATE = pd.Timestamp("2015-01-01")
SCALES = [15, 30, 60]
MIN_PRIOR = 250
COOLDOWN_MIN = 30
MIN_RAW_FOR_COOLDOWN = 100
MIN_CENSUS_EPISODES = 100

MARKETS = [
    "XAUUSD", "XAGUSD", "UDXUSD", "EURUSD", "GBPUSD", "USDJPY",
    "AUDUSD", "USDCHF", "USDCAD", "SPXUSD", "NSXUSD", "WTIUSD", "BCOUSD"
]
GRAPH = [
    ("XAUUSD", "XAGUSD"), ("XAUUSD", "UDXUSD"), ("XAGUSD", "UDXUSD"),
    ("USDCAD", "WTIUSD"), ("USDCAD", "BCOUSD"), ("WTIUSD", "BCOUSD"),
    ("NSXUSD", "SPXUSD"), ("UDXUSD", "EURUSD"), ("UDXUSD", "GBPUSD"),
    ("UDXUSD", "AUDUSD"), ("UDXUSD", "USDJPY"), ("UDXUSD", "USDCHF"),
    ("UDXUSD", "USDCAD"),
]

def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def causal_z(s, min_periods=MIN_PRIOR):
    s = pd.to_numeric(s, errors="coerce").astype(float)
    mu = s.expanding(min_periods=min_periods).mean().shift(1)
    sd = s.expanding(min_periods=min_periods).std().shift(1).replace(0, np.nan)
    return (s - mu) / sd

def latest_cache(root):
    base = root / "Research" / "Autonomous" / "guardian_m5_motion_topology_v1_1"
    runs = [p for p in sorted(base.glob("GEFM5T-*"))
            if (p / "RUN_RECEIPT.json").exists() and (p / "CACHE_MANIFEST.json").exists()]
    if not runs:
        raise RuntimeError("No completed M5 topology V1.1 cache")
    run = runs[-1]
    rc = json.loads((run / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
    if rc.get("alpha_tests") != 0 or rc.get("edge_trials") != 0:
        raise RuntimeError("Refuse cache with prior alpha/edge trials")
    if rc.get("2015_plus_outcomes_accessed"):
        raise RuntimeError("Refuse cache that opened 2015+")
    return run

def load_state_only(cache):
    manifest = json.loads((cache / "CACHE_MANIFEST.json").read_text(encoding="utf-8"))
    states = {}
    for s in MARKETS:
        d = pd.read_parquet(Path(manifest["market_files"][s]["state"]))
        d.index = pd.to_datetime(d.index)
        if len(d.index[d.index >= FORBIDDEN_DATE]):
            raise RuntimeError(f"2015+ state rows in cache for {s}")
        states[s] = d
    cross = pd.read_parquet(Path(manifest["cross_state_path"]))
    cross.index = pd.to_datetime(cross.index)
    if len(cross.index[cross.index >= FORBIDDEN_DATE]):
        raise RuntimeError("2015+ cross-state rows in cache")
    # Deliberately do NOT open target_files here.
    return manifest, states, cross

def common_index(states):
    idx = states[MARKETS[0]].index
    for s in MARKETS[1:]:
        if not idx.equals(states[s].index):
            raise RuntimeError("State indexes differ")
    return idx

def pair_prefix(a, b):
    if (a, b) in GRAPH:
        return f"{a}__{b}"
    if (b, a) in GRAPH:
        return f"{b}__{a}"
    raise RuntimeError(f"Pair not frozen in graph: {a},{b}")

def incident_peers(target):
    out = []
    for a, b in GRAPH:
        if a == target:
            out.append(b)
        elif b == target:
            out.append(a)
    return out

def bucket_strength(z):
    a = pd.to_numeric(z, errors="coerce").abs()
    out = pd.Series(np.nan, index=a.index, dtype=float)
    out.loc[a < 0.75] = 0
    out.loc[(a >= 0.75) & (a < 1.50)] = 1
    out.loc[a >= 1.50] = 2
    return out

def bucket_three(x, low, high):
    x = pd.to_numeric(x, errors="coerce")
    out = pd.Series(np.nan, index=x.index, dtype=float)
    out.loc[x < low] = -1
    out.loc[(x >= low) & (x <= high)] = 0
    out.loc[x > high] = 1
    return out

def encode_state(states, cross, target, L):
    st = states[target]
    retL = pd.to_numeric(st[f"ret_{L}m"], errors="coerce")
    move_z = causal_z(retL)
    move_dir = np.sign(retL).replace(0, np.nan)
    strength = bucket_strength(move_z)
    accel = pd.to_numeric(st["accel_5_vs_15"], errors="coerce")
    accel_rel = pd.Series(np.sign(move_dir * accel), index=st.index)
    shock = pd.to_numeric(st["shock_abs_ge_1p5"], errors="coerce")
    breadth = bucket_three(cross["breadth_positive_frac_5m"], 0.40, 0.60)
    dispersion = bucket_three(causal_z(cross["dispersion_ret5"]), -0.75, 0.75)

    resid_ext = pd.Series(False, index=st.index)
    corr_ext = pd.Series(False, index=st.index)
    for peer in incident_peers(target):
        pref = pair_prefix(target, peer)
        rz = pd.to_numeric(cross[f"{pref}__resid_z"], errors="coerce")
        cbz = causal_z(cross[f"{pref}__corr_break"])
        resid_ext |= rz.abs().ge(1.50)
        corr_ext |= cbz.abs().ge(1.50)

    valid = (
        st["tradable"].astype(bool)
        & move_dir.notna()
        & strength.notna()
        & accel_rel.notna()
        & shock.notna()
        & breadth.notna()
        & dispersion.notna()
    )

    df = pd.DataFrame({
        "move_dir": move_dir,
        "strength": strength,
        "accel_rel": accel_rel,
        "shock": shock,
        "breadth": breadth,
        "dispersion": dispersion,
        "resid_ext": resid_ext.astype(int),
        "corr_ext": corr_ext.astype(int),
        "valid": valid,
    }, index=st.index)

    def fmt(r):
        if not bool(r["valid"]):
            return None
        return (
            f"D{int(r['move_dir']):+d}|S{int(r['strength'])}|A{int(r['accel_rel']):+d}|"
            f"K{int(r['shock'])}|B{int(r['breadth']):+d}|P{int(r['dispersion']):+d}|"
            f"R{int(r['resid_ext'])}|C{int(r['corr_ext'])}"
        )

    ids = df.apply(fmt, axis=1)
    ids.name = "state_id"
    return ids

def episode_stats(times):
    times = pd.DatetimeIndex(times).sort_values()
    if len(times) == 0:
        return 0, 0
    keep = []
    last = None
    cd = pd.Timedelta(minutes=COOLDOWN_MIN)
    for t in times:
        if last is None or t - last >= cd:
            keep.append(t)
            last = t
    kept = pd.DatetimeIndex(keep)
    return len(kept), int(kept.normalize().nunique())

def census_series(ids, family, target, L, seq_len):
    if seq_len == 1:
        obj = ids.copy()
    else:
        parts = [ids.shift(k) for k in range(seq_len - 1, -1, -1)]
        valid = pd.Series(True, index=ids.index)
        for p in parts:
            valid &= p.notna()
        obj = parts[0].astype("string")
        for p in parts[1:]:
            obj = obj + ">" + p.astype("string")
        obj = obj.where(valid)

    rows = []
    for motif, raw_n in obj.value_counts(dropna=True).items():
        if int(raw_n) < MIN_RAW_FOR_COOLDOWN:
            continue
        times = obj.index[obj == motif]
        episodes, days = episode_stats(times)
        rows.append({
            "family": family,
            "target": target,
            "lookback_min": L,
            "sequence_len": seq_len,
            "motif": str(motif),
            "raw_rows": int(raw_n),
            "episodes_30m": int(episodes),
            "utc_days": int(days),
            "eligible_for_outcome_test": bool(episodes >= MIN_CENSUS_EPISODES),
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args = ap.parse_args()

    root = Path(args.root)
    repo = root / "guardian-research"
    specp = repo / "research" / "campaigns" / "GUARDIAN_M5_M09_M10_MOTIF_CENSUS_SPEC_2026_09_27.json"
    if not specp.exists():
        raise RuntimeError("Missing frozen M09-M10 census spec")
    spec = json.loads(specp.read_text(encoding="utf-8"))
    if spec.get("status") != "FROZEN_BEFORE_MOTIF_CENSUS":
        raise RuntimeError("M09-M10 census spec not frozen")

    cache = latest_cache(root)
    outbase = root / "Research" / "Autonomous" / "guardian_m5_motion_topology_m09_m10"
    outbase.mkdir(parents=True, exist_ok=True)
    rid = "GEFM5MC-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out = outbase / rid
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def status(step, total, msg, **extra):
        p = {"run_id": rid, "engine_version": ENGINE_VERSION, "step": step, "steps": total,
             "elapsed_s": round(time.time() - t0, 1), "message": msg, **extra}
        write_json(out / "LIVE_STATUS.json", p)
        tail = " | ".join(f"{k}={v}" for k, v in extra.items())
        print(f"[M09-M10-CENSUS] {step}/{total} | {msg}" + (f" | {tail}" if tail else ""), flush=True)

    status(1, 8, "load predictor-only V1.1 cache; target files stay unopened", cache=cache.name)
    manifest, states, cross = load_state_only(cache)
    idx = common_index(states)
    cross = cross.reindex(idx)
    if idx.max() >= FORBIDDEN_DATE:
        raise RuntimeError("2015+ state index reached census")

    disc = (idx >= DISCOVERY_START) & (idx < FORBIDDEN_DATE)
    if not np.any(disc):
        raise RuntimeError("No 2012-2014 discovery state rows")
    status(2, 8, "predictor cache loaded", rows=int(np.sum(disc)), cross_features=int(cross.shape[1]))

    m09_rows, m10_rows, support = [], [], []
    total_jobs = len(MARKETS) * len(SCALES)
    job = 0
    for target in MARKETS:
        for L in SCALES:
            job += 1
            ids = encode_state(states, cross, target, L).loc[disc]
            support.append({"target": target, "lookback_min": L,
                            "valid_state_rows": int(ids.notna().sum()),
                            "unique_states": int(ids.nunique(dropna=True))})
            m09_rows.extend(census_series(ids, "M09", target, L, 1))
            m10_rows.extend(census_series(ids, "M10", target, L, 2))
            m10_rows.extend(census_series(ids, "M10", target, L, 3))
            print(f"[M09-M10-CENSUS] state {job}/{total_jobs} {target} L{L}", flush=True)

    status(3, 8, "all compact state vectors encoded", market_scales=total_jobs)
    cols = ["family","target","lookback_min","sequence_len","motif","raw_rows",
            "episodes_30m","utc_days","eligible_for_outcome_test"]
    M09 = pd.DataFrame(m09_rows, columns=cols)
    M10 = pd.DataFrame(m10_rows, columns=cols)
    SUP = pd.DataFrame(support)
    M09.to_csv(out / "M09_MOTIF_CENSUS_ALL.csv", index=False)
    M10.to_csv(out / "M10_SEQUENCE_CENSUS_ALL.csv", index=False)
    SUP.to_csv(out / "STATE_SUPPORT.csv", index=False)
    status(4, 8, "census tables written", m09_rows=len(M09), m10_rows=len(M10))

    F09 = M09[M09["eligible_for_outcome_test"]].copy().sort_values(["target","lookback_min","motif"], kind="mergesort")
    F10 = M10[M10["eligible_for_outcome_test"]].copy().sort_values(["target","lookback_min","sequence_len","motif"], kind="mergesort")
    F09.to_csv(out / "FROZEN_M09_DICTIONARY.csv", index=False)
    F10.to_csv(out / "FROZEN_M10_DICTIONARY.csv", index=False)
    status(5, 8, "predictor-only dictionaries frozen", m09_frozen=len(F09), m10_frozen=len(F10))

    freeze = {
        "run_id": rid,
        "status": "M09_M10_DICTIONARY_FROZEN_BEFORE_OUTCOME_ASSOCIATION",
        "engine_version": ENGINE_VERSION,
        "cache_run": cache.name,
        "spec_sha256": sha256(specp),
        "m09_dictionary_sha256": sha256(out / "FROZEN_M09_DICTIONARY.csv"),
        "m10_dictionary_sha256": sha256(out / "FROZEN_M10_DICTIONARY.csv"),
        "m09_motifs": int(len(F09)),
        "m10_sequences": int(len(F10)),
        "minimum_census_episodes": MIN_CENSUS_EPISODES,
        "outcome_files_accessed": False,
        "2015_plus_state_accessed": False,
        "2015_plus_outcomes_accessed": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
    }
    write_json(out / "MOTIF_DICTIONARY_FREEZE.json", freeze)
    status(6, 8, "immutable dictionary freeze receipt written")

    receipt = {
        "run_id": rid,
        "status": "COMPLETE_M09_M10_PREDICTOR_ONLY_CENSUS",
        "engine_version": ENGINE_VERSION,
        "cache_run": cache.name,
        "market_scales": total_jobs,
        "m09_census_rows": int(len(M09)),
        "m10_census_rows": int(len(M10)),
        "m09_frozen_motifs": int(len(F09)),
        "m10_frozen_sequences": int(len(F10)),
        "outcome_files_accessed": False,
        "2015_plus_state_accessed": False,
        "2015_plus_outcomes_accessed": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
        "next": "REVIEW CENSUS SUPPORT THEN BUILD SEPARATE M09-M10 OUTCOME DISCOVERY AGAINST FROZEN DICTIONARY ONLY"
    }
    write_json(out / "RUN_RECEIPT.json", receipt)
    status(7, 8, "run receipt written; no outcome association performed")
    status(8, 8, "DONE")
    print("\n=== M09-M10 CENSUS RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    print("\n=== FROZEN DICTIONARY HASHES ===")
    print(json.dumps({"m09_sha": freeze["m09_dictionary_sha256"], "m10_sha": freeze["m10_dictionary_sha256"]}, indent=2))
    print("\nRUN:", out)

if __name__ == "__main__":
    main()
