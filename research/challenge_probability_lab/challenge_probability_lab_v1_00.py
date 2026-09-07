#!/usr/bin/env python3
"""Guardian Challenge Probability Lab v1.00 — stdlib-only Monte Carlo pass simulator."""
from __future__ import annotations

import argparse, csv, hashlib, json, math, random
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Sequence

VERSION = "1.00"
DEFAULT_RISKS = (0.10, 0.15, 0.20, 0.25, 0.33, 0.50)
R_ALIASES = ("net_r", "r_net", "netR", "net_r_baseline", "realized_r", "r")
TIME_ALIASES = ("entry_time", "signal_time", "time", "timestamp", "exit_time")


@dataclass(frozen=True)
class Trade:
    timestamp: datetime
    block_day: date
    exit_timestamp: Optional[datetime]
    r: float
    adverse_r: Optional[float]
    source: str
    row_number: int


@dataclass(frozen=True)
class DayBlock:
    day: date
    trades: tuple[Trade, ...]


@dataclass(frozen=True)
class LabConfig:
    initial_balance: float
    profit_target_pct: float
    daily_loss_pct: float
    max_loss_pct: float
    max_days: int
    block_days: int
    risk_basis: str
    max_loss_anchor: str
    dense_calendar: bool


@dataclass(frozen=True)
class PathResult:
    passed: bool
    daily_breach: bool
    max_breach: bool
    same_event_both: bool
    timeout: bool
    days_elapsed: int
    trades_elapsed: int
    max_drawdown_pct_initial: float
    end_balance: float


def parse_dt(value: str) -> datetime:
    s = (value or "").strip()
    if not s:
        raise ValueError("empty timestamp")
    if len(s) == 8 and s.isdigit():
        return datetime.strptime(s, "%Y%m%d")
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y.%m.%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.replace(tzinfo=None)  # Preserve exported wall-clock day; no hidden timezone conversion.
    except ValueError as exc:
        raise ValueError(f"unsupported timestamp format {value!r}") from exc


def finite(value: str, *, field: str, path: Path, row: int) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path}:{row}: invalid {field}={value!r}") from exc
    if not math.isfinite(x):
        raise ValueError(f"{path}:{row}: non-finite {field}={value!r}")
    return x


def sniff(sample: str) -> str:
    first = sample.splitlines()[0] if sample.splitlines() else sample
    return max((",", ";", "\t"), key=first.count)


def pick_column(fields: Sequence[str], requested: Optional[str], aliases: Sequence[str], label: str) -> str:
    if requested:
        if requested not in fields:
            raise ValueError(f"{label} column {requested!r} absent; columns={list(fields)!r}")
        return requested
    for name in aliases:
        if name in fields:
            return name
    raise ValueError(f"cannot auto-detect {label} column; columns={list(fields)!r}")


