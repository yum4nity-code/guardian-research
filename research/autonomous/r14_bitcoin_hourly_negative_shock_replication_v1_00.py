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

PROTECTED = pd.Timestamp("2026-01-01", tz="UTC")
REPL0 = pd.Timestamp("2017-08-17", tz="UTC")
REPL1 = pd.Timestamp("2021-07-01", tz="UTC")
CONF1 = pd.Timestamp("2025-01-01", tz="UTC")
PRE1 = PROTECTED

FILTERS = [0.005, 0.010, 0.015, 0.025, 0.035, 0.050]
HOLDS = [1, 2, 3, 4, 5, 6, 12, 24]
COSTS = {"E1": 0.001, "STRESS": 0.002}
EXPECTED = {
    "BTCUSDT_spot_5m_2017_2025.csv":
    "75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8"
}

def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def hb(path, completed, total, stage, extra=None):
    if not path:
        return
    payload = {
        "completed": int(completed),
        "total": int(total),
        "stage": stage,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(extra or {})
    atomic_json(path, payload)

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_m5(path):
    path = Path(path)
    if "2026" in path.name:
        raise RuntimeError("protected filename forbidden")
    if path.name not in EXPECTED:
        raise RuntimeError(f"unexpected input file: {path.name}")
    if sha256(path) != EXPECTED[path.name]:
        raise RuntimeError(f"input hash mismatch: {path.name}")
    raw = pd.read_csv(path)
    req = {"time", "open", "high", "low", "close"}
    if not req.issubset(raw.columns):
        raise RuntimeError("missing OHLC")
    d = pd.DataFrame({
        "time": pd.to_datetime(raw["time"], utc=True, errors="coerce", format="mixed"),
        "open": pd.to_numeric(raw["open"], errors="coerce"),
        "high": pd.to_numeric(raw["high"], errors="coerce"),
        "low": pd.to_numeric(raw["low"], errors="coerce"),
        "close": pd.to_numeric(raw["close"], errors="coerce"),
    }).dropna().sort_values("time").reset_index(drop=True)
    if d["time"].duplicated().any():
        raise RuntimeError("duplicate timestamps")
    if (d["time"] >= PROTECTED).any():
        raise RuntimeError("protected 2026 row present")
    return d

def to_h1(m5):
    g = m5.set_index("time").resample("1h", label="left", closed="left")
    ohlc = g.agg({"open":"first", "high":"max", "low":"min", "close":"last"})
    count = g["close"].count()
    out = ohlc.loc[count.eq(12)].dropna().reset_index()
    if out["time"].duplicated().any():
        raise RuntimeError("duplicate H1 timestamps")
    return out

def rules():
    return [{"filter": f, "hold_hours": h} for f in FILTERS for h in HOLDS]

def cid(rule):
    raw = json.dumps(rule, sort_keys=True, separators=(",", ":")).encode()
    return "R14-" + hashlib.sha256(raw).hexdigest()[:12].upper()

def pvalue_normal_approx(values):
    a = np.asarray(values, dtype=float)
    if len(a) < 2:
        return 1.0
    sd = float(a.std(ddof=1))
    mu = float(a.mean())
    if sd <= 0:
        return 0.0 if mu != 0 else 1.0
    z = abs(mu / (sd / math.sqrt(len(a))))
    return float(math.erfc(z / math.sqrt(2)))

def metrics(values):
    a = np.asarray(values, dtype=float)
    n = len(a)
    if n == 0:
        return {"n":0, "mean":None, "std":None, "net_sum":None, "t_stat":None, "p":1.0}
    mean = float(a.mean())
    net = float(a.sum())
    if n < 2:
        std = None
        t_stat = None
    else:
        std = float(a.std(ddof=1))
        t_stat = None if std <= 0 else float(mean / (std / math.sqrt(n)))
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "net_sum": net,
        "t_stat": t_stat,
        "p": pvalue_normal_approx(a),
    }

def bh(ps):
    n = len(ps)
    if not n:
        return []
    order = np.argsort(ps)
    q = np.ones(n, dtype=float)
    prev = 1.0
    for j in range(n - 1, -1, -1):
        i = int(order[j])
        prev = min(prev, float(ps[i]) * n / (j + 1))
        q[i] = prev
    return q.tolist()

def _continuous(index, start, end):
    si = index.get(start)
    ei = index.get(end)
    if si is None or ei is None or ei < si:
        return False
    expected = int((end - start) / pd.Timedelta(hours=1)) + 1
    return ei - si + 1 == expected

