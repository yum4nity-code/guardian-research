from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

ENGINE_VERSION = "V103.0"
EXPECTED_V102_RUN = "GEF102-20260922-143744"
EXPECTED_FINAL_SHA = "f6aa7d91488a5e52eeb1d5fa3c614dcff918ac3f1e4dd680ec3e3cac7060b865"
FORBIDDEN_YEAR = 2023
SLOW_MIN_PERIODS = 500
BOOTSTRAPS = 2000
BOOTSTRAP_SEED = 103


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def mean_bp(x):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    return float(x.mean() * 1e4) if len(x) else np.nan


def causal_states(series, min_periods, zcut=1.0):
    s = pd.to_numeric(series, errors="coerce")
    mu = s.expanding(min_periods=min_periods).mean().shift(1)
    sd = s.expanding(min_periods=min_periods).std().shift(1).replace(0, np.nan)
    z = ((s - mu) / sd).to_numpy(dtype=np.float32)
    finite = np.isfinite(z)
    return finite & (z <= -zcut), finite & (z >= zcut)


def target_parts(target):
    m = re.fullmatch(r"([A-Z]+)_fwd_(\d+)m", str(target))
    if not m:
        raise RuntimeError(f"Unsupported target {target}")
    return m.group(1), int(m.group(2))


