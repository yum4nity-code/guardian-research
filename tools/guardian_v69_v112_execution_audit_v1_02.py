import sys, json, math, traceback, warnings
from pathlib import Path
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

warnings.filterwarnings("ignore", category=UserWarning, message=r"Converting to PeriodArray.*")

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

UTC = timezone.utc
CAP = datetime(2026, 1, 1, tzinfo=UTC)
OOS0 = datetime(2023, 1, 1, tzinfo=UTC)
START = datetime(2018, 1, 1, tzinfo=UTC)

EXPECTED = {
    "V69": {"n": 155, "mean_bp": 4.639075481195655},
    "V112": {"n": 556, "mean_bp": 1.4552352492311669},
}

def guard(dt):
    if dt >= CAP:
        raise RuntimeError(f"2026 protection triggered: {dt.isoformat()}")

def resolve(base):
    if mt5.symbol_info(base):
        mt5.symbol_select(base, True)
        return base
    cands = []
    for s in (mt5.symbols_get() or []):
        u = s.name.upper()
        b = base.upper()
        if u == b:
            cands.append((0, len(s.name), s.name))
        elif u.startswith(b):
            cands.append((1, len(s.name), s.name))
        elif b in u:
            cands.append((2, len(s.name), s.name))
    if not cands:
        raise RuntimeError(f"Broker symbol not found: {base}")
    cands.sort()
    mt5.symbol_select(cands[0][2], True)
    return cands[0][2]

def rates(symbol, tf, start, end):
    guard(start)
    end = min(end, CAP - timedelta(seconds=1))
    a = mt5.copy_rates_range(symbol, tf, start, end)
    if a is None or len(a) == 0:
        return pd.DataFrame()
    d = pd.DataFrame(a)
    d["time"] = pd.to_datetime(d["time"], unit="s", utc=True)
    return d.sort_values("time").drop_duplicates("time").reset_index(drop=True)

def ticks(symbol, start, end):
    guard(start)
    end = min(end, CAP - timedelta(milliseconds=1))
    a = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    if a is None or len(a) == 0:
        return pd.DataFrame()
    d = pd.DataFrame(a)
    d["time"] = pd.to_datetime(d["time_msc"], unit="ms", utc=True)
    if {"bid", "ask"} <= set(d.columns):
        d = d[(d.bid > 0) & (d.ask > 0)]
    return d.sort_values("time").reset_index(drop=True)

def first_tick(symbol, when, fb_bid, fb_spread_pts, point):
    t = ticks(symbol, when, when + timedelta(seconds=90))
    if not t.empty:
        r = t.iloc[0]
        return r["time"], float(r.bid), float(r.ask), "tick"
    spr = float(fb_spread_pts or 0) * point
    return pd.Timestamp(when), float(fb_bid), float(fb_bid + spr), "m1_fallback"

def last_tick_min(symbol, when, fb_bid, fb_spread_pts, point):
    t = ticks(symbol, when, when + timedelta(seconds=59, milliseconds=999))
    if not t.empty:
        r = t.iloc[-1]
        return r["time"], float(r.bid), float(r.ask), "tick"
    spr = float(fb_spread_pts or 0) * point
    return pd.Timestamp(when + timedelta(seconds=59)), float(fb_bid), float(fb_bid + spr), "m1_fallback"

def trim_best(x, pct):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    if len(x) == 0:
        return np.nan
    k = int(math.ceil(len(x) * pct))
    return float(np.mean(np.sort(x)[:-k])) if 0 < k < len(x) else float(np.mean(x))

def remove_best(x, n):
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    return float(np.mean(np.sort(x)[:-n])) if len(x) > n else np.nan

def max_dd(x):
    x = np.asarray(pd.Series(x).fillna(0), dtype=float)
    eq = np.r_[0.0, np.cumsum(x)]
    peak = np.maximum.accumulate(eq)
    return float(np.min(eq - peak))

def stat(df, col):
    if df.empty or col not in df:
        return {}
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    if s.empty:
        return {}
    tmp = df.loc[s.index, ["entry_time"]].copy()
    tmp["r"] = s
    tmp["year"] = pd.to_datetime(tmp.entry_time, utc=True).dt.year
    years = {
        str(int(y)): {
            "n": int(len(g)),
            "mean_bp": float(g.r.mean()),
            "win_rate": float((g.r > 0).mean()),
        }
        for y, g in tmp.groupby("year")
    }
    return {
        "n": int(len(s)),
        "mean_bp": float(s.mean()),
        "median_bp": float(s.median()),
        "win_rate": float((s > 0).mean()),
        "trim1_bp": trim_best(s, .01),
        "trim2_bp": trim_best(s, .02),
        "remove_best5_bp": remove_best(s, 5),
        "max_drawdown_cumsum_bp": max_dd(s),
        "worst_bp": float(s.min()),
        "best_bp": float(s.max()),
        "years": years,
    }

