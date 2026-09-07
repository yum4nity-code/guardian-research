#!/usr/bin/env python3
"""D053 US-index ORB30 deterministic smoke -> DEV workflow and scorer."""
from __future__ import annotations

import json
import math
import random
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import result_transport
import runner
import tester

ROOT = Path(__file__).resolve().parents[2]
KEY = "D053"
EXPERIMENT_ID = "D053-US-INDEX-ORB30-ENTRY-ALPHA-V0"
PREREG = "research/campaigns/D053_US_INDEX_ORB30_ENTRY_ALPHA_V0_PREREGISTRATION_2026_09_07.md"
SOURCE = "research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5"
SOURCE_VERSION = "1.00"
EXPECTED_PREREG_BLOB = "2d66799b1e25cc6cf19dd5d033bd2731372c5cd3"
EXPECTED_SOURCE_BLOB = "f60329c6fcb79b308c5a60e74c0512b52481386a"
EXPECTED_SOURCE_SHA256 = "bbd0178f3c71a99802b75db563f06f38a94d4735bc828a78ee8c009dd4900ec8"
SYMBOLS = ["SPX500", "NDX100", "US30", "US2000"]
SMOKE_SYMBOLS = ["SPX500", "NDX100", "US2000"]
SMOKE_FROM, SMOKE_TO = "2023-10-02", "2023-10-31"
DEV_FROM, DEV_TO = "2024-01-02", "2025-12-31"
HOLDOUT_FROM, HOLDOUT_TO = "2026-07-01", "2026-08-31"
BOOTSTRAP_REPS = 20000


