from pathlib import Path
import argparse
import hashlib
import json
import math
import re
import time
import xml.etree.ElementTree as ET
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.special import ndtr

ENGINE_VERSION = "V101.2"
FAST_MIN_PERIODS = 5000
SLOW_MIN_PERIODS = 500
STATE_Z = 1.0
GENERIC_COST_BP = 1.0

PRICE_ATOMS_PER_GROUP = 10
RATE_ATOMS_PER_GROUP = 8
MAX_FROZEN_TRIPLES = 150

MIN_ATOM_TRAIN_N = 120
MIN_ATOM_HOLD_N = 40
MIN_TRIPLE_TRAIN_N = 80
MIN_TRIPLE_HOLD_N = 20

MIN_REP_N = 40
MIN_VAL_N = 60

DISCOVERY_Q = 0.10

FORBIDDEN_YEAR = 2023


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def p_two(x):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return np.nan
    m = float(x.mean())
    sd = float(x.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        return np.nan
    z = m / (sd / math.sqrt(n))
    return float(2.0 * ndtr(-abs(z)))


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


def causal_states(series, min_periods):
    s = pd.to_numeric(series, errors="coerce")
    mu = s.expanding(min_periods=min_periods).mean().shift(1)
    sd = s.expanding(min_periods=min_periods).std().shift(1).replace(0, np.nan)
    z = ((s - mu) / sd).to_numpy(dtype=np.float32)
    finite = np.isfinite(z)
    return finite & (z <= -STATE_Z), finite & (z >= STATE_Z)


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
    y = np.sort(x)[:-k]
    return mean_bp(y)


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
    if not keep:
        return np.nan, 0
    z = vals[np.asarray(keep, dtype=int)]
    return mean_bp(z), int(len(z))


def metrics(times, vals, horizon_min, robust=False):
    vals = np.asarray(vals, dtype=np.float64)
    ok = np.isfinite(vals)
    vals = vals[ok]
    times = pd.DatetimeIndex(times)[ok]
    out = {
        "n": int(len(vals)),
        "mean_bp": mean_bp(vals),
        "net1bp_mean_bp": mean_bp(vals) - GENERIC_COST_BP if len(vals) else np.nan,
        "median_bp": float(np.median(vals) * 1e4) if len(vals) else np.nan,
        "win_rate_pct": float((vals > 0).mean() * 100) if len(vals) else np.nan,
    }
    pyf, yearly = positive_year_fraction(times, vals)
    out["positive_year_fraction"] = pyf
    out["yearly_mean_bp_json"] = json.dumps(yearly, sort_keys=True)
    out["trim_best_1pct_mean_bp"] = trimmed_best_mean_bp(vals, 0.01)
    if robust:
        out["trim_best_2pct_mean_bp"] = trimmed_best_mean_bp(vals, 0.02)
        out["remove_best_3_mean_bp"] = remove_best_k_mean_bp(vals, 3)
        no, nn = nonoverlap_mean_bp(times, vals, horizon_min)
        out["nonoverlap_mean_bp"] = no
        out["nonoverlap_n"] = nn
    return out


def feature_market(feature):
    m = re.match(r"price_([A-Z]+)_", str(feature))
    return m.group(1) if m else None


def target_parts(target):
    m = re.fullmatch(r"([A-Z]+)_fwd_(\d+)m", str(target))
    if not m:
        raise RuntimeError(f"Unsupported target {target}")
    return m.group(1), int(m.group(2))


def supported_fast(feature):
    pats = [
        r"price_[A-Z]+_ret_\d+m",
        r"price_[A-Z]+_rv_\d+m",
        r"price_[A-Z]+_trend_\d+m",
        r"price_[A-Z]+_zret_\d+m",
    ]
    return any(re.fullmatch(p, str(feature)) for p in pats)


def build_fast_feature(name, P):
    m = re.fullmatch(r"price_([A-Z]+)_ret_(\d+)m", name)
    if m:
        sym, mins = m.group(1), int(m.group(2))
        k = mins // 5
        return (P[sym] / P[sym].shift(k) - 1).astype("float32")
    m = re.fullmatch(r"price_([A-Z]+)_rv_(\d+)m", name)
    if m:
        sym, mins = m.group(1), int(m.group(2))
        k = mins // 5
        r5 = P[sym].pct_change(1, fill_method=None)
        return r5.rolling(k, min_periods=max(3, k // 2)).std().astype("float32")
    m = re.fullmatch(r"price_([A-Z]+)_trend_(\d+)m", name)
    if m:
        sym, mins = m.group(1), int(m.group(2))
        k = mins // 5
        return (P[sym] / P[sym].shift(k) - 1).astype("float32")
    m = re.fullmatch(r"price_([A-Z]+)_zret_(\d+)m", name)
    if m:
        sym, mins = m.group(1), int(m.group(2))
        k = mins // 5
        r5 = P[sym].pct_change(1, fill_method=None)
        mu = r5.rolling(k, min_periods=max(3, k // 2)).mean()
        sd = r5.rolling(k, min_periods=max(3, k // 2)).std().replace(0, np.nan)
        return ((r5 - mu) / sd).astype("float32")
    raise RuntimeError(f"Unsupported fast feature reconstruction: {name}")


def load_m1(root, sym, start_year, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError(f"V101 refuses year >= {FORBIDDEN_YEAR}")
    parts = []
    skipped_legacy_warmup = []
    for year in range(start_year, end_year + 1):
        if year >= FORBIDDEN_YEAR:
            raise RuntimeError(f"Forbidden year requested: {year}")
        p = root / "DataLake" / "raw" / "histdata" / sym / "M1" / f"{sym}_M1_{year}.parquet"
        if not p.exists():
            # Match the frozen V83 discovery builder: legacy pre-2013 files were optional
            # and missing years were skipped. From 2013 onward, match V92 and fail closed.
            if year <= 2012:
                skipped_legacy_warmup.append(year)
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
        raise RuntimeError(f"No usable M1 files for {sym} in {start_year}-{end_year}")
    if skipped_legacy_warmup:
        print(f"[GEF101] {sym} skipped legacy warmup years {skipped_legacy_warmup} (V83-compatible)", flush=True)
    q = pd.concat(parts, ignore_index=True).sort_values("utc").drop_duplicates("utc", keep="last")
    return q.set_index("utc")["px"]


def parse_treasury(root, folder, prefix, end_year):
    if end_year >= FORBIDDEN_YEAR:
        raise RuntimeError(f"V101 refuses Treasury year >= {FORBIDDEN_YEAR}")
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
        if len(src) < 4:
            raise RuntimeError(f"Too few source rows for {c}")
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


def get_latest_completed(base, prefix, required_file=None):
    runs = sorted(base.glob(f"{prefix}-*"))
    out = []
    for p in runs:
        if not (p / "RUN_RECEIPT.json").exists():
            continue
        if required_file and not (p / required_file).exists():
            continue
        out.append(p)
    if not out:
        raise RuntimeError(f"No completed run for {base} / {prefix}")
    return out[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\MT5_Backtests")
    args = ap.parse_args()

    root = Path(args.root)
    repo = root / "guardian-research"
    base = root / "Research" / "Autonomous" / "guardian_edge_factory_v101_sparse_triple_rates"
    base.mkdir(parents=True, exist_ok=True)

    rid = "GEF101-" + pd.Timestamp.now("UTC").strftime("%Y%m%d-%H%M%S")
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
        print(f"[GEF101] {step}/{total} {100*step/total:.0f}% | {message}" + (f" | {tail}" if tail else ""), flush=True)

    status(1, 12, "locating frozen V85/V83B lineage; 2023+ forbidden")

    v85 = get_latest_completed(root / "Research" / "Autonomous" / "guardian_edge_factory_v85", "GEF85")
    r85 = json.loads((v85 / "RUN_RECEIPT.json").read_text(encoding="utf-8"))
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
    bridge = np.load(manifest["bridge_path"])
    F.index = pd.to_datetime(F.index)
    S.index = pd.to_datetime(S.index)
    Y = Y.reindex(F.index)

    if F.index.max().year >= 2014 or S.index.max().year >= 2014:
        raise RuntimeError("Unexpected post-2013 rows in frozen discovery matrices")

    targets = [c for c in Y.columns if "_fwd_" in str(c)]
    nt = len(targets)
    nf = len(catalog)
    if nt != int(design["targets"]):
        raise RuntimeError("V85 target count mismatch")

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

    status(2, 12, "frozen discovery matrices loaded", features=nf, targets=nt, v85=v85.name)

    atoms = []
    for fi, row in catalog.iterrows():
        layer = str(row["layer"])
        family = str(row["family"])
        feature = str(row["feature"])
        kind = None
        if layer == "fast" and supported_fast(feature):
            kind = "price"
        elif family == "rates_yields":
            kind = "rates"
        if kind is None:
            continue

        for st in range(2):
            state_name = ("LO", "HI")[st]
            for ti, target in enumerate(targets):
                slot = fi * 2 * nt + st * nt + ti
                if slot >= singleton_slots:
                    raise RuntimeError("Singleton slot decode overflow")
                pv = float(pmap[slot])
                if not np.isfinite(pv) or pv > 0.05:
                    continue
                mt = ST[fi, st, :]
                mh = SH[fi, st, :]
                vt = YT[:, ti][mt]
                vh = YH[:, ti][mh]
                vt = vt[np.isfinite(vt)]
                vh = vh[np.isfinite(vh)]
                if len(vt) < MIN_ATOM_TRAIN_N or len(vh) < MIN_ATOM_HOLD_N:
                    continue
                raw_mean = float(vt.mean())
                if raw_mean == 0 or not np.isfinite(raw_mean):
                    continue
                direction = 1 if raw_mean > 0 else -1
                train_dir = vt * direction
                hold_dir = vh * direction
                if float(hold_dir.mean()) <= 0:
                    continue
                atoms.append({
                    "feature_i": int(fi),
                    "feature": feature,
                    "family": family,
                    "layer": layer,
                    "kind": kind,
                    "state_i": int(st),
                    "state": state_name,
                    "target_i": int(ti),
                    "target": str(target),
                    "horizon_min": int(horizons[ti]),
                    "direction_sign": int(direction),
                    "direction": "LONG" if direction > 0 else "SHORT",
                    "train_n": int(len(train_dir)),
                    "train_mean_bp": mean_bp(train_dir),
                    "train_p_two": pv,
                    "hold2013_n": int(len(hold_dir)),
                    "hold2013_mean_bp": mean_bp(hold_dir),
                    "hold2013_p_two": p_two(hold_dir),
                })

    A = pd.DataFrame(atoms)
    if A.empty:
        raise RuntimeError("No eligible atomic price/rates phenomena survived the predeclared atomic screen")
    A = A.sort_values(
        ["target_i", "direction_sign", "kind", "train_p_two", "hold2013_mean_bp", "train_mean_bp"],
        ascending=[True, True, True, True, False, False],
        kind="mergesort",
    ).reset_index(drop=True)
    A.to_csv(out / "ATOMIC_SHORTLIST.csv", index=False)
    status(3, 12, "atomic shortlist frozen from 2010-2013 only", atoms=len(A))

    triple_rows = []
    attempted = 0
    groups = A.groupby(["target_i", "direction_sign"], sort=True)
    for (ti, direction), g in groups:
        gp = g[g["kind"] == "price"].drop_duplicates(["feature", "state"]).head(PRICE_ATOMS_PER_GROUP)
        gr = g[g["kind"] == "rates"].drop_duplicates(["feature", "state"]).head(RATE_ATOMS_PER_GROUP)
        if len(gp) < 2 or gr.empty:
            continue
        for ia, ib in combinations(gp.index.tolist(), 2):
            a = gp.loc[ia]
            b = gp.loc[ib]
            if a["family"] == b["family"]:
                continue
            for ir in gr.index.tolist():
                c = gr.loc[ir]
                attempted += 1
                mask_t = (
                    ST[int(a["feature_i"]), int(a["state_i"]), :]
                    & ST[int(b["feature_i"]), int(b["state_i"]), :]
                    & ST[int(c["feature_i"]), int(c["state_i"]), :]
                )
                mask_h = (
                    SH[int(a["feature_i"]), int(a["state_i"]), :]
                    & SH[int(b["feature_i"]), int(b["state_i"]), :]
                    & SH[int(c["feature_i"]), int(c["state_i"]), :]
                )
                yt = YT[:, int(ti)][mask_t]
                yh = YH[:, int(ti)][mask_h]
                yt = yt[np.isfinite(yt)] * int(direction)
                yh = yh[np.isfinite(yh)] * int(direction)
                if len(yt) < MIN_TRIPLE_TRAIN_N or len(yh) < MIN_TRIPLE_HOLD_N:
                    continue
                tm = mean_bp(yt)
                hm = mean_bp(yh)
                if not np.isfinite(tm) or not np.isfinite(hm) or tm <= 0 or hm <= 0:
                    continue
                key = "|".join([
                    str(a["feature"]), str(a["state"]),
                    str(b["feature"]), str(b["state"]),
                    str(c["feature"]), str(c["state"]),
                    str(a["target"]), str(int(direction)),
                ])
                cid = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
                triple_rows.append({
                    "candidate_id": cid,
                    "target_i": int(ti),
                    "target": str(a["target"]),
                    "horizon_min": int(a["horizon_min"]),
                    "direction_sign": int(direction),
                    "direction": "LONG" if int(direction) > 0 else "SHORT",
                    "price_a_feature_i": int(a["feature_i"]),
                    "price_a_feature": str(a["feature"]),
                    "price_a_family": str(a["family"]),
                    "price_a_state_i": int(a["state_i"]),
                    "price_a_state": str(a["state"]),
                    "price_b_feature_i": int(b["feature_i"]),
                    "price_b_feature": str(b["feature"]),
                    "price_b_family": str(b["family"]),
                    "price_b_state_i": int(b["state_i"]),
                    "price_b_state": str(b["state"]),
                    "rate_feature_i": int(c["feature_i"]),
                    "rate_feature": str(c["feature"]),
                    "rate_state_i": int(c["state_i"]),
                    "rate_state": str(c["state"]),
                    "train_n": int(len(yt)),
                    "train_mean_bp": tm,
                    "train_p_two": p_two(yt),
                    "hold2013_n": int(len(yh)),
                    "hold2013_mean_bp": hm,
                    "hold2013_p_two": p_two(yh),
                })

    T = pd.DataFrame(triple_rows)
    if T.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_NO_DISCOVERY_SURVIVORS",
            "engine_version": ENGINE_VERSION,
            "attempted_triples": int(attempted),
            "finite_triples": 0,
            "2014_plus_accessed": False,
            "2023_plus_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "TEST101_REPORT.md").write_text(
            "# V101 result\n\nNo sparse price x price x rates triple passed the discovery/2013 screen. Later windows were not opened.\n",
            encoding="utf-8",
        )
        status(12, 12, "DONE - no discovery survivors", attempted=attempted)
        print(json.dumps(receipt, indent=2))
        return

    T["bh_q"] = bh_qvalues(T["train_p_two"].to_numpy())
    T = T.sort_values(
        ["bh_q", "train_p_two", "hold2013_mean_bp", "train_mean_bp"],
        ascending=[True, True, False, False],
        kind="mergesort",
    ).reset_index(drop=True)
    T.to_csv(out / "TRIPLE_DISCOVERY_ALL.csv", index=False)

    frozen = T[T["bh_q"].le(DISCOVERY_Q)].copy().head(MAX_FROZEN_TRIPLES)
    if frozen.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_NO_FDR_DISCOVERY_SURVIVORS",
            "engine_version": ENGINE_VERSION,
            "attempted_triples": int(attempted),
            "finite_triples": int(len(T)),
            "fdr_q": DISCOVERY_Q,
            "2014_plus_accessed": False,
            "2023_plus_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "TEST101_REPORT.md").write_text(
            "# V101 result\n\nTriples were found, but none survived the predeclared discovery FDR gate. 2014+ was not opened.\n",
            encoding="utf-8",
        )
        status(12, 12, "DONE - no FDR survivors", attempted=attempted, finite=len(T))
        print(json.dumps(receipt, indent=2))
        return

    frozen.to_csv(out / "FROZEN_TRIPLES_PRE_2014.csv", index=False)
    freeze = {
        "run_id": rid,
        "status": "FROZEN_BEFORE_REPLICATION",
        "attempted_triples": int(attempted),
        "finite_triples": int(len(T)),
        "frozen_triples": int(len(frozen)),
        "fdr_q": DISCOVERY_Q,
        "frozen_csv_sha256": sha256(out / "FROZEN_TRIPLES_PRE_2014.csv"),
        "2014_plus_accessed_at_freeze": False,
        "2023_plus_accessed": False,
        "2026_accessed": False,
    }
    write_json(out / "DISCOVERY_FREEZE.json", freeze)
    status(4, 12, "discovery triples physically frozen before 2014+", frozen=len(frozen), attempted=attempted)

    feature_lookup = {str(r["feature"]): int(i) for i, r in catalog.iterrows()}

    def reconstruct(end_year, candidates, do_parity):
        if end_year >= FORBIDDEN_YEAR:
            raise RuntimeError("V101 reconstruction refuses 2023+")
        fast_features = sorted(set(candidates["price_a_feature"]).union(set(candidates["price_b_feature"])))
        rate_features = sorted(set(candidates["rate_feature"]))
        target_names = sorted(set(candidates["target"]))
        markets = sorted(
            {feature_market(f) for f in fast_features}
            | {target_parts(t)[0] for t in target_names}
        )
        if None in markets:
            markets.remove(None)

        grid = pd.date_range("2010-01-01 00:00", f"{end_year}-12-31 23:55", freq="5min")
        P = pd.DataFrame(index=grid)

        for j, sym in enumerate(markets, 1):
            raw = load_m1(root, sym, 2009, end_year)
            P[sym] = raw.resample("5min", label="right", closed="left").last().reindex(grid).astype("float64")
            print(f"[GEF101] price rebuild {j}/{len(markets)} {sym} through {end_year}", flush=True)

        states = {}
        parity_rows = []
        for f in fast_features:
            x = build_fast_feature(f, P)
            lo, hi = causal_states(x, FAST_MIN_PERIODS)
            states[(f, "LO")] = lo
            states[(f, "HI")] = hi

        diffs = pd.Series(S.index).diff().dropna()
        if diffs.empty:
            raise RuntimeError("Cannot infer slow-grid frequency")
        slow_freq = diffs.mode().iloc[0]
        slow_grid = pd.date_range(S.index.min(), f"{end_year}-12-31 23:00", freq=slow_freq)
        RF = build_rates_frame(root, end_year)
        Rj = asof_selected(slow_grid, RF, rate_features)

        # V83B is the canonical repaired source actually consumed by V85.
        # Recomputing 2009-2013 Treasury XML is useful for extension, but it must
        # never replace the exact frozen feature values used in discovery.
        # Anchor every selected rates feature to V83B through its final timestamp,
        # then use the causally rebuilt series only for later observations.
        anchor_end = S.index.max()
        if not S.index.equals(slow_grid[:len(S.index)]):
            raise RuntimeError("V101 slow-grid prefix does not exactly match canonical V83B index")
        for f in rate_features:
            if f not in S.columns:
                raise RuntimeError(f"Selected rates feature missing from canonical V83B matrix: {f}")
            Rj.loc[S.index, f] = pd.to_numeric(S[f], errors="coerce").to_numpy()

        slow_state = {}
        for f in rate_features:
            lo, hi = causal_states(Rj[f], SLOW_MIN_PERIODS)
            slow_state[(f, "LO")] = lo
            slow_state[(f, "HI")] = hi

        slow_ns = slow_grid.view("int64")
        fast_ns = grid.view("int64")
        br = np.searchsorted(slow_ns, fast_ns, side="right") - 1
        if (br < 0).any():
            br[br < 0] = -1
        for f in rate_features:
            for st in ("LO", "HI"):
                src = slow_state[(f, st)]
                z = np.zeros(len(grid), dtype=np.bool_)
                ok = br >= 0
                z[ok] = src[br[ok]]
                states[(f, st)] = z

        if do_parity:
            if len(F.index) > len(grid) or not F.index.equals(grid[: len(F.index)]):
                raise RuntimeError("Rebuilt fast grid does not match frozen 2010-2013 grid")
            ntr = len(train_rows)
            nh = len(hold_rows)
            for f in fast_features + rate_features:
                fi = feature_lookup.get(f)
                if fi is None:
                    raise RuntimeError(f"Feature not found in frozen catalog: {f}")
                for st_i, st in enumerate(("LO", "HI")):
                    rebuilt = states[(f, st)][: len(F.index)]
                    frozen_state = np.concatenate([np.asarray(ST[fi, st_i, :]), np.asarray(SH[fi, st_i, :])])
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
                bad = PR[~PR["parity_ok"]]
                raise RuntimeError(f"2010-2013 reconstruction parity failed:\n{bad.to_string(index=False)}")

        targets_map = {t: build_target(P, grid, t) for t in target_names}
        return grid, states, targets_map

    status(5, 12, "opening replication only: rebuilding through 2017")
    grid17, states17, targets17 = reconstruct(2017, frozen, True)
    status(6, 12, "2010-2013 reconstruction parity exact; replication scoring")

    rep_rows = []
    rep_window = (grid17 >= pd.Timestamp("2014-01-01")) & (grid17 < pd.Timestamp("2018-01-01"))
    for r in frozen.itertuples(index=False):
        m = (
            states17[(r.price_a_feature, r.price_a_state)]
            & states17[(r.price_b_feature, r.price_b_state)]
            & states17[(r.rate_feature, r.rate_state)]
            & rep_window
        )
        y = targets17[r.target][m] * int(r.direction_sign)
        times = grid17[m]
        met = metrics(times, y, int(r.horizon_min), robust=False)
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
    rep_pass = R[R["replication_pass"].astype(bool)].copy()

    if rep_pass.empty:
        receipt = {
            "run_id": rid,
            "status": "COMPLETE_REPLICATION_FAIL_ALL",
            "engine_version": ENGINE_VERSION,
            "discovery_frozen": int(len(frozen)),
            "replication_pass": 0,
            "validation_accessed": False,
            "2023_plus_accessed": False,
            "2026_accessed": False,
        }
        write_json(out / "RUN_RECEIPT.json", receipt)
        (out / "TEST101_REPORT.md").write_text(
            f"# V101 result\n\nDiscovery frozen: {len(frozen)}. Replication 2014-2017 survivors: 0. Validation was not opened.\n",
            encoding="utf-8",
        )
        status(12, 12, "DONE - replication killed all candidates", discovery=len(frozen))
        print(json.dumps(receipt, indent=2))
        return

    rep_pass.to_csv(out / "FROZEN_PRE_VALIDATION.csv", index=False)
    pre_val = {
        "run_id": rid,
        "status": "FROZEN_BEFORE_VALIDATION",
        "replication_survivors": int(len(rep_pass)),
        "frozen_csv_sha256": sha256(out / "FROZEN_PRE_VALIDATION.csv"),
        "2018_plus_accessed_at_freeze": False,
        "2023_plus_accessed": False,
        "2026_accessed": False,
    }
    write_json(out / "PRE_VALIDATION_FREEZE.json", pre_val)
    status(7, 12, "replication survivors frozen before 2018+", survivors=len(rep_pass))

    status(8, 12, "opening validation only: rebuilding through 2022")
    grid22, states22, targets22 = reconstruct(2022, rep_pass, False)
    val_window = (grid22 >= pd.Timestamp("2018-01-01")) & (grid22 < pd.Timestamp("2023-01-01"))

    val_rows = []
    for r in rep_pass.itertuples(index=False):
        m = (
            states22[(r.price_a_feature, r.price_a_state)]
            & states22[(r.price_b_feature, r.price_b_state)]
            & states22[(r.rate_feature, r.rate_state)]
            & val_window
        )
        y = targets22[r.target][m] * int(r.direction_sign)
        times = grid22[m]
        met = metrics(times, y, int(r.horizon_min), robust=True)
        passed = (
            met["n"] >= MIN_VAL_N
            and np.isfinite(met["mean_bp"]) and met["mean_bp"] > 0
            and np.isfinite(met["net1bp_mean_bp"]) and met["net1bp_mean_bp"] > 0
            and np.isfinite(met["positive_year_fraction"]) and met["positive_year_fraction"] >= 0.60
            and np.isfinite(met["trim_best_1pct_mean_bp"]) and met["trim_best_1pct_mean_bp"] > 0
            and np.isfinite(met["trim_best_2pct_mean_bp"]) and met["trim_best_2pct_mean_bp"] > 0
            and np.isfinite(met["remove_best_3_mean_bp"]) and met["remove_best_3_mean_bp"] > 0
            and np.isfinite(met["nonoverlap_mean_bp"]) and met["nonoverlap_mean_bp"] > 0
        )
        val_rows.append({**r._asdict(), **{f"val_{k}": v for k, v in met.items()}, "validation_pass": bool(passed)})

    V = pd.DataFrame(val_rows)
    V.to_csv(out / "VALIDATION_RESULTS.csv", index=False)
    survivors = V[V["validation_pass"].astype(bool)].copy()
    survivors.to_csv(out / "FINAL_SURVIVORS.csv", index=False)
    status(9, 12, "validation scored without retuning", validation_candidates=len(V), survivors=len(survivors))

    report_lines = [
        "# GEF V101 — Sparse Triple Rates Discovery",
        "",
        f"Run: {rid}",
        "",
        f"- Atomic shortlist: {len(A)}",
        f"- Triple combinations attempted: {attempted}",
        f"- Finite discovery triples: {len(T)}",
        f"- Discovery/FDR frozen: {len(frozen)}",
        f"- Replication survivors: {len(rep_pass)}",
        f"- Validation survivors: {len(survivors)}",
        "- 2023-2025 accessed: false",
        "- 2026 accessed: false",
        "",
    ]
    if len(survivors):
        report_lines += ["## Final survivors", "", survivors[[
            "candidate_id", "target", "direction",
            "price_a_feature", "price_a_state",
            "price_b_feature", "price_b_state",
            "rate_feature", "rate_state",
            "rep_mean_bp", "val_mean_bp", "val_net1bp_mean_bp",
            "val_positive_year_fraction", "val_trim_best_2pct_mean_bp",
            "val_remove_best_3_mean_bp", "val_nonoverlap_mean_bp"
        ]].to_markdown(index=False), ""]
    else:
        report_lines += ["No candidate passed the complete predeclared validation gate.", ""]
    (out / "TEST101_REPORT.md").write_text("\n".join(report_lines), encoding="utf-8")

    receipt = {
        "run_id": rid,
        "status": "COMPLETE_V101_SPARSE_TRIPLE_RATES",
        "engine_version": ENGINE_VERSION,
        "source_v85": v85.name,
        "source_v83b": v83b.name,
        "atomic_shortlist": int(len(A)),
        "attempted_triples": int(attempted),
        "finite_discovery_triples": int(len(T)),
        "discovery_frozen": int(len(frozen)),
        "replication_survivors": int(len(rep_pass)),
        "validation_survivors": int(len(survivors)),
        "discovery_freeze_sha256": sha256(out / "FROZEN_TRIPLES_PRE_2014.csv"),
        "pre_validation_freeze_sha256": sha256(out / "FROZEN_PRE_VALIDATION.csv"),
        "final_survivors_sha256": sha256(out / "FINAL_SURVIVORS.csv"),
        "v100_frozen_ranks_used_for_selection": False,
        "2023_2025_accessed": False,
        "2026_accessed": False,
        "next": "HUMAN_REVIEW_V101_SURVIVORS; DO_NOT_OPEN_2023_2025_OR_2026",
    }
    write_json(out / "RUN_RECEIPT.json", receipt)
    status(10, 12, "receipt/report written", survivors=len(survivors))
    status(11, 12, "explicit firewall assertion", accessed_2023_2025=False, accessed_2026=False)
    status(12, 12, "DONE")

    print("\n=== V101 RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    if len(survivors):
        print("\n=== V101 FINAL SURVIVORS ===")
        print(survivors[[
            "candidate_id", "target", "direction",
            "price_a_feature", "price_a_state",
            "price_b_feature", "price_b_state",
            "rate_feature", "rate_state",
            "rep_mean_bp", "val_mean_bp", "val_net1bp_mean_bp",
        ]].to_string(index=False))
    print("\nRUN:", out)


if __name__ == "__main__":
    main()