def bootstrap_month_q025(df, col, reps=5000, seed=69112):
    if df.empty:
        return np.nan
    d = df[["entry_time", col]].dropna().copy()
    d["month"] = pd.to_datetime(d.entry_time, utc=True).dt.to_period("M").astype(str)
    groups = [g[col].to_numpy(float) for _, g in d.groupby("month") if len(g)]
    if len(groups) < 2:
        return np.nan
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(reps):
        sample = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        vals.append(sample.mean())
    return float(np.quantile(vals, .025))

def cost_grid(df, col, name):
    rows = []
    if df.empty:
        return pd.DataFrame(rows)
    x = pd.to_numeric(df[col], errors="coerce").dropna().to_numpy(float)
    for c in [0,.25,.5,.75,1,1.5,2,3,4,5]:
        r = x - c
        rows.append({
            "strategy": name,
            "extra_cost_bp_after_spread": c,
            "n": len(r),
            "mean_net_bp": float(r.mean()) if len(r) else np.nan,
            "win_rate": float((r > 0).mean()) if len(r) else np.nan,
            "max_drawdown_cumsum_bp": max_dd(r),
        })
    return pd.DataFrame(rows)

def metadata(symbol):
    i = mt5.symbol_info(symbol)
    t = mt5.symbol_info_tick(symbol)
    if not i:
        return {}
    keys = ["name","digits","point","spread","spread_float","trade_contract_size",
            "trade_tick_size","trade_tick_value","swap_mode","swap_long","swap_short",
            "swap_rollover3days","currency_base","currency_profit"]
    o = {k: getattr(i, k) for k in keys if hasattr(i, k)}
    if t:
        o["current_bid"] = float(t.bid)
        o["current_ask"] = float(t.ask)
    return o

def audit_v69(symbol):
    info = mt5.symbol_info(symbol)
    point = float(info.point)
    d1 = rates(symbol, mt5.TIMEFRAME_D1, START, CAP - timedelta(seconds=1))
    if d1.empty:
        raise RuntimeError("No USDCHF D1 history")

    gross = []
    for i in range(len(d1)-1):
        a, b = d1.iloc[i], d1.iloc[i+1]
        if a.time.weekday() != 4:
            continue
        gross.append({
            "entry_time": a.time,
            "exit_time": b.time,
            "gross_bp": (float(b.close)/float(a.close)-1)*10000,
            "entry_close": float(a.close),
            "exit_close": float(b.close),
            "next_open": float(b.open),
            "weekend_gap_bp": (float(b.open)/float(a.close)-1)*10000,
        })
    gross = pd.DataFrame(gross)
    gross.to_csv(OUT/"V69_GROSS_RECONSTRUCTION_2018_2025.csv", index=False)

    rows = []
    for i in range(len(d1)-2):
        fri, mon, tue = d1.iloc[i], d1.iloc[i+1], d1.iloc[i+2]
        if fri.time.weekday() != 4 or not (pd.Timestamp(OOS0) <= fri.time < pd.Timestamp(CAP)):
            continue
        if tue.time >= pd.Timestamp(CAP):
            continue

        fm = rates(symbol, mt5.TIMEFRAME_M1, fri.time.to_pydatetime(),
                   mon.time.to_pydatetime()-timedelta(seconds=1))
        mm = rates(symbol, mt5.TIMEFRAME_M1, mon.time.to_pydatetime(),
                   tue.time.to_pydatetime()-timedelta(seconds=1))
        if fm.empty or mm.empty:
            continue

        eb, xb = fm.iloc[-1], mm.iloc[-1]
        et, ebid, eask, esrc = last_tick_min(
            symbol, eb.time.to_pydatetime(), float(eb.close), float(eb.get("spread",0)), point)
        xt, xbid, xask, xsrc = last_tick_min(
            symbol, xb.time.to_pydatetime(), float(xb.close), float(xb.get("spread",0)), point)

        bidret = (xbid/ebid-1)*10000
        execret = (xbid/eask-1)*10000
        lows = pd.to_numeric(mm.low, errors="coerce").dropna()
        highs = pd.to_numeric(mm.high, errors="coerce").dropna()

        rows.append({
            "entry_time": et, "exit_time": xt,
            "entry_source": esrc, "exit_source": xsrc,
            "entry_bid": ebid, "entry_ask": eask,
            "exit_bid": xbid, "exit_ask": xask,
            "entry_spread_bp": (eask-ebid)/ebid*10000,
            "exit_spread_bp": (xask-xbid)/xbid*10000,
            "gross_d1_bp": (float(mon.close)/float(fri.close)-1)*10000,
            "bid_tick_to_bid_tick_bp": bidret,
            "executable_ask_to_bid_bp": execret,
            "spread_drag_bp": bidret-execret,
            "weekend_gap_bp": (float(mon.open)/float(fri.close)-1)*10000,
            "mae_bp": (float(lows.min())/eask-1)*10000 if len(lows) else np.nan,
            "mfe_bp": (float(highs.max())/eask-1)*10000 if len(highs) else np.nan,
        })

    det = pd.DataFrame(rows)
    det.to_csv(OUT/"V69_OOS_EXECUTION_LEDGER.csv", index=False)

    go = gross[(pd.to_datetime(gross.entry_time, utc=True) >= pd.Timestamp(OOS0)) &
               (pd.to_datetime(gross.entry_time, utc=True) < pd.Timestamp(CAP))]
    recon_mean = float(go.gross_bp.mean()) if len(go) else np.nan
    parity = {
        "expected_n": EXPECTED["V69"]["n"],
        "reconstructed_n": int(len(go)),
        "expected_mean_bp": EXPECTED["V69"]["mean_bp"],
        "reconstructed_mean_bp": recon_mean,
        "n_match": int(len(go)) == EXPECTED["V69"]["n"],
        "mean_abs_diff_bp": abs(recon_mean-EXPECTED["V69"]["mean_bp"]) if np.isfinite(recon_mean) else None,
    }
    parity["pass"] = bool(parity["n_match"] and parity["mean_abs_diff_bp"] <= .25)

    cost_grid(det, "executable_ask_to_bid_bp", "V69_USDCHF_FRIDAY_LONG").to_csv(
        OUT/"V69_EXTRA_COST_GRID.csv", index=False)

    return {
        "symbol": symbol,
        "gross_oos": stat(go, "gross_bp"),
        "execution_oos": stat(det, "executable_ask_to_bid_bp"),
        "bootstrap_month_q025_exec_bp": bootstrap_month_q025(det, "executable_ask_to_bid_bp"),
        "parity": parity,
        "symbol_metadata_now": metadata(symbol),
        "note": "Execution return includes observed tick spread when available, M1 spread fallback otherwise. Historical swap and slippage are stressed separately via cost grid."
    }

