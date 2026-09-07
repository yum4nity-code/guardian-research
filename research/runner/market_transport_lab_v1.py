#!/usr/bin/env python3
"""Deterministic Market Transport Lab V1.

This is a separate cross-market transport layer. It never edits the frozen
parent sources. For each frozen parent SHA it materializes a deterministic local
transport derivative whose only semantic changes are the preregistered symbol
allowlist, asset-class mapping, explicit commission handling and evidence names.

The normal runner active-experiment guard remains strict. This module installs a
process-local context only while executing one synthetic transport experiment,
then restores runner.load_context immediately.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import batch
import experiment
import result_transport
import runner
import state_tools
import tester
import trade_path_validate

ROOT = Path(__file__).resolve().parents[2]
PREREG = "research/campaigns/MARKET_TRANSPORT_LAB_V1_PREREGISTRATION_2026_09_07.md"
GENERATED_DIR = ROOT / "local" / "market_transport_v1_generated"

NEW_SYMBOLS = [
    "AUDUSD", "USDCAD", "USDCHF", "EURJPY", "GBPJPY", "AUDJPY",
    "SPX500", "NDX100", "GER30", "US30", "XAGUSD", "XPTUSD",
]
SMOKE_SYMBOLS = ["AUDUSD", "SPX500", "XAGUSD"]
INDEX_SYMBOLS = ["SPX500", "NDX100", "GER30", "US30"]
METAL_SYMBOLS = ["XAGUSD", "XPTUSD"]

PARENTS: dict[str, dict[str, Any]] = {
    "D038": {
        "transport_id": "D047-MARKET-TRANSPORT-NR7-V1",
        "family": "NR7 volatility-contraction breakout market transport",
        "source": "research/strategies/d038/D038_NR7_TickPath_M15_v1_00.mq5",
        "source_sha256": "e99bbe8817ed0e2c74c9aa757e8dbc5877fe0f2a5d7cd660112bf242cda79eb8",
        "generated_name": "MTL_V1_D038_NR7_TickPath_M15_v1_00.mq5",
        "output_prefix": "D038_V100",
        "role": "PRIMARY",
        "aggregate_n_min": 500,
        "qualified_symbol_n_min": 30,
        "qualified_symbols_min": 10,
    },
    "D039": {
        "transport_id": "D048-MARKET-TRANSPORT-INSIDE-DAY-V1",
        "family": "Inside-Day breakout market transport",
        "source": "research/strategies/d039/D039_InsideDay_TickPath_M15_v1_00.mq5",
        "source_sha256": "543fb1979c66dfb204a1ec6f872f1520db25640de51c8496ec5e78aa2cf008fd",
        "generated_name": "MTL_V1_D039_InsideDay_TickPath_M15_v1_00.mq5",
        "output_prefix": "D039_V100",
        "role": "PRIMARY",
        "aggregate_n_min": 500,
        "qualified_symbol_n_min": 30,
        "qualified_symbols_min": 10,
    },
    "D045": {
        "transport_id": "D049-MARKET-TRANSPORT-DONCHIAN20-10-V1",
        "family": "D1 Donchian 20/10 benchmark market transport",
        "source": "research/strategies/d045/D045_D1_Donchian20_10_TickPath_M15_v1_00.mq5",
        "source_sha256": "2b8c9d73a9e19c9e94f6c0bd6c6e160fd7ac7c666f1e8a06fb55a41c8d910723",
        "generated_name": "MTL_V1_D045_Donchian20_10_TickPath_M15_v1_00.mq5",
        "output_prefix": "D045_V100",
        "role": "PRIMARY",
        "aggregate_n_min": 120,
        "qualified_symbol_n_min": 8,
        "qualified_symbols_min": 10,
    },
    "D040": {
        "transport_id": "D050-MARKET-TRANSPORT-NR4-COMPARATOR-V1",
        "family": "NR4 volatility-contraction breakout market-transport comparator",
        "source": "research/strategies/d040/D040_NR4_TickPath_M15_v1_00.mq5",
        "source_sha256": "b6264adb884a87cc66a1041e04732602a098fa6a8b22a95e0606f08537f7fc0c",
        "generated_name": "MTL_V1_D040_NR4_TickPath_M15_v1_00.mq5",
        "output_prefix": "D040_V100",
        "role": "COMPARATOR",
        "aggregate_n_min": 500,
        "qualified_symbol_n_min": 30,
        "qualified_symbols_min": 10,
    },
}


class MarketTransportError(RuntimeError):
    pass


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _replace_function(text: str, signature: str, replacement: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise MarketTransportError(f"cannot find function signature {signature!r}")
    brace = text.find("{", start + len(signature))
    if brace < 0:
        raise MarketTransportError(f"cannot find opening brace for {signature!r}")
    depth = 0
    end = None
    for index in range(brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        raise MarketTransportError(f"cannot find closing brace for {signature!r}")
    return text[:start] + replacement.rstrip() + text[end:]


def _symbol_or_expression(symbols: list[str]) -> str:
    pieces = [f'StringFind(_Symbol,"{symbol}")>=0' for symbol in symbols]
    return " ||\n           ".join(pieces)


def materialize_transport_source(parent_key: str) -> tuple[Path, str, dict[str, Any]]:
    spec = PARENTS[parent_key]
    parent_path = ROOT / spec["source"]
    if not parent_path.is_file():
        raise MarketTransportError(f"parent source missing: {spec['source']}")
    actual_parent_sha = runner.source_identity_sha256(parent_path, runner.SOURCE_SHA_MODE_TEXT_LF)
    if actual_parent_sha.lower() != spec["source_sha256"].lower():
        raise MarketTransportError(
            f"parent source SHA mismatch for {parent_key}: expected={spec['source_sha256']} actual={actual_parent_sha}"
        )

    text = parent_path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    text, n = re.subn(
        r'string\s+EXPERIMENT_ID\s*=\s*"[^"]+"\s*;',
        f'string EXPERIMENT_ID="{spec["transport_id"]}";',
        text,
        count=1,
    )
    if n != 1:
        raise MarketTransportError(f"cannot replace EXPERIMENT_ID in {parent_key}")
    text, n = re.subn(
        r'string\s+SOURCE_NAME\s*=\s*"[^"]+"\s*;',
        f'string SOURCE_NAME="{spec["generated_name"]}";',
        text,
        count=1,
    )
    if n != 1:
        raise MarketTransportError(f"cannot replace SOURCE_NAME in {parent_key}")
    text, n = re.subn(
        r'string\s+SOURCE_VERSION\s*=\s*"[^"]+"\s*;',
        'string SOURCE_VERSION="1.00-MTL1";',
        text,
        count=1,
    )
    if n != 1:
        raise MarketTransportError(f"cannot replace SOURCE_VERSION in {parent_key}")

    allowed = f'''bool IsAllowedSymbol()\n{{\n   return ({_symbol_or_expression(NEW_SYMBOLS)});\n}}'''
    asset = f'''string AssetClass()\n{{\n   if({_symbol_or_expression(METAL_SYMBOLS)}) return "METAL";\n   if({_symbol_or_expression(INDEX_SYMBOLS)}) return "INDEX";\n   return "FOREX";\n}}'''
    commission_rule = '''string CommissionRule()\n{\n   string c=AssetClass();\n   if(c=="FOREX") return "USD5_PER_LOT_PER_SIDE";\n   if(c=="METAL") return "0.0016PCT_NOTIONAL_PER_SIDE";\n   if(c=="INDEX") return "ZERO_EXPLICIT_COMMISSION";\n   return "UNSUPPORTED";\n}'''
    commission = '''double CommissionUSD1Lot(double exit_px)\n{\n   if(!ValidPrice(g_entry) || !ValidPrice(exit_px)) return -1.0;\n   string c=AssetClass();\n   if(c=="FOREX") return 10.0;\n   if(c=="INDEX") return 0.0;\n   if(c!="METAL") return -1.0;\n   double contract=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_CONTRACT_SIZE);\n   if(contract<=0.0 || !MathIsValidNumber(contract)) return -1.0;\n   double rate=0.000016;\n   double value=contract*g_entry*rate + contract*exit_px*rate;\n   return (value>=0.0 && MathIsValidNumber(value)) ? value : -1.0;\n}'''

    text = _replace_function(text, "bool IsAllowedSymbol()", allowed)
    text = _replace_function(text, "string AssetClass()", asset)
    text = _replace_function(text, "string CommissionRule()", commission_rule)
    text = _replace_function(text, "double CommissionUSD1Lot(double exit_px)", commission)

    header = (
        "// MARKET TRANSPORT LAB V1 GENERATED DERIVATIVE. DO NOT EDIT.\n"
        f"// parent={parent_key} parent_sha256={actual_parent_sha}\n"
        f"// transport_id={spec['transport_id']} frozen_universe={','.join(NEW_SYMBOLS)}\n"
        "// allowed changes: symbol universe, asset-class/commission transport, evidence identity only.\n"
    )
    text = header + text

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    generated = GENERATED_DIR / spec["generated_name"]
    generated.write_text(text, encoding="utf-8", newline="\n")
    generated_sha = runner.source_identity_sha256(generated, runner.SOURCE_SHA_MODE_TEXT_LF)
    return generated, generated_sha, {
        "parent_key": parent_key,
        "parent_source": spec["source"],
        "parent_source_sha256": actual_parent_sha,
        "generated_source": str(generated.relative_to(ROOT)),
        "generated_source_sha256": generated_sha,
        "patch_contract": "ALLOWLIST_ASSETCLASS_COMMISSION_AND_EVIDENCE_IDENTITY_ONLY",
    }


def _manifest(parent_key: str, stage_name: str, generated: Path, generated_sha: str) -> tuple[Path, dict[str, Any]]:
    spec = PARENTS[parent_key]
    if stage_name not in {"smoke", "development"}:
        raise MarketTransportError("V1 implements smoke and development only")
    output_prefix = spec["output_prefix"]
    manifest = {
        "schema_version": 1,
        "experiment_id": spec["transport_id"],
        "strategy_family": spec["family"],
        "status": "READY_SMOKE" if stage_name == "smoke" else "READY_DEV",
        "hypothesis": f"Does frozen parent {parent_key} transport broadly across the preregistered 12-market FundedNext V1 universe without signal or management changes?",
        "preregistration": {
            "path": PREREG,
            "git_blob_sha": None,
            "frozen_before_result_inspection": True,
            "execution_deviations": [
                "Local source is deterministically materialized from the frozen parent SHA by market_transport_lab_v1.py; parent repository source is never edited."
            ],
        },
        "source": {
            "canonical_path": str(generated.relative_to(ROOT)).replace("\\", "/"),
            "source_sha256": generated_sha,
            "source_sha256_mode": "UTF8_TEXT_LF_NORMALIZED",
            "git_blob_sha": None,
            "version": "1.00-MTL1",
            "complete_repository_source": True,
            "strategy_semantics_frozen": True,
            "engineering_lineage": [
                f"Frozen parent {parent_key} SHA {spec['source_sha256']}",
                "Deterministic Market Transport Lab V1 derived source",
                "No signal/management parameter changes permitted",
            ],
        },
        "execution": {
            "timeframe": "M15",
            "reference_timeframes": ["D1"],
            "symbols": list(NEW_SYMBOLS),
            "account_currency": "USD",
            "prop_firm_profile": "FUNDEDNEXT_MARKET_TRANSPORT_V1",
        },
        "runner_contract": {
            "expert_relative_path": f"GuardianResearch\\{generated.stem}",
            "default_stage": stage_name,
            "stage_selection": "TESTER_DATE_RANGE_ONLY",
            "tester_model_reference": 0,
            "tester_model_fast_candidate": None,
            "output": {
                "location": "FILE_COMMON",
                "stats_template": f"{output_prefix}_{{stage_token}}_{{symbol_clean}}_STATS.csv",
                "trades_template": f"{output_prefix}_{{stage_token}}_{{symbol_clean}}_TRADES.csv",
                "stage_tokens": {"smoke": "RUN", "development": "RUN", "confirmation": "RUN"},
            },
        },
        "cost_model": {
            "name": "MARKET_TRANSPORT_V1_PARENT_COMPARABLE",
            "spread_source": "tester executable bid/ask ticks",
            "commission_stress_multiplier": 1.5,
            "forex": "USD 5 per lot per side",
            "metals": "0.0016% notional per side",
            "indices": "zero explicit commission; executable spread retained",
            "swap": "excluded; must be separately reviewed before production interpretation",
        },
        "stages": {
            "smoke": {
                "stage_name": f"{spec['transport_id']}_SMOKE_OCT2023",
                "from": "2023-10-02",
                "to": "2023-10-31",
                "symbols": list(SMOKE_SYMBOLS),
                "status": "READY" if stage_name == "smoke" else "PASS",
                "gates": {"engineering_only": True, "trade_path_required": True},
                "result_paths": [],
            },
            "development": {
                "stage_name": f"{spec['transport_id']}_DEV_2024_2025",
                "from": "2024-01-02",
                "to": "2025-12-31",
                "symbols": list(NEW_SYMBOLS),
                "status": "READY" if stage_name == "development" else "LOCKED",
                "gates": {
                    "aggregate_n_min": spec["aggregate_n_min"],
                    "qualified_symbol_n_min": spec["qualified_symbol_n_min"],
                    "qualified_symbols_min": spec["qualified_symbols_min"],
                    "aggregate_mean_net_r_strictly_positive": True,
                    "aggregate_pf_min": 1.10,
                    "positive_symbols_min": 8,
                    "aggregate_2024_positive": True,
                    "aggregate_2025_positive": True,
                    "aggregate_positive_at_commission_stress": True,
                    "max_positive_symbol_contribution_share": 0.35,
                    "integrity_events_max": 0,
                },
                "result_paths": [],
            },
            "confirmation": {
                "stage_name": f"{spec['transport_id']}_CONFIRM_2026_H1",
                "from": "2026-01-02",
                "to": "2026-06-30",
                "symbols": list(NEW_SYMBOLS),
                "status": "UNOPENED",
                "gates": {"locked_until_transport_dev_pass": True},
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
        raise MarketTransportError(f"synthetic manifest invalid for {parent_key}: {'; '.join(errors)}")
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = GENERATED_DIR / f"{spec['transport_id']}_{stage_name}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return manifest_path, manifest


@contextlib.contextmanager
def _transport_context(manifest_path: Path, manifest: dict[str, Any]) -> Iterator[None]:
    original = runner.load_context
    state = state_tools.load_state()

    def local_context(identifier: str):
        accepted = {
            manifest["experiment_id"].upper(),
            manifest["experiment_id"].split("-")[0].upper(),
            str(manifest_path).upper(),
            str(manifest_path.relative_to(ROOT)).upper(),
        }
        if str(identifier).upper() not in accepted:
            raise runner.RunnerError(f"Market Transport V1 context refuses unrelated identifier: {identifier}")
        return state, manifest_path, manifest

    runner.load_context = local_context
    try:
        yield
    finally:
        runner.load_context = original


def _profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def _score(parent_key: str, batch_result: dict[str, Any]) -> dict[str, Any]:
    spec = PARENTS[parent_key]
    tests = batch_result.get("tests", [])
    rows_by_symbol: dict[str, list[dict[str, str]]] = {}
    integrity_events = 0
    all_rows: list[dict[str, str]] = []
    for item in tests:
        symbol = item["symbol"]
        rows = tester.read_semicolon_csv(Path(item["trades"]["path"]))
        rows_by_symbol[symbol] = rows
        all_rows.extend(rows)
        integ = item.get("integrity", {})
        integrity_events += int(integ.get("invalid_price", 0))
        integrity_events += int(integ.get("invalid_risk", 0))
        integrity_events += int(integ.get("pnl_calc_failures", 0))

    per_symbol_n = {symbol: len(rows_by_symbol.get(symbol, [])) for symbol in NEW_SYMBOLS}
    per_symbol_total: dict[str, float] = {}
    net: list[float] = []
    stress: list[float] = []
    year_total: dict[int, float] = defaultdict(float)
    for symbol in NEW_SYMBOLS:
        total = 0.0
        for row in rows_by_symbol.get(symbol, []):
            value = float(row["net_r"])
            stressed = float(row["net_r_commission_x1_5"])
            if not math.isfinite(value) or not math.isfinite(stressed):
                raise MarketTransportError(f"non-finite R value in {parent_key}/{symbol}")
            total += value
            net.append(value)
            stress.append(stressed)
            try:
                year = int(row["entry_time"][:4])
            except (KeyError, ValueError) as exc:
                raise MarketTransportError(f"cannot parse entry year in {parent_key}/{symbol}") from exc
            year_total[year] += value
        per_symbol_total[symbol] = total

    positive_symbols = [symbol for symbol, total in per_symbol_total.items() if total > 0]
    positive_total = sum(per_symbol_total[symbol] for symbol in positive_symbols)
    max_share = max((per_symbol_total[symbol] / positive_total for symbol in positive_symbols), default=0.0) if positive_total > 0 else 0.0
    pf = _profit_factor(net)
    qualified = sum(1 for n in per_symbol_n.values() if n >= int(spec["qualified_symbol_n_min"]))
    metrics = {
        "aggregate_n": len(net),
        "per_symbol_n": per_symbol_n,
        "qualified_symbols_n": qualified,
        "qualified_symbol_n_min": spec["qualified_symbol_n_min"],
        "aggregate_mean_net_r": (sum(net) / len(net)) if net else 0.0,
        "aggregate_pf": None if pf is None or math.isinf(pf) else pf,
        "aggregate_pf_infinite": bool(pf is not None and math.isinf(pf)),
        "positive_symbols": positive_symbols,
        "positive_symbols_n": len(positive_symbols),
        "per_symbol_total_net_r": per_symbol_total,
        "aggregate_total_net_r": sum(net),
        "aggregate_total_stress_net_r": sum(stress),
        "year_total_net_r": {str(year): total for year, total in sorted(year_total.items())},
        "max_positive_symbol_contribution_share": max_share,
        "integrity_events": integrity_events,
    }
    pf_pass = metrics["aggregate_pf_infinite"] or (metrics["aggregate_pf"] is not None and metrics["aggregate_pf"] >= 1.10)
    gates = {
        "aggregate_n_min": metrics["aggregate_n"] >= int(spec["aggregate_n_min"]),
        "qualified_symbols_min": qualified >= int(spec["qualified_symbols_min"]),
        "aggregate_mean_net_r_positive": metrics["aggregate_mean_net_r"] > 0,
        "aggregate_pf_min": pf_pass,
        "positive_symbols_min": metrics["positive_symbols_n"] >= 8,
        "aggregate_2024_positive": year_total.get(2024, 0.0) > 0,
        "aggregate_2025_positive": year_total.get(2025, 0.0) > 0,
        "aggregate_positive_at_commission_stress": metrics["aggregate_total_stress_net_r"] > 0,
        "max_positive_symbol_contribution_share": max_share <= 0.35,
        "integrity_events_max": integrity_events == 0,
    }
    passed = all(gates.values())
    if spec["role"] == "COMPARATOR":
        verdict = "COMPARATOR_BROAD_PASS" if passed else "COMPARATOR_NO_BROAD_PASS"
    else:
        verdict = "TRANSPORT_CANDIDATE_CONFIRM" if passed else "TRANSPORT_NO_BROAD_PASS"
    return {
        "schema_version": 1,
        "status": "MARKET_TRANSPORT_SCORE_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "lab": "MARKET_TRANSPORT_V1",
        "parent": parent_key,
        "transport_id": spec["transport_id"],
        "role": spec["role"],
        "stage": "development",
        "metrics": metrics,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": verdict,
        "parent_verdict_unchanged": True,
        "autosync_used": False,
    }


def _write_local_result(parent_key: str, stage: str, kind: str, payload: dict[str, Any]) -> Path:
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    path = workspace / "market_transport" / "v1" / PARENTS[parent_key]["transport_id"] / stage / _stamp() / f"{kind}.json"
    runner.write_receipt(path, payload)
    return path


def run_parent(parent_key: str, stage_name: str) -> dict[str, Any]:
    generated, generated_sha, provenance = materialize_transport_source(parent_key)
    manifest_path, manifest = _manifest(parent_key, stage_name, generated, generated_sha)
    identifier = manifest["experiment_id"]
    with _transport_context(manifest_path, manifest):
        compile_rc = runner.cmd_compile(identifier)
        if compile_rc != 0:
            raise MarketTransportError(f"compile failed for {parent_key}")
        batch_result = batch.run_batch(identifier, stage_name)
        batch_transport = result_transport.safe_publish_event(identifier, stage_name, "market-transport-batch", batch_result)

        if stage_name == "smoke":
            path_reports = []
            for item in batch_result["tests"]:
                report = trade_path_validate.validate_paths(Path(item["stats"]["path"]), Path(item["trades"]["path"]))
                path_reports.append({"symbol": item["symbol"], **report})
            payload = {
                "schema_version": 1,
                "status": "MARKET_TRANSPORT_SMOKE_PASS",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "lab": "MARKET_TRANSPORT_V1",
                "parent": parent_key,
                "transport_id": identifier,
                "source_provenance": provenance,
                "batch_path": batch_result["batch_path"],
                "symbols": list(SMOKE_SYMBOLS),
                "trade_path": path_reports,
                "batch_transport": batch_transport,
                "autosync_used": False,
            }
            local = _write_local_result(parent_key, stage_name, "smoke", payload)
            payload["smoke_path"] = str(local)
            payload["github_transport"] = result_transport.safe_publish_event(identifier, stage_name, "market-transport-smoke", payload)
            return payload

        score_payload = _score(parent_key, batch_result)
        score_payload["source_provenance"] = provenance
        score_payload["batch_path"] = batch_result["batch_path"]
        score_payload["batch_transport"] = batch_transport
        local = _write_local_result(parent_key, stage_name, "score", score_payload)
        score_payload["verdict_path"] = str(local)
        score_payload["github_transport"] = result_transport.safe_publish_event(identifier, stage_name, "market-transport-score", score_payload)
        return score_payload


def _rank(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [item for item in results if item.get("stage") == "development" and item.get("status") == "MARKET_TRANSPORT_SCORE_PASS"]
    def key(item: dict[str, Any]):
        metrics = item["metrics"]
        years = metrics["year_total_net_r"]
        year_consistency = min(float(years.get("2024", 0.0)), float(years.get("2025", 0.0)))
        pf = math.inf if metrics.get("aggregate_pf_infinite") else float(metrics.get("aggregate_pf") or 0.0)
        return (
            1 if item.get("all_gates_pass") else 0,
            int(metrics["positive_symbols_n"]),
            year_consistency,
            pf,
            float(metrics["aggregate_mean_net_r"]),
            -float(metrics["max_positive_symbol_contribution_share"]),
            item["transport_id"],
        )
    return sorted(scored, key=key, reverse=True)


def run_lab(stage_name: str) -> dict[str, Any]:
    if not (ROOT / PREREG).is_file():
        raise MarketTransportError(f"preregistration missing: {PREREG}")
    results = []
    failures = []
    for parent_key in ("D038", "D039", "D045", "D040"):
        try:
            results.append(run_parent(parent_key, stage_name))
        except Exception as exc:
            failures.append({"parent": parent_key, "error": str(exc)})

    status = "MARKET_TRANSPORT_LAB_PASS" if not failures else "MARKET_TRANSPORT_LAB_ENGINEERING_INCOMPLETE"
    payload: dict[str, Any] = {
        "schema_version": 1,
        "status": status,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "lab": "MARKET_TRANSPORT_V1",
        "stage": stage_name,
        "preregistration": PREREG,
        "frozen_symbols": list(NEW_SYMBOLS),
        "parents": ["D038", "D039", "D045", "D040"],
        "results": results,
        "engineering_failures": failures,
        "parent_verdicts_unchanged": True,
        "autosync_used": False,
    }
    if stage_name == "development":
        payload["ranking"] = [
            {
                "transport_id": item["transport_id"],
                "parent": item["parent"],
                "role": item["role"],
                "verdict": item["verdict"],
                "positive_symbols_n": item["metrics"]["positive_symbols_n"],
                "aggregate_pf": item["metrics"]["aggregate_pf"],
                "aggregate_mean_net_r": item["metrics"]["aggregate_mean_net_r"],
            }
            for item in _rank(results)
        ]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run frozen Market Transport Lab V1")
    parser.add_argument("--stage", required=True, choices=("smoke", "development"))
    args = parser.parse_args()
    try:
        result = run_lab(args.stage)
    except (MarketTransportError, runner.RunnerError, tester.TestError, experiment.ManifestError, OSError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"] == "MARKET_TRANSPORT_LAB_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
