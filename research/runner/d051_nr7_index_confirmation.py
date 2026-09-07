#!/usr/bin/env python3
"""Run preregistered D051 NR7 equity-index confirmation on untouched 2026 H1.

D051 is a new hypothesis generated from D047 development discovery. It does not
rewrite D038 or D047 verdicts. The executable source is generated deterministically
from the exact D047 transport derivative, changing evidence identity only.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import batch
import experiment
import market_transport_lab_v1 as lab
import result_transport
import runner
import tester
import trade_path_validate

ROOT = Path(__file__).resolve().parents[2]
PARENT = "D038"
EXPERIMENT_ID = "D051-NR7-EQUITY-INDEX-CLUSTER-CONFIRMATION-V0"
PREREG = "research/campaigns/D051_NR7_EQUITY_INDEX_CLUSTER_CONFIRMATION_V0_PREREGISTRATION_2026_09_07.md"
SYMBOLS = ["SPX500", "NDX100", "GER30", "US30"]
D047_GENERATED_SHA256 = "8718cf1ae5910577ae0c149348ad9981f8d30326ad86132b08296dd93e7f05f6"
GENERATED_DIR = ROOT / "local" / "d051_generated"
GENERATED_NAME = "D051_NR7_EquityIndex_Confirmation_M15_v1_00.mq5"
SOURCE_VERSION = "1.00-D051"


class D051Error(RuntimeError):
    pass


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def materialize_source() -> tuple[Path, str, dict[str, Any]]:
    base, base_sha, base_provenance = lab.materialize_transport_source(PARENT)
    if base_sha.lower() != D047_GENERATED_SHA256.lower():
        raise D051Error(
            f"D047 deterministic source identity changed: expected={D047_GENERATED_SHA256} actual={base_sha}"
        )

    text = base.read_text(encoding="utf-8")
    original = text

    text, n = re.subn(
        r'string\s+EXPERIMENT_ID\s*=\s*"[^"]+"\s*;',
        f'string EXPERIMENT_ID="{EXPERIMENT_ID}";',
        text,
        count=1,
    )
    if n != 1:
        raise D051Error("cannot replace D051 EXPERIMENT_ID")

    text, n = re.subn(
        r'string\s+SOURCE_NAME\s*=\s*"[^"]+"\s*;',
        f'string SOURCE_NAME="{GENERATED_NAME}";',
        text,
        count=1,
    )
    if n != 1:
        raise D051Error("cannot replace D051 SOURCE_NAME")

    text, n = re.subn(
        r'string\s+SOURCE_VERSION\s*=\s*"[^"]+"\s*;',
        f'string SOURCE_VERSION="{SOURCE_VERSION}";',
        text,
        count=1,
    )
    if n != 1:
        raise D051Error("cannot replace D051 SOURCE_VERSION")

    output_replacements = text.count('D038_V100_RUN_')
    if output_replacements != 2:
        raise D051Error(f"expected exactly 2 D038 output-name anchors; got {output_replacements}")
    text = text.replace('D038_V100_RUN_', 'D051_V100_RUN_')

    # Evidence identity only: reject accidental structural edits by checking that
    # reversing the exact identity substitutions reconstructs the D047 derivative.
    check = text.replace(f'string EXPERIMENT_ID="{EXPERIMENT_ID}";', 'string EXPERIMENT_ID="D047-MARKET-TRANSPORT-NR7-V1";', 1)
    check = check.replace(f'string SOURCE_NAME="{GENERATED_NAME}";', 'string SOURCE_NAME="MTL_V1_D038_NR7_TickPath_M15_v1_00.mq5";', 1)
    check = check.replace(f'string SOURCE_VERSION="{SOURCE_VERSION}";', 'string SOURCE_VERSION="1.00-MTL1";', 1)
    check = check.replace('D051_V100_RUN_', 'D038_V100_RUN_')
    if check != original:
        raise D051Error("D051 source differs from D047 beyond evidence identity")

    header = (
        "// D051 GENERATED EVIDENCE-IDENTITY DERIVATIVE. DO NOT EDIT.\n"
        f"// exact D047 derivative sha256={D047_GENERATED_SHA256}\n"
        "// scientific semantics unchanged; only experiment/source/output identity differs.\n"
    )
    text = header + text

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    generated = GENERATED_DIR / GENERATED_NAME
    generated.write_text(text, encoding="utf-8", newline="\n")
    generated_sha = runner.source_identity_sha256(generated, runner.SOURCE_SHA_MODE_TEXT_LF)

    provenance = {
        "parent": PARENT,
        "parent_source": base_provenance["parent_source"],
        "parent_source_sha256": base_provenance["parent_source_sha256"],
        "d047_generated_source_sha256": D047_GENERATED_SHA256,
        "d051_generated_source": str(generated.relative_to(ROOT)).replace("\\", "/"),
        "d051_generated_source_sha256": generated_sha,
        "patch_contract": "D047_EXACT_SEMANTICS_EVIDENCE_IDENTITY_ONLY",
    }
    return generated, generated_sha, provenance


def build_manifest(generated: Path, source_sha: str) -> tuple[Path, dict[str, Any]]:
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "strategy_family": "NR7 volatility-contraction breakout equity-index cluster confirmation",
        "status": "READY_CONFIRMATION",
        "hypothesis": "The unchanged D038/D047 NR7 breakout has a positive distributed edge across SPX500, NDX100, GER30 and US30 on untouched 2026 H1 data.",
        "preregistration": {
            "path": PREREG,
            "git_blob_sha": None,
            "frozen_before_result_inspection": True,
            "execution_deviations": [
                "D051 source is generated from the exact D047 transport derivative and changes evidence identity only.",
                "No new smoke is required because all four symbols already passed D047 Model0 engineering/integrity under identical strategy and transport semantics.",
            ],
        },
        "source": {
            "canonical_path": str(generated.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": source_sha,
            "source_sha256_mode": "UTF8_TEXT_LF_NORMALIZED",
            "git_blob_sha": None,
            "version": SOURCE_VERSION,
            "complete_repository_source": True,
            "strategy_semantics_frozen": True,
            "engineering_lineage": [
                "D038 frozen NR7 source",
                f"D047 deterministic market-transport derivative SHA {D047_GENERATED_SHA256}",
                "D051 evidence-identity-only derivative",
            ],
        },
        "execution": {
            "timeframe": "M15",
            "reference_timeframes": ["D1"],
            "symbols": list(SYMBOLS),
            "account_currency": "USD",
            "prop_firm_profile": "FUNDEDNEXT_D051_NR7_INDEX_CONFIRMATION",
        },
        "runner_contract": {
            "expert_relative_path": f"GuardianResearch\\{generated.stem}",
            "default_stage": "confirmation",
            "stage_selection": "TESTER_DATE_RANGE_ONLY",
            "tester_model_reference": 0,
            "tester_model_fast_candidate": None,
            "output": {
                "location": "FILE_COMMON",
                "stats_template": "D051_V100_{stage_token}_{symbol_clean}_STATS.csv",
                "trades_template": "D051_V100_{stage_token}_{symbol_clean}_TRADES.csv",
                "stage_tokens": {"smoke": "RUN", "development": "RUN", "confirmation": "RUN"},
            },
        },
        "cost_model": {
            "name": "D047_PARENT_COMPARABLE_INDEX_TRANSPORT",
            "spread_source": "tester executable bid/ask ticks",
            "commission_stress_multiplier": 1.5,
            "indices": "zero explicit commission; executable spread retained",
            "swap": "not applicable to D038 same-day/EOD exits except tester-end edge cases",
        },
        "stages": {
            "smoke": {
                "stage_name": "D051_ENGINEERING_PROOF_REUSED_FROM_D047",
                "from": "2023-10-02",
                "to": "2023-10-31",
                "symbols": ["SPX500"],
                "status": "PASS_REUSED_D047",
                "gates": {"engineering_only": True, "reused_exact_semantics": True},
                "result_paths": ["backtests/d047/live/events/smoke/market-transport-smoke/20260907T120557Z"],
            },
            "development": {
                "stage_name": "D051_DISCOVERY_FROM_D047_2024_2025",
                "from": "2024-01-02",
                "to": "2025-12-31",
                "symbols": list(SYMBOLS),
                "status": "DISCOVERY_EVIDENCE_REUSED",
                "gates": {"discovery_only_not_confirmation": True, "all_four_indices_positive": True},
                "result_paths": ["backtests/d047/live/events/development/market-transport-score/20260907T122446Z"],
            },
            "confirmation": {
                "stage_name": "D051_CONFIRM_2026_H1",
                "from": "2026-01-02",
                "to": "2026-06-30",
                "symbols": list(SYMBOLS),
                "status": "READY",
                "gates": {
                    "aggregate_n_min": 60,
                    "each_symbol_n_min": 10,
                    "aggregate_mean_net_r_strictly_positive": True,
                    "aggregate_pf_min": 1.10,
                    "positive_symbols_min": 3,
                    "aggregate_total_net_r_positive": True,
                    "max_positive_symbol_contribution_share": 0.60,
                    "integrity_events_max": 0,
                },
                "result_paths": [],
            },
        },
        "decision_policy": {
            "no_posthoc_rescue": True,
            "confirmation_locked_until_dev_pass": True,
            "invalid_run_is_not_strategy_reject": True,
        },
        "results": {
            "compile": None,
            "smoke": {"status": "REUSED_D047_ENGINEERING_PROOF"},
            "development": {
                "status": "D047_DISCOVERY_ONLY",
                "n": 299,
                "total_net_r": 31.66879718,
                "mean_net_r": 0.10591570963210702,
                "positive_symbols": 4,
            },
            "confirmation": None,
            "final_verdict": None,
        },
    }
    errors = experiment.validate_manifest(manifest)
    if errors:
        raise D051Error("invalid D051 synthetic manifest: " + "; ".join(errors))
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = GENERATED_DIR / "D051.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path, manifest


def pf(values: list[float]) -> float | None:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def score(batch_result: dict[str, Any], provenance: dict[str, Any], path_reports: list[dict[str, Any]]) -> dict[str, Any]:
    per_symbol_n: dict[str, int] = {}
    per_symbol_total: dict[str, float] = {}
    net: list[float] = []
    stress: list[float] = []
    integrity_events = 0

    for item in batch_result["tests"]:
        symbol = item["symbol"]
        rows = tester.read_semicolon_csv(Path(item["trades"]["path"]))
        per_symbol_n[symbol] = len(rows)
        total = 0.0
        for row in rows:
            value = float(row["net_r"])
            stressed = float(row["net_r_commission_x1_5"])
            if not math.isfinite(value) or not math.isfinite(stressed):
                raise D051Error(f"non-finite R in {symbol}")
            total += value
            net.append(value)
            stress.append(stressed)
        per_symbol_total[symbol] = total
        integ = item.get("integrity", {})
        integrity_events += int(integ.get("invalid_price", 0))
        integrity_events += int(integ.get("invalid_risk", 0))
        integrity_events += int(integ.get("pnl_calc_failures", 0))

    positive = [s for s in SYMBOLS if per_symbol_total.get(s, 0.0) > 0]
    positive_total = sum(per_symbol_total[s] for s in positive)
    max_share = max((per_symbol_total[s] / positive_total for s in positive), default=0.0) if positive_total > 0 else 0.0
    ratio = pf(net)
    mean = sum(net) / len(net) if net else 0.0
    total = sum(net)

    gates = {
        "aggregate_n_min": len(net) >= 60,
        "each_symbol_n_min": all(per_symbol_n.get(s, 0) >= 10 for s in SYMBOLS),
        "aggregate_mean_net_r_positive": mean > 0,
        "aggregate_pf_min": bool(ratio is not None and (math.isinf(ratio) or ratio >= 1.10)),
        "positive_symbols_min": len(positive) >= 3,
        "aggregate_total_net_r_positive": total > 0,
        "max_positive_symbol_contribution_share": max_share <= 0.60,
        "integrity_events_max": integrity_events == 0,
    }
    passed = all(gates.values())
    verdict = "D051_CONFIRM_PASS_OPEN_RESERVED_HOLDOUT" if passed else "D051_UNCONFIRMED_CLOSE"

    return {
        "schema_version": 1,
        "status": verdict,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": EXPERIMENT_ID,
        "stage": "confirmation",
        "verdict": verdict,
        "all_gates_pass": passed,
        "metrics": {
            "aggregate_n": len(net),
            "per_symbol_n": per_symbol_n,
            "aggregate_mean_net_r": mean,
            "aggregate_pf": None if ratio is None or math.isinf(ratio) else ratio,
            "aggregate_pf_infinite": bool(ratio is not None and math.isinf(ratio)),
            "aggregate_total_net_r": total,
            "aggregate_total_stress_net_r": sum(stress),
            "positive_symbols": positive,
            "positive_symbols_n": len(positive),
            "per_symbol_total_net_r": per_symbol_total,
            "max_positive_symbol_contribution_share": max_share,
            "integrity_events": integrity_events,
        },
        "gates": gates,
        "trade_path": path_reports,
        "source_provenance": provenance,
        "parent_d038_verdict_unchanged": True,
        "d047_broad_transport_verdict_unchanged": True,
        "reserved_holdout": {
            "status": "LOCKED_UNLESS_CONFIRM_PASS",
            "from": "2026-07-01",
            "to": "2026-08-31",
            "symbols": list(SYMBOLS),
        },
        "autosync_used": False,
    }


def main() -> int:
    if not (ROOT / PREREG).is_file():
        raise D051Error(f"missing preregistration: {PREREG}")

    generated, source_sha, provenance = materialize_source()
    manifest_path, manifest = build_manifest(generated, source_sha)
    identifier = manifest["experiment_id"]

    with lab._transport_context(manifest_path, manifest):
        identity = {
            "schema_version": 1,
            "status": "D051_SOURCE_IDENTITY_FROZEN_PRE_RUN",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "experiment_id": identifier,
            "stage": "confirmation",
            "source_sha256": source_sha,
            "source_provenance": provenance,
            "preregistration": PREREG,
            "symbols": list(SYMBOLS),
            "window": {"from": "2026-01-02", "to": "2026-06-30"},
            "autosync_used": False,
        }
        identity_transport = result_transport.safe_publish_event(
            identifier, "confirmation", "source-identity-pre-run", identity
        )
        if identity_transport.get("status") not in {"EVENT_PUBLISH_PASS", "EVENT_PUBLISH_NOOP_ALREADY_PRESENT"}:
            raise D051Error(f"pre-run source identity publication failed: {identity_transport}")

        if runner.cmd_compile(identifier) != 0:
            raise D051Error("D051 compile failed")

        batch_result = batch.run_batch(identifier, "confirmation")
        batch_transport = result_transport.safe_publish_event(
            identifier, "confirmation", "d051-confirm-batch", batch_result
        )

        path_reports: list[dict[str, Any]] = []
        for item in batch_result["tests"]:
            report = trade_path_validate.validate_paths(Path(item["stats"]["path"]), Path(item["trades"]["path"]))
            path_reports.append({"symbol": item["symbol"], **report})

        payload = score(batch_result, provenance, path_reports)
        payload["batch_path"] = batch_result["batch_path"]
        payload["batch_transport"] = batch_transport

        config = runner.load_config()
        workspace = runner._expand_path(config["workspace_dir"])
        outdir = workspace / "d051" / "confirmation" / stamp()
        outdir.mkdir(parents=True, exist_ok=False)
        score_path = outdir / "score.json"
        runner.write_receipt(score_path, payload)
        payload["verdict_path"] = str(score_path)
        payload["github_transport"] = result_transport.safe_publish_event(
            identifier, "confirmation", "d051-confirm-score", payload
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D051 ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