def audit_v112(symbol):
    info = mt5.symbol_info(symbol)
    point = float(info.point)
    rows = []
    day = OOS0

    # C3 H21 is an hour-only calendar effect whose pre-OOS N (1029 for 2018-2022)
    # is consistent with Mon-Thu sessions. Friday is excluded.
    while day < CAP:
        if day.weekday() < 4:
            ent = datetime(day.year, day.month, day.day, 21, 0, tzinfo=UTC)
            ext = ent + timedelta(minutes=120)
            m1 = rates(symbol, mt5.TIMEFRAME_M1, ent, ext + timedelta(minutes=2))
            if not m1.empty:
                ew = m1[(m1.time >= pd.Timestamp(ent)) & (m1.time <= pd.Timestamp(ent+timedelta(minutes=2)))]
                xw = m1[(m1.time >= pd.Timestamp(ext)) & (m1.time <= pd.Timestamp(ext+timedelta(minutes=2)))]
                if not ew.empty and not xw.empty:
                    eb, xb = ew.iloc[0], xw.iloc[0]
                    if (eb.time-pd.Timestamp(ent)).total_seconds() <= 120 and (xb.time-pd.Timestamp(ext)).total_seconds() <= 120:
                        et, ebid, eask, esrc = first_tick(symbol, ent, float(eb.open), float(eb.get("spread",0)), point)
                        xt, xbid, xask, xsrc = first_tick(symbol, ext, float(xb.open), float(xb.get("spread",0)), point)
                        gross = -((float(xb.open)/float(eb.open))-1)*10000
                        bidret = -((xbid/ebid)-1)*10000
                        execret = (ebid-xask)/ebid*10000
                        intr = m1[(m1.time >= pd.Timestamp(ent)) & (m1.time < pd.Timestamp(ext))]
                        lows = pd.to_numeric(intr.low, errors="coerce").dropna()
                        highs = pd.to_numeric(intr.high, errors="coerce").dropna()
                        rows.append({
                            "entry_time": et, "exit_time": xt,
                            "entry_source": esrc, "exit_source": xsrc,
                            "entry_bid": ebid, "entry_ask": eask,
                            "exit_bid": xbid, "exit_ask": xask,
                            "entry_spread_bp": (eask-ebid)/ebid*10000,
                            "exit_spread_bp": (xask-xbid)/xbid*10000,
                            "gross_bid_open_to_open_bp": gross,
                            "tick_bid_to_bid_bp": bidret,
                            "executable_bid_to_ask_bp": execret,
                            "spread_drag_bp": bidret-execret,
                            "mae_bp": (ebid-float(highs.max()))/ebid*10000 if len(highs) else np.nan,
                            "mfe_bp": (ebid-float(lows.min()))/ebid*10000 if len(lows) else np.nan,
                        })
        day += timedelta(days=1)

    det = pd.DataFrame(rows)
    det.to_csv(OUT/"V112_OOS_EXECUTION_LEDGER.csv", index=False)

    recon_mean = float(det.gross_bid_open_to_open_bp.mean()) if len(det) else np.nan
    parity = {
        "expected_n": EXPECTED["V112"]["n"],
        "reconstructed_n": int(len(det)),
        "expected_mean_bp": EXPECTED["V112"]["mean_bp"],
        "reconstructed_mean_bp": recon_mean,
        "n_abs_diff": abs(int(len(det))-EXPECTED["V112"]["n"]),
        "mean_abs_diff_bp": abs(recon_mean-EXPECTED["V112"]["mean_bp"]) if np.isfinite(recon_mean) else None,
    }
    parity["pass"] = bool(parity["n_abs_diff"] <= 5 and parity["mean_abs_diff_bp"] <= .25)

    cost_grid(det, "executable_bid_to_ask_bp", "V112_AUDUSD_H21_SHORT_120M").to_csv(
        OUT/"V112_EXTRA_COST_GRID.csv", index=False)

    return {
        "symbol": symbol,
        "gross_oos": stat(det, "gross_bid_open_to_open_bp"),
        "execution_oos": stat(det, "executable_bid_to_ask_bp"),
        "bootstrap_month_q025_exec_bp": bootstrap_month_q025(det, "executable_bid_to_ask_bp"),
        "parity": parity,
        "symbol_metadata_now": metadata(symbol),
        "note": "C3 H21 reconstructed Mon-Thu only. Execution return includes observed spread; additional swap/slippage stress is in cost grid."
    }