def load_trades(paths: Sequence[str], *, r_column=None, time_column=None, day_column=None,
                adverse_r_column=None, stage=None) -> tuple[list[Trade], dict]:
    trades: list[Trade] = []
    meta = {"files": [], "r_columns": {}, "time_columns": {}, "day_column": day_column,
            "adverse_r_column": adverse_r_column}
    for p0 in paths:
        path = Path(p0)
        raw = path.read_text(encoding="utf-8-sig")
        delim = sniff(raw[:8192])
        reader = csv.DictReader(raw.splitlines(), delimiter=delim)
        fields = list(reader.fieldnames or [])
        if not fields:
            raise ValueError(f"{path}: missing CSV header")
        rc = pick_column(fields, r_column, R_ALIASES, "R")
        tc = pick_column(fields, time_column, TIME_ALIASES, "time")
        if day_column and day_column not in fields:
            raise ValueError(f"{path}: day column {day_column!r} absent")
        if adverse_r_column and adverse_r_column not in fields:
            raise ValueError(f"{path}: adverse-R column {adverse_r_column!r} absent")
        used = 0
        for rowno, row in enumerate(reader, 2):
            if not any((v or "").strip() for v in row.values() if v is not None):
                continue
            if stage is not None:
                if "run_stage" not in fields:
                    raise ValueError(f"{path}: --stage requires run_stage")
                if row.get("run_stage") != stage:
                    continue
            ts = parse_dt(row.get(tc, ""))
            block_day = parse_dt(row.get(day_column, "")).date() if day_column else ts.date()
            r = finite(row.get(rc, ""), field=rc, path=path, row=rowno)
            adverse = None
            if adverse_r_column and (row.get(adverse_r_column) or "").strip():
                adverse = finite(row[adverse_r_column], field=adverse_r_column, path=path, row=rowno)
                if adverse > 1e-12:
                    raise ValueError(f"{path}:{rowno}: adverse R must be signed <= 0")
            exit_ts = parse_dt(row["exit_time"]) if "exit_time" in fields and (row.get("exit_time") or "").strip() else None
            trades.append(Trade(ts, block_day, exit_ts, r, adverse, str(path), rowno))
            used += 1
        meta["files"].append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "rows_used": used, "delimiter": delim})
        meta["r_columns"][str(path)] = rc
        meta["time_columns"][str(path)] = tc
    if not trades:
        raise ValueError("no trade rows loaded")
    trades.sort(key=lambda t: (t.block_day, t.timestamp, t.source, t.row_number))
    meta.update({
        "trade_count": len(trades),
        "cross_day_trade_count": sum(1 for t in trades if t.exit_timestamp and t.exit_timestamp.date() != t.timestamp.date()),
        "first_timestamp": trades[0].timestamp.isoformat(),
        "last_timestamp": trades[-1].timestamp.isoformat(),
    })
    return trades, meta


def build_day_blocks(trades: Sequence[Trade], *, dense_calendar: bool) -> list[DayBlock]:
    by: dict[date, list[Trade]] = {}
    for t in trades:
        by.setdefault(t.block_day, []).append(t)
    if not by:
        raise ValueError("zero days")
    dates = []
    if dense_calendar:
        d, end = min(by), max(by)
        while d <= end:
            dates.append(d); d += timedelta(days=1)
    else:
        dates = sorted(by)
    return [DayBlock(d, tuple(sorted(by.get(d, ()), key=lambda t: (t.timestamp, t.source, t.row_number)))) for d in dates]


def path_seed(seed: int, index: int) -> int:
    return int.from_bytes(hashlib.blake2b(f"{seed}:{index}".encode(), digest_size=8).digest(), "big")


def simulate_one(days: Sequence[DayBlock], cfg: LabConfig, *, risk_pct: float, seed: int,
                 use_adverse_r: bool) -> PathResult:
    rng = random.Random(seed); n = len(days); initial = cfg.initial_balance
    balance = running_peak = peak_eod = initial
    target = initial * (1 + cfg.profit_target_pct / 100)
    static_floor = initial * (1 - cfg.max_loss_pct / 100)
    max_dd = 0.0; trades_n = 0; eps = max(1e-9, initial * 1e-12)
    block: list[DayBlock] = []; pos = 0
    for day_n in range(1, cfg.max_days + 1):
        if pos >= len(block):
            start = rng.randrange(n)
            block = [days[(start + j) % n] for j in range(cfg.block_days)]
            pos = 0
        sample = block[pos]; pos += 1
        day_start = balance
        daily_floor = day_start - initial * cfg.daily_loss_pct / 100
        max_floor = peak_eod - initial * cfg.max_loss_pct / 100 if cfg.max_loss_anchor == "trailing_eod" else static_floor
        for t in sample.trades:
            risk_base = initial if cfg.risk_basis == "initial" else balance
            risk_amount = max(0.0, risk_base * risk_pct / 100)
            if use_adverse_r and t.adverse_r is not None:
                adverse_eq = balance + risk_amount * t.adverse_r
                max_dd = max(max_dd, (running_peak - adverse_eq) / initial * 100)
                dh, mh = adverse_eq <= daily_floor + eps, adverse_eq <= max_floor + eps
                if dh or mh:
                    return PathResult(False, dh, mh, dh and mh, False, day_n, trades_n + 1, max_dd, adverse_eq)
            balance += risk_amount * t.r; trades_n += 1
            running_peak = max(running_peak, balance)
            max_dd = max(max_dd, (running_peak - balance) / initial * 100)
            dh, mh = balance <= daily_floor + eps, balance <= max_floor + eps
            if dh or mh:
                return PathResult(False, dh, mh, dh and mh, False, day_n, trades_n, max_dd, balance)
            if balance >= target - eps:
                return PathResult(True, False, False, False, False, day_n, trades_n, max_dd, balance)
        peak_eod = max(peak_eod, balance)
    return PathResult(False, False, False, False, True, cfg.max_days, trades_n, max_dd, balance)


