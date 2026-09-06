#!/usr/bin/env python3
"""Deterministic MT5 Strategy Tester execution for Guardian Research Runner.

Scope v1:
- consumes the active experiment manifest;
- requires a matching successful compile receipt;
- generates a one-test MT5 configuration file;
- runs one symbol sequentially with the reference tester model;
- quarantines stale expected CSV outputs before launch;
- collects immutable STATS/TRADES evidence from FILE_COMMON;
- validates source identity and lifecycle integrity;
- can recover a completed local test whose immutable evidence was copied before
  a post-run parser failure, without re-running MT5.

No Git transport and no AutoSync are involved.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import runner

ROOT = Path(__file__).resolve().parents[2]


class TestError(RuntimeError):
    pass


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clean_symbol(symbol: str) -> str:
    return symbol.replace(".", "_").replace("#", "_").replace(" ", "_")


def decode_csv_text(path: Path) -> tuple[str, str]:
    """Decode MT5 CSV deterministically, including FILE_UNICODE UTF-16 output."""
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeDecodeError as exc:
            raise TestError(f"cannot decode UTF-16 CSV {path}: {exc}") from exc

    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise TestError(f"cannot decode CSV with supported encodings: {path}")


def read_semicolon_csv(path: Path) -> list[dict[str, str]]:
    text, _ = decode_csv_text(path)
    with io.StringIO(text, newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def latest_compile_receipt(config: dict[str, Any], manifest: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    base = runner._expand_path(config["workspace_dir"]) / "builds" / manifest["experiment_id"]
    candidates = sorted(base.glob("*/build.json"), reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "COMPILE_PASS":
            continue
        if payload.get("experiment_id") != manifest["experiment_id"]:
            continue
        if payload.get("deploy", {}).get("source_sha256", "").lower() != manifest["source"]["source_sha256"].lower():
            continue
        ex5 = Path(payload.get("compile", {}).get("ex5", ""))
        if not ex5.is_file():
            continue
        if runner.sha256_file(ex5).lower() != payload.get("compile", {}).get("ex5_sha256", "").lower():
            continue
        return path, payload
    raise TestError("no trusted COMPILE_PASS receipt matches the active source SHA; run runner.py compile first")


def validate_test_config(config: dict[str, Any]) -> list[str]:
    errors = runner.validate_config(config)
    for key in ("terminal_exe", "common_files_dir", "mt5_root"):
        if not config.get(key):
            errors.append(f"runner config missing: {key}")
    if config.get("terminal_exe") and not runner._expand_path(config["terminal_exe"]).is_file():
        errors.append(f"terminal executable not found: {config['terminal_exe']}")
    if config.get("common_files_dir") and not runner._expand_path(config["common_files_dir"]).is_dir():
        errors.append(f"common files directory not found: {config['common_files_dir']}")
    return errors


def expected_output_names(manifest: dict[str, Any], stage_name: str, symbol: str) -> tuple[str, str]:
    contract = manifest.get("runner_contract", {})
    output = contract.get("output", {})
    stage_tokens = output.get("stage_tokens", {})
    if stage_name not in stage_tokens:
        raise TestError(f"runner contract has no output stage token for {stage_name}")
    values = {"stage_token": stage_tokens[stage_name], "symbol_clean": clean_symbol(symbol)}
    try:
        return output["stats_template"].format(**values), output["trades_template"].format(**values)
    except KeyError as exc:
        raise TestError(f"invalid output template: missing token {exc}") from exc


def ensure_stage_allowed(manifest: dict[str, Any], stage_name: str, symbol: str) -> dict[str, Any]:
    stages = manifest["stages"]
    if stage_name not in stages:
        raise TestError(f"unknown stage: {stage_name}")
    stage = stages[stage_name]
    if symbol not in stage["symbols"]:
        raise TestError(f"symbol {symbol} is outside frozen {stage_name} universe")

    contract = manifest.get("runner_contract", {})
    default_stage = contract.get("default_stage")
    if stage_name != default_stage:
        raise TestError(
            f"v1 runner only executes the EA default stage ({default_stage}) without a frozen .set file; "
            f"requested {stage_name}"
        )

    if stage_name == "confirmation" and manifest.get("results", {}).get("development") is None:
        raise TestError("confirmation is locked until a development result exists and passes gates")
    if stage.get("status") in {"FAIL", "INVALID"}:
        raise TestError(f"stage {stage_name} is closed with status {stage['status']}")
    return stage


def render_tester_ini(manifest: dict[str, Any], stage_name: str, stage: dict[str, Any], symbol: str, model: int) -> str:
    contract = manifest["runner_contract"]
    execution = manifest["execution"]
    from_date = stage["from"].replace("-", ".")
    to_date = stage["to"].replace("-", ".")
    expert = contract["expert_relative_path"]
    period = execution["timeframe"]
    currency = execution["account_currency"]

    return "\n".join([
        "[Tester]",
        f"Expert={expert}",
        f"Symbol={symbol}",
        f"Period={period}",
        f"Model={model}",
        "ExecutionMode=0",
        "Optimization=0",
        f"FromDate={from_date}",
        f"ToDate={to_date}",
        "ForwardMode=0",
        "Deposit=10000",
        f"Currency={currency}",
        "Leverage=1:100",
        "UseLocal=1",
        "UseRemote=0",
        "UseCloud=0",
        "Visual=0",
        "ShutdownTerminal=1",
        "",
    ])


def quarantine_stale(paths: list[Path], workspace: Path, experiment_id: str, stage_name: str, symbol: str) -> list[str]:
    moved: list[str] = []
    existing = [p for p in paths if p.exists()]
    if not existing:
        return moved
    destination = workspace / "quarantine" / "stale_outputs" / experiment_id / stage_name / clean_symbol(symbol) / utc_stamp()
    destination.mkdir(parents=True, exist_ok=True)
    for path in existing:
        target = destination / path.name
        shutil.move(str(path), str(target))
        moved.append(str(target))
    return moved


def validate_evidence(stats_path: Path, trades_path: Path, manifest: dict[str, Any], stage_name: str, symbol: str) -> dict[str, Any]:
    stats = read_semicolon_csv(stats_path)
    trades = read_semicolon_csv(trades_path)
    if not stats:
        raise TestError("STATS CSV contains no data rows")

    statuses = [row.get("status", "") for row in stats]
    if "INIT" not in statuses or "READY" not in statuses:
        raise TestError(f"STATS lifecycle missing INIT/READY: {statuses[:10]}")
    final = stats[-1]
    if final.get("status") != "FINAL":
        raise TestError(f"run did not finish cleanly; final status={final.get('status')} fatal={final.get('fatal_status')}")

    expected_source = Path(manifest["source"]["canonical_path"]).name
    expected_version = str(manifest["source"]["version"])
    if final.get("source_name") != expected_source:
        raise TestError(f"source_name mismatch: expected={expected_source} got={final.get('source_name')}")
    if final.get("source_version") != expected_version:
        raise TestError(f"source_version mismatch: expected={expected_version} got={final.get('source_version')}")
    if symbol not in final.get("symbol", ""):
        raise TestError(f"symbol mismatch in STATS: expected contains {symbol}, got={final.get('symbol')}")
    if final.get("fatal_status") not in ("", None):
        raise TestError(f"fatal_status is non-empty: {final.get('fatal_status')}")

    numeric_fields = ("trades_opened", "trades_closed", "csv_trade_rows", "invalid_price", "invalid_risk", "pnl_calc_failures")
    values: dict[str, int] = {}
    for field in numeric_fields:
        try:
            values[field] = int(final.get(field, ""))
        except ValueError as exc:
            raise TestError(f"invalid integer in STATS {field}={final.get(field)!r}") from exc

    if not (values["trades_opened"] == values["trades_closed"] == values["csv_trade_rows"] == len(trades)):
        raise TestError(
            "lifecycle mismatch: "
            f"opened={values['trades_opened']} closed={values['trades_closed']} "
            f"rows={values['csv_trade_rows']} parsed_trades={len(trades)}"
        )
    if values["invalid_price"] or values["invalid_risk"] or values["pnl_calc_failures"]:
        raise TestError(
            f"integrity counters non-zero: invalid_price={values['invalid_price']} "
            f"invalid_risk={values['invalid_risk']} pnl_calc_failures={values['pnl_calc_failures']}"
        )

    contract = manifest["runner_contract"]
    expected_stage_token = contract["output"]["stage_tokens"][stage_name]
    if final.get("run_stage") != expected_stage_token:
        raise TestError(f"run_stage mismatch: expected={expected_stage_token} got={final.get('run_stage')}")

    _, stats_encoding = decode_csv_text(stats_path)
    _, trades_encoding = decode_csv_text(trades_path)
    return {
        "final_status": final["status"],
        "source_name": final["source_name"],
        "source_version": final["source_version"],
        "run_stage": final["run_stage"],
        "symbol": final["symbol"],
        "trades": len(trades),
        "trades_opened": values["trades_opened"],
        "trades_closed": values["trades_closed"],
        "invalid_price": values["invalid_price"],
        "invalid_risk": values["invalid_risk"],
        "pnl_calc_failures": values["pnl_calc_failures"],
        "stats_encoding": stats_encoding,
        "trades_encoding": trades_encoding,
    }


def run_one(identifier: str, stage_name: str, symbol: str, model: int | None = None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    source_path, blockers = runner.source_readiness(manifest)
    if blockers or source_path is None:
        raise TestError("source is not execution-ready: " + "; ".join(blockers))

    stage = ensure_stage_allowed(manifest, stage_name, symbol)
    config = runner.load_config()
    config_errors = validate_test_config(config)
    if config_errors:
        raise TestError("invalid local config: " + "; ".join(config_errors))

    receipt_path, compile_receipt = latest_compile_receipt(config, manifest)
    contract = manifest["runner_contract"]
    reference_model = int(contract["tester_model_reference"])
    selected_model = reference_model if model is None else int(model)
    if selected_model != reference_model:
        raise TestError(
            f"normal execution is pinned to reference tester model {reference_model}; "
            "fast-model conformance must be implemented/proved separately"
        )

    common = runner._expand_path(config["common_files_dir"])
    workspace = runner._expand_path(config["workspace_dir"])
    stats_name, trades_name = expected_output_names(manifest, stage_name, symbol)
    expected_paths = [common / stats_name, common / trades_name]
    quarantined = quarantine_stale(expected_paths, workspace, manifest["experiment_id"], stage_name, symbol)

    run_id = f"{utc_stamp()}_{clean_symbol(symbol)}_M{selected_model}"
    run_dir = workspace / "runs" / manifest["experiment_id"] / stage_name / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    ini_path = run_dir / "tester.ini"
    ini_path.write_text(render_tester_ini(manifest, stage_name, stage, symbol, selected_model), encoding="utf-8", newline="\n")

    terminal = runner._expand_path(config["terminal_exe"])
    command = [str(terminal), f"/config:{ini_path}"]
    if bool(config.get("portable_mode", True)):
        command.append("/portable")

    timeout_seconds = int(config.get("tester_timeout_seconds", 14400))
    started = datetime.now(timezone.utc)
    process = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout_seconds)
    finished = datetime.now(timezone.utc)

    missing = [str(path) for path in expected_paths if not path.is_file()]
    if missing:
        raise TestError(
            f"MT5 process exited code={process.returncode} but expected FILE_COMMON output is missing: {missing}; "
            f"stdout={process.stdout[-1000:]} stderr={process.stderr[-1000:]}"
        )

    collected_stats = run_dir / stats_name
    collected_trades = run_dir / trades_name
    shutil.copy2(expected_paths[0], collected_stats)
    shutil.copy2(expected_paths[1], collected_trades)
    integrity = validate_evidence(collected_stats, collected_trades, manifest, stage_name, symbol)

    evidence = {
        "schema_version": 1,
        "status": "TEST_PASS_INTEGRITY",
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "stage": stage_name,
        "symbol": symbol,
        "tester_model": selected_model,
        "started_at_utc": started.isoformat(),
        "finished_at_utc": finished.isoformat(),
        "terminal_exit_code": process.returncode,
        "command": command,
        "compile_receipt": str(receipt_path),
        "source_sha256": manifest["source"]["source_sha256"],
        "ex5_sha256": compile_receipt["compile"]["ex5_sha256"],
        "quarantined_stale_outputs": quarantined,
        "stats": {"path": str(collected_stats), "sha256": runner.sha256_file(collected_stats)},
        "trades": {"path": str(collected_trades), "sha256": runner.sha256_file(collected_trades)},
        "integrity": integrity,
        "recovered_after_parser_failure": False,
        "autosync_used": False,
    }
    runner.write_receipt(run_dir / "run.json", evidence)
    return evidence


def recover_latest(identifier: str, stage_name: str, symbol: str) -> dict[str, Any]:
    """Validate the newest copied evidence set lacking run.json; never launches MT5."""
    _, manifest_path, manifest = runner.load_context(identifier)
    source_path, blockers = runner.source_readiness(manifest)
    if blockers or source_path is None:
        raise TestError("source is not execution-ready: " + "; ".join(blockers))
    ensure_stage_allowed(manifest, stage_name, symbol)

    config = runner.load_config()
    config_errors = validate_test_config(config)
    if config_errors:
        raise TestError("invalid local config: " + "; ".join(config_errors))
    receipt_path, compile_receipt = latest_compile_receipt(config, manifest)

    workspace = runner._expand_path(config["workspace_dir"])
    stats_name, trades_name = expected_output_names(manifest, stage_name, symbol)
    base = workspace / "runs" / manifest["experiment_id"] / stage_name
    candidates = sorted((p for p in base.glob(f"*_{clean_symbol(symbol)}_M*") if p.is_dir()), reverse=True) if base.exists() else []
    run_dir: Path | None = None
    for candidate in candidates:
        if (candidate / "run.json").exists():
            continue
        if (candidate / stats_name).is_file() and (candidate / trades_name).is_file():
            run_dir = candidate
            break
    if run_dir is None:
        raise TestError("no recoverable incomplete run with copied STATS/TRADES evidence was found")

    collected_stats = run_dir / stats_name
    collected_trades = run_dir / trades_name
    integrity = validate_evidence(collected_stats, collected_trades, manifest, stage_name, symbol)
    reference_model = int(manifest["runner_contract"]["tester_model_reference"])
    evidence = {
        "schema_version": 1,
        "status": "TEST_PASS_INTEGRITY",
        "experiment_id": manifest["experiment_id"],
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "stage": stage_name,
        "symbol": symbol,
        "tester_model": reference_model,
        "started_at_utc": None,
        "finished_at_utc": datetime.fromtimestamp(max(collected_stats.stat().st_mtime, collected_trades.stat().st_mtime), tz=timezone.utc).isoformat(),
        "terminal_exit_code": None,
        "command": ["RECOVER_EXISTING_COPIED_EVIDENCE_NO_MT5_RERUN"],
        "compile_receipt": str(receipt_path),
        "source_sha256": manifest["source"]["source_sha256"],
        "ex5_sha256": compile_receipt["compile"]["ex5_sha256"],
        "quarantined_stale_outputs": [],
        "stats": {"path": str(collected_stats), "sha256": runner.sha256_file(collected_stats)},
        "trades": {"path": str(collected_trades), "sha256": runner.sha256_file(collected_trades)},
        "integrity": integrity,
        "recovered_after_parser_failure": True,
        "recovery_reason": "MT5 completed and immutable evidence was copied before the previous UTF-8-only CSV parser failed on MT5 UTF-16 BOM output",
        "autosync_used": False,
    }
    runner.write_receipt(run_dir / "run.json", evidence)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run or recover one Guardian MT5 Strategy Tester case")
    parser.add_argument("experiment", help="D037 or experiment manifest path")
    parser.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--recover-latest", action="store_true", help="validate copied evidence from latest incomplete run without launching MT5")
    args = parser.parse_args()
    try:
        evidence = recover_latest(args.experiment, args.stage, args.symbol) if args.recover_latest else run_one(args.experiment, args.stage, args.symbol)
    except (TestError, runner.RunnerError, experiment.ManifestError, subprocess.TimeoutExpired, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
