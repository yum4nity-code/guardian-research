#!/usr/bin/env python3
"""D052 Management-as-Alpha paired-null workflow.

One MT5 run per symbol evaluates the frozen reference + 11 management candidates
on identical simultaneous LONG/SHORT null entries. The workflow:

1. verifies committed preregistration/source blob identities before execution;
2. computes and publishes normalized source identity before any MT5 outcome;
3. compiles the unchanged source;
4. runs/validates engineering smoke on EURUSD/SPX500/XAUUSD;
5. only after clean smoke, runs 2024-2025 DEV on 12 frozen symbols;
6. performs paired management scoring + deterministic month-block bootstrap;
7. mechanically selects at most one candidate under frozen gates;
8. NEVER opens the Jul-Aug 2026 holdout in this command.

No AutoSync. MT5 remains sequential.
"""
from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import math
import os
import random
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import experiment
import result_transport
import runner
import state_tools
import tester

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ID = "D052-MANAGEMENT-AS-ALPHA-PAIRED-NULL-ENTRY-V0"
PREREG = "research/campaigns/D052_MANAGEMENT_AS_ALPHA_PAIRED_NULL_ENTRY_V0_PREREGISTRATION_2026_09_07.md"
SOURCE = "research/strategies/d052/D052_ManagementAsAlpha_PairedNull_M15_v1_00.mq5"
PREREG_GIT_BLOB_SHA = "faa986bb7460806ccc7b5423ba8a697f7569de8e"
SOURCE_GIT_BLOB_SHA = "98ca64ebe2c8e21f2579e9f4cc804b8848d6325b"
SOURCE_VERSION = "1.00"

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF",
    "SPX500", "NDX100", "GER30", "US30", "XAUUSD", "XAGUSD",
]
SMOKE_SYMBOLS = ["EURUSD", "SPX500", "XAUUSD"]

MANAGEMENTS = [
    "REF_EOD_NO_STOP",
    "SL1_EOD",
    "SL1_TP1",
    "SL1_TP2",
    "SL1_TP3",
    "SL1_BE_AFTER_1R_EOD",
    "SL1_BE_AFTER_2R_EOD",
    "SL1_P50_AT_1R_BE_REST",
    "SL1_P40_AT_2_5R_BE_REST",
    "SL1_TRAIL1_AFTER_1R",
    "SL1_TRAIL1_5_AFTER_2R",
    "SL1_P50_AT_1R_TRAIL1_REST",
]
REFERENCE = MANAGEMENTS[0]
CANDIDATES = MANAGEMENTS[1:]
SIDES = ["LONG", "SHORT"]

SMOKE_FROM = "2023-10-02"
SMOKE_TO = "2023-10-31"
DEV_FROM = "2024-01-02"
DEV_TO = "2025-12-31"
HOLDOUT_FROM = "2026-07-01"
HOLDOUT_TO = "2026-08-31"

BOOTSTRAP_REPS = 20_000


