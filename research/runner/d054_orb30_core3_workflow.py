#!/usr/bin/env python3
"""D054 ORB30 Core-3 independent Jul-Aug 2026 confirmation workflow.

D054 is a derived hypothesis selected from D053 discovery. It reuses the exact
D053 v1.01 trading source and spends only untouched Jul-Aug 2026 evidence.
"""
from __future__ import annotations

import json
import math
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import d053_orb30_index_workflow as d053
import experiment
import result_transport
import runner
import tester

ROOT = Path(__file__).resolve().parents[2]
KEY = "D054"
EXPERIMENT_ID = "D054-ORB30-CORE3-JUL-AUG2026-CONFIRMATION-V0"
PREREG = "research/campaigns/D054_ORB30_CORE3_JUL_AUG_2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md"
EXPECTED_PREREG_BLOB = "2c1bb149664a9e4153c6f6cb8ae59ce1e874da57"
SOURCE = "research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5"
SOURCE_VERSION = "1.01"
EXPECTED_SOURCE_BLOB = "7da58ecf8968d6814b634be0ee0043b9616fb6c6"
EXPECTED_SOURCE_SHA256 = "d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad"
SYMBOLS = ["SPX500", "NDX100", "US30"]
SMOKE_FROM, SMOKE_TO = "2023-10-02", "2023-10-31"
HOLDOUT_FROM, HOLDOUT_TO = "2026-07-01", "2026-08-31"
BOOTSTRAP_REPS = 20_000
BOOTSTRAP_SEED = 540054

FROZEN_CONFIRMATION_GATES: dict[str, Any] = {
    "aggregate_n_min": 100,
    "each_symbol_n_min": 25,
    "aggregate_mean_net_r_positive": True,
    "aggregate_pf_min": 1.05,
    "aggregate_total_net_r_positive": True,
    "spread_stress_total_positive": True,
    "positive_symbols_min": 2,
    "july_total_positive": True,
    "august_total_positive": True,
    "long_mean_positive": True,
    "short_mean_positive": True,
    "day_block_bootstrap_lower_95_positive": True,
    "max_positive_symbol_contribution_share": 0.70,
    "integrity_events_max": 0,
}


