#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPL0 = pd.Timestamp("2004-11-08", tz="UTC")
REPL1 = pd.Timestamp("2019-05-31", tz="UTC")
CONF1 = pd.Timestamp("2025-01-01", tz="UTC")
PRE1 = pd.Timestamp("2026-01-01", tz="UTC")
COSTS = {"E1": 0.001, "STRESS": 0.002}

def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def hb(path: Path | None, completed: int, total: int, stage: str, extra=None) -> None:
    if not path:
        return
    obj = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        obj.update(extra)
    atomic_json(path, obj)

def load_boundaries(manifest_path: Path, csv_path: Path) -> pd.DataFrame:
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    if m.get("status") != "PASS":
        raise RuntimeError("Dukascopy manifest not PASS")
    if m.get("protected_2026_opened") is not False:
        raise RuntimeError("manifest does not prove protected 2026 remained unopened")
    if m.get("boundary_csv_sha256") != sha256(csv_path):
        raise RuntimeError("boundary CSV hash mismatch")

    z = pd.read_csv(csv_path)
    req = {"date_ny", "p_1130_raw", "p_1200_raw", "p_1530_raw", "p_1600_raw"}
    if not req.issubset(z.columns):
        raise RuntimeError(f"boundary CSV missing columns: {req - set(z.columns)}")
    z["date_ts"] = pd.to_datetime(z["date_ny"], utc=True)
    if (z["date_ts"] >= PRE1).any():
        raise RuntimeError("protected 2026 row present")
    for c in ["p_1130_raw", "p_1200_raw", "p_1530_raw", "p_1600_raw"]:
        z[c] = pd.to_numeric(z[c], errors="raise")
        if (z[c] <= 0).any():
            raise RuntimeError(f"nonpositive boundary price: {c}")
    if z["date_ts"].duplicated().any():
        raise RuntimeError("duplicate New York dates in boundary dataset")

    z = z.sort_values("date_ts").reset_index(drop=True)
    z["r5"] = np.log(z["p_1200_raw"] / z["p_1130_raw"])
    z["r13"] = np.log(z["p_1600_raw"] / z["p_1530_raw"])
    z["simple_last_half"] = z["p_1600_raw"] / z["p_1530_raw"] - 1.0
    return z

def hac_reg(x, y) -> dict:
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    n = len(x)
    if n < 3:
        return {"n": n, "alpha": None, "beta": None, "r2": None, "t": None, "p": 1.0, "lag": None}

    X = np.column_stack([np.ones(n), x])
    xtx = X.T @ X
    if abs(float(np.linalg.det(xtx))) < 1e-18:
        return {"n": n, "alpha": None, "beta": None, "r2": None, "t": None, "p": 1.0, "lag": None}

    inv = np.linalg.inv(xtx)
    b = inv @ (X.T @ y)
    u = y - X @ b

    lag = max(1, int(math.floor(4 * (n / 100.0) ** (2 / 9))))
    S = np.zeros((2, 2))
    for t in range(n):
        S += u[t] * u[t] * np.outer(X[t], X[t])

    for L in range(1, min(lag, n - 1) + 1):
        w = 1.0 - L / (lag + 1.0)
        G = np.zeros((2, 2))
        for t in range(L, n):
            G += u[t] * u[t - L] * np.outer(X[t], X[t - L])
        S += w * (G + G.T)

    cov = inv @ S @ inv
    se = math.sqrt(max(float(cov[1, 1]), 0.0))
    tv = float(b[1] / se) if se > 0 else None
    p = float(math.erfc(abs(tv) / math.sqrt(2))) if tv is not None else 1.0

    ssr = float(np.sum(u * u))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ssr / sst if sst > 0 else None

    return {
        "n": int(n),
        "alpha": float(b[0]),
        "beta": float(b[1]),
        "r2": r2,
        "t": tv,
        "p": p,
        "lag": int(lag),
    }

def window(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df[(df["date_ts"] >= start) & (df["date_ts"] < end)].copy()

def trading_metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "n": 0, "gross_mean": None, "gross_net": None,
            "E1_mean": None, "E1_net": None,
            "STRESS_mean": None, "STRESS_net": None,
            "stress_ex_best": None, "concentration": None,
        }
    direction = np.where(df["r5"].to_numpy(float) > 0, 1.0, -1.0)
    gross = direction * df["simple_last_half"].to_numpy(float)
    e1 = gross - COSTS["E1"]
    st = gross - COSTS["STRESS"]

    if len(st) > 1:
        best_i = int(np.argmax(st))
        stress_ex_best = float(np.delete(st, best_i).sum())
    else:
        stress_ex_best = -1.0

    pos = st[st > 0]
    concentration = float(pos.max() / pos.sum()) if len(pos) and pos.sum() > 0 else 1.0

    return {
        "n": int(len(df)),
        "gross_mean": float(gross.mean()),
        "gross_net": float(gross.sum()),
        "E1_mean": float(e1.mean()),
        "E1_net": float(e1.sum()),
        "STRESS_mean": float(st.mean()),
        "STRESS_net": float(st.sum()),
        "stress_ex_best": stress_ex_best,
        "concentration": concentration,
    }