class D052Error(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise D052Error(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def verify_frozen_repository_identity() -> dict[str, str]:
    checks = [(PREREG, PREREG_GIT_BLOB_SHA), (SOURCE, SOURCE_GIT_BLOB_SHA)]
    out: dict[str, str] = {}
    for path, expected in checks:
        actual = _git("rev-parse", f"HEAD:{path}")
        if actual.lower() != expected.lower():
            raise D052Error(f"frozen Git blob changed for {path}: expected={expected} actual={actual}")
        diff = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--quiet", "HEAD", "--", path], check=False
        )
        if diff.returncode != 0:
            raise D052Error(f"working-tree modification detected in frozen file: {path}")
        out[path] = actual
    return out


def build_manifest(source_sha: str) -> tuple[Path, dict[str, Any]]:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "strategy_family": "management-as-alpha paired direction-neutral null-entry lab",
        "status": "READY_SMOKE_THEN_DEV",
        "hypothesis": (
            "Can one frozen mechanical management rule create robust positive expectancy after costs "
            "on simultaneous LONG+SHORT price-independent null entries across 12 liquid markets?"
        ),
        "preregistration": {
            "path": PREREG,
            "git_blob_sha": PREREG_GIT_BLOB_SHA,
            "frozen_before_result_inspection": True,
            "execution_deviations": [
                "Specialized D052 runner validates paired virtual-management rows rather than generic one-row-per-trade lifecycle.",
                "One MT5 symbol run simulates all frozen management variants on identical paired entries.",
            ],
        },
        "source": {
            "canonical_path": SOURCE,
            "source_sha256": source_sha,
            "source_sha256_mode": "UTF8_TEXT_LF_NORMALIZED",
            "git_blob_sha": SOURCE_GIT_BLOB_SHA,
            "version": SOURCE_VERSION,
            "complete_repository_source": True,
            "strategy_semantics_frozen": True,
            "engineering_lineage": [
                "D052 source committed after preregistration and before any D052 outcome",
                f"Frozen source Git blob {SOURCE_GIT_BLOB_SHA}",
            ],
        },
        "execution": {
            "timeframe": "M15",
            "reference_timeframes": ["D1"],
            "symbols": list(SYMBOLS),
            "account_currency": "USD",
            "prop_firm_profile": "FUNDEDNEXT_D052_MANAGEMENT_NULL_V0",
        },
        "runner_contract": {
            "expert_relative_path": "GuardianResearch\\D052_ManagementAsAlpha_PairedNull_M15_v1_00",
            "default_stage": "development",
            "stage_selection": "TESTER_DATE_RANGE_ONLY",
            "tester_model_reference": 0,
            "tester_model_fast_candidate": None,
            "output": {
                "location": "FILE_COMMON",
                "stats_template": "D052_V100_{stage_token}_{symbol_clean}_STATS.csv",
                "trades_template": "D052_V100_{stage_token}_{symbol_clean}_RESULTS.csv",
                "stage_tokens": {"smoke": "RUN", "development": "RUN", "confirmation": "RUN"},
            },
        },
        "cost_model": {
            "name": "D052_PARENT_COMPARABLE_INTRADAY",
            "spread_source": "tester executable bid/ask ticks",
            "commission_stress_multiplier": 1.5,
            "forex": "USD 5 per lot per side",
            "indices": "zero explicit commission; executable spread retained",
            "metals": "0.0016% notional per side",
            "swap": "excluded; normal D052 rows close before broker-day change",
        },
        "stages": {
            "smoke": {
                "stage_name": "D052_SMOKE_OCT2023",
                "from": SMOKE_FROM,
                "to": SMOKE_TO,
                "symbols": list(SMOKE_SYMBOLS),
                "status": "READY",
                "gates": {"engineering_only": True, "paired_matrix_integrity_required": True},
                "result_paths": [],
            },
            "development": {
                "stage_name": "D052_DEV_2024_2025",
                "from": DEV_FROM,
                "to": DEV_TO,
                "symbols": list(SYMBOLS),
                "status": "LOCKED_UNTIL_SMOKE_PASS",
                "gates": {
                    "candidate_n_min": 8000,
                    "each_symbol_n_min": 600,
                    "candidate_mean_positive": True,
                    "candidate_pf_min": 1.05,
                    "candidate_stress_total_positive": True,
                    "long_mean_positive": True,
                    "short_mean_positive": True,
                    "positive_symbols_min": 9,
                    "both_years_positive": True,
                    "paired_delta_positive": True,
                    "bootstrap_absolute_lower_positive": True,
                    "bootstrap_delta_lower_positive": True,
                    "max_positive_symbol_share": 0.25,
                    "integrity_events_max": 0,
                },
                "result_paths": [],
            },
            "confirmation": {
                "stage_name": "D052_HOLDOUT_JUL_AUG2026",
                "from": HOLDOUT_FROM,
                "to": HOLDOUT_TO,
                "symbols": list(SYMBOLS),
                "status": "UNOPENED",
                "gates": {"locked_until_single_dev_candidate_passes_all_frozen_gates": True},
                "result_paths": [],
            },
        },
        "decision_policy": {
            "no_posthoc_rescue": True,
            "confirmation_locked_until_dev_pass": True,
            "invalid_run_is_not_strategy_reject": True,
        },
        "results": {"compile": None, "smoke": None, "development": None, "confirmation": None, "final_verdict": None},
    }
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise D052Error("synthetic D052 manifest invalid: " + "; ".join(errors))
    local = ROOT / "local" / "d052_generated" / "D052.json"
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return local, manifest