class D054Error(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def git_blob_sha(relative: str) -> str:
    completed = subprocess.run(
        ["git", "hash-object", relative], cwd=ROOT,
        capture_output=True, text=True, check=False,
    )
    if completed.returncode != 0:
        raise D054Error(f"git hash-object failed for {relative}: {completed.stderr.strip()}")
    value = completed.stdout.strip()
    if len(value) != 40:
        raise D054Error(f"invalid git blob for {relative}: {value}")
    return value


def verify_frozen_repository_identity() -> dict[str, str]:
    prereg_blob = git_blob_sha(PREREG)
    source_blob = git_blob_sha(SOURCE)
    source_sha = runner.source_identity_sha256(ROOT / SOURCE, runner.SOURCE_SHA_MODE_TEXT_LF)
    if prereg_blob.lower() != EXPECTED_PREREG_BLOB:
        raise D054Error(f"prereg blob mismatch expected={EXPECTED_PREREG_BLOB} actual={prereg_blob}")
    if source_blob.lower() != EXPECTED_SOURCE_BLOB:
        raise D054Error(f"source blob mismatch expected={EXPECTED_SOURCE_BLOB} actual={source_blob}")
    if source_sha.lower() != EXPECTED_SOURCE_SHA256:
        raise D054Error(f"source SHA mismatch expected={EXPECTED_SOURCE_SHA256} actual={source_sha}")

    manifest_path, manifest = experiment.load_manifest(KEY)
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise D054Error("D054 manifest invalid: " + "; ".join(errors))
    if manifest["experiment_id"] != EXPERIMENT_ID:
        raise D054Error("D054 manifest experiment_id mismatch")
    if manifest["preregistration"].get("git_blob_sha") != prereg_blob:
        raise D054Error("D054 manifest prereg blob mismatch")
    if manifest["source"].get("git_blob_sha") != source_blob:
        raise D054Error("D054 manifest source blob mismatch")
    if manifest["source"].get("source_sha256") != source_sha:
        raise D054Error("D054 manifest source SHA mismatch")
    if manifest["execution"]["symbols"] != SYMBOLS:
        raise D054Error("D054 universe mismatch")

    conf = manifest["stages"]["confirmation"]
    if conf["from"] != HOLDOUT_FROM or conf["to"] != HOLDOUT_TO or conf["symbols"] != SYMBOLS:
        raise D054Error("D054 holdout contract mismatch")
    if conf.get("status") != "UNOPENED":
        raise D054Error("D054 holdout must remain UNOPENED before operator execution")
    if conf.get("gates") != FROZEN_CONFIRMATION_GATES:
        raise D054Error("D054 manifest confirmation gates differ from frozen runner gates")

    return {"prereg_blob": prereg_blob, "source_blob": source_blob, "source_sha256": source_sha}


def patch_d053_runtime_for_exact_reuse() -> None:
    """Reuse D053's proven MT5 executor/CSV validator, changing only evidence identity/universe."""
    d053.EXPERIMENT_ID = EXPERIMENT_ID
    d053.SOURCE_VERSION = SOURCE_VERSION
    d053.EXPECTED_SOURCE_BLOB = EXPECTED_SOURCE_BLOB
    d053.EXPECTED_SOURCE_SHA256 = EXPECTED_SOURCE_SHA256
    d053.SYMBOLS = list(SYMBOLS)
    d053.SMOKE_SYMBOLS = list(SYMBOLS)


def run_stage(
    manifest: dict[str, Any], source_sha: str, stage: str, start: str, end: str
) -> dict[str, Any]:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    batch_dir = workspace / "d054" / stage / stamp()
    batch_dir.mkdir(parents=True, exist_ok=False)
    receipt = batch_dir / "batch.json"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": "RUNNING",
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "symbols": list(SYMBOLS),
        "from": start,
        "to": end,
        "execution_mode": "SEQUENTIAL_ONE_MT5_RUN_PER_SYMBOL_MODEL0_EXACT_D053_V101_SOURCE",
        "source_sha256": source_sha,
        "tests": [],
        "autosync_used": False,
    }
    runner.write_receipt(receipt, payload)
    symbol = ""
    try:
        for symbol in SYMBOLS:
            result = d053.run_symbol(manifest, source_sha, stage, symbol, start, end)
            payload["tests"].append(result)
            runner.write_receipt(receipt, payload)
    except Exception as exc:
        payload["status"] = "D054_BATCH_INVALID_ENGINEERING"
        payload["failed_symbol"] = symbol
        payload["error"] = str(exc)
        payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        runner.write_receipt(receipt, payload)
        raise D054Error(
            f"D054 {stage} stopped on {symbol}; completed={len(payload['tests'])}; "
            f"receipt={receipt}; cause={exc}"
        ) from exc

    payload["status"] = "D054_BATCH_PASS_INTEGRITY"
    payload["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    payload["batch_path"] = str(receipt)
    runner.write_receipt(receipt, payload)
    return payload


def as_float(row: dict[str, str], key: str) -> float:
    try:
        value = float(row[key])
    except Exception as exc:
        raise D054Error(f"invalid {key}={row.get(key)!r}") from exc
    if not math.isfinite(value):
        raise D054Error(f"non-finite {key}")
    return value


def pf(values: list[float]) -> float | None:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def score_confirmation(batch: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    integrity_events = 0
    for test in batch["tests"]:
        rows.extend(tester.read_semicolon_csv(Path(test["trades"]["path"])))
        integrity_events += int(test["integrity"].get("integrity_events", 0))

    net: list[float] = []
    stress: list[float] = []
    symbol_values: dict[str, list[float]] = defaultdict(list)
    side_values: dict[str, list[float]] = defaultdict(list)
    day_values: dict[str, list[float]] = defaultdict(list)
    month_values: dict[str, list[float]] = defaultdict(list)
    mfe: list[float] = []
    mae: list[float] = []

    for row in rows:
        symbol = str(row["symbol"])
        if symbol not in SYMBOLS:
            raise D054Error(f"row outside D054 universe: {symbol}")
        side = str(row["side"])
        if side not in ("LONG", "SHORT"):
            raise D054Error(f"invalid side={side}")
        day = str(row["day_key"])
        if len(day) != 8 or not day.isdigit() or not day.startswith("2026"):
            raise D054Error(f"invalid holdout day_key={day}")

        value = as_float(row, "net_r")
        net.append(value)
        stress.append(as_float(row, "net_r_spread_x1_5"))
        symbol_values[symbol].append(value)
        side_values[side].append(value)
        day_values[day].append(value)
        month_values[day[:6]].append(value)
        mfe.append(as_float(row, "mfe_r"))
        mae.append(as_float(row, "mae_r"))

    aggregate_pf = pf(net)
    per_symbol_n = {s: len(symbol_values[s]) for s in SYMBOLS}
    per_symbol_total = {s: sum(symbol_values[s]) for s in SYMBOLS}
    positive_symbols = [s for s in SYMBOLS if per_symbol_total[s] > 0]
    positive_total = sum(per_symbol_total[s] for s in positive_symbols)
    max_positive_share = (
        max((per_symbol_total[s] / positive_total for s in positive_symbols), default=0.0)
        if positive_total > 0 else 0.0
    )
    ci = d053.block_bootstrap_ci(day_values, BOOTSTRAP_REPS, BOOTSTRAP_SEED)
    mean = statistics.fmean(net) if net else 0.0
    total = sum(net)
    long_mean = statistics.fmean(side_values["LONG"]) if side_values["LONG"] else 0.0
    short_mean = statistics.fmean(side_values["SHORT"]) if side_values["SHORT"] else 0.0
    july_total = sum(month_values["202607"])
    august_total = sum(month_values["202608"])

    gates = {
        "aggregate_n_min": len(net) >= 100,
        "each_symbol_n_min": all(per_symbol_n[s] >= 25 for s in SYMBOLS),
        "aggregate_mean_net_r_positive": mean > 0,
        "aggregate_pf_min": bool(aggregate_pf is not None and (math.isinf(aggregate_pf) or aggregate_pf >= 1.05)),
        "aggregate_total_net_r_positive": total > 0,
        "spread_stress_total_positive": sum(stress) > 0,
        "positive_symbols_min": len(positive_symbols) >= 2,
        "july_total_positive": july_total > 0,
        "august_total_positive": august_total > 0,
        "long_mean_positive": long_mean > 0,
        "short_mean_positive": short_mean > 0,
        "day_block_bootstrap_lower_95_positive": ci["lower_95"] > 0,
        "max_positive_symbol_contribution_share": max_positive_share <= 0.70,
        "integrity_events_max": integrity_events == 0,
    }
    passed = all(gates.values())

    return {
        "schema_version": 1,
        "status": "D054_CONFIRMED_CORE3_ENTRY_ALPHA" if passed else "D054_UNCONFIRMED_CLOSE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "stage": "confirmation",
        "metrics": {
            "aggregate_n": len(net),
            "aggregate_mean_net_r": mean,
            "aggregate_pf": None if aggregate_pf is None or math.isinf(aggregate_pf) else aggregate_pf,
            "aggregate_pf_infinite": bool(aggregate_pf is not None and math.isinf(aggregate_pf)),
            "aggregate_total_net_r": total,
            "spread_stress_total_net_r": sum(stress),
            "per_symbol_n": per_symbol_n,
            "per_symbol_total_net_r": per_symbol_total,
            "positive_symbols": positive_symbols,
            "positive_symbols_n": len(positive_symbols),
            "max_positive_symbol_contribution_share": max_positive_share,
            "month_total_net_r": {
                "202607": july_total,
                "202608": august_total,
            },
            "side": {
                "LONG": {
                    "n": len(side_values["LONG"]),
                    "mean_net_r": long_mean,
                    "total_net_r": sum(side_values["LONG"]),
                },
                "SHORT": {
                    "n": len(side_values["SHORT"]),
                    "mean_net_r": short_mean,
                    "total_net_r": sum(side_values["SHORT"]),
                },
            },
            "day_block_bootstrap": ci,
            "path_descriptive": {
                "mean_mfe_r": statistics.fmean(mfe) if mfe else 0.0,
                "mean_mae_r": statistics.fmean(mae) if mae else 0.0,
            },
            "integrity_events": integrity_events,
        },
        "gates": gates,
        "all_gates_pass": passed,
        "frozen_gate_contract": FROZEN_CONFIRMATION_GATES,
        "d053_verdict_unchanged": "D053_REJECT_V0",
        "discovery_period_reused_as_oos": False,
        "posthoc_symbol_or_direction_deletion": False,
        "autosync_used": False,
    }


def write_local(kind: str, payload: dict[str, Any]) -> Path:
    workspace = runner._expand_path(runner.load_config()["workspace_dir"])
    out = workspace / "d054" / kind / stamp() / f"{kind}.json"
    runner.write_receipt(out, payload)
    return out


def publish_failure(stage: str, kind: str, exc: Exception, source_sha: str) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "status": "D054_ENGINEERING_INCOMPLETE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "stage": stage,
        "error": str(exc),
        "source_sha256": source_sha,
        "scientific_verdict": None,
        "autosync_used": False,
    }
    local = write_local(kind, payload)
    payload["local_path"] = str(local)
    payload["github_transport"] = result_transport.safe_publish_event(KEY, stage, kind, payload)
    return payload


def main() -> int:
    identities = verify_frozen_repository_identity()
    patch_d053_runtime_for_exact_reuse()
    _, manifest = experiment.load_manifest(KEY)
    source_sha = identities["source_sha256"]

    freeze = {
        "schema_version": 1,
        "status": "D054_FROZEN_BEFORE_HOLDOUT",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "preregistration": PREREG,
        "preregistration_git_blob_sha": identities["prereg_blob"],
        "source": SOURCE,
        "source_git_blob_sha": identities["source_blob"],
        "source_sha256": source_sha,
        "symbols": SYMBOLS,
        "holdout": [HOLDOUT_FROM, HOLDOUT_TO],
        "confirmation_gate_contract": FROZEN_CONFIRMATION_GATES,
        "exact_d053_v101_source_reuse": True,
        "autosync_used": False,
    }
    local = write_local("source-freeze", freeze)
    freeze["local_path"] = str(local)
    freeze["github_transport"] = result_transport.safe_publish_event(
        KEY, "smoke", "d054-source-freeze", freeze
    )
    print(json.dumps(freeze, indent=2, ensure_ascii=False))

    rc = runner.cmd_compile(KEY)
    if rc != 0:
        raise D054Error("D054 compile failed")

    try:
        smoke = run_stage(manifest, source_sha, "smoke", SMOKE_FROM, SMOKE_TO)
    except Exception as exc:
        failure = publish_failure("smoke", "d054-smoke-invalid", exc, source_sha)
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2

    if any(int(t["integrity"]["trades"]) <= 0 for t in smoke["tests"]):
        failure = publish_failure(
            "smoke", "d054-smoke-invalid",
            D054Error("one or more smoke symbols produced zero trades"), source_sha,
        )
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 2

    smoke_local = write_local("smoke-pass", smoke)
    smoke["local_path"] = str(smoke_local)
    smoke["github_transport"] = result_transport.safe_publish_event(
        KEY, "smoke", "d054-smoke-pass", smoke
    )
    print(json.dumps({
        "status": "D054_SMOKE_PASS_HOLDOUT_NOW_OPENS",
        "symbols": SYMBOLS,
        "trades": {t["symbol"]: t["integrity"]["trades"] for t in smoke["tests"]},
        "source_sha256": source_sha,
        "frozen_gates": FROZEN_CONFIRMATION_GATES,
    }, indent=2, ensure_ascii=False))

    try:
        confirmation = run_stage(manifest, source_sha, "confirmation", HOLDOUT_FROM, HOLDOUT_TO)
    except Exception as exc:
        failure = publish_failure("confirmation", "d054-confirmation-invalid", exc, source_sha)
        print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        return 3

    batch_local = write_local("confirmation-batch", confirmation)
    confirmation["local_path"] = str(batch_local)
    batch_transport = result_transport.safe_publish_event(
        KEY, "confirmation", "d054-confirmation-batch", confirmation
    )

    score = score_confirmation(confirmation)
    score["source_sha256"] = source_sha
    score["batch_path"] = confirmation["batch_path"]
    score["batch_transport"] = batch_transport
    score_local = write_local("confirmation-score", score)
    score["score_path"] = str(score_local)
    score["github_transport"] = result_transport.safe_publish_event(
        KEY, "confirmation", "d054-confirmation-score", score
    )
    print(json.dumps(score, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            identities = verify_frozen_repository_identity()
            failure = publish_failure(
                "confirmation", "d054-workflow-incomplete", exc, identities["source_sha256"]
            )
            print(json.dumps(failure, indent=2, ensure_ascii=False), file=sys.stderr)
        except Exception as publish_exc:
            print(
                f"D054 WORKFLOW ERROR: {exc}; failure publication also failed: {publish_exc}",
                file=sys.stderr,
            )
        raise SystemExit(1)