def load_m1(root, sym, start_year, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError("V103 refuses 2023+")
    parts = []
    skipped = []
    for year in range(start_year, end_year + 1):
        p = root / "DataLake" / "raw" / "histdata" / sym / "M1" / f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year <= 2012:
                skipped.append(year)
                continue
            raise RuntimeError(f"Missing required <=2022 file {p}")
        d = pd.read_parquet(p)
        dc = next((c for c in d.columns if str(c).lower() in ["datetime","timestamp","time","date"]), None)
        pc = next((c for c in d.columns if str(c).lower() == "close"), None)
        if dc is None and isinstance(d.index, pd.DatetimeIndex):
            d = d.reset_index()
            dc = d.columns[0]
        if dc is None or pc is None:
            raise RuntimeError(f"Cannot identify datetime/close in {p}")
        utc = pd.to_datetime(d[dc], errors="coerce") + pd.Timedelta(hours=5)
        q = pd.DataFrame({"utc": utc, "px": pd.to_numeric(d[pc], errors="coerce")}).dropna()
        q = q[q["utc"].dt.year.between(start_year, end_year)]
        parts.append(q)
    if not parts:
        raise RuntimeError(f"No usable M1 files for {sym}")
    if skipped:
        print(f"[GEF103] {sym} skipped legacy warmup {skipped}", flush=True)
    q = pd.concat(parts, ignore_index=True).sort_values("utc").drop_duplicates("utc", keep="last")
    return q.set_index("utc")["px"]


def parse_treasury(root, folder, prefix, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError("V103 Treasury parser refuses 2023+")
    records = []
    for y in range(2009, end_year + 1):
        p = root / "DataLake" / "raw" / "treasury" / folder / f"{folder}_{y}.xml"
        if not p.exists():
            continue
        tree = ET.parse(p).getroot()
        for entry in tree.iter():
            vals = {}
            for x in entry.iter():
                tag = x.tag.split("}")[-1]
                txt = (x.text or "").strip()
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag=="NEW_DATE"):
                    vals[tag] = txt
            if vals:
                records.append(vals)
    if not records:
        return pd.DataFrame()
    d = pd.DataFrame(records).drop_duplicates()
    dc = next((c for c in d.columns if "DATE" in c), None)
    if dc is None:
        raise RuntimeError(f"No date field in Treasury {folder}")
    d["obs_date"] = pd.to_datetime(d[dc], errors="coerce").dt.normalize()
    d = d.dropna(subset=["obs_date"]).sort_values("obs_date").drop_duplicates("obs_date", keep="last")
    out = pd.DataFrame(index=d["obs_date"])
    for c in d.columns:
        if c in [dc, "obs_date"]:
            continue
        v = pd.to_numeric(d[c], errors="coerce")
        if v.notna().sum() >= 250:
            out[f"{prefix}_{c}"] = v.to_numpy()
    return out


def tenor_from_col(c):
    m = re.search(r"(?:BC_|TC_)(\d+)(MONTH|YEAR)", c)
    if not m:
        return None
    n = int(m.group(1))
    return n / 12 if m.group(2) == "MONTH" else float(n)


def build_rates_frame(root, end_year):
    nom = parse_treasury(root, "nominal_yield_curve", "NOM", end_year)
    real = parse_treasury(root, "real_yield_curve", "REAL", end_year)
    if nom.empty or real.empty:
        raise RuntimeError("Treasury reconstruction failed")
    rates = pd.concat([nom, real], axis=1).sort_index()
    nom_by = {tenor_from_col(c): c for c in nom.columns if tenor_from_col(c) is not None}
    real_by = {tenor_from_col(c): c for c in real.columns if tenor_from_col(c) is not None}
    for ten in sorted(set(nom_by).intersection(real_by)):
        label = f"{int(ten*12)}M" if ten < 1 else f"{int(ten)}Y"
        rates[f"BE_{label}"] = rates[nom_by[ten]] - rates[real_by[ten]]
    for a,b in [(2,10),(5,10),(10,30),(5,30)]:
        if a in nom_by and b in nom_by:
            rates[f"NOM_SLOPE_{b}Y_{a}Y"] = rates[nom_by[b]] - rates[nom_by[a]]
        if a in real_by and b in real_by:
            rates[f"REAL_SLOPE_{b}Y_{a}Y"] = rates[real_by[b]] - rates[real_by[a]]
    parts = []
    for c in rates.columns:
        s = pd.to_numeric(rates[c], errors="coerce")
        parts += [
            s.rename(f"rates_yields_{c}_level"),
            s.diff(1).rename(f"rates_yields_{c}_d1"),
            s.diff(5).rename(f"rates_yields_{c}_d5"),
        ]
        mu = s.rolling(252, min_periods=126).mean()
        sd = s.rolling(252, min_periods=126).std().replace(0, np.nan)
        parts.append(((s-mu)/sd).rename(f"rates_yields_{c}_z252"))
    rf = pd.concat(parts, axis=1)
    rf["AVAILABLE_AT"] = pd.DatetimeIndex(rf.index) + pd.Timedelta(days=1)
    return rf.reset_index(drop=True)


def asof_selected(grid, frame, features):
    base = pd.DataFrame({"decision_time_utc": grid})
    cols = {}
    for c in features:
        src = pd.DataFrame({
            "AVAILABLE_AT": frame["AVAILABLE_AT"],
            c: pd.to_numeric(frame[c], errors="coerce"),
        }).dropna().sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT", keep="last")
        if len(src) < 4:
            raise RuntimeError(f"Too few source observations for {c}")
        z = pd.merge_asof(base, src, left_on="decision_time_utc", right_on="AVAILABLE_AT", direction="backward")
        cols[c] = z[c].to_numpy()
    return pd.DataFrame(cols, index=grid)


def build_target(P, grid, target):
    sym, mins = target_parts(target)
    k = mins // 5
    raw = P[sym].shift(-k) / P[sym] - 1
    y = np.array(raw.reindex(grid), dtype=np.float64, copy=True)
    minute = (grid.view("int64") // 60_000_000_000).astype(np.int64)
    y[(minute % mins) != 0] = np.nan
    return y


def trimmed_best(x, pct):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan
    k = int(math.ceil(len(x) * pct))
    if k <= 0:
        return mean_bp(x)
    if k >= len(x):
        return np.nan
    return mean_bp(np.sort(x)[:-k])


def remove_best(x, k):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) <= k:
        return np.nan
    return mean_bp(np.sort(x)[:-k])


def subset_first_per_day(times, vals):
    d = pd.DataFrame({"t": pd.DatetimeIndex(times), "v": np.asarray(vals, dtype=float)})
    d = d[np.isfinite(d["v"])].copy()
    if d.empty:
        return np.asarray([]), pd.DatetimeIndex([])
    d["day"] = d["t"].dt.floor("D")
    z = d.sort_values("t").groupby("day", as_index=False).first()
    return z["v"].to_numpy(), pd.DatetimeIndex(z["t"])


def subset_first_per_episode(full_mask, grid, target_vals):
    # One observation per contiguous TRUE state episode, using the first
    # timestamp inside that episode where the frozen target is actually eligible.
    m = np.asarray(full_mask, dtype=bool)
    y = np.asarray(target_vals, dtype=float)
    starts = np.flatnonzero(m & ~np.r_[False, m[:-1]])
    ends = np.flatnonzero(m & ~np.r_[m[1:], False]) + 1
    vals = []
    times = []
    for start, end in zip(starts, ends):
        eligible = np.flatnonzero(np.isfinite(y[start:end]))
        if not len(eligible):
            continue
        i = start + int(eligible[0])
        vals.append(float(y[i]))
        times.append(grid[i])
    return np.asarray(vals, dtype=float), pd.DatetimeIndex(times)


def nonoverlap(times, vals, horizon_min):
    d = pd.DataFrame({"t": pd.DatetimeIndex(times), "v": np.asarray(vals, dtype=float)})
    d = d[np.isfinite(d["v"])].sort_values("t")
    keep = []
    next_allowed = None
    gap = pd.Timedelta(minutes=int(horizon_min))
    for row in d.itertuples(index=False):
        if next_allowed is None or row.t >= next_allowed:
            keep.append((row.t, row.v))
            next_allowed = row.t + gap
    if not keep:
        return np.asarray([]), pd.DatetimeIndex([])
    return np.asarray([x[1] for x in keep]), pd.DatetimeIndex([x[0] for x in keep])


def remove_best_month_mean(times, vals):
    d = pd.DataFrame({"t": pd.DatetimeIndex(times), "v": np.asarray(vals, dtype=float)})
    d = d[np.isfinite(d["v"])].copy()
    if d.empty:
        return np.nan, None
    d["month"] = d["t"].dt.to_period("M").astype(str)
    sums = d.groupby("month")["v"].sum()
    best = str(sums.idxmax())
    return mean_bp(d.loc[d["month"] != best, "v"].to_numpy()), best


def leave_one_year_out_min(times, vals):
    d = pd.DataFrame({"t": pd.DatetimeIndex(times), "v": np.asarray(vals, dtype=float)})
    d = d[np.isfinite(d["v"])].copy()
    if d.empty:
        return np.nan, {}
    d["year"] = d["t"].dt.year
    out = {}
    for y in sorted(d["year"].unique()):
        out[str(int(y))] = mean_bp(d.loc[d["year"] != y, "v"].to_numpy())
    return min(out.values()) if out else np.nan, out


def month_block_bootstrap(times, vals, draws=2000, seed=103):
    d = pd.DataFrame({"t": pd.DatetimeIndex(times), "v": np.asarray(vals, dtype=float)})
    d = d[np.isfinite(d["v"])].copy()
    d["month"] = d["t"].dt.to_period("M").astype(str)
    groups = [g["v"].to_numpy() for _, g in d.groupby("month") if len(g)]
    if len(groups) < 2:
        return (np.nan, np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=float)
    for i in range(draws):
        pick = rng.integers(0, len(groups), size=len(groups))
        sample = np.concatenate([groups[j] for j in pick])
        means[i] = mean_bp(sample)
    return tuple(float(x) for x in np.quantile(means, [0.025,0.5,0.975]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args = ap.parse_args()
    root = Path(args.root)

    v102 = root / "Research" / "Autonomous" / "guardian_edge_factory_v102_standalone_rates" / EXPECTED_V102_RUN
    receipt_path = v102 / "RUN_RECEIPT.json"
    final_path = v102 / "FINAL_SURVIVORS.csv"
    if not receipt_path.exists() or not final_path.exists():
        raise RuntimeError(f"Missing exact V102 source run {v102}")
    r102 = json.loads(receipt_path.read_text(encoding="utf-8"))
    if r102.get("status") != "COMPLETE_V102_STANDALONE_RATES":
        raise RuntimeError(f"Wrong V102 status: {r102.get('status')}")
    if sha256(final_path) != EXPECTED_FINAL_SHA:
        raise RuntimeError("V102 FINAL_SURVIVORS SHA mismatch")
    C = pd.read_csv(final_path)
    if len(C) != 5:
        raise RuntimeError(f"Expected exact 5 V102 survivors, got {len(C)}")

    base = root / "Research" / "Autonomous" / "guardian_edge_factory_v103_rates_preoos_forensic"
    base.mkdir(parents=True, exist_ok=True)
    rid = "GEF103-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out = base / rid
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def status(step,total,msg,**extra):
        p={"run_id":rid,"engine_version":ENGINE_VERSION,"step":step,"steps":total,
           "percent":round(100*step/total,1),"elapsed_s":round(time.time()-t0,1),
           "message":msg,**extra}
        write_json(out/"LIVE_STATUS.json",p)
        tail=" | ".join(f"{k}={v}" for k,v in extra.items())
        print(f"[GEF103] {step}/{total} {100*step/total:.0f}% | {msg}"+(f" | {tail}" if tail else ""),flush=True)

    status(1,10,"exact V102 final panel verified",source=EXPECTED_V102_RUN,sha=EXPECTED_FINAL_SHA[:16])

    # Resolve canonical V83B from V102 receipt.
    v83b = root / "Research" / "Autonomous" / "guardian_edge_factory_v83b" / str(r102["source_v83b"])
    manifest = json.loads((v83b/"REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))
    S = pd.read_parquet(manifest["slow_state_repaired_path"])
    S.index = pd.to_datetime(S.index)

    features = sorted(C["feature"].astype(str).unique())
    targets = sorted(C["target"].astype(str).unique())
    markets = sorted({target_parts(t)[0] for t in targets})

    grid = pd.date_range("2010-01-01 00:00","2022-12-31 23:55",freq="5min")
    P = pd.DataFrame(index=grid)
    for i,sym in enumerate(markets,1):
        raw=load_m1(root,sym,2009,2022)
        P[sym]=raw.resample("5min",label="right",closed="left").last().reindex(grid).astype("float64")
        print(f"[GEF103] target rebuild {i}/{len(markets)} {sym}",flush=True)
    T={t:build_target(P,grid,t) for t in targets}
    status(2,10,"target histories rebuilt through 2022 only",markets=len(markets))

    diffs=pd.Series(S.index).diff().dropna()
    slow_freq=diffs.mode().iloc[0]
    slow_grid=pd.date_range(S.index.min(),"2022-12-31 23:00",freq=slow_freq)
    RF=build_rates_frame(root,2022)
    Rj=asof_selected(slow_grid,RF,features)
    if not S.index.equals(slow_grid[:len(S.index)]):
        raise RuntimeError("V103 slow grid does not match V83B prefix")
    for f in features:
        if f not in S.columns:
            raise RuntimeError(f"Missing canonical V83B feature {f}")
        Rj.loc[S.index,f]=pd.to_numeric(S[f],errors="coerce").to_numpy()

    state_sets={}
    for f in features:
        for label,zcut,delay in [
            ("base",1.0,0),("z09",0.9,0),("z11",1.1,0),("lag1",1.0,24),("lag2",1.0,48)
        ]:
            series=Rj[f].shift(delay) if delay else Rj[f]
            lo,hi=causal_states(series,SLOW_MIN_PERIODS,zcut)
            state_sets[(f,label,"LO")]=lo
            state_sets[(f,label,"HI")]=hi

    slow_ns=slow_grid.view("int64")
    fast_ns=grid.view("int64")
    bridge=np.searchsorted(slow_ns,fast_ns,side="right")-1
    ok=bridge>=0

    def fastmask(feature,label,state):
        src=state_sets[(feature,label,state)]
        z=np.zeros(len(grid),dtype=bool)
        z[ok]=src[bridge[ok]]
        return z

    status(3,10,"rate states rebuilt with base/neighbors/lags")

    val_window=(grid>=pd.Timestamp("2018-01-01"))&(grid<pd.Timestamp("2023-01-01"))
    rows=[]
    series_by_candidate={}
    masks_by_candidate={}

    for idx,r in C.reset_index(drop=True).iterrows():
        feature=str(r["feature"]); state=str(r["state"]); target=str(r["target"])
        direction=1 if str(r["direction"]).upper()=="LONG" else -1
        horizon=int(target_parts(target)[1])
        cid=f"C{idx+1}"
        base_mask=fastmask(feature,"base",state)&val_window
        vals=T[target][base_mask]*direction
        times=grid[base_mask]
        finite=np.isfinite(vals)
        vals=vals[finite]; times=times[finite]
        series_by_candidate[cid]=pd.Series(vals,index=times)
        eligible_mask = base_mask & np.isfinite(T[target])
        masks_by_candidate[cid]=eligible_mask

        nonv,nont=nonoverlap(times,vals,horizon)
        dailyv,dailyt=subset_first_per_day(times,vals)
        epv,ept=subset_first_per_episode(base_mask,grid,T[target]*direction)

        rm_month,best_month=remove_best_month_mean(times,vals)
        loo_min,loo_json=leave_one_year_out_min(times,vals)
        b025,b50,b975=month_block_bootstrap(times,vals,BOOTSTRAPS,BOOTSTRAP_SEED+idx)

        def alt_mean(label):
            m=fastmask(feature,label,state)&val_window
            return mean_bp(T[target][m]*direction)

        m=mean_bp(vals)
        rec={
            "candidate_id":cid,
            "feature":feature,"state":state,"target":target,"direction":str(r["direction"]),
            "signal_family_key":f"{feature}|{state}|{horizon}m|{str(r['direction']).upper()}",
            "n":int(len(vals)),
            "mean_bp":m,
            "median_bp":float(np.median(vals)*1e4) if len(vals) else np.nan,
            "win_rate_pct":float((vals>0).mean()*100) if len(vals) else np.nan,
            "net1bp_mean_bp":m-1.0,
            "net2bp_mean_bp":m-2.0,
            "net3bp_mean_bp":m-3.0,
            "net5bp_mean_bp":m-5.0,
            "trim1_mean_bp":trimmed_best(vals,0.01),
            "trim2_mean_bp":trimmed_best(vals,0.02),
            "trim5_mean_bp":trimmed_best(vals,0.05),
            "remove_best5_mean_bp":remove_best(vals,5),
            "remove_best10_mean_bp":remove_best(vals,10),
            "remove_best_month_mean_bp":rm_month,
            "removed_best_month":best_month,
            "leave_one_year_out_min_mean_bp":loo_min,
            "leave_one_year_out_json":json.dumps(loo_json,sort_keys=True),
            "nonoverlap_n":int(len(nonv)),
            "nonoverlap_mean_bp":mean_bp(nonv),
            "daily_first_n":int(len(dailyv)),
            "daily_first_mean_bp":mean_bp(dailyv),
            "episode_first_n":int(len(epv)),
            "episode_first_mean_bp":mean_bp(epv),
            "z09_mean_bp":alt_mean("z09"),
            "z11_mean_bp":alt_mean("z11"),
            "lag1d_mean_bp":alt_mean("lag1"),
            "lag2d_mean_bp":alt_mean("lag2"),
            "bootstrap_month_q025_bp":b025,
            "bootstrap_month_q50_bp":b50,
            "bootstrap_month_q975_bp":b975,
        }
        gates=[
            rec["mean_bp"]>0,
            rec["net1bp_mean_bp"]>0,
            rec["trim2_mean_bp"]>0,
            rec["trim5_mean_bp"]>0,
            rec["remove_best10_mean_bp"]>0,
            rec["remove_best_month_mean_bp"]>0,
            rec["leave_one_year_out_min_mean_bp"]>0,
            rec["nonoverlap_mean_bp"]>0,
            rec["daily_first_mean_bp"]>0,
            rec["episode_first_mean_bp"]>0,
            rec["lag1d_mean_bp"]>0,
            rec["lag2d_mean_bp"]>0,
            rec["z09_mean_bp"]>0,
            rec["z11_mean_bp"]>0,
            rec["bootstrap_month_q025_bp"]>0,
        ]
        rec["final_preoos_pass"]=bool(all(gates))
        rec["failed_gate_count"]=int(sum(not bool(x) for x in gates))
        rows.append(rec)

    R=pd.DataFrame(rows)
    R.to_csv(out/"FORENSIC_RESULTS.csv",index=False)
    status(4,10,"candidate-level forensic complete",passed=int(R["final_preoos_pass"].sum()))

    # Dependency matrices.
    ids=R["candidate_id"].tolist()
    overlap=pd.DataFrame(np.nan,index=ids,columns=ids)
    corr=pd.DataFrame(np.nan,index=ids,columns=ids)
    for a in ids:
        for b in ids:
            ma=masks_by_candidate[a]&val_window
            mb=masks_by_candidate[b]&val_window
            union=int((ma|mb).sum())
            inter=int((ma&mb).sum())
            overlap.loc[a,b]=inter/union if union else np.nan
            sa=series_by_candidate[a]
            sb=series_by_candidate[b]
            common=sa.index.intersection(sb.index)
            if len(common)>=3:
                corr.loc[a,b]=float(np.corrcoef(sa.loc[common].to_numpy(),sb.loc[common].to_numpy())[0,1])
    overlap.to_csv(out/"SIGNAL_JACCARD.csv")
    corr.to_csv(out/"COMMON_TIMESTAMP_RETURN_CORRELATION.csv")

    groups=R.groupby("signal_family_key").agg(
        candidate_count=("candidate_id","count"),
        passing_candidates=("final_preoos_pass","sum")
    ).reset_index()
    groups["family_pass"]=groups["passing_candidates"]>0
    groups.to_csv(out/"SIGNAL_FAMILY_SUMMARY.csv",index=False)

    passing=R[R["final_preoos_pass"]].copy()
    passing.to_csv(out/"FINAL_PREOOS_SURVIVORS.csv",index=False)
    unique_passing_families=int(passing["signal_family_key"].nunique()) if len(passing) else 0
    status(5,10,"dependency audit complete",candidate_passes=len(passing),unique_signal_families=unique_passing_families)

    # Human-readable report.
    cols=[
        "candidate_id","feature","state","target","direction","mean_bp",
        "trim5_mean_bp","remove_best10_mean_bp","remove_best_month_mean_bp",
        "leave_one_year_out_min_mean_bp","nonoverlap_mean_bp","daily_first_mean_bp",
        "episode_first_mean_bp","lag1d_mean_bp","lag2d_mean_bp",
        "bootstrap_month_q025_bp","final_preoos_pass"
    ]
    report=[
        "# GEF V103 — V102 final pre-OOS forensic","",
        f"Run: {rid}",
        f"- exact V102 source: {EXPECTED_V102_RUN}",
        f"- candidate passes: {len(passing)}/5",
        f"- unique passing signal families: {unique_passing_families}",
        "- 2023-2025 accessed: false",
        "- 2026 accessed: false","",
        "## Forensic summary","",
        R[cols].to_markdown(index=False),"",
        "## Signal families","",
        groups.to_markdown(index=False),"",
        "STOP. Do not open locked OOS automatically."
    ]
    (out/"V103_REPORT.md").write_text("\n".join(report),encoding="utf-8")
    status(6,10,"report written")

    receipt={
        "run_id":rid,
        "status":"COMPLETE_V103_RATES_PREOOS_FORENSIC",
        "engine_version":ENGINE_VERSION,
        "source_v102":EXPECTED_V102_RUN,
        "source_final_sha256":EXPECTED_FINAL_SHA,
        "candidates_audited":5,
        "candidate_preoos_passes":int(len(passing)),
        "unique_signal_families_all":int(R["signal_family_key"].nunique()),
        "unique_signal_families_passing":unique_passing_families,
        "forensic_results_sha256":sha256(out/"FORENSIC_RESULTS.csv"),
        "final_preoos_survivors_sha256":sha256(out/"FINAL_PREOOS_SURVIVORS.csv"),
        "2023_2025_accessed":False,
        "2026_accessed":False,
        "next":"STOP_FOR_HUMAN_REVIEW; IF ANY FAMILY PASSES, PREDECLARE SEPARATE V104 LOCKED-OOS PROTOCOL BEFORE ANY 2023-2025 ACCESS"
    }
    write_json(out/"RUN_RECEIPT.json",receipt)
    status(7,10,"receipt written")
    status(8,10,"2023-2025 firewall asserted",accessed=False)
    status(9,10,"2026 firewall asserted",accessed=False)
    status(10,10,"DONE")
    print("\n=== V103 RECEIPT ===")
    print(json.dumps(receipt,indent=2))
    print("\n=== V103 FORENSIC RESULTS ===")
    print(R[cols].to_string(index=False))
    print("\n=== V103 SIGNAL FAMILIES ===")
    print(groups.to_string(index=False))
    print("\nRUN:",out)


if __name__=="__main__":
    main()