@contextlib.contextmanager
def d052_context(manifest_path: Path, manifest: dict[str, Any]) -> Iterator[None]:
    original = runner.load_context
    state = state_tools.load_state()

    def local_context(identifier: str):
        accepted = {
            EXPERIMENT_ID.upper(), "D052", str(manifest_path).upper(),
            str(manifest_path.relative_to(ROOT)).upper(),
        }
        if str(identifier).upper() not in accepted:
            raise runner.RunnerError(f"D052 context refuses unrelated identifier: {identifier}")
        return state, manifest_path, manifest

    runner.load_context = local_context
    try:
        yield
    finally:
        runner.load_context = original


def _output_names(symbol: str) -> tuple[str, str]:
    clean = tester.clean_symbol(symbol)
    return f"D052_V100_RUN_{clean}_STATS.csv", f"D052_V100_RUN_{clean}_RESULTS.csv"


def _render_ini(manifest: dict[str, Any], symbol: str, start: str, end: str) -> str:
    expert = manifest["runner_contract"]["expert_relative_path"]
    return "\n".join([
        "[Tester]",
        f"Expert={expert}",
        f"Symbol={symbol}",
        "Period=M15",
        "Model=0",
        "ExecutionMode=0",
        "Optimization=0",
        f"FromDate={start.replace('-', '.')}",
        f"ToDate={end.replace('-', '.')}",
        "ForwardMode=0",
        "Deposit=10000",
        "Currency=USD",
        "Leverage=1:100",
        "UseLocal=1",
        "UseRemote=0",
        "UseCloud=0",
        "Visual=0",
        "ShutdownTerminal=1",
        "",
    ])


