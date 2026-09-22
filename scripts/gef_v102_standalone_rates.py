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

ENGINE_VERSION = "V102.0"
FAST_MIN_PERIODS = 5000
SLOW_MIN_PERIODS = 500
STATE_Z = 1.0
GENERIC_COST_BP = 1.0
DISCOVERY_Q = 0.10
MAX_FROZEN = 200
FORBIDDEN_YEAR = 2023

MIN_TRAIN_N = 120
MIN_HOLD_N = 40
MIN_REP_N = 60
MIN_VAL_N = 80


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def bh_qvalues(pvals):
    p = np.asarray(pvals, dtype=np.float64)
    q = np.full(len(p), np.nan, dtype=np.float64)
    finite = np.flatnonzero(np.isfinite(p))
    if not len(finite):
        return q
    order = finite[np.argsort(p[finite], kind="mergesort")]
    m = len(order)
    running = 1.0
    for rev_rank, idx in enumerate(order[::-1], 1):
        rank = m - rev_rank + 1
        val = min(1.0, p[idx] * m / rank)
        running = min(running, val)
        q[idx] = running
    return q


def causal_states(series, min_periods, zcut=1.0):
    s = pd.to_numeric(series, errors="coerce")
    mu = s.expanding(min_periods=min_periods).mean().shift(1)
    sd = s.expanding(min_periods=min_periods).std().shift(1).replace(0, np.nan)
    z = ((s - mu) / sd).to_numpy(dtype=np.float32)
    finite = np.isfinite(z)
    return finite & (z <= -zcut), finite & (z >= zcut)


def mean_bp(x):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    return float(x.mean() * 1e4) if len(x) else np.nan


def trimmed_best_mean_bp(x, pct):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan
    k = int(math.ceil(len(x) * pct))
    if k <= 0:
        return mean_bp(x)
    if k >= len(x):
        return np.nan
    return mean_bp(np.sort(x)[:-k])


def remove_best_k_mean_bp(x, k):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if len(x) <= k:
        return np.nan
    return mean_bp(np.sort(x)[:-k])


def positive_year_fraction(times, vals):
    d = pd.DataFrame({"t": pd.to_datetime(times), "v": np.asarray(vals, dtype=np.float64)})
    d = d[np.isfinite(d["v"])]
    if d.empty:
        return np.nan, {}
    d["year"] = d["t"].dt.year
    y = d.groupby("year")["v"].mean() * 1e4
    return float((y > 0).mean()), {str(int(k)): float(v) for k, v in y.items()}


def nonoverlap_mean_bp(times, vals, horizon_min):
    times = pd.DatetimeIndex(times)
    vals = np.asarray(vals, dtype=np.float64)
    ok = np.isfinite(vals)
    times = times[ok]
    vals = vals[ok]
    if not len(vals):
        return np.nan, 0
    keep = []
    next_allowed = None
    gap = pd.Timedelta(minutes=int(horizon_min))
    for i, t in enumerate(times):
        if next_allowed is None or t >= next_allowed:
            keep.append(i)
            next_allowed = t + gap
    z = vals[np.asarray(keep, dtype=int)] if keep else np.asarray([], dtype=float)
    return (mean_bp(z), int(len(z))) if len(z) else (np.nan, 0)


def metrics(times, vals, horizon_min, remove_best=0):
    vals = np.asarray(vals, dtype=np.float64)
    ok = np.isfinite(vals)
    vals = vals[ok]
    times = pd.DatetimeIndex(times)[ok]
    pyf, yearly = positive_year_fraction(times, vals)
    no_mean, no_n = nonoverlap_mean_bp(times, vals, horizon_min)
    out = {
        "n": int(len(vals)),
        "mean_bp": mean_bp(vals),
        "net1bp_mean_bp": mean_bp(vals) - GENERIC_COST_BP if len(vals) else np.nan,
        "median_bp": float(np.median(vals) * 1e4) if len(vals) else np.nan,
        "win_rate_pct": float((vals > 0).mean() * 100) if len(vals) else np.nan,
        "positive_year_fraction": pyf,
        "yearly_mean_bp_json": json.dumps(yearly, sort_keys=True),
        "trim_best_1pct_mean_bp": trimmed_best_mean_bp(vals, 0.01),
        "trim_best_2pct_mean_bp": trimmed_best_mean_bp(vals, 0.02),
        "nonoverlap_mean_bp": no_mean,
        "nonoverlap_n": no_n,
    }
    if remove_best:
        out[f"remove_best_{remove_best}_mean_bp"] = remove_best_k_mean_bp(vals, remove_best)
    return out


