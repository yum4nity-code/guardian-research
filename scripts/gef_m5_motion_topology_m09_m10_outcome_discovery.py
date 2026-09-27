from pathlib import Path
import argparse, hashlib, json, math, time
import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ENGINE_VERSION = "M5-MOTION-TOPOLOGY-M09-M10-OUTCOME-DISCOVERY-1.1"
DISCOVERY_START = pd.Timestamp("2012-01-01")
FORBIDDEN_DATE = pd.Timestamp("2015-01-01")
EXPECTED_CENSUS_RUN = "GEFM5MC-20260927-100900"
EXPECTED_CACHE_RUN = "GEFM5T-20260923-050308"
EXPECTED_M09_ROWS = 6393
EXPECTED_M10_ROWS = 14662
EXPECTED_M09_SHA = "f4b16ed02534ada03aee9acbbcfb42c9450524c54cd17065a281aacb5b3d0e80"
EXPECTED_M10_SHA = "5df682a7a81d02ca9e72439e8e86434ccdf6579c0f16958316853c38729e1893"

SCALES = [15, 30, 60]
MIN_PRIOR = 250
COOLDOWN_MIN = 30
MIN_EPISODES = 200
MIN_DAYS = 120
BH_Q = 0.05

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

def make_object(ids, seq_len):
    if seq_len == 1:
        return ids.copy()
    parts = [ids.shift(k) for k in range(seq_len - 1, -1, -1)]
    valid = pd.Series(True, index=ids.index)
    for p in parts:
        valid &= p.notna()
    obj = parts[0].astype("string")
    for p in parts[1:]:
        obj = obj + ">" + p.astype("string")
    return obj.where(valid)

def cooldown_indices(times, minutes=COOLDOWN_MIN):
    t = pd.DatetimeIndex(times)
    if len(t) == 0:
        return np.empty(0, dtype=np.int64)

    # IMPORTANT: never assume DatetimeIndex.view("i8") is nanoseconds.
    # Parquet/pandas can preserve microsecond resolution, while Timedelta.value
    # is nanoseconds. That mismatch inflated a 30-minute cooldown to ~20.8 days
    # and collapsed high-support motifs to ~53 episodes over 2012-2014.
    ns = t.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    gap = int(pd.Timedelta(minutes=minutes).to_timedelta64().astype("timedelta64[ns]").astype(np.int64))

    keep = []
    last = None
    for i, v in enumerate(ns):
        if last is None or v - last >= gap:
            keep.append(i)
            last = v
    return np.asarray(keep, dtype=np.int64)

def cluster_intercept_test(y, times):
    y = np.asarray(y, dtype=float)
    times = pd.DatetimeIndex(times)
    good = np.isfinite(y)
    y = y[good]
    times = times[good]
    n = len(y)
    if n < 2:
        return {"n": n, "days": 0, "mean": np.nan, "se": np.nan, "t": np.nan,
                "p_one": np.nan, "median": np.nan, "positive_frac": np.nan}

    clusters = times.normalize().to_numpy()
    codes, _ = pd.factorize(clusters, sort=False)
    uniq = np.unique(codes)
    g = len(uniq)
    mean = float(np.mean(y))
    median = float(np.median(y))
    positive_frac = float(np.mean(y > 0))

    if g < 2:
        return {"n": n, "days": g, "mean": mean, "se": np.nan, "t": np.nan,
                "p_one": np.nan, "median": median, "positive_frac": positive_frac}

    resid = y - mean
    meat = 0.0
    for c in uniq:
        meat += float(np.sum(resid[codes == c])) ** 2
    vcov = (g / (g - 1.0)) * meat / (n * n)
    se = math.sqrt(vcov) if np.isfinite(vcov) and vcov > 0 else np.nan
    tv = mean / se if np.isfinite(se) and se > 0 else np.nan
    p_one = float(student_t.sf(tv, df=max(g - 1, 1))) if np.isfinite(tv) and mean > 0 else 1.0 if np.isfinite(mean) else np.nan
    return {"n": n, "days": g, "mean": mean, "se": se,
            "t": float(tv) if np.isfinite(tv) else np.nan, "p_one": p_one,
            "median": median, "positive_frac": positive_frac}