def quantile(values: Sequence[float], q: float) -> Optional[float]:
    if not values: return None
    xs = sorted(values); p = (len(xs) - 1) * q; lo, hi = math.floor(p), math.ceil(p)
    return float(xs[lo] if lo == hi else xs[lo] * (hi - p) + xs[hi] * (p - lo))


def prob(k: int, n: int) -> dict:
    p = k / n if n else 0.0; z = 1.959963984540054; zz = z*z
    if not n: return {"count": 0, "probability": 0.0, "ci95_wilson": [0.0, 0.0]}
    den = 1 + zz/n; center = (p + zz/(2*n))/den
    half = z * math.sqrt((p*(1-p) + zz/(4*n))/n) / den
    return {"count": k, "probability": p, "ci95_wilson": [max(0.0, center-half), min(1.0, center+half)]}


def summarize(risk: float, rows: Sequence[PathResult]) -> dict:
    n = len(rows); passed = [x for x in rows if x.passed]; dds = [x.max_drawdown_pct_initial for x in rows]
    count = lambda f: sum(1 for x in rows if f(x))
    return {
        "risk_pct": risk, "paths": n,
        "pass": prob(len(passed), n),
        "daily_dd_violation": prob(count(lambda x: x.daily_breach), n),
        "max_dd_violation": prob(count(lambda x: x.max_breach), n),
        "same_event_both_limits": prob(count(lambda x: x.same_event_both), n),
        "any_dd_violation": prob(count(lambda x: x.daily_breach or x.max_breach), n),
        "timeout": prob(count(lambda x: x.timeout), n),
        "pass_duration_days": {k: quantile([x.days_elapsed for x in passed], q) for k,q in (("median",.5),("p25",.25),("p75",.75),("p90",.9))},
        "trades_to_pass": {k: quantile([x.trades_elapsed for x in passed], q) for k,q in (("median",.5),("p90",.9))},
        "max_drawdown_pct_initial": {"median_typical": quantile(dds,.5), "p90": quantile(dds,.9),
                                      "p95_bad": quantile(dds,.95), "p99": quantile(dds,.99),
                                      "worst_observed": max(dds) if dds else None},
    }


def run_lab(days: Sequence[DayBlock], cfg: LabConfig, *, risks: Sequence[float], paths: int,
            seed: int, use_adverse_r: bool) -> dict:
    if paths < 100: raise ValueError("paths must be >= 100")
    if not days: raise ValueError("no day blocks")
    if not 1 <= cfg.block_days <= len(days): raise ValueError(f"block_days must be 1..{len(days)}")
    if cfg.initial_balance <= 0 or cfg.max_days < 1: raise ValueError("invalid balance/max_days")
    if min(cfg.profit_target_pct, cfg.daily_loss_pct, cfg.max_loss_pct) <= 0: raise ValueError("target/loss percentages must be positive")
    if cfg.risk_basis not in {"initial","current"}: raise ValueError("risk_basis must be initial/current")
    if cfg.max_loss_anchor not in {"initial","trailing_eod"}: raise ValueError("max_loss_anchor must be initial/trailing_eod")
    rr = [float(x) for x in risks]
    if any(not math.isfinite(x) or x <= 0 for x in rr): raise ValueError("risks must be positive finite percentages")
    bucket = {r: [] for r in rr}
    for i in range(paths):
        common = path_seed(seed, i)  # common random day path across risks
        for r in rr: bucket[r].append(simulate_one(days, cfg, risk_pct=r, seed=common, use_adverse_r=use_adverse_r))
    results = [summarize(r, bucket[r]) for r in rr]
    best = max(results, key=lambda s: (s["pass"]["probability"], -s["any_dd_violation"]["probability"],
                                       -(s["max_drawdown_pct_initial"]["p95_bad"] or 0), -s["risk_pct"]))
    return {
        "lab": "GUARDIAN_CHALLENGE_PROBABILITY_LAB", "version": VERSION,
        "objective": "maximize probability of reaching challenge target before a drawdown rule breach",
        "selection_rule": "highest pass probability; ties prefer lower DD violation, lower p95 drawdown, then lower risk",
        "seed": seed, "paths_per_risk": paths, "risk_levels_pct": rr, "config": asdict(cfg),
        "bootstrap": {"method": "circular_moving_block_calendar_days", "block_days": cfg.block_days,
                      "historical_day_count": len(days), "historical_trade_count": sum(len(d.trades) for d in days),
                      "common_random_numbers_across_risk_levels": True},
        "equity_model": {"atomic_trade_outcomes": True,
                         "daily_anchor": "simulated start-of-day balance; daily limit amount is % of initial balance",
                         "intratrade_adverse_excursion_used": use_adverse_r},
        "results": results, "optimal_risk_for_pass_pct": best["risk_pct"],
        "optimal_risk_pass_probability": best["pass"]["probability"],
    }