class D053Error(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_blob_sha(relative: str) -> str:
    completed = subprocess.run(
        ["git", "hash-object", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise D053Error(f"git hash-object failed for {relative}: {completed.stderr.strip()}")
    value = completed.stdout.strip()
    if len(value) != 40:
        raise D053Error(f"invalid git blob for {relative}: {value}")
    return value


def verify_frozen_repository_identity() -> dict[str, str]:
    prereg_blob = git_blob_sha(PREREG)
    source_blob = git_blob_sha(SOURCE)
    source_sha = runner.source_identity_sha256(ROOT / SOURCE, runner.SOURCE_SHA_MODE_TEXT_LF)
    if prereg_blob.lower() != EXPECTED_PREREG_BLOB:
        raise D053Error(f"prereg blob mismatch: expected={EXPECTED_PREREG_BLOB} actual={prereg_blob}")
    if source_blob.lower() != EXPECTED_SOURCE_BLOB:
        raise D053Error(f"source blob mismatch: expected={EXPECTED_SOURCE_BLOB} actual={source_blob}")
    if source_sha.lower() != EXPECTED_SOURCE_SHA256:
        raise D053Error(f"source SHA mismatch: expected={EXPECTED_SOURCE_SHA256} actual={source_sha}")
    manifest_path, manifest = experiment.load_manifest(KEY)
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise D053Error("D053 manifest invalid: " + "; ".join(errors))
    if manifest["experiment_id"] != EXPERIMENT_ID:
        raise D053Error("D053 manifest experiment_id mismatch")
    if manifest["preregistration"].get("git_blob_sha") != prereg_blob:
        raise D053Error("manifest prereg blob mismatch")
    if manifest["source"].get("git_blob_sha") != source_blob:
        raise D053Error("manifest source blob mismatch")
    if manifest["source"].get("source_sha256") != source_sha:
        raise D053Error("manifest normalized source SHA mismatch")
    if manifest["execution"]["symbols"] != SYMBOLS:
        raise D053Error("manifest symbol universe mismatch")
    if manifest["stages"]["confirmation"]["from"] != HOLDOUT_FROM or manifest["stages"]["confirmation"]["to"] != HOLDOUT_TO:
        raise D053Error("manifest holdout window mismatch")
    return {"prereg_blob": prereg_blob, "source_blob": source_blob, "source_sha256": source_sha}


def _output_names(symbol: str) -> tuple[str, str]:
    clean = tester.clean_symbol(symbol)
    return f"D053_V100_RUN_{clean}_STATS.csv", f"D053_V100_RUN_{clean}_TRADES.csv"


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
    raise D053Error("no trusted D053 COMPILE_PASS receipt for frozen source SHA")


def _as_int(row: dict[str, str], field: str) -> int:
    try:
        return int(row.get(field, ""))
    except (TypeError, ValueError) as exc:
        raise D053Error(f"invalid integer {field}={row.get(field)!r}") from exc


def _as_float(row: dict[str, str], field: str) -> float:
    try:
        value = float(row.get(field, ""))
    except (TypeError, ValueError) as exc:
        raise D053Error(f"invalid float {field}={row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise D053Error(f"non-finite {field}={value}")
    return value


def validate_symbol_evidence(stats_path: Path, trades_path: Path, symbol: str) -> dict[str, Any]:
    stats = tester.read_semicolon_csv(stats_path)
    rows = tester.read_semicolon_csv(trades_path)
    if not stats:
        raise D053Error(f"{symbol}: empty STATS")
    statuses = [row.get("status", "") for row in stats]
    if "INIT" not in statuses or "READY" not in statuses:
        raise D053Error(f"{symbol}: lifecycle missing INIT/READY")
    final = stats[-1]
    if final.get("status") != "FINAL":
        raise D053Error(f"{symbol}: final status={final.get('status')}")
    if final.get("source_name") != Path(SOURCE).name or final.get("source_version") != SOURCE_VERSION:
        raise D053Error(f"{symbol}: source identity fields mismatch")
    if final.get("run_stage") != "RUN":
        raise D053Error(f"{symbol}: run_stage mismatch")
    if symbol not in str(final.get("symbol", "")):
        raise D053Error(f"{symbol}: stats symbol mismatch")
    if final.get("fatal_status") not in ("", None):
        raise D053Error(f"{symbol}: fatal_status={final.get('fatal_status')}")

    range_days = _as_int(final, "range_days")
    opened = _as_int(final, "trades_opened")
    closed = _as_int(final, "trades_closed")
    csv_rows = _as_int(final, "csv_trade_rows")
    if range_days <= 0:
        raise D053Error(f"{symbol}: zero usable opening ranges")
    if not (opened == closed == csv_rows == len(rows)):
        raise D053Error(f"{symbol}: lifecycle mismatch opened={opened} closed={closed} csv={csv_rows} parsed={len(rows)}")

    fatal_counters = (
        "day_change_open_trade", "invalid_price", "invalid_risk",
        "risk_calc_failures", "pnl_calc_failures", "path_calc_failures",
    )
    for field in fatal_counters:
        if _as_int(final, field) != 0:
            raise D053Error(f"{symbol}: integrity counter {field}={final.get(field)}")

    required = {
        "run_stage", "symbol", "day_key", "side", "entry_time", "exit_time",
        "entry", "initial_stop", "exit", "entry_spread", "exit_spread",
        "risk_money_1lot_usd", "gross_r", "net_r", "net_r_spread_x1_5",
        "exit_reason", "trade_id", "mfe_r", "mae_r",
    }
    if rows and not required.issubset(rows[0]):
        raise D053Error(f"{symbol}: missing trade fields {sorted(required - set(rows[0]))}")

    seen_days: set[str] = set()
    seen_ids: set[str] = set()
    for row in rows:
        if row.get("run_stage") != "RUN" or symbol not in str(row.get("symbol", "")):
            raise D053Error(f"{symbol}: row identity mismatch")
        if row.get("side") not in ("LONG", "SHORT"):
            raise D053Error(f"{symbol}: invalid side={row.get('side')}")
        day = str(row.get("day_key", ""))
        trade_id = str(row.get("trade_id", ""))
        if not day or not trade_id:
            raise D053Error(f"{symbol}: missing day/trade id")
        if day in seen_days:
            raise D053Error(f"{symbol}: more than one trade on day={day}")
        if trade_id in seen_ids:
            raise D053Error(f"{symbol}: duplicate trade_id={trade_id}")
        seen_days.add(day)
        seen_ids.add(trade_id)
        for field in (
            "entry", "initial_stop", "exit", "entry_spread", "exit_spread",
            "risk_money_1lot_usd", "gross_r", "net_r", "net_r_spread_x1_5",
            "mfe_r", "mae_r",
        ):
            _as_float(row, field)
        if _as_float(row, "risk_money_1lot_usd") <= 0:
            raise D053Error(f"{symbol}: nonpositive risk")

    return {
        "status": "D053_SYMBOL_PASS_INTEGRITY",
        "symbol": symbol,
        "range_days": range_days,
        "trades": len(rows),
        "ambiguous_days": _as_int(final, "ambiguous_days"),
        "range_unusable_days": _as_int(final, "range_unusable_days"),
        "integrity_events": 0,
    }


def run_symbol(
    manifest: dict[str, Any], source_sha: str, stage: str, symbol: str, start: str, end: str
) -> dict[str, Any]:
    config = runner.load_config()
    errors = tester.validate_test_config(config)
    if errors:
        raise D053Error("invalid local tester config: " + "; ".join(errors))
    compile_receipt = _latest_compile_receipt(config, source_sha)
    common = runner._expand_path(config["common_files_dir"])
    workspace = runner._expand_path(config["workspace_dir"])
    stats_name, trades_name = _output_names(symbol)
    expected = [common / stats_name, common / trades_name]

    quarantine = workspace / "quarantine" / "d053" / stage / symbol / stamp()
    moved: list[str] = []
    existing = [path for path in expected if path.exists()]
    if existing:
        quarantine.mkdir(parents=True, exist_ok=True)
        for path in existing:
            target = quarantine / path.name
            shutil.move(str(path), str(target))
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
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
    finished = datetime.now(timezone.utc)

    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise D053Error(
            f"{symbol}: MT5 exit={completed.returncode}, missing outputs={missing}; "
            f"stdout={completed.stdout[-600:]} stderr={completed.stderr[-600:]}"
        )

    local_stats = run_dir / stats_name
    local_trades = run_dir / trades_name
    shutil.copy2(expected[0], local_stats)
    shutil.copy2(expected[1], local_trades)
    integrity = validate_symbol_evidence(local_stats, local_trades, symbol)
    payload = {
        "schema_version": 1,
        "status": "D053_SYMBOL_PASS_INTEGRITY",
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "symbol": symbol,
        "from": start,
        "to": end,
        "tester_model": 0,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "terminal_exit_code": completed.returncode,
        "source_sha256": source_sha,
        "ex5_sha256": compile_receipt["compile"]["ex5_sha256"],
        "quarantined_stale_outputs": moved,
        "stats": {"path": str(local_stats), "sha256": runner.sha256_file(local_stats)},
        "trades": {"path": str(local_trades), "sha256": runner.sha256_file(local_trades)},
        "integrity": integrity,
        "autosync_used": False,
    }
    runner.write_receipt(run_dir / "run.json", payload)
    return payload


def run_stage(
    manifest: dict[str, Any], source_sha: str, stage: str, symbols: list[str], start: str, end: str
) -> dict[str, Any]:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    batch_dir = workspace / "d053" / stage / stamp()
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
        "execution_mode": "SEQUENTIAL_ONE_MT5_RUN_PER_SYMBOL_MODEL0",
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
        payload["status"] = "D053_BATCH_INVALID_ENGINEERING"
        payload["failed_symbol"] = symbol
        payload["error"] = str(exc)
        payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        runner.write_receipt(receipt, payload)
        raise D053Error(
            f"D053 {stage} stopped on {symbol}; completed={len(payload['tests'])}; "
            f"receipt={receipt}; cause={exc}"
        ) from exc

    payload["status"] = "D053_BATCH_PASS_INTEGRITY"
    payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["batch_path"] = str(receipt)
    runner.write_receipt(receipt, payload)
    return payload


def _pf(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        raise D053Error("cannot take quantile of empty sample")
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return values[lo]
    weight = pos - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def block_bootstrap_ci(values_by_block: dict[str, list[float]], reps: int, seed: int) -> dict[str, Any]:
    blocks = sorted(values_by_block)
    if len(blocks) < 6:
        raise D053Error(f"insufficient bootstrap blocks: {len(blocks)}")
    summaries = [(sum(values_by_block[key]), len(values_by_block[key])) for key in blocks]
    rng = random.Random(seed)
    samples: list[float] = []
    count = len(summaries)
    for _ in range(reps):
        total = 0.0
        n = 0
        for _j in range(count):
            subtotal, subn = summaries[rng.randrange(count)]
            total += subtotal
            n += subn
        samples.append(total / n)
    return {
        "lower_95": _quantile(samples, 0.025),
        "median": _quantile(samples, 0.5),
        "upper_95": _quantile(samples, 0.975),
        "reps": reps,
        "blocks": count,
        "seed": seed,
    }


def score_rows(rows: list[dict[str, str]], integrity_events: int = 0) -> dict[str, Any]:
    net: list[float] = []
    stress: list[float] = []
    side_values: dict[str, list[float]] = defaultdict(list)
    symbol_values: dict[str, list[float]] = defaultdict(list)
    year_values: dict[str, list[float]] = defaultdict(list)
    month_values: dict[str, list[float]] = defaultdict(list)
    mfe_values: list[float] = []
    mae_values: list[float] = []

    for row in rows:
        symbol = str(row["symbol"])
        if symbol not in SYMBOLS:
            raise D053Error(f"score row outside universe: {symbol}")
        side = str(row["side"])
        if side not in ("LONG", "SHORT"):
            raise D053Error(f"score invalid side={side}")
        value = _as_float(row, "net_r")
        stressed = _as_float(row, "net_r_spread_x1_5")
        day = str(row["day_key"])
        if len(day) < 6:
            raise D053Error(f"invalid day_key={day}")
        net.append(value)
        stress.append(stressed)
        side_values[side].append(value)
        symbol_values[symbol].append(value)
        year_values[day[:4]].append(value)
        month_values[day[:6]].append(value)
        mfe_values.append(_as_float(row, "mfe_r"))
        mae_values.append(_as_float(row, "mae_r"))

    pf = _pf(net)
    per_symbol_n = {symbol: len(symbol_values[symbol]) for symbol in SYMBOLS}
    per_symbol_total = {symbol: sum(symbol_values[symbol]) for symbol in SYMBOLS}
    positive = [symbol for symbol in SYMBOLS if per_symbol_total[symbol] > 0]
    positive_total = sum(per_symbol_total[symbol] for symbol in positive)
    max_share = (
        max((per_symbol_total[symbol] / positive_total for symbol in positive), default=0.0)
        if positive_total > 0 else 0.0
    )
    ci = block_bootstrap_ci(month_values, BOOTSTRAP_REPS, 530053)
    mean = _mean(net)
    total = sum(net)

    gates = {
        "aggregate_n_min": len(net) >= 1000,
        "each_symbol_n_min": all(per_symbol_n[symbol] >= 200 for symbol in SYMBOLS),
        "aggregate_mean_net_r_min": mean >= 0.05,
        "aggregate_pf_min": bool(pf is not None and (math.isinf(pf) or pf >= 1.10)),
        "aggregate_total_net_r_positive": total > 0,
        "spread_stress_total_positive": sum(stress) > 0,
        "positive_symbols_min": len(positive) >= 3,
        "year_2024_positive": sum(year_values["2024"]) > 0,
        "year_2025_positive": sum(year_values["2025"]) > 0,
        "month_block_bootstrap_lower_95_positive": ci["lower_95"] > 0,
        "max_positive_symbol_contribution_share": max_share <= 0.55,
        "integrity_events_max": integrity_events == 0,
    }
    passed = all(gates.values())
    return {
        "schema_version": 1,
        "status": "D053_DEV_PASS_HOLDOUT_LOCKED" if passed else "D053_REJECT_V0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "stage": "development",
        "metrics": {
            "aggregate_n": len(net),
            "aggregate_mean_net_r": mean,
            "aggregate_pf": None if pf is None or math.isinf(pf) else pf,
            "aggregate_pf_infinite": bool(pf is not None and math.isinf(pf)),
            "aggregate_total_net_r": total,
            "spread_stress_total_net_r": sum(stress),
            "per_symbol_n": per_symbol_n,
            "per_symbol_total_net_r": per_symbol_total,
            "positive_symbols": positive,
            "positive_symbols_n": len(positive),
            "year_total_net_r": {
                "2024": sum(year_values["2024"]),
                "2025": sum(year_values["2025"]),
            },
            "side": {
                "LONG": {"n": len(side_values["LONG"]), "mean_net_r": _mean(side_values["LONG"]), "total_net_r": sum(side_values["LONG"])},
                "SHORT": {"n": len(side_values["SHORT"]), "mean_net_r": _mean(side_values["SHORT"]), "total_net_r": sum(side_values["SHORT"])},
            },
            "month_block_bootstrap": ci,
            "max_positive_symbol_contribution_share": max_share,
            "path_descriptive": {
                "mean_mfe_r": _mean(mfe_values),
                "mean_mae_r": _mean(mae_values),
            },
            "integrity_events": integrity_events,
        },
        "gates": gates,
        "all_gates_pass": passed,
        "holdout": {
            "status": "LOCKED_UNOPENED",
            "from": HOLDOUT_FROM,
            "to": HOLDOUT_TO,
            "symbols": SYMBOLS,
            "opened_by_this_workflow": False,
        },
        "autosync_used": False,
    }


def score_development(batch: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    integrity_events = 0
    for test in batch["tests"]:
        rows.extend(tester.read_semicolon_csv(Path(test["trades"]["path"])))
        integrity_events += int(test["integrity"].get("integrity_events", 0))
    return score_rows(rows, integrity_events)


def _write_local(kind: str, payload: dict[str, Any]) -> Path:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    out = workspace / "d053" / kind / stamp() / f"{kind}.json"
    runner.write_receipt(out, payload)
    return out


def publish_failure(stage: str, kind: str, error: Exception, source_sha: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "D053_WORKFLOW_INCOMPLETE_ENGINEERING_OR_TOOLING",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "error": str(error),
        "source_sha256": source_sha,
        "scientific_verdict": None,
        "holdout_opened": False,
        "autosync_used": False,
    }
    local = _write_local(kind, payload)
    payload["local_path"] = str(local)
    payload["github_transport"] = result_transport.safe_publish_event(
        EXPERIMENT_ID, stage, kind, payload
    )
    return payload


def main() -> int:
    identities = verify_frozen_repository_identity()
    _, manifest = experiment.load_manifest(KEY)
    source_sha = identities["source_sha256"]

    source_freeze = {
        "schema_version": 1,
        "status": "D053_SOURCE_IDENTITY_FROZEN_BEFORE_MT5_OUTCOME",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "preregistration": PREREG,
        "preregistration_git_blob_sha": identities["prereg_blob"],
        "source": SOURCE,
        "source_git_blob_sha": identities["source_blob"],
        "source_sha256": source_sha,
        "symbols": SYMBOLS,
        "opening_range_server_time": "16:30:00-16:59:59",
        "entry_from_server_time": "17:00:00",
        "forced_exit_server_time": "22:45:00",
        "holdout_window_locked_unopened": [HOLDOUT_FROM, HOLDOUT_TO],
        "autosync_used": False,
    }
    local = _write_local("source-freeze", source_freeze)
    source_freeze["local_path"] = str(local)
    source_freeze["github_transport"] = result_transport.safe_publish_event(
        EXPERIMENT_ID, "smoke", "d053-source-freeze", source_freeze
    )
    print(json.dumps(source_freeze, indent=2, ensure_ascii=False))

    rc = runner.cmd_compile(KEY)
    if rc != 0:
        raise D053Error("D053 compile failed")

    try:
        smoke = run_stage(manifest, source_sha, "smoke", SMOKE_SYMBOLS, SMOKE_FROM, SMOKE_TO)
    except Exception as exc:
        failure = publish_failure("smoke", "d053-smoke-invalid", exc, source_sha)
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2

    if sum(test["integrity"]["trades"] for test in smoke["tests"]) <= 0:
        failure = publish_failure(
            "smoke", "d053-smoke-invalid",
            D053Error("smoke produced zero trades across batch"), source_sha
        )
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2

    smoke_local = _write_local("smoke-pass", smoke)
    smoke["local_path"] = str(smoke_local)
    smoke["github_transport"] = result_transport.safe_publish_event(
        EXPERIMENT_ID, "smoke", "d053-smoke-pass", smoke
    )
    print(json.dumps({
        "status": "D053_SMOKE_PASS",
        "symbols": SMOKE_SYMBOLS,
        "range_days": {test["symbol"]: test["integrity"]["range_days"] for test in smoke["tests"]},
        "trades": {test["symbol"]: test["integrity"]["trades"] for test in smoke["tests"]},
        "source_sha256": source_sha,
        "autosync_used": False,
    }, indent=2, ensure_ascii=False))

    try:
        dev = run_stage(manifest, source_sha, "development", SYMBOLS, DEV_FROM, DEV_TO)
    except Exception as exc:
        failure = publish_failure("development", "d053-development-invalid", exc, source_sha)
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 3

    dev_local = _write_local("development-batch", dev)
    dev["local_path"] = str(dev_local)
    dev_transport = result_transport.safe_publish_event(
        EXPERIMENT_ID, "development", "d053-development-batch", dev
    )

    score = score_development(dev)
    score["source_sha256"] = source_sha
    score["batch_path"] = dev["batch_path"]
    score["batch_transport"] = dev_transport
    score_local = _write_local("development-score", score)
    score["score_path"] = str(score_local)
    score["github_transport"] = result_transport.safe_publish_event(
        EXPERIMENT_ID, "development", "d053-development-score", score
    )
    print(json.dumps(score, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            identities = verify_frozen_repository_identity()
            failure = publish_failure("development", "d053-workflow-incomplete", exc, identities["source_sha256"])
            print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception as publish_exc:
            print(f"D053 WORKFLOW ERROR: {exc}; failure publication also failed: {publish_exc}", file=sys.stderr)
        raise SystemExit(1)