def trim_best_mean(y, pct):
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    if len(y) == 0:
        return np.nan
    k = int(math.ceil(len(y) * pct))
    if k <= 0:
        return float(np.mean(y))
    if k >= len(y):
        return np.nan
    return float(np.mean(np.sort(y)[:-k]))

def score_group(g):
    g = g.sort_values("time", kind="mergesort")
    keep = cooldown_indices(g["time"])
    if len(keep) == 0:
        return {"episodes": 0, "days": 0, "mean_endpoint": np.nan, "median_endpoint": np.nan,
                "positive_frac": np.nan, "se": np.nan, "t": np.nan, "p_one": np.nan,
                "trim_best_1pct_mean": np.nan, "trim_best_2pct_mean": np.nan,
                "mean_2012": np.nan, "mean_2013": np.nan, "mean_2014": np.nan}
    gg = g.iloc[keep]
    y = gg["y"].to_numpy(dtype=float)
    tt = pd.DatetimeIndex(gg["time"])
    fit = cluster_intercept_test(y, tt)
    years = tt.year
    out = {
        "episodes": fit["n"],
        "days": fit["days"],
        "mean_endpoint": fit["mean"],
        "median_endpoint": fit["median"],
        "positive_frac": fit["positive_frac"],
        "se": fit["se"],
        "t": fit["t"],
        "p_one": fit["p_one"],
        "trim_best_1pct_mean": trim_best_mean(y, 0.01),
        "trim_best_2pct_mean": trim_best_mean(y, 0.02),
    }
    for yr in [2012, 2013, 2014]:
        yy = y[years == yr]
        out[f"mean_{yr}"] = float(np.mean(yy)) if len(yy) else np.nan
    return out