def _latest_compile_receipt(config: dict[str, Any], source_sha: str) -> dict[str, Any]:
    base = runner._expand_path(config["workspace_dir"]) / "builds" / EXPERIMENT_ID
    candidates = sorted(base.glob("*/build.json"), reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("status") != "COMPILE_PASS":
            continue
        if str(payload.get("deploy", {}).get("source_sha256", "")).lower() != source_sha.lower():
            continue
        ex5 = Path(str(payload.get("compile", {}).get("ex5", "")))
        if ex5.is_file() and runner.sha256_file(ex5) == payload.get("compile", {}).get("ex5_sha256"):
            return {"path": str(path), **payload}
    raise D052Error("no trusted D052 COMPILE_PASS receipt for frozen source SHA")


def _int(row: dict[str, str], field: str) -> int:
    try:
        return int(row.get(field, ""))
    except (TypeError, ValueError) as exc:
        raise D052Error(f"invalid integer {field}={row.get(field)!r}") from exc


def _float(row: dict[str, str], field: str) -> float:
    try:
        value = float(row.get(field, ""))
    except (TypeError, ValueError) as exc:
        raise D052Error(f"invalid float {field}={row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise D052Error(f"non-finite {field}={value}")
    return value


def validate_symbol_evidence(stats_path: Path, results_path: Path, symbol: str) -> dict[str, Any]:
    stats = tester.read_semicolon_csv(stats_path)
    rows = tester.read_semicolon_csv(results_path)
    if not stats:
        raise D052Error(f"{symbol}: empty STATS")
    statuses = [r.get("status", "") for r in stats]
    if "INIT" not in statuses or "READY" not in statuses:
        raise D052Error(f"{symbol}: lifecycle missing INIT/READY: {statuses[:10]}")
    final = stats[-1]
    if final.get("status") != "FINAL":
        raise D052Error(f"{symbol}: final status is not FINAL: {final.get('status')}")
    if final.get("source_name") != Path(SOURCE).name or final.get("source_version") != SOURCE_VERSION:
        raise D052Error(f"{symbol}: source identity fields mismatch")
    if final.get("run_stage") != "RUN":
        raise D052Error(f"{symbol}: run_stage mismatch: {final.get('run_stage')}")
    if symbol not in str(final.get("symbol", "")):
        raise D052Error(f"{symbol}: STATS symbol mismatch {final.get('symbol')}")
    if final.get("fatal_status") not in ("", None):
        raise D052Error(f"{symbol}: fatal_status={final.get('fatal_status')}")
    if _int(final, "management_count") != len(MANAGEMENTS):
        raise D052Error(f"{symbol}: management_count mismatch")

    opened = _int(final, "virtual_opened")
    closed = _int(final, "virtual_closed")
    csv_rows = _int(final, "csv_rows")
    paired_events = _int(final, "paired_events_opened")
    if paired_events <= 0:
        raise D052Error(f"{symbol}: zero paired events")
    if not (opened == closed == csv_rows == len(rows)):
        raise D052Error(
            f"{symbol}: lifecycle mismatch opened={opened} closed={closed} csv={csv_rows} parsed={len(rows)}"
        )
    for field in ("invalid_price", "invalid_risk", "pnl_calc_failures"):
        if _int(final, field) != 0:
            raise D052Error(f"{symbol}: integrity counter {field}={final.get(field)}")

    required = {
        "run_stage", "symbol", "event_id", "day_key", "side", "management",
        "net_r", "net_r_commission_x1_5", "gross_r", "commission_r",
    }
    if not rows or not required.issubset(rows[0]):
        raise D052Error(f"{symbol}: RESULTS missing fields {sorted(required - set(rows[0] if rows else []))}")

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    event_sides: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("run_stage") != "RUN":
            raise D052Error(f"{symbol}: result run_stage mismatch")
        if symbol not in str(row.get("symbol", "")):
            raise D052Error(f"{symbol}: result symbol mismatch")
        side = str(row.get("side", ""))
        mgmt = str(row.get("management", ""))
        event_id = str(row.get("event_id", ""))
        if side not in SIDES or mgmt not in MANAGEMENTS or not event_id:
            raise D052Error(f"{symbol}: invalid row identity side={side} mgmt={mgmt} event={event_id}")
        key = (event_id, side, mgmt)
        if key in seen:
            raise D052Error(f"{symbol}: duplicate row {key}")
        seen.add(key)
        groups[(event_id, side)].append(mgmt)
        event_sides[event_id].add(side)
        for field in ("net_r", "net_r_commission_x1_5", "gross_r", "commission_r"):
            _float(row, field)

    expected_set = set(MANAGEMENTS)
    for key, labels in groups.items():
        if len(labels) != len(MANAGEMENTS) or set(labels) != expected_set:
            raise D052Error(f"{symbol}: incomplete management matrix for {key}")
    for event_id, sides in event_sides.items():
        if sides != set(SIDES):
            raise D052Error(f"{symbol}: event lacks paired LONG/SHORT sleeves: {event_id} -> {sides}")
    if len(rows) != paired_events * len(SIDES) * len(MANAGEMENTS):
        raise D052Error(
            f"{symbol}: row/event matrix mismatch rows={len(rows)} events={paired_events}"
        )

    return {
        "status": "D052_SYMBOL_PASS_INTEGRITY",
        "symbol": symbol,
        "paired_events": paired_events,
        "virtual_rows": len(rows),
        "reference_unusable_days": _int(final, "reference_unusable_days"),
        "schedule_missed_days": _int(final, "schedule_missed_days"),
        "invalid_price": 0,
        "invalid_risk": 0,
        "pnl_calc_failures": 0,
    }


def run_symbol(
    manifest: dict[str, Any], source_sha: str, stage: str, symbol: str, start: str, end: str
) -> dict[str, Any]:
    config = runner.load_config()
    config_errors = tester.validate_test_config(config)
    if config_errors:
        raise D052Error("invalid local tester config: " + "; ".join(config_errors))
    compile_receipt = _latest_compile_receipt(config, source_sha)
    common = runner._expand_path(config["common_files_dir"])
    workspace = runner._expand_path(config["workspace_dir"])
    stats_name, results_name = _output_names(symbol)
    expected = [common / stats_name, common / results_name]

    quarantine = workspace / "quarantine" / "d052" / stage / symbol / stamp()
    moved: list[str] = []
    existing = [p for p in expected if p.exists()]
    if existing:
        quarantine.mkdir(parents=True, exist_ok=True)
        for p in existing:
            target = quarantine / p.name
            shutil.move(str(p), str(target))
            moved.append(str(target))

    run_id = f"{stamp()}_{tester.clean_symbol(symbol)}_M0"
    run_dir = workspace / "runs" / EXPERIMENT_ID / stage / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    ini = run_dir / "tester.ini"
    ini.write_text(_render_ini(manifest, symbol, start, end), encoding="utf-8", newline="\n")

    terminal = runner._expand_path(config["terminal_exe"])
    command = [str(terminal), f"/config:{ini}"]
    if bool(config.get("portable_mode", True)):
        command.append("/portable")
    timeout = int(config.get("tester_timeout_seconds", 14400))
    started = datetime.now(timezone.utc)
    proc = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
    finished = datetime.now(timezone.utc)

    missing = [str(p) for p in expected if not p.is_file()]
    if missing:
        raise D052Error(
            f"{symbol}: MT5 exit={proc.returncode}, missing outputs={missing}; "
            f"stdout={proc.stdout[-800:]} stderr={proc.stderr[-800:]}"
        )

    local_stats = run_dir / stats_name
    local_results = run_dir / results_name
    shutil.copy2(expected[0], local_stats)
    shutil.copy2(expected[1], local_results)
    integrity = validate_symbol_evidence(local_stats, local_results, symbol)
    evidence = {
        "schema_version": 1,
        "status": "D052_SYMBOL_PASS_INTEGRITY",
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "symbol": symbol,
        "from": start,
        "to": end,
        "tester_model": 0,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "terminal_exit_code": proc.returncode,
        "command": command,
        "source_sha256": source_sha,
        "ex5_sha256": compile_receipt["compile"]["ex5_sha256"],
        "quarantined_stale_outputs": moved,
        "stats": {"path": str(local_stats), "sha256": runner.sha256_file(local_stats)},
        "results": {"path": str(local_results), "sha256": runner.sha256_file(local_results)},
        "integrity": integrity,
        "autosync_used": False,
    }
    runner.write_receipt(run_dir / "run.json", evidence)
    return evidence


def run_stage(
    manifest: dict[str, Any], source_sha: str, stage: str, symbols: list[str], start: str, end: str
) -> dict[str, Any]:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    batch_dir = workspace / "d052" / stage / stamp()
    batch_dir.mkdir(parents=True, exist_ok=False)
    receipt = batch_dir / "batch.json"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "RUNNING",
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "symbols": symbols,
        "from": start,
        "to": end,
        "execution_mode": "SEQUENTIAL_ONE_MT5_RUN_PER_SYMBOL_ALL_MANAGEMENTS_PARALLEL_VIRTUAL",
        "tester_model": 0,
        "source_sha256": source_sha,
        "tests": [],
        "autosync_used": False,
    }
    runner.write_receipt(receipt, payload)
    try:
        for symbol in symbols:
            result = run_symbol(manifest, source_sha, stage, symbol, start, end)
            payload["tests"].append(result)
            runner.write_receipt(receipt, payload)
    except Exception as exc:
        payload["status"] = "D052_BATCH_INVALID_ENGINEERING"
        payload["failed_symbol"] = symbol
        payload["error"] = str(exc)
        payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        runner.write_receipt(receipt, payload)
        raise D052Error(
            f"D052 {stage} stopped on {symbol}; completed={len(payload['tests'])}; receipt={receipt}; cause={exc}"
        ) from exc
    payload["status"] = "D052_BATCH_PASS_INTEGRITY"
    payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["batch_path"] = str(receipt)
    runner.write_receipt(receipt, payload)
    return payload


def _pf(values: list[float]) -> float | None:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _quantile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise D052Error("cannot take quantile of empty sample")
    pos=(len(sorted_values)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return sorted_values[lo]
    w=pos-lo
    return sorted_values[lo]*(1-w)+sorted_values[hi]*w


def block_bootstrap_ci(
    values_by_block: dict[str, list[float]], reps: int, seed: int
) -> dict[str, float]:
    blocks = sorted(values_by_block)
    if len(blocks) < 6:
        raise D052Error(f"insufficient bootstrap blocks: {len(blocks)}")
    summaries = [(sum(values_by_block[b]), len(values_by_block[b])) for b in blocks]
    rng = random.Random(seed)
    samples: list[float] = []
    k = len(summaries)
    for _ in range(reps):
        total=0.0; n=0
        for _j in range(k):
            s,c = summaries[rng.randrange(k)]
            total += s; n += c
        samples.append(total/n)
    samples.sort()
    return {
        "lower_95": _quantile(samples,0.025),
        "median": _quantile(samples,0.5),
        "upper_95": _quantile(samples,0.975),
        "reps": reps,
        "blocks": k,
        "seed": seed,
    }


def score_development(batch: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    integrity_events=0
    for test in batch["tests"]:
        path=Path(test["results"]["path"])
        rows.extend(tester.read_semicolon_csv(path))
        integ=test["integrity"]
        integrity_events += int(integ.get("invalid_price",0))+int(integ.get("invalid_risk",0))+int(integ.get("pnl_calc_failures",0))

    by_key: dict[tuple[str,str,str], dict[str, dict[str,str]]] = defaultdict(dict)
    for row in rows:
        key=(row["symbol"],row["event_id"],row["side"])
        by_key[key][row["management"]]=row
    for key,matrix in by_key.items():
        if set(matrix)!=set(MANAGEMENTS):
            raise D052Error(f"development matrix incomplete for {key}")

    candidates_report: list[dict[str,Any]]=[]
    for idx,name in enumerate(CANDIDATES, start=1):
        net: list[float]=[]; stress: list[float]=[]; delta: list[float]=[]
        side_values: dict[str,list[float]]=defaultdict(list)
        symbol_values: dict[str,list[float]]=defaultdict(list)
        year_values: dict[str,list[float]]=defaultdict(list)
        abs_blocks: dict[str,list[float]]=defaultdict(list)
        delta_blocks: dict[str,list[float]]=defaultdict(list)

        for (symbol,event_id,side),matrix in sorted(by_key.items()):
            cand=matrix[name]; ref=matrix[REFERENCE]
            v=_float(cand,"net_r")
            s=_float(cand,"net_r_commission_x1_5")
            d=v-_float(ref,"net_r")
            day=str(cand["day_key"])
            year=day[:4]; month=day[:6]
            net.append(v); stress.append(s); delta.append(d)
            side_values[side].append(v)
            symbol_values[symbol].append(v)
            year_values[year].append(v)
            abs_blocks[month].append(v)
            delta_blocks[month].append(d)

        pf=_pf(net)
        per_symbol_n={s:len(symbol_values[s]) for s in SYMBOLS}
        per_symbol_total={s:sum(symbol_values[s]) for s in SYMBOLS}
        positive=[s for s in SYMBOLS if per_symbol_total[s]>0]
        positive_total=sum(per_symbol_total[s] for s in positive)
        max_share=max((per_symbol_total[s]/positive_total for s in positive),default=0.0) if positive_total>0 else 0.0
        abs_ci=block_bootstrap_ci(abs_blocks,BOOTSTRAP_REPS,520520+idx)
        delta_ci=block_bootstrap_ci(delta_blocks,BOOTSTRAP_REPS,521520+idx)
        mean=_mean(net); total=sum(net); delta_mean=_mean(delta)
        long_mean=_mean(side_values["LONG"]); short_mean=_mean(side_values["SHORT"])
        gates={
            "aggregate_n_min": len(net)>=8000,
            "each_symbol_n_min": all(per_symbol_n[s]>=600 for s in SYMBOLS),
            "aggregate_mean_positive": mean>0,
            "pf_min": bool(pf is not None and (math.isinf(pf) or pf>=1.05)),
            "aggregate_total_positive": total>0,
            "stress_total_positive": sum(stress)>0,
            "long_mean_positive": long_mean>0,
            "short_mean_positive": short_mean>0,
            "positive_symbols_min": len(positive)>=9,
            "year_2024_positive": sum(year_values["2024"])>0,
            "year_2025_positive": sum(year_values["2025"])>0,
            "paired_delta_positive": delta_mean>0,
            "bootstrap_absolute_lower_positive": abs_ci["lower_95"]>0,
            "bootstrap_delta_lower_positive": delta_ci["lower_95"]>0,
            "max_positive_symbol_share": max_share<=0.25,
            "integrity_events_max": integrity_events==0,
        }
        report={
            "management": name,
            "all_gates_pass": all(gates.values()),
            "metrics": {
                "n": len(net),
                "mean_net_r": mean,
                "median_net_r": statistics.median(net) if net else 0.0,
                "pf": None if pf is None or math.isinf(pf) else pf,
                "pf_infinite": bool(pf is not None and math.isinf(pf)),
                "total_net_r": total,
                "stress_total_net_r": sum(stress),
                "long_mean_net_r": long_mean,
                "short_mean_net_r": short_mean,
                "per_symbol_n": per_symbol_n,
                "per_symbol_total_net_r": per_symbol_total,
                "positive_symbols": positive,
                "positive_symbols_n": len(positive),
                "year_total_net_r": {"2024":sum(year_values["2024"]),"2025":sum(year_values["2025"])},
                "paired_delta_mean_r": delta_mean,
                "paired_delta_total_r": sum(delta),
                "max_positive_symbol_contribution_share": max_share,
                "absolute_mean_month_block_bootstrap": abs_ci,
                "paired_delta_month_block_bootstrap": delta_ci,
                "integrity_events": integrity_events,
            },
            "gates": gates,
        }
        candidates_report.append(report)

    passing=[r for r in candidates_report if r["all_gates_pass"]]
    selected=None
    if passing:
        def selection_key(r: dict[str,Any]):
            m=r["metrics"]
            lower=min(
                m["absolute_mean_month_block_bootstrap"]["lower_95"],
                m["paired_delta_month_block_bootstrap"]["lower_95"],
            )
            pfv=float("inf") if m["pf_infinite"] else float(m["pf"] or 0.0)
            return (-lower,-pfv,-float(m["mean_net_r"]),float(m["max_positive_symbol_contribution_share"]),r["management"])
        selected=sorted(passing,key=selection_key)[0]["management"]
        status="D052_DEV_CANDIDATE_SELECTED_HOLDOUT_REMAINS_UNOPENED"
    else:
        status="D052_NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY"

    reference_values=[]
    for matrix in by_key.values():
        reference_values.append(_float(matrix[REFERENCE],"net_r"))
    ref_pf=_pf(reference_values)

    return {
        "schema_version":1,
        "status":status,
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "experiment_id":EXPERIMENT_ID,
        "stage":"development",
        "reference":{
            "management":REFERENCE,
            "n":len(reference_values),
            "mean_net_r":_mean(reference_values),
            "total_net_r":sum(reference_values),
            "pf":None if ref_pf is None or math.isinf(ref_pf) else ref_pf,
            "pf_infinite":bool(ref_pf is not None and math.isinf(ref_pf)),
        },
        "candidates":candidates_report,
        "passing_candidates":[r["management"] for r in passing],
        "selected_candidate":selected,
        "selection_rule":"FROZEN_LEXICOGRAPHIC_BOOTSTRAP_LOWER_THEN_PF_THEN_MEAN_THEN_CONCENTRATION_THEN_NAME",
        "holdout":{
            "status":"UNOPENED" if selected is None else "LOCKED_PENDING_ASSISTANT_REVIEW_AND_TWO-MANAGEMENT_DERIVATIVE",
            "from":HOLDOUT_FROM,"to":HOLDOUT_TO,"symbols":SYMBOLS,
            "losing_candidate_holdout_outcomes_must_not_be_generated":True,
        },
        "integrity_events":integrity_events,
        "autosync_used":False,
    }


def _write_local(kind: str, payload: dict[str,Any]) -> Path:
    workspace=runner._expand_path(runner.load_config()["workspace_dir"])
    out=workspace/"d052"/kind/stamp()/f"{kind}.json"
    runner.write_receipt(out,payload)
    return out


def main() -> int:
    identities=verify_frozen_repository_identity()
    source_path=ROOT/SOURCE
    source_sha=runner.source_identity_sha256(source_path,runner.SOURCE_SHA_MODE_TEXT_LF)
    manifest_path,manifest=build_manifest(source_sha)

    with d052_context(manifest_path,manifest):
        source_freeze={
            "schema_version":1,
            "status":"D052_SOURCE_IDENTITY_FROZEN_BEFORE_MT5_OUTCOME",
            "created_at_utc":datetime.now(timezone.utc).isoformat(),
            "experiment_id":EXPERIMENT_ID,
            "preregistration":PREREG,
            "preregistration_git_blob_sha":identities[PREREG],
            "source":SOURCE,
            "source_git_blob_sha":identities[SOURCE],
            "source_sha256_mode":"UTF8_TEXT_LF_NORMALIZED",
            "source_sha256":source_sha,
            "managements":MANAGEMENTS,
            "symbols":SYMBOLS,
            "smoke_window":[SMOKE_FROM,SMOKE_TO],
            "development_window":[DEV_FROM,DEV_TO],
            "holdout_window_locked_unopened":[HOLDOUT_FROM,HOLDOUT_TO],
            "autosync_used":False,
        }
        freeze_local=_write_local("source-freeze",source_freeze)
        source_freeze["local_path"]=str(freeze_local)
        source_freeze["github_transport"]=result_transport.safe_publish_event(
            EXPERIMENT_ID,"smoke","d052-source-freeze",source_freeze
        )
        print(json.dumps(source_freeze,indent=2,ensure_ascii=False,allow_nan=False))

        rc=runner.cmd_compile(EXPERIMENT_ID)
        if rc!=0:
            raise D052Error("D052 compile failed")

        try:
            smoke=run_stage(manifest,source_sha,"smoke",SMOKE_SYMBOLS,SMOKE_FROM,SMOKE_TO)
        except Exception as exc:
            failure={
                "schema_version":1,"status":"D052_SMOKE_INVALID_ENGINEERING",
                "created_at_utc":datetime.now(timezone.utc).isoformat(),"error":str(exc),
                "source_sha256":source_sha,"autosync_used":False,
            }
            local=_write_local("smoke-invalid",failure); failure["local_path"]=str(local)
            failure["github_transport"]=result_transport.safe_publish_event(
                EXPERIMENT_ID,"smoke","d052-smoke-invalid",failure
            )
            print(json.dumps(failure,indent=2,ensure_ascii=False,allow_nan=False))
            return 2

        smoke_local=_write_local("smoke-pass",smoke); smoke["local_path"]=str(smoke_local)
        smoke["github_transport"]=result_transport.safe_publish_event(
            EXPERIMENT_ID,"smoke","d052-smoke-pass",smoke
        )
        print(json.dumps({
            "status":"D052_SMOKE_PASS","symbols":SMOKE_SYMBOLS,
            "paired_events":{t["symbol"]:t["integrity"]["paired_events"] for t in smoke["tests"]},
            "source_sha256":source_sha,"autosync_used":False,
        },indent=2,ensure_ascii=False))

        # Same source SHA; no semantic transition or parameter change between smoke and DEV.
        dev=run_stage(manifest,source_sha,"development",SYMBOLS,DEV_FROM,DEV_TO)
        dev_local=_write_local("development-batch",dev); dev["local_path"]=str(dev_local)
        dev_transport=result_transport.safe_publish_event(
            EXPERIMENT_ID,"development","d052-development-batch",dev
        )

        score=score_development(dev)
        score["source_sha256"]=source_sha
        score["batch_path"]=dev["batch_path"]
        score["batch_transport"]=dev_transport
        score_local=_write_local("development-score",score)
        score["score_path"]=str(score_local)
        score["github_transport"]=result_transport.safe_publish_event(
            EXPERIMENT_ID,"development","d052-development-score",score
        )
        print(json.dumps(score,indent=2,ensure_ascii=False,allow_nan=False))
        return 0


if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D052 WORKFLOW ERROR: {exc}",file=sys.stderr)
        raise SystemExit(1)