def paper_event_returns(h1, threshold, hold, start, end):
    """Paper-style overlapping event returns: close_t -> close_t+h."""
    idx = {t:i for i,t in enumerate(h1["time"])}
    out = []
    for i in range(1, len(h1)):
        t = h1["time"].iloc[i]
        if t < start or t >= end:
            continue
        prev = t - pd.Timedelta(hours=1)
        pi = idx.get(prev)
        if pi is None:
            continue
        ret = math.log(float(h1["close"].iloc[i]) / float(h1["close"].iloc[pi]))
        if not ret < -threshold:
            continue
        xt = t + pd.Timedelta(hours=hold)
        if xt >= end:
            continue
        xi = idx.get(xt)
        if xi is None or not _continuous(idx, t, xt):
            continue
        acr = math.log(float(h1["close"].iloc[xi]) / float(h1["close"].iloc[i]))
        out.append({"decision_time":t, "exit_time":xt, "acr":acr})
    return out

def executable_trades(h1, threshold, hold, start, end):
    """Causal long translation with one-position semantics."""
    idx = {t:i for i,t in enumerate(h1["time"])}
    out = []
    next_free = None
    for i in range(1, len(h1)):
        t = h1["time"].iloc[i]
        if t < start or t >= end:
            continue
        prev = t - pd.Timedelta(hours=1)
        pi = idx.get(prev)
        if pi is None:
            continue
        shock = math.log(float(h1["close"].iloc[i]) / float(h1["close"].iloc[pi]))
        if not shock < -threshold:
            continue
        et = t + pd.Timedelta(hours=1)
        xt = et + pd.Timedelta(hours=hold)
        if et >= end or xt >= end:
            continue
        if next_free is not None and et < next_free:
            continue
        ei = idx.get(et)
        xi = idx.get(xt)
        if ei is None or xi is None:
            continue
        if not _continuous(idx, t, xt):
            continue
        gross = float(h1["open"].iloc[xi] / h1["open"].iloc[ei] - 1.0)
        out.append({
            "decision_time": t,
            "entry_time": et,
            "exit_time": xt,
            "gross": gross,
            "E1": gross - COSTS["E1"],
            "STRESS": gross - COSTS["STRESS"],
        })
        next_free = xt
    return out

def executable_metrics(trades):
    out = {"n":len(trades)}
    for k in ("gross","E1","STRESS"):
        vals = [x[k] for x in trades]
        out[k] = metrics(vals)
    return out