def pct(x): return "NA" if x is None else f"{100*x:.2f}%"
def num(x, n=2): return "NA" if x is None else f"{x:.{n}f}"


def render_markdown(rep: dict) -> str:
    c=rep["config"]
    out=[f"# Guardian Challenge Probability Lab v{rep['version']}","",f"**Objective:** {rep['objective']}.","",
         f"Paths/risk: **{rep['paths_per_risk']}** · block: **{c['block_days']} calendar days** · seed: `{rep['seed']}`.",
         f"Target **{c['profit_target_pct']:.2f}%** · daily loss **{c['daily_loss_pct']:.2f}%** · max loss **{c['max_loss_pct']:.2f}%** · horizon **{c['max_days']} days**.","",
         "| Risk/trade | Pass | Daily DD | Max DD | Timeout | Median days | Median DD | P95 DD |",
         "|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s in rep["results"]:
        out.append(f"| {s['risk_pct']:.2f}% | {pct(s['pass']['probability'])} | {pct(s['daily_dd_violation']['probability'])} | {pct(s['max_dd_violation']['probability'])} | {pct(s['timeout']['probability'])} | {num(s['pass_duration_days']['median'],1)} | {num(s['max_drawdown_pct_initial']['median_typical'])}% | {num(s['max_drawdown_pct_initial']['p95_bad'])}% |")
    out += ["",f"## Risk selected for passing: **{rep['optimal_risk_for_pass_pct']:.2f}% per trade**","",
            f"Estimated pass probability: **{pct(rep['optimal_risk_pass_probability'])}**.","","## Interpretation boundary",""]
    if rep["equity_model"]["intratrade_adverse_excursion_used"]:
        out += ["- Supplied signed adverse-R is checked intratrade.",
                "- Concurrent adverse excursions still require synchronized portfolio mark-to-market data."]
    else:
        out += ["- **DD probabilities are atomic/closed-equity estimates** and can understate floating-equity breaches.",
                "- Exact overlapping/multi-day portfolio DD requires synchronized mark-to-market data."]
    out += ["- Moving calendar-day blocks preserve observed clustering/short regime persistence; trades are not iid-shuffled.",
            "- `max_days` is a truncation horizon; timeout is reported explicitly."]
    return "\n".join(out)+"\n"


def write_csv(rep: dict, path: Path) -> None:
    fields=("risk_pct","pass_probability","pass_ci95_low","pass_ci95_high","daily_dd_violation_probability",
            "max_dd_violation_probability","any_dd_violation_probability","timeout_probability","median_days_to_pass",
            "p90_days_to_pass","median_max_dd_pct_initial","p95_max_dd_pct_initial","p99_max_dd_pct_initial","worst_observed_dd_pct_initial")
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for s in rep["results"]:
            w.writerow({"risk_pct":s["risk_pct"],"pass_probability":s["pass"]["probability"],
                        "pass_ci95_low":s["pass"]["ci95_wilson"][0],"pass_ci95_high":s["pass"]["ci95_wilson"][1],
                        "daily_dd_violation_probability":s["daily_dd_violation"]["probability"],
                        "max_dd_violation_probability":s["max_dd_violation"]["probability"],
                        "any_dd_violation_probability":s["any_dd_violation"]["probability"],"timeout_probability":s["timeout"]["probability"],
                        "median_days_to_pass":s["pass_duration_days"]["median"],"p90_days_to_pass":s["pass_duration_days"]["p90"],
                        "median_max_dd_pct_initial":s["max_drawdown_pct_initial"]["median_typical"],
                        "p95_max_dd_pct_initial":s["max_drawdown_pct_initial"]["p95_bad"],"p99_max_dd_pct_initial":s["max_drawdown_pct_initial"]["p99"],
                        "worst_observed_dd_pct_initial":s["max_drawdown_pct_initial"]["worst_observed"]})


def choose(cli, profile, key, default): return cli if cli is not None else profile.get(key,default)


def main() -> int:
    a=argparse.ArgumentParser(description="Guardian Challenge Probability Lab v1.00")
    a.add_argument("--input",action="append",required=True); a.add_argument("--profile")
    a.add_argument("--r-column"); a.add_argument("--time-column"); a.add_argument("--day-column")
    a.add_argument("--adverse-r-column"); a.add_argument("--stage"); a.add_argument("--risk",action="append",type=float,dest="risks")
    a.add_argument("--paths",type=int,default=10000); a.add_argument("--seed",type=int,default=20260907)
    a.add_argument("--initial-balance",type=float); a.add_argument("--profit-target-pct",type=float)
    a.add_argument("--daily-loss-pct",type=float); a.add_argument("--max-loss-pct",type=float); a.add_argument("--max-days",type=int)
    a.add_argument("--block-days",type=int); a.add_argument("--risk-basis",choices=("initial","current"))
    a.add_argument("--max-loss-anchor",choices=("initial","trailing_eod")); a.add_argument("--trading-days-only",action="store_true")
    a.add_argument("--out-prefix",required=True); q=a.parse_args()
    profile=json.loads(Path(q.profile).read_text(encoding="utf-8")) if q.profile else {}
    cfg=LabConfig(float(choose(q.initial_balance,profile,"initial_balance",100000)),float(choose(q.profit_target_pct,profile,"profit_target_pct",10)),
                  float(choose(q.daily_loss_pct,profile,"daily_loss_pct",5)),float(choose(q.max_loss_pct,profile,"max_loss_pct",10)),
                  int(choose(q.max_days,profile,"max_days",730)),int(choose(q.block_days,profile,"block_days",5)),
                  str(choose(q.risk_basis,profile,"risk_basis","initial")),str(choose(q.max_loss_anchor,profile,"max_loss_anchor","initial")),not q.trading_days_only)
    risks=q.risks or profile.get("risk_levels_pct") or list(DEFAULT_RISKS)
    trades,meta=load_trades(q.input,r_column=q.r_column,time_column=q.time_column,day_column=q.day_column,
                            adverse_r_column=q.adverse_r_column,stage=q.stage)
    rep=run_lab(build_day_blocks(trades,dense_calendar=cfg.dense_calendar),cfg,risks=risks,paths=q.paths,seed=q.seed,use_adverse_r=bool(q.adverse_r_column))
    rep["input"]={**meta,"stage_filter":q.stage,"day_mode":"dense_calendar" if cfg.dense_calendar else "observed_trade_days_only"}
    rep["warnings"]=[]
    if not q.adverse_r_column: rep["warnings"].append("No adverse-R supplied: DD probabilities can understate floating-equity breaches.")
    if meta["cross_day_trade_count"]: rep["warnings"].append(f"{meta['cross_day_trade_count']} trades cross calendar days; atomic trade assignment is not exact daily mark-to-market equity.")
    prefix=Path(q.out_prefix); prefix.parent.mkdir(parents=True,exist_ok=True)
    jp,cp,mp=(Path(str(prefix)+x) for x in (".json",".csv",".md"))
    jp.write_text(json.dumps(rep,indent=2,allow_nan=False),encoding="utf-8"); write_csv(rep,cp); mp.write_text(render_markdown(rep),encoding="utf-8")
    print(render_markdown(rep),end=""); print(f"JSON: {jp}\nCSV:  {cp}\nMD:   {mp}"); return 0


if __name__ == "__main__": raise SystemExit(main())