def publish(publisher: str | None, status: str, summary: str, artifacts: list[Path]) -> None:
    if not publisher:
        return
    cmd = [
        "python", publisher,
        "--phase", "r15-xauusd-gld-intraday-momentum-v101",
        "--status", status,
        "--summary", summary,
    ]
    for p in artifacts:
        cmd += ["--artifact", str(p)]
    subprocess.run(cmd, check=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boundary-csv", required=True)
    ap.add_argument("--market-manifest", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prog = Path(args.progress_file) if args.progress_file else None

    hb(prog, 0, 4, "load")
    data = load_boundaries(Path(args.market_manifest), Path(args.boundary_csv))

    hb(prog, 1, 4, "replication_2004_2019")
    repl = window(data, REPL0, REPL1)
    rr = hac_reg(repl["r5"], repl["r13"])
    replication_pass = (
        rr["n"] >= 250
        and rr["beta"] is not None
        and rr["beta"] > 0
        and rr["p"] <= 0.05
    )

    conf = pd.DataFrame()
    cr = {"n": 0, "beta": None, "p": 1.0}
    year_beta = {}
    positive_years = 0
    confirmation_pass = False

    if replication_pass:
        hb(prog, 2, 4, "confirmation_2019_2024")
        conf = window(data, REPL1, CONF1)
        cr = hac_reg(conf["r5"], conf["r13"])

        for year in range(2020, 2025):
            y0 = pd.Timestamp(f"{year}-01-01", tz="UTC")
            y1 = pd.Timestamp(f"{year+1}-01-01", tz="UTC")
            q = window(conf, y0, y1)
            yr = hac_reg(q["r5"], q["r13"])
            year_beta[str(year)] = yr
            if yr["beta"] is not None and yr["beta"] > 0:
                positive_years += 1

        confirmation_pass = (
            cr["n"] >= 500
            and cr["beta"] is not None
            and cr["beta"] > 0
            and cr["p"] <= 0.05
            and positive_years >= 4
        )

    econ = {"n": 0}
    economic_pass = False
    if confirmation_pass:
        hb(prog, 3, 4, "economic_2019_2024")
        econ = trading_metrics(conf)
        economic_pass = (
            econ["E1_mean"] > 0
            and econ["STRESS_mean"] > 0
            and econ["stress_ex_best"] > 0
            and econ["concentration"] <= 0.35
        )

    pre = {"n": 0}
    h1 = {"n": 0}
    h2 = {"n": 0}
    pre_pass = False
    if economic_pass:
        y25 = window(data, CONF1, PRE1)
        pre = trading_metrics(y25)
        h1 = trading_metrics(y25[y25["date_ts"] < pd.Timestamp("2025-07-01", tz="UTC")])
        h2 = trading_metrics(y25[y25["date_ts"] >= pd.Timestamp("2025-07-01", tz="UTC")])
        pre_pass = (
            pre["n"] >= 100
            and pre["E1_mean"] > 0
            and pre["STRESS_mean"] > 0
            and h1["E1_net"] > 0
            and h2["E1_net"] > 0
            and pre["stress_ex_best"] > 0
            and pre["concentration"] <= 0.35
        )

    funnel = {
        "replication_pass": int(replication_pass),
        "confirmation_pass": int(confirmation_pass),
        "economic_pass": int(economic_pass),
        "preoos_survivors": int(pre_pass),
    }

    result = {
        "schema": 1,
        "method": "xauusd_gld_intraday_momentum_dukascopy_near_replication",
        "source_paper_doi": "10.1016/j.resourpol.2020.101830",
        "source_revision": "R15-v1.01",
        "preregistration": "research/autonomous/R15_XAUUSD_GLD_INTRADAY_MOMENTUM_PREREGISTRATION_2026_09_13.md",
        "source_amendment": "research/autonomous/R15_DUKASCOPY_SOURCE_AMENDMENT_2026_09_13.md",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened": False,
        "paper_reference": {
            "asset": "GLD",
            "sample": "2004-11-08/2019-05-30",
            "predictor": "r5",
            "target": "r13",
            "beta": 0.0436,
            "t": 3.03,
            "r2": 0.0049,
            "oos_r2": 0.0026,
        },
        "market_source": "Dukascopy XAUUSD BID M1 boundary opens",
        "replication_window": "2004-11-08/2019-05-30",
        "confirmation_window": "2019-05-31/2024-12-31",
        "preoos_window": "2025",
        "replication": rr,
        "replication_pass": replication_pass,
        "confirmation": cr,
        "confirmation_years": year_beta,
        "positive_confirmation_years_2020_2024": positive_years,
        "confirmation_pass": confirmation_pass,
        "economic": econ,
        "economic_pass": economic_pass,
        "preoos_2025": pre,
        "preoos_h1": h1,
        "preoos_h2": h2,
        "survivor_count": int(pre_pass),
        "funnel": funnel,
    }

    rp = out / "r15_xauusd_gld_intraday_momentum_v101_result.json"
    atomic_json(rp, result)

    diag = out / "r15_xauusd_gld_intraday_momentum_v101_daily.csv"
    data[(data["date_ts"] >= REPL0) & (data["date_ts"] < PRE1)].to_csv(diag, index=False)

    hb(prog, 4, 4, "complete", {"survivors": int(pre_pass), **funnel})
    status = "PASS" if pre_pass else "FAIL"
    summary = (
        f"R15 v1.01 Dukascopy XAUUSD/GLD intraday-momentum near-replication {status}: "
        f"funnel={funnel}; protected 2026 untouched."
    )
    publish(args.publisher, status, summary, [rp, diag])

    print(json.dumps({
        "status": status,
        "funnel": funnel,
        "replication": rr,
        "confirmation": cr,
        "survivors": int(pre_pass),
        "protected_2026_opened": False,
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