def bh_qvalues(p):
    p = np.asarray(p, dtype=float)
    q = np.full(len(p), np.nan)
    ok = np.flatnonzero(np.isfinite(p))
    if not len(ok):
        return q
    order = ok[np.argsort(p[ok], kind="mergesort")]
    m = len(order)
    running = 1.0
    for rev, idx in enumerate(order[::-1], 1):
        rank = m - rev + 1
        val = min(1.0, p[idx] * m / rank)
        running = min(running, val)
        q[idx] = running
    return q

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args = ap.parse_args()
    root = Path(args.root)
    repo = root / "guardian-research"

    specp = repo / "research" / "campaigns" / "GUARDIAN_M5_M09_M10_OUTCOME_DISCOVERY_SPEC_2026_09_27.json"
    if not specp.exists():
        raise RuntimeError("Missing frozen M09-M10 outcome discovery spec")
    spec = json.loads(specp.read_text(encoding="utf-8"))
    if spec.get("status") != "FROZEN_BEFORE_OUTCOME_ASSOCIATION":
        raise RuntimeError("Outcome discovery spec is not frozen")

    census = root / "Research" / "Autonomous" / "guardian_m5_motion_topology_m09_m10" / EXPECTED_CENSUS_RUN
    if not census.exists():
        raise RuntimeError(f"Missing exact frozen census run: {census}")
    for req in ["RUN_RECEIPT.json", "MOTIF_DICTIONARY_FREEZE.json", "FROZEN_M09_DICTIONARY.csv", "FROZEN_M10_DICTIONARY.csv"]:
        if not (census / req).exists():
            raise RuntimeError(f"Missing census artifact {req}")

    census_receipt = json.loads((census / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
    freeze = json.loads((census / "MOTIF_DICTIONARY_FREEZE.json").read_text(encoding="utf-8"))
    if census_receipt.get("outcome_files_accessed") is not False:
        raise RuntimeError("Parent census was not predictor-only")
    if census_receipt.get("2015_plus_state_accessed") or census_receipt.get("2015_plus_outcomes_accessed"):
        raise RuntimeError("Parent census crossed temporal firewall")
    if freeze.get("cache_run") != EXPECTED_CACHE_RUN:
        raise RuntimeError(f"Unexpected cache run {freeze.get('cache_run')}")
    if sha256(census / "FROZEN_M09_DICTIONARY.csv") != EXPECTED_M09_SHA:
        raise RuntimeError("M09 frozen dictionary hash mismatch")
    if sha256(census / "FROZEN_M10_DICTIONARY.csv") != EXPECTED_M10_SHA:
        raise RuntimeError("M10 frozen dictionary hash mismatch")

    D09 = pd.read_csv(census / "FROZEN_M09_DICTIONARY.csv")
    D10 = pd.read_csv(census / "FROZEN_M10_DICTIONARY.csv")
    if len(D09) != EXPECTED_M09_ROWS or len(D10) != EXPECTED_M10_ROWS:
        raise RuntimeError(f"Dictionary row-count mismatch M09={len(D09)} M10={len(D10)}")

    cache = root / "Research" / "Autonomous" / "guardian_m5_motion_topology_v1_1" / EXPECTED_CACHE_RUN
    if not cache.exists():
        raise RuntimeError(f"Missing exact frozen cache {cache}")
    manifest = json.loads((cache / "CACHE_MANIFEST.json").read_text(encoding="utf-8"))

    outbase = root / "Research" / "Autonomous" / "guardian_m5_motion_topology_m09_m10_discovery"
    outbase.mkdir(parents=True, exist_ok=True)
    rid = "GEFM5MD-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out = outbase / rid
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def status(step, total, msg, **extra):
        p = {"run_id": rid, "engine_version": ENGINE_VERSION, "step": step, "steps": total,
             "elapsed_s": round(time.time() - t0, 1), "message": msg, **extra}
        write_json(out / "LIVE_STATUS.json", p)
        tail = " | ".join(f"{k}={v}" for k, v in extra.items())
        print(f"[M09-M10-DISCOVERY] {step}/{total} | {msg}" + (f" | {tail}" if tail else ""), flush=True)

    status(1, 9, "frozen census verified before outcomes", m09=len(D09), m10=len(D10))

    states = {}
    for s in MARKETS:
        p = Path(manifest["market_files"][s]["state"])
        d = pd.read_parquet(p)
        d.index = pd.to_datetime(d.index)
        if len(d.index[d.index >= FORBIDDEN_DATE]):
            raise RuntimeError(f"2015+ state rows in cache for {s}")
        states[s] = d

    cross = pd.read_parquet(Path(manifest["cross_state_path"]))
    cross.index = pd.to_datetime(cross.index)
    if len(cross.index[cross.index >= FORBIDDEN_DATE]):
        raise RuntimeError("2015+ cross-state rows reached discovery")
    idx = states[MARKETS[0]].index
    for s in MARKETS[1:]:
        if not idx.equals(states[s].index):
            raise RuntimeError("State indexes differ")
    cross = cross.reindex(idx)
    disc = (idx >= DISCOVERY_START) & (idx < FORBIDDEN_DATE)
    status(2, 9, "2011-2014 predictor state loaded; 2015+ forbidden", discovery_rows=int(np.sum(disc)))

    targets = {}
    for s in MARKETS:
        p = Path(manifest["target_files"][s])
        t = pd.read_parquet(p)
        t.index = pd.to_datetime(t.index)
        if len(t.index) and (t.index.max() >= FORBIDDEN_DATE or t.index.min() < DISCOVERY_START):
            raise RuntimeError(f"Target file escaped 2012-2014 firewall for {s}")
        targets[s] = t
    status(3, 9, "2012-2014 endpoint outcomes opened for frozen dictionaries only")

    all_rows = []
    jobs = []
    for target in MARKETS:
        for L in SCALES:
            jobs.append((target, L, 1, "M09"))
            jobs.append((target, L, 2, "M10"))
            jobs.append((target, L, 3, "M10"))

    done = 0
    for target, L, seq_len, family in jobs:
        done += 1
        dictionary = D09 if family == "M09" else D10
        sub = dictionary[
            (dictionary["target"] == target)
            & (dictionary["lookback_min"].astype(int) == L)
            & (dictionary["sequence_len"].astype(int) == seq_len)
        ].copy()
        if sub.empty:
            print(f"[M09-M10-DISCOVERY] object {done}/{len(jobs)} {family} {target} L{L} seq{seq_len} dictionary=0", flush=True)
            continue

        ids = encode_state(states, cross, target, L).loc[disc]
        obj = make_object(ids, seq_len)
        ycol = f"endpoint_score_{L}m_{L}m"
        y = pd.to_numeric(targets[target][ycol], errors="coerce").reindex(obj.index)

        motifs = set(sub["motif"].astype(str).tolist())
        use = obj.notna() & y.notna() & obj.astype(str).isin(motifs)
        work = pd.DataFrame({
            "time": obj.index[use],
            "motif": obj.loc[use].astype(str).to_numpy(),
            "y": y.loc[use].to_numpy(dtype=float),
        })

        scored = {}
        if len(work):
            for motif, g in work.groupby("motif", sort=False):
                scored[str(motif)] = score_group(g)

        for r in sub.itertuples(index=False):
            motif = str(r.motif)
            sc = scored.get(motif, {
                "episodes": 0, "days": 0, "mean_endpoint": np.nan, "median_endpoint": np.nan,
                "positive_frac": np.nan, "se": np.nan, "t": np.nan, "p_one": np.nan,
                "trim_best_1pct_mean": np.nan, "trim_best_2pct_mean": np.nan,
                "mean_2012": np.nan, "mean_2013": np.nan, "mean_2014": np.nan
            })
            valid = bool(
                sc["episodes"] >= MIN_EPISODES
                and sc["days"] >= MIN_DAYS
                and np.isfinite(sc["p_one"])
            )
            all_rows.append({
                "family": family,
                "target": target,
                "lookback_min": L,
                "horizon_min": L,
                "sequence_len": seq_len,
                "motif": motif,
                "census_raw_rows": int(r.raw_rows),
                "census_episodes_30m": int(r.episodes_30m),
                "census_utc_days": int(r.utc_days),
                **sc,
                "valid": valid,
            })

        print(
            f"[M09-M10-DISCOVERY] object {done}/{len(jobs)} {family} {target} L{L} seq{seq_len} "
            f"dict={len(sub)} rows={len(work)}",
            flush=True,
        )

    status(4, 9, "all frozen objects scored", tests=len(all_rows))
    D = pd.DataFrame(all_rows)
    expected_total = EXPECTED_M09_ROWS + EXPECTED_M10_ROWS
    if len(D) != expected_total:
        raise RuntimeError(f"Scored {len(D)} tests != frozen total {expected_total}")

    D["bh_q"] = np.nan
    D["bh_pass"] = False
    for family in ["M09", "M10"]:
        ix = D.index[D["family"] == family].to_numpy()
        p = np.where(D.loc[ix, "valid"].to_numpy(bool), D.loc[ix, "p_one"].to_numpy(float), np.nan)
        q = bh_qvalues(p)
        D.loc[ix, "bh_q"] = q
        D.loc[ix, "bh_pass"] = (
            D.loc[ix, "valid"].to_numpy(bool)
            & (D.loc[ix, "mean_endpoint"].to_numpy(float) > 0)
            & (q <= BH_Q)
        )

    D.to_csv(out / "DISCOVERY_ALL.csv", index=False)
    survivors = D[D["bh_pass"]].copy().sort_values(
        ["family", "bh_q", "p_one", "target", "lookback_min", "sequence_len", "motif"],
        kind="mergesort",
    )
    survivors.to_csv(out / "FROZEN_DISCOVERY_SURVIVORS.csv", index=False)
    status(5, 9, "BH-FDR applied separately within M09/M10", survivors=len(survivors))

    summary = []
    for family in ["M09", "M10"]:
        g = D[D["family"] == family]
        summary.append({
            "family": family,
            "frozen_tests": int(len(g)),
            "valid_tests": int(g["valid"].sum()),
            "bh_discoveries": int(g["bh_pass"].sum()),
            "minimum_required_episodes": MIN_EPISODES,
            "minimum_required_days": MIN_DAYS,
            "bh_q_max": BH_Q,
        })
    S = pd.DataFrame(summary)
    S.to_csv(out / "FAMILY_SUMMARY.csv", index=False)
    status(6, 9, "family summary written")

    surv_sha = sha256(out / "FROZEN_DISCOVERY_SURVIVORS.csv")
    freeze_receipt = {
        "run_id": rid,
        "status": "M09_M10_DISCOVERY_FROZEN_BEFORE_2015",
        "engine_version": ENGINE_VERSION,
        "parent_census_run": EXPECTED_CENSUS_RUN,
        "m09_dictionary_sha256": EXPECTED_M09_SHA,
        "m10_dictionary_sha256": EXPECTED_M10_SHA,
        "survivors": int(len(survivors)),
        "survivor_sha256": surv_sha,
        "discovery_outcomes_accessed": "2012-2014_only",
        "2015_plus_state_accessed": False,
        "2015_plus_outcomes_accessed": False,
        "2018_plus_accessed": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
    }
    write_json(out / "DISCOVERY_FREEZE_RECEIPT.json", freeze_receipt)

    provenance = {
        "run_id": rid,
        "engine_version": ENGINE_VERSION,
        "spec_sha256": sha256(specp),
        "parent_census_run": EXPECTED_CENSUS_RUN,
        "parent_cache_run": EXPECTED_CACHE_RUN,
        "m09_dictionary_sha256": EXPECTED_M09_SHA,
        "m10_dictionary_sha256": EXPECTED_M10_SHA,
        "target": "matched endpoint_score_Lm_Lm",
        "cooldown_min": COOLDOWN_MIN,
        "minimum_independent_episodes": MIN_EPISODES,
        "minimum_utc_days": MIN_DAYS,
        "bh_q": BH_Q,
        "2015_plus_accessed": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
    }
    write_json(out / "RUNTIME_PROVENANCE.json", provenance)

    receipt = {
        "run_id": rid,
        "status": "COMPLETE_M09_M10_OUTCOME_DISCOVERY",
        "engine_version": ENGINE_VERSION,
        "frozen_tests": int(len(D)),
        "valid_tests": int(D["valid"].sum()),
        "bh_discoveries": int(D["bh_pass"].sum()),
        "discoveries_by_family": {
            "M09": int(((D["family"] == "M09") & D["bh_pass"]).sum()),
            "M10": int(((D["family"] == "M10") & D["bh_pass"]).sum()),
        },
        "survivor_sha256": surv_sha,
        "2015_plus_state_accessed": False,
        "2015_plus_outcomes_accessed": False,
        "2018_plus_accessed": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
        "next": "IF SURVIVORS: FREEZE EXACT OBJECTS AND BUILD 2015-2017 REPLICATION; IF NONE: CLOSE M09-M10 DISCOVERY"
    }
    write_json(out / "RUN_RECEIPT.json", receipt)
    status(7, 9, "immutable discovery freeze written; 2015+ still unopened")
    status(8, 9, "receipt written")
    status(9, 9, "DONE")

    print("\n=== M09-M10 OUTCOME DISCOVERY RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    print("\n=== FAMILY SUMMARY ===")
    print(S.to_string(index=False))
    print("\n=== TOP FROZEN SURVIVORS ===")
    if len(survivors):
        cols = [
            "family", "target", "lookback_min", "sequence_len", "episodes", "days",
            "mean_endpoint", "median_endpoint", "p_one", "bh_q",
            "trim_best_1pct_mean", "trim_best_2pct_mean", "motif"
        ]
        print(survivors[cols].head(30).to_string(index=False))
    else:
        print("NONE")
    print("\nRUN:", out)

if __name__ == "__main__":
    main()
