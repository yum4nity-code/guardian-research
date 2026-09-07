#!/usr/bin/env python3
"""Publish a descriptive score for the 11 valid D049 development markets.

This is NOT a formal Market Transport V1 score. The preregistered universe is
12 symbols and XPTUSD remains engineering-invalid. This diagnostic reads the
latest trusted partial D049 batch with exactly 11 completed tests, computes
metrics only on those immutable valid tests, and publishes them so research can
continue without rerunning MT5 or silently dropping XPTUSD from the formal
experiment.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import market_transport_lab_v1 as lab

PARENT = "D045"
STAGE = "development"
FAILED_SYMBOL = "XPTUSD"
EXPECTED_VALID = 11


def latest_partial(workspace: Path, experiment_id: str) -> tuple[Path, dict]:
    base = workspace / "batches" / experiment_id / STAGE
    candidates = sorted(base.glob("*/batch.json"), key=lambda p: p.stat().st_mtime, reverse=True) if base.exists() else []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "BATCH_INVALID_ENGINEERING":
            continue
        if payload.get("failed_symbol") != FAILED_SYMBOL:
            continue
        tests = payload.get("tests", [])
        if len(tests) != EXPECTED_VALID:
            continue
        symbols = [item.get("symbol") for item in tests]
        if symbols != list(lab.NEW_SYMBOLS[:-1]):
            continue
        return path, payload
    raise lab.MarketTransportError("no trusted D049 partial batch with 11 valid tests found")


def profit_factor(values: list[float]) -> float | None:
    gains = sum(v for v in values if v > 0)
    losses = -sum(v for v in values if v < 0)
    if losses == 0:
        return math.inf if gains > 0 else None
    return gains / losses


def main() -> int:
    generated, generated_sha, provenance = lab.materialize_transport_source(PARENT)
    manifest_path, manifest = lab._manifest(PARENT, STAGE, generated, generated_sha)
    identifier = manifest["experiment_id"]
    config = lab.runner.load_config()
    workspace = lab.runner._expand_path(config["workspace_dir"])
    batch_path, batch = latest_partial(workspace, identifier)

    valid_symbols = list(lab.NEW_SYMBOLS[:-1])
    rows_by_symbol: dict[str, list[dict[str, str]]] = {}
    all_net: list[float] = []
    all_stress: list[float] = []
    per_symbol_total: dict[str, float] = {}
    per_symbol_n: dict[str, int] = {}
    year_total: dict[int, float] = defaultdict(float)
    integrity_events = 0

    for item in batch["tests"]:
        symbol = item["symbol"]
        rows = lab.tester.read_semicolon_csv(Path(item["trades"]["path"]))
        rows_by_symbol[symbol] = rows
        per_symbol_n[symbol] = len(rows)
        total = 0.0
        for row in rows:
            net = float(row["net_r"])
            stress = float(row["net_r_commission_x1_5"])
            if not math.isfinite(net) or not math.isfinite(stress):
                raise lab.MarketTransportError(f"non-finite R in {symbol}")
            total += net
            all_net.append(net)
            all_stress.append(stress)
            year_total[int(row["entry_time"][:4])] += net
        per_symbol_total[symbol] = total
        integ = item.get("integrity", {})
        integrity_events += int(integ.get("invalid_price", 0))
        integrity_events += int(integ.get("invalid_risk", 0))
        integrity_events += int(integ.get("pnl_calc_failures", 0))

    positive_symbols = [s for s in valid_symbols if per_symbol_total.get(s, 0.0) > 0]
    positive_total = sum(per_symbol_total[s] for s in positive_symbols)
    max_share = max((per_symbol_total[s] / positive_total for s in positive_symbols), default=0.0) if positive_total > 0 else 0.0
    pf = profit_factor(all_net)

    payload = {
        "schema_version": 1,
        "status": "D049_DESCRIPTIVE_11_VALID_MARKETS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "lab": "MARKET_TRANSPORT_V1",
        "parent": PARENT,
        "transport_id": identifier,
        "stage": STAGE,
        "formal_status": "MARKET_TRANSPORT_ENGINEERING_INCOMPLETE",
        "formal_verdict": None,
        "formal_gate_evaluation_skipped": True,
        "reason": "Frozen 12-symbol universe incomplete because XPTUSD repeatedly ends FINAL_INVALID_REFERENCE; 11-market metrics are descriptive only.",
        "failed_symbol": FAILED_SYMBOL,
        "valid_symbols": valid_symbols,
        "metrics_11_valid_only": {
            "aggregate_n": len(all_net),
            "per_symbol_n": per_symbol_n,
            "aggregate_mean_net_r": (sum(all_net) / len(all_net)) if all_net else 0.0,
            "aggregate_pf": None if pf is None or math.isinf(pf) else pf,
            "aggregate_pf_infinite": bool(pf is not None and math.isinf(pf)),
            "aggregate_total_net_r": sum(all_net),
            "aggregate_total_stress_net_r": sum(all_stress),
            "year_total_net_r": {str(y): v for y, v in sorted(year_total.items())},
            "positive_symbols": positive_symbols,
            "positive_symbols_n": len(positive_symbols),
            "per_symbol_total_net_r": per_symbol_total,
            "max_positive_symbol_contribution_share": max_share,
            "integrity_events": integrity_events,
        },
        "source_partial_batch": str(batch_path),
        "source_provenance": provenance,
        "parent_verdict_unchanged": True,
        "scientific_semantics_changed": False,
        "xptusd_not_dropped_from_formal_universe": True,
        "autosync_used": False,
    }
    local = lab._write_local_result(PARENT, STAGE, "descriptive-11-valid", payload)
    payload["local_path"] = str(local)
    payload["github_transport"] = lab.result_transport.safe_publish_event(
        identifier, STAGE, "market-transport-descriptive-11-valid", payload
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"D049 11-MARKET DIAGNOSTIC ERROR: {exc}")
        raise SystemExit(1)