def target_parts(target):
    m = re.fullmatch(r"([A-Z]+)_fwd_(\d+)m", str(target))
    if not m:
        raise RuntimeError(f"Unsupported target {target}")
    return m.group(1), int(m.group(2))


def load_m1(root, sym, start_year, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError(f"V102 refuses year >= {FORBIDDEN_YEAR}")
    parts = []
    skipped = []
    for year in range(start_year, end_year + 1):
        if year >= FORBIDDEN_YEAR:
            raise RuntimeError(f"Forbidden year requested: {year}")
        p = root / "DataLake" / "raw" / "histdata" / sym / "M1" / f"{sym}_M1_{year}.parquet"
        if not p.exists():
            if year <= 2012:
                skipped.append(year)
                continue
            raise RuntimeError(f"Missing required replication/validation file {p}")
        d = pd.read_parquet(p)
        dc = next((c for c in d.columns if str(c).lower() in ["datetime", "timestamp", "time", "date"]), None)
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
        print(f"[GEF102] {sym} skipped legacy warmup years {skipped} (V83-compatible)", flush=True)
    q = pd.concat(parts, ignore_index=True).sort_values("utc").drop_duplicates("utc", keep="last")
    return q.set_index("utc")["px"]


def parse_treasury(root, folder, prefix, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError("V102 Treasury parser refuses 2023+")
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
                if txt and (tag.startswith("NEW_DATE") or tag.startswith("BC_") or tag.startswith("TC_") or tag == "NEW_DATE"):
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
        raise RuntimeError(f"Treasury parse failed nominal={nom.shape} real={real.shape}")
    rates = pd.concat([nom, real], axis=1).sort_index()
    nom_by = {tenor_from_col(c): c for c in nom.columns if tenor_from_col(c) is not None}
    real_by = {tenor_from_col(c): c for c in real.columns if tenor_from_col(c) is not None}
    for ten in sorted(set(nom_by).intersection(real_by)):
        label = f"{int(ten * 12)}M" if ten < 1 else f"{int(ten)}Y"
        rates[f"BE_{label}"] = rates[nom_by[ten]] - rates[real_by[ten]]
    for a, b in [(2, 10), (5, 10), (10, 30), (5, 30)]:
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
        parts.append(((s - mu) / sd).rename(f"rates_yields_{c}_z252"))
    rf = pd.concat(parts, axis=1)
    rf["AVAILABLE_AT"] = pd.DatetimeIndex(rf.index) + pd.Timedelta(days=1)
    return rf.reset_index(drop=True)


def asof_selected(grid, frame, features):
    base = pd.DataFrame({"decision_time_utc": grid})
    cols = {}
    for c in features:
        if c not in frame.columns:
            raise RuntimeError(f"Selected rates feature missing after rebuild: {c}")
        src = pd.DataFrame({
            "AVAILABLE_AT": frame["AVAILABLE_AT"],
            c: pd.to_numeric(frame[c], errors="coerce"),
        }).dropna(subset=["AVAILABLE_AT", c]).sort_values("AVAILABLE_AT").drop_duplicates("AVAILABLE_AT", keep="last")
        z = pd.merge_asof(base, src, left_on="decision_time_utc", right_on="AVAILABLE_AT", direction="backward")
        cols[c] = z[c].to_numpy()
    return pd.DataFrame(cols, index=grid)


def build_target(P, grid, target):
    sym, mins = target_parts(target)
    k = mins // 5
    raw = P[sym].shift(-k) / P[sym] - 1
    y = np.array(raw.reindex(grid), dtype=np.float32, copy=True)
    minute = (grid.view("int64") // 60_000_000_000).astype(np.int64)
    y[(minute % mins) != 0] = np.nan
    return y


def latest_run(base, prefix):
    runs = sorted(base.glob(f"{prefix}-*"))
    runs = [p for p in runs if (p / "RUN_RECEIPT.json").exists()]
    if not runs:
        raise RuntimeError(f"No completed {prefix} run")
    return runs[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args = ap.parse_args()

    root = Path(args.root)
    base = root / "Research" / "Autonomous" / "guardian_edge_factory_v102_standalone_rates"
    base.mkdir(parents=True, exist_ok=True)
    rid = "GEF102-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
    out = base / rid
    out.mkdir(parents=True, exist_ok=False)
    t0 = time.time()

    def status(step, total, message, **extra):
        payload = {
            "run_id": rid,
            "engine_version": ENGINE_VERSION,
            "step": step,
            "steps": total,
            "percent": round(100 * step / total, 1),
            "elapsed_s": round(time.time() - t0, 1),
            "timestamp_utc": pd.Timestamp.now("UTC").isoformat(),
            "message": message,
            **extra,
        }
        write_json(out / "LIVE_STATUS.json", payload)
        tail = " | ".join(f"{k}={v}" for k, v in extra.items())
        print(f"[GEF102] {step}/{total} {100*step/total:.0f}% | {message}" + (f" | {tail}" if tail else ""), flush=True)

    status(1, 12, "load frozen V85/V83B rates lineage; 2023+ forbidden")

    v85 = latest_run(root / "Research" / "Autonomous" / "guardian_edge_factory_v85", "GEF85")
    design = json.loads((v85 / "TRIAL_DESIGN.json").read_text(encoding="utf-8"))
    catalog = pd.read_csv(v85 / "FROZEN_ELIGIBLE_FEATURES.csv").reset_index(drop=True)
    state_meta = json.loads((v85 / "STATE_CACHE_META.json").read_text(encoding="utf-8"))

    v84c = root / "Research" / "Autonomous" / "guardian_edge_factory_v84c" / design["source_v84c"]
    r84 = json.loads((v84c / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
    v83b = root / "Research" / "Autonomous" / "guardian_edge_factory_v83b" / r84["source_v83b"]
    manifest = json.loads((v83b / "REPAIRED_ARCHITECTURE_MANIFEST.json").read_text(encoding="utf-8"))

    F = pd.read_parquet(manifest["price_state_5m_path"])
    S = pd.read_parquet(manifest["slow_state_repaired_path"])
    Y = pd.read_parquet(manifest["targets_5m_path"])
    F.index = pd.to_datetime(F.index)
    S.index = pd.to_datetime(S.index)
    Y = Y.reindex(F.index)

    targets = [c for c in Y.columns if "_fwd_" in str(c)]
    nt = len(targets)
    nf = len(catalog)
    train_rows = np.flatnonzero(F.index.year <= 2012)
    hold_rows = np.flatnonzero(F.index.year == 2013)

    train_shape = tuple(state_meta["train_shape"])
    hold_shape = tuple(state_meta["hold_shape"])
    ST = np.memmap(v85 / "STATE_TRAIN.bool.dat", mode="r", dtype=np.bool_, shape=train_shape)
    SH = np.memmap(v85 / "STATE_HOLD.bool.dat", mode="r", dtype=np.bool_, shape=hold_shape)

    YT = np.array(Y[targets], dtype=np.float32, copy=True)[train_rows, :]
    YH = np.array(Y[targets], dtype=np.float32, copy=True)[hold_rows, :]
    train_times = F.index[train_rows]
    hold_times = F.index[hold_rows]
    train_minute = (train_times.view("int64") // 60_000_000_000).astype(np.int64)
    hold_minute = (hold_times.view("int64") // 60_000_000_000).astype(np.int64)
    horizons = []
    for ti, target in enumerate(targets):
        _, h = target_parts(target)
        horizons.append(h)
        YT[(train_minute % h) != 0, ti] = np.nan
        YH[(hold_minute % h) != 0, ti] = np.nan

    total_slots = int(design["predeclared_trial_slots"])
    singleton_slots = int(design["singleton_slots"])
    pmap = np.memmap(v85 / "TRAIN_PVALUES.float32.dat", mode="r", dtype=np.float32, shape=(total_slots,))

    rate_idx = catalog.index[catalog["family"].astype(str).eq("rates_yields")].tolist()
    if not rate_idx:
        raise RuntimeError("No rates_yields features in frozen catalog")
    status(2, 12, "frozen discovery data loaded", rate_features=len(rate_idx), targets=nt)

    rows = []
    for fi in rate_idx:
        feature = str(catalog.loc[fi, "feature"])
        for st in range(2):
            state_name = ("LO", "HI")[st]
            for ti, target in enumerate(targets):
                slot = fi * 2 * nt + st * nt + ti
                if slot >= singleton_slots:
                    raise RuntimeError("Singleton slot overflow")
                pv = float(pmap[slot])
                if not np.isfinite(pv):
                    continue
                mt = np.asarray(ST[fi, st, :])
                mh = np.asarray(SH[fi, st, :])
                vt = YT[:, ti][mt]
                vh = YH[:, ti][mh]
                vt = vt[np.isfinite(vt)]
                vh = vh[np.isfinite(vh)]
                if len(vt) < MIN_TRAIN_N:
                    continue
                raw = float(vt.mean())
                if not np.isfinite(raw) or raw == 0:
                    continue
                direction = 1 if raw > 0 else -1
                hold_dir = vh * direction
                rows.append({
                    "feature_i": int(fi),
                    "feature": feature,
                    "state_i": int(st),
                    "state": state_name,
                    "target_i": int(ti),
                    "target": str(target),
                    "horizon_min": int(horizons[ti]),
                    "direction_sign": int(direction),
                    "direction": "LONG" if direction > 0 else "SHORT",
                    "train_n": int(len(vt)),
                    "train_mean_bp": mean_bp(vt * direction),
                    "train_p_two": pv,
                    "hold2013_n": int(np.isfinite(hold_dir).sum()),
                    "hold2013_mean_bp": mean_bp(hold_dir),
                })

    A = pd.DataFrame(rows)
    if A.empty:
        raise RuntimeError("No finite standalone rates tests")
    A["bh_q"] = bh_qvalues(A["train_p_two"].to_numpy())
    A = A.sort_values(["bh_q", "train_p_two", "hold2013_mean_bp", "train_mean_bp"],
                      ascending=[True, True, False, False], kind="mergesort").reset_index(drop=True)
    A.to_csv(out / "RATE_ATOMS_ALL.csv", index=False)

    frozen = A[
        A["train_p_two"].le(0.05)
        & A["bh_q"].le(DISCOVERY_Q)
        & A["hold2013_n"].ge(MIN_HOLD_N)
        & A["hold2013_mean_bp"].gt(0)
    ].head(MAX_FROZEN).copy()

    if frozen.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_V102_NO_DISCOVERY_SURVIVORS",
            "engine_version": ENGINE_VERSION,
            "finite_rate_tests": int(len(A)),
            "2014_plus_accessed": False,
            "2023_2025_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "V102_REPORT.md").write_text("# V102\n\nNo standalone rates candidate survived discovery + 2013 confirmation.\n", encoding="utf-8")
        status(12, 12, "DONE - no discovery survivors")
        print(json.dumps(receipt, indent=2))
        return

    frozen.to_csv(out / "FROZEN_RATES_PRE_2014.csv", index=False)
    write_json(out / "DISCOVERY_FREEZE.json", {
        "run_id": rid,
        "status": "FROZEN_BEFORE_REPLICATION",
        "finite_rate_tests": int(len(A)),
        "frozen_candidates": int(len(frozen)),
        "frozen_csv_sha256": sha256(out / "FROZEN_RATES_PRE_2014.csv"),
        "2014_plus_accessed_at_freeze": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
    })
    status(3, 12, "standalone rates candidates frozen before 2014+", frozen=len(frozen))

    feature_lookup = {str(r["feature"]): int(i) for i, r in catalog.iterrows()}

    def reconstruct(end_year, candidates, parity):
        if end_year >= FORBIDDEN_YEAR:
            raise RuntimeError("V102 reconstruction refuses 2023+")
        features = sorted(set(candidates["feature"]))
        target_names = sorted(set(candidates["target"]))
        markets = sorted({target_parts(t)[0] for t in target_names})

        grid = pd.date_range("2010-01-01 00:00", f"{end_year}-12-31 23:55", freq="5min")
        P = pd.DataFrame(index=grid)
        for j, sym in enumerate(markets, 1):
            raw = load_m1(root, sym, 2009, end_year)
            P[sym] = raw.resample("5min", label="right", closed="left").last().reindex(grid).astype("float64")
            print(f"[GEF102] target price rebuild {j}/{len(markets)} {sym} through {end_year}", flush=True)

        diffs = pd.Series(S.index).diff().dropna()
        slow_freq = diffs.mode().iloc[0]
        slow_grid = pd.date_range(S.index.min(), f"{end_year}-12-31 23:00", freq=slow_freq)

        RF = build_rates_frame(root, end_year)
        Rj = asof_selected(slow_grid, RF, features)
        if not S.index.equals(slow_grid[:len(S.index)]):
            raise RuntimeError("V102 slow-grid prefix does not match canonical V83B")
        for f in features:
            if f not in S.columns:
                raise RuntimeError(f"Missing canonical V83B feature {f}")
            Rj.loc[S.index, f] = pd.to_numeric(S[f], errors="coerce").to_numpy()

        slow_states = {}
        slow_states_09 = {}
        slow_states_11 = {}
        slow_states_lag1d = {}
        for f in features:
            lo, hi = causal_states(Rj[f], SLOW_MIN_PERIODS, 1.0)
            lo09, hi09 = causal_states(Rj[f], SLOW_MIN_PERIODS, 0.9)
            lo11, hi11 = causal_states(Rj[f], SLOW_MIN_PERIODS, 1.1)
            lol, hil = causal_states(Rj[f].shift(24), SLOW_MIN_PERIODS, 1.0)
            slow_states[(f, "LO")], slow_states[(f, "HI")] = lo, hi
            slow_states_09[(f, "LO")], slow_states_09[(f, "HI")] = lo09, hi09
            slow_states_11[(f, "LO")], slow_states_11[(f, "HI")] = lo11, hi11
            slow_states_lag1d[(f, "LO")], slow_states_lag1d[(f, "HI")] = lol, hil

        slow_ns = slow_grid.view("int64")
        fast_ns = grid.view("int64")
        bridge = np.searchsorted(slow_ns, fast_ns, side="right") - 1
        states, states09, states11, stateslag = {}, {}, {}, {}
        ok = bridge >= 0
        for f in features:
            for st in ("LO", "HI"):
                for src, dst in [
                    (slow_states, states),
                    (slow_states_09, states09),
                    (slow_states_11, states11),
                    (slow_states_lag1d, stateslag),
                ]:
                    z = np.zeros(len(grid), dtype=np.bool_)
                    z[ok] = src[(f, st)][bridge[ok]]
                    dst[(f, st)] = z

        if parity:
            parity_rows = []
            if not F.index.equals(grid[:len(F.index)]):
                raise RuntimeError("V102 fast grid prefix mismatch")
            for f in features:
                fi = feature_lookup[f]
                for st_i, st in enumerate(("LO", "HI")):
                    rebuilt = states[(f, st)][:len(F.index)]
                    frozen_state = np.concatenate([
                        np.asarray(ST[fi, st_i, :]),
                        np.asarray(SH[fi, st_i, :])
                    ])
                    mismatch = int(np.count_nonzero(rebuilt != frozen_state))
                    parity_rows.append({
                        "feature": f,
                        "state": st,
                        "rows": int(len(rebuilt)),
                        "mismatch_rows": mismatch,
                        "parity_ok": mismatch == 0,
                    })
            PR = pd.DataFrame(parity_rows)
            PR.to_csv(out / "RECONSTRUCTION_PARITY_2010_2013.csv", index=False)
            if not bool(PR["parity_ok"].all()):
                raise RuntimeError("V102 canonical rates state parity failed")

        targets_map = {t: build_target(P, grid, t) for t in target_names}
        return grid, states, states09, states11, stateslag, targets_map

    status(4, 12, "rebuild through 2017 and verify exact 2010-2013 parity")
    grid17, states17, states09_17, states11_17, stateslag17, targets17 = reconstruct(2017, frozen, True)
    status(5, 12, "parity exact; scoring replication 2014-2017")

    rep_window = (grid17 >= pd.Timestamp("2014-01-01")) & (grid17 < pd.Timestamp("2018-01-01"))
    rep_rows = []
    for r in frozen.itertuples(index=False):
        mask = states17[(r.feature, r.state)] & rep_window
        y = targets17[r.target][mask] * int(r.direction_sign)
        times = grid17[mask]
        met = metrics(times, y, int(r.horizon_min), remove_best=3)
        passed = (
            met["n"] >= MIN_REP_N
            and np.isfinite(met["mean_bp"]) and met["mean_bp"] > 0
            and np.isfinite(met["net1bp_mean_bp"]) and met["net1bp_mean_bp"] > 0
            and np.isfinite(met["positive_year_fraction"]) and met["positive_year_fraction"] >= 0.50
            and np.isfinite(met["trim_best_1pct_mean_bp"]) and met["trim_best_1pct_mean_bp"] > 0
        )
        rep_rows.append({**r._asdict(), **{f"rep_{k}": v for k, v in met.items()}, "replication_pass": bool(passed)})
    R = pd.DataFrame(rep_rows)
    R.to_csv(out / "REPLICATION_RESULTS.csv", index=False)
    rp = R[R["replication_pass"].astype(bool)].copy()
    status(6, 12, "replication complete", frozen=len(frozen), replication_survivors=len(rp))

    if rp.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_V102_REPLICATION_FAIL_ALL",
            "engine_version": ENGINE_VERSION,
            "discovery_frozen": int(len(frozen)),
            "replication_survivors": 0,
            "validation_accessed": False,
            "2023_2025_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "V102_REPORT.md").write_text(f"# V102\n\n{len(frozen)} discovery candidates; 0 replication survivors.\n", encoding="utf-8")
        status(12, 12, "DONE - replication killed all")
        print(json.dumps(receipt, indent=2))
        return

    robust_rows = []
    for r in rp.itertuples(index=False):
        direction = int(r.direction_sign)
        def score(mask_source):
            m = mask_source[(r.feature, r.state)] & rep_window
            yy = targets17[r.target][m] * direction
            return mean_bp(yy)

        robust_pass = (
            np.isfinite(r.rep_trim_best_2pct_mean_bp) and r.rep_trim_best_2pct_mean_bp > 0
            and np.isfinite(r.rep_remove_best_3_mean_bp) and r.rep_remove_best_3_mean_bp > 0
            and np.isfinite(r.rep_nonoverlap_mean_bp) and r.rep_nonoverlap_mean_bp > 0
        )
        n09 = score(states09_17)
        n11 = score(states11_17)
        lag1 = score(stateslag17)
        robust_pass = bool(robust_pass and np.isfinite(n09) and n09 > 0 and np.isfinite(n11) and n11 > 0 and np.isfinite(lag1) and lag1 > 0)
        robust_rows.append({
            **r._asdict(),
            "robust_z09_mean_bp": n09,
            "robust_z11_mean_bp": n11,
            "robust_lag1d_mean_bp": lag1,
            "robustness_pass": robust_pass,
        })

    B = pd.DataFrame(robust_rows)
    B.to_csv(out / "ROBUSTNESS_RESULTS.csv", index=False)
    robust = B[B["robustness_pass"].astype(bool)].copy()

    if robust.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_V102_ROBUSTNESS_FAIL_ALL",
            "engine_version": ENGINE_VERSION,
            "discovery_frozen": int(len(frozen)),
            "replication_survivors": int(len(rp)),
            "robustness_survivors": 0,
            "validation_accessed": False,
            "2023_2025_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "V102_REPORT.md").write_text(
            f"# V102\n\nDiscovery frozen: {len(frozen)}. Replication: {len(rp)}. Robustness: 0. Validation unopened.\n",
            encoding="utf-8",
        )
        status(12, 12, "DONE - robustness killed all")
        print(json.dumps(receipt, indent=2))
        return

    robust.to_csv(out / "FROZEN_PRE_VALIDATION.csv", index=False)
    write_json(out / "PRE_VALIDATION_FREEZE.json", {
        "run_id": rid,
        "status": "FROZEN_BEFORE_VALIDATION",
        "survivors": int(len(robust)),
        "frozen_csv_sha256": sha256(out / "FROZEN_PRE_VALIDATION.csv"),
        "2018_plus_accessed_at_freeze": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
    })
    status(7, 12, "robust survivors frozen before 2018+", survivors=len(robust))

    status(8, 12, "rebuild through 2022; validation only")
    grid22, states22, _, _, _, targets22 = reconstruct(2022, robust, False)
    val_window = (grid22 >= pd.Timestamp("2018-01-01")) & (grid22 < pd.Timestamp("2023-01-01"))

    val_rows = []
    for r in robust.itertuples(index=False):
        mask = states22[(r.feature, r.state)] & val_window
        y = targets22[r.target][mask] * int(r.direction_sign)
        times = grid22[mask]
        met = metrics(times, y, int(r.horizon_min), remove_best=5)
        passed = (
            met["n"] >= MIN_VAL_N
            and np.isfinite(met["mean_bp"]) and met["mean_bp"] > 0
            and np.isfinite(met["net1bp_mean_bp"]) and met["net1bp_mean_bp"] > 0
            and np.isfinite(met["positive_year_fraction"]) and met["positive_year_fraction"] >= 0.60
            and np.isfinite(met["trim_best_1pct_mean_bp"]) and met["trim_best_1pct_mean_bp"] > 0
            and np.isfinite(met["trim_best_2pct_mean_bp"]) and met["trim_best_2pct_mean_bp"] > 0
            and np.isfinite(met["remove_best_5_mean_bp"]) and met["remove_best_5_mean_bp"] > 0
            and np.isfinite(met["nonoverlap_mean_bp"]) and met["nonoverlap_mean_bp"] > 0
        )
        val_rows.append({**r._asdict(), **{f"val_{k}": v for k, v in met.items()}, "validation_pass": bool(passed)})

    V = pd.DataFrame(val_rows)
    V.to_csv(out / "VALIDATION_RESULTS.csv", index=False)
    final = V[V["validation_pass"].astype(bool)].copy()
    final.to_csv(out / "FINAL_SURVIVORS.csv", index=False)
    status(9, 12, "validation complete", validation_candidates=len(V), final_survivors=len(final))

    report = [
        "# GEF V102 — Standalone Rates / Real Yields / Breakevens",
        "",
        f"Run: {rid}",
        f"- Finite standalone rates tests: {len(A)}",
        f"- Discovery frozen: {len(frozen)}",
        f"- Replication survivors: {len(rp)}",
        f"- Robustness survivors: {len(robust)}",
        f"- Validation survivors: {len(final)}",
        "- 2023-2025 accessed: false",
        "- 2026 accessed: false",
        "",
    ]
    if len(final):
        cols = [
            "feature", "state", "target", "direction",
            "train_mean_bp", "hold2013_mean_bp",
            "rep_mean_bp", "robust_z09_mean_bp", "robust_z11_mean_bp", "robust_lag1d_mean_bp",
            "val_mean_bp", "val_net1bp_mean_bp", "val_positive_year_fraction",
            "val_trim_best_2pct_mean_bp", "val_remove_best_5_mean_bp", "val_nonoverlap_mean_bp"
        ]
        report += ["## Final survivors", "", final[cols].to_markdown(index=False), ""]
    else:
        report += ["No standalone rates candidate passed the complete validation gate.", ""]
    (out / "V102_REPORT.md").write_text("\n".join(report), encoding="utf-8")

    receipt = {
        "run_id": rid,
        "status": "COMPLETE_V102_STANDALONE_RATES",
        "engine_version": ENGINE_VERSION,
        "source_v85": v85.name,
        "source_v83b": v83b.name,
        "finite_rate_tests": int(len(A)),
        "discovery_frozen": int(len(frozen)),
        "replication_survivors": int(len(rp)),
        "robustness_survivors": int(len(robust)),
        "validation_survivors": int(len(final)),
        "discovery_freeze_sha256": sha256(out / "FROZEN_RATES_PRE_2014.csv"),
        "pre_validation_freeze_sha256": sha256(out / "FROZEN_PRE_VALIDATION.csv"),
        "final_survivors_sha256": sha256(out / "FINAL_SURVIVORS.csv"),
        "v100_used_for_selection": False,
        "v101_triples_used_for_selection": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
        "next": "HUMAN_REVIEW_V102; DO_NOT_OPEN_2023_2025_OR_2026",
    }
    write_json(out / "RUN_RECEIPT.json", receipt)
    status(10, 12, "report and receipt written")
    status(11, 12, "firewall assertion", accessed_2023_2025=False, accessed_2026=False)
    status(12, 12, "DONE")
    print("\n=== V102 RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    if len(final):
        print("\n=== V102 FINAL SURVIVORS ===")
        print(final[["feature","state","target","direction","rep_mean_bp","val_mean_bp","val_net1bp_mean_bp"]].to_string(index=False))
    print("\nRUN:", out)


if __name__ == "__main__":
    main()