def publish(pub, status, summary, artifacts):
    if not pub:
        return
    cmd = [
        "python", pub,
        "--phase", "r14-bitcoin-hourly-negative-shock-replication",
        "--status", status,
        "--summary", summary,
    ]
    for art in artifacts:
        cmd += ["--artifact", str(art)]
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--progress-file")
    ap.add_argument("--publisher")
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress = Path(args.progress_file) if args.progress_file else None

    src = Path(args.data_dir) / "BTCUSDT_spot_5m_2017_2025.csv"
    R = rules()
    total = len(R)
    if total != 48 or len({cid(r) for r in R}) != 48:
        raise RuntimeError("rule count/identity mismatch")

    hb(progress, 0, total, "load")
    m5 = load_m5(src)
    h1 = to_h1(m5)
    input_hash = sha256(src)

    # Stage 1: near-replication of published negative-shock table.
    rows = []
    ps = []
    cache_repl = {}
    for n, rule in enumerate(R, 1):
        rid = cid(rule)
        ev = paper_event_returns(h1, rule["filter"], rule["hold_hours"], REPL0, REPL1)
        cache_repl[rid] = ev
        m = metrics([x["acr"] for x in ev])
        ps.append(m["p"])
        rows.append({"candidate_id":rid, "rule":rule, "replication":m})
        hb(progress, n, total, "replication_metrics_2017_2021")

    qs = bh(ps)
    replication = []
    for row, q in zip(rows, qs):
        m = row["replication"]
        row["replication_bh_q"] = q
        row["gate_replication_enough_n"] = m["n"] >= 30
        row["gate_replication_positive"] = m["mean"] is not None and m["mean"] > 0
        row["gate_replication_fdr"] = q <= 0.05
        row["replication_pass"] = (
            row["gate_replication_enough_n"]
            and row["gate_replication_positive"]
            and row["gate_replication_fdr"]
        )
        if row["replication_pass"]:
            replication.append(row)

    repl_ids = sorted(x["candidate_id"] for x in replication)
    repl_hash = hashlib.sha256("|".join(repl_ids).encode()).hexdigest()
    hb(progress, total, total, "replication_frozen_before_confirmation",
       {"count":len(repl_ids), "sha256":repl_hash})

    # Stage 2: independent later confirmation.
    conf_temp = []
    conf_ps = []
    for row in replication:
        rule = row["rule"]
        ev = paper_event_returns(h1, rule["filter"], rule["hold_hours"], REPL1, CONF1)
        m = metrics([x["acr"] for x in ev])
        years = {}
        pos_full_years = 0
        for year in (2022, 2023, 2024):
            ys = pd.Timestamp(f"{year}-01-01", tz="UTC")
            ye = pd.Timestamp(f"{year+1}-01-01", tz="UTC")
            yev = [x for x in ev if ys <= x["decision_time"] < ye]
            ym = metrics([x["acr"] for x in yev])
            years[str(year)] = ym
            if ym["net_sum"] is not None and ym["net_sum"] > 0:
                pos_full_years += 1
        h2_2021 = metrics([
            x["acr"] for x in ev
            if REPL1 <= x["decision_time"] < pd.Timestamp("2022-01-01", tz="UTC")
        ])
        conf_temp.append((row, m, years, h2_2021, pos_full_years))
        conf_ps.append(m["p"])

    conf_qs = bh(conf_ps)
    confirmed = []
    for q, item in zip(conf_qs, conf_temp):
        row, m, years, h2_2021, pos_full_years = item
        z = dict(row)
        z.update({
            "confirmation":m,
            "confirmation_years":years,
            "confirmation_2021_h2":h2_2021,
            "positive_full_confirmation_years":pos_full_years,
            "confirmation_bh_q":q,
            "gate_confirmation_enough_n":m["n"] >= 30,
            "gate_confirmation_positive":m["mean"] is not None and m["mean"] > 0,
            "gate_confirmation_stability":pos_full_years >= 2,
            "gate_confirmation_fdr":q <= 0.05,
        })
        z["confirmation_pass"] = (
            z["gate_confirmation_enough_n"]
            and z["gate_confirmation_positive"]
            and z["gate_confirmation_stability"]
            and z["gate_confirmation_fdr"]
        )
        if z["confirmation_pass"]:
            confirmed.append(z)

    conf_ids = sorted(x["candidate_id"] for x in confirmed)
    conf_hash = hashlib.sha256("|".join(conf_ids).encode()).hexdigest()
    hb(progress, total, total, "confirmation_frozen_before_economic",
       {"count":len(conf_ids), "sha256":conf_hash})

    # Stage 3: causal executable translation and costs.
    economic = []
    for row in confirmed:
        rule = row["rule"]
        trades = executable_trades(h1, rule["filter"], rule["hold_hours"], REPL1, CONF1)
        em = executable_metrics(trades)
        z = dict(row)
        z["economic_confirmation"] = em
        z["economic_pass"] = (
            em["E1"]["mean"] is not None and em["E1"]["mean"] > 0
            and em["STRESS"]["mean"] is not None and em["STRESS"]["mean"] > 0
        )
        if z["economic_pass"]:
            economic.append(z)

    econ_ids = sorted(x["candidate_id"] for x in economic)
    econ_hash = hashlib.sha256("|".join(econ_ids).encode()).hexdigest()
    hb(progress, total, total, "economic_frozen_before_2025",
       {"count":len(econ_ids), "sha256":econ_hash})

    # Stage 4: frozen 2025 pre-OOS.
    survivors = []
    for row in economic:
        rule = row["rule"]
        trades = executable_trades(h1, rule["filter"], rule["hold_hours"], CONF1, PRE1)
        em = executable_metrics(trades)
        h1_trades = [x for x in trades if CONF1 <= x["decision_time"] < pd.Timestamp("2025-07-01", tz="UTC")]
        h2_trades = [x for x in trades if pd.Timestamp("2025-07-01", tz="UTC") <= x["decision_time"] < PRE1]
        h1m = executable_metrics(h1_trades)
        h2m = executable_metrics(h2_trades)

        stress_vals = sorted([x["STRESS"] for x in trades])
        ex_best = sum(stress_vals[:-1]) if len(stress_vals) > 1 else -1.0
        pos = [v for v in stress_vals if v > 0]
        conc = max(pos) / sum(pos) if pos and sum(pos) > 0 else 1.0

        pre_pass = (
            em["n"] >= 10
            and em["E1"]["mean"] is not None and em["E1"]["mean"] > 0
            and em["STRESS"]["mean"] is not None and em["STRESS"]["mean"] > 0
            and h1m["E1"]["net_sum"] is not None and h1m["E1"]["net_sum"] > 0
            and h2m["E1"]["net_sum"] is not None and h2m["E1"]["net_sum"] > 0
            and ex_best > 0
            and conc <= 0.35
        )
        if pre_pass:
            z = dict(row)
            z.update({
                "preoos_2025":em,
                "preoos_h1":h1m,
                "preoos_h2":h2m,
                "stress_ex_best_net_sum":float(ex_best),
                "stress_best_positive_concentration":float(conc),
                "preoos_pass":True,
            })
            survivors.append(z)

    # Auditable funnel.
    funnel = {
        "tested": total,
        "replication_enough_n": sum(int(r["gate_replication_enough_n"]) for r in rows),
        "replication_positive": sum(int(r["gate_replication_positive"]) for r in rows),
        "replication_fdr": sum(int(r["gate_replication_fdr"]) for r in rows),
        "replication_pass": len(replication),
        "confirmation_enough_n": sum(int(item[1]["n"] >= 30) for item in conf_temp),
        "confirmation_positive": sum(int(item[1]["mean"] is not None and item[1]["mean"] > 0) for item in conf_temp),
        "confirmation_stability": sum(int(item[4] >= 2) for item in conf_temp),
        "confirmation_fdr": sum(int(q <= 0.05) for q in conf_qs),
        "confirmation_pass": len(confirmed),
        "economic_pass": len(economic),
        "preoos_survivors": len(survivors),
    }

    diagnostics = []
    for row in rows:
        m = row["replication"]
        diagnostics.append({
            "candidate_id":row["candidate_id"],
            "filter":row["rule"]["filter"],
            "hold_hours":row["rule"]["hold_hours"],
            "n":m["n"],
            "mean_acr":m["mean"],
            "std_acr":m["std"],
            "t_stat":m["t_stat"],
            "p":m["p"],
            "bh_q":row["replication_bh_q"],
            "gate_enough_n":row["gate_replication_enough_n"],
            "gate_positive":row["gate_replication_positive"],
            "gate_fdr":row["gate_replication_fdr"],
            "replication_pass":row["replication_pass"],
        })

    result = {
        "schema":1,
        "method":"bitcoin_hourly_negative_shock_literature_replication",
        "source_paper_doi":"10.1080/15140326.2022.2151253",
        "source_paper_original_window":"2016-03-01/2021-06-30",
        "preregistration":"research/autonomous/R14_BITCOIN_HOURLY_NEGATIVE_SHOCK_REPLICATION_PREREGISTRATION_2026_09_13.md",
        "source_revision":"R14-v1.00",
        "replication_window":"2017-08-17/2021-06-30",
        "confirmation_window":"2021-07-01/2024-12-31",
        "preoos_window":"2025",
        "architecture":"published_replication_then_independent_confirmation_then_economic_then_preoos",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "protected_2026_opened":False,
        "definitions_tested":total,
        "input_sha256":{src.name:input_hash},
        "replication_candidate_count":len(replication),
        "replication_frozen_ids_sha256":repl_hash,
        "confirmation_candidate_count":len(confirmed),
        "confirmation_frozen_ids_sha256":conf_hash,
        "economic_candidate_count":len(economic),
        "economic_frozen_ids_sha256":econ_hash,
        "survivor_count":len(survivors),
        "funnel":funnel,
        "survivors":survivors,
    }

    rp = out / "r14_bitcoin_hourly_negative_shock_replication_result.json"
    cp = out / "r14_bitcoin_hourly_negative_shock_replication_survivors.csv"
    dp = out / "r14_bitcoin_hourly_negative_shock_replication_diagnostics.csv"

    atomic_json(rp, result)
    pd.json_normalize(survivors).to_csv(cp, index=False)
    pd.DataFrame(diagnostics).to_csv(dp, index=False)

    hb(progress, total, total, "complete", {
        "tested":total,
        "replication_candidates":len(replication),
        "confirmation_candidates":len(confirmed),
        "economic_candidates":len(economic),
        "pre_oos_survivors":len(survivors),
        "survivors":len(survivors),
    })

    status = "PASS" if survivors else "FAIL"
    summary = (
        f"R14 Bitcoin negative-shock literature replication {status}: "
        f"replication={len(replication)}, confirmation={len(confirmed)}, "
        f"economic={len(economic)}, pre-OOS survivors={len(survivors)}; "
        f"protected 2026 untouched."
    )
    publish(args.publisher, status, summary, [rp, cp, dp])
    print(json.dumps({
        "status":status,
        "funnel":funnel,
        "survivors":len(survivors),
        "protected_2026_opened":False,
    }))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