def main():
    if not mt5.initialize():
        raise RuntimeError("MT5 initialization failed. Open MT5, log into the broker account, then rerun. " + str(mt5.last_error()))
    try:
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None:
            raise RuntimeError("MT5 is open but no account information is available.")
        broker_identity = " ".join(str(x or "") for x in [
            getattr(account, "server", ""),
            getattr(account, "company", ""),
            getattr(account, "name", "")
        ]).strip()
        if "ftmo" not in broker_identity.lower():
            raise RuntimeError(
                "FTMO GUARD FAILED: Python connected to a non-FTMO MT5/account. "
                f"Detected: {broker_identity!r}. Close other MT5 terminals and keep only FTMO open."
            )
        usdchf = resolve("USDCHF")
        audusd = resolve("AUDUSD")
        result = {
            "mt5_account_server": getattr(account, "server", None),
            "mt5_account_company": getattr(account, "company", None),
            "mt5_account_name": getattr(account, "name", None),
            "mt5_terminal_path": getattr(terminal, "path", None) if terminal else None,
            "run_started_utc": datetime.now(UTC).isoformat(),
            "data_cap": "2025-12-31T23:59:59Z",
            "protected_2026_accessed": False,
            "V69": audit_v69(usdchf),
            "V112": audit_v112(audusd),
        }
        result["run_finished_utc"] = datetime.now(UTC).isoformat()
        (OUT/"SUMMARY.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

        compact = []
        for k in ["V69","V112"]:
            s = result[k]["execution_oos"]
            p = result[k]["parity"]
            compact.append({
                "strategy": k,
                "symbol": result[k]["symbol"],
                "parity_pass": p["pass"],
                "n_exec": s.get("n"),
                "mean_exec_bp_after_spread": s.get("mean_bp"),
                "median_exec_bp_after_spread": s.get("median_bp"),
                "win_rate": s.get("win_rate"),
                "trim2_exec_bp": s.get("trim2_bp"),
                "remove_best5_exec_bp": s.get("remove_best5_bp"),
                "max_drawdown_cumsum_bp": s.get("max_drawdown_cumsum_bp"),
                "bootstrap_month_q025_exec_bp": result[k]["bootstrap_month_q025_exec_bp"],
            })
        pd.DataFrame(compact).to_csv(OUT/"RESULTS_COMPACT.csv", index=False)
        (OUT/"SUCCESS.flag").write_text("OK\n2026_ACCESS=false\n", encoding="utf-8")

        print("=== COMPLETE ===")
        print(f"Results: {OUT}")
        print("2026 accessed: FALSE")
        for k in ["V69","V112"]:
            print(k, result[k]["parity"], result[k]["execution_oos"])
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        (OUT/"FAILED.txt").write_text(str(e)+"\n\n"+traceback.format_exc(), encoding="utf-8")
        print("=== FAILED ===")
        print(e)
        sys.exit(1)
