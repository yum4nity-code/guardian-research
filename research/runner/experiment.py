#!/usr/bin/env python3
"""Generic D0xx experiment-manifest validation.

The validator checks research invariants that should be true before any local
MT5 runner is allowed to spend time on a campaign. It intentionally performs no
trading and has no MetaTrader dependency.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = ROOT / "research" / "experiments"
ID_RE = re.compile(r"^D\d{3}(?:-[A-Z0-9][A-Z0-9_-]*)+$")


class ManifestError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON: {path}: {exc}") from exc


def resolve_manifest(identifier: str) -> Path:
    candidate = Path(identifier)
    if candidate.suffix.lower() == ".json":
        path = candidate if candidate.is_absolute() else ROOT / candidate
        return path

    short = identifier.upper()
    if not short.startswith("D"):
        short = "D" + short
    exact = EXPERIMENT_DIR / f"{short}.json"
    if exact.exists():
        return exact

    matches = sorted(EXPERIMENT_DIR.glob(f"{short}*.json"))
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ManifestError(f"no experiment manifest resolves from: {identifier}")
    raise ManifestError(f"ambiguous experiment identifier {identifier}: {[p.name for p in matches]}")


def load_manifest(identifier: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_manifest(identifier)
    return path, _read_json(path)


def _parse_date(value: Any, label: str, errors: list[str]) -> date | None:
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO date string")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label} is not YYYY-MM-DD: {value}")
        return None


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(manifest.get("schema_version") == 1, "unsupported experiment schema_version")

    experiment_id = manifest.get("experiment_id")
    require(isinstance(experiment_id, str) and bool(ID_RE.match(experiment_id)),
            "experiment_id must look like D037-NAME-V0 using uppercase machine-safe tokens")
    require(bool(manifest.get("strategy_family")), "strategy_family is required")
    require(bool(manifest.get("hypothesis")), "hypothesis is required")

    prereg = manifest.get("preregistration", {})
    prereg_path = prereg.get("path")
    require(bool(prereg_path), "preregistration.path is required")
    if prereg_path:
        require((ROOT / prereg_path).is_file(), f"preregistration path does not exist: {prereg_path}")
    require(prereg.get("frozen_before_result_inspection") is True,
            "preregistration must be frozen before result inspection")

    source = manifest.get("source", {})
    require(bool(source.get("version")), "source.version is required")
    require(source.get("strategy_semantics_frozen") is True,
            "strategy_semantics_frozen must be true before execution")
    complete_source = source.get("complete_repository_source") is True
    canonical_path = source.get("canonical_path")
    if complete_source:
        require(bool(canonical_path), "complete source requires canonical_path")
        if canonical_path:
            require((ROOT / canonical_path).is_file(), f"canonical source missing: {canonical_path}")
        require(bool(source.get("source_sha256")), "complete source requires source_sha256")
    else:
        require(canonical_path in (None, ""),
                "incomplete source must not masquerade as a canonical_path")

    execution = manifest.get("execution", {})
    symbols = execution.get("symbols")
    require(isinstance(symbols, list) and len(symbols) > 0, "execution.symbols must be non-empty")
    if isinstance(symbols, list):
        require(len(symbols) == len(set(symbols)), "execution.symbols contains duplicates")
        require(all(isinstance(x, str) and x for x in symbols), "execution.symbols must be non-empty strings")
    require(bool(execution.get("timeframe")), "execution.timeframe is required")
    require(bool(execution.get("prop_firm_profile")), "execution.prop_firm_profile is required")

    cost = manifest.get("cost_model", {})
    require(bool(cost.get("name")), "cost_model.name is required")
    stress = cost.get("commission_stress_multiplier")
    require(isinstance(stress, (int, float)) and stress >= 1.0,
            "commission_stress_multiplier must be numeric and >= 1.0")

    stages = manifest.get("stages", {})
    required_stages = ("smoke", "development", "confirmation")
    parsed: dict[str, tuple[date | None, date | None]] = {}
    for name in required_stages:
        stage = stages.get(name, {})
        require(bool(stage), f"missing stage: {name}")
        require(bool(stage.get("stage_name")), f"{name}.stage_name is required")
        require(isinstance(stage.get("symbols"), list) and len(stage.get("symbols", [])) > 0,
                f"{name}.symbols must be non-empty")
        require(bool(stage.get("gates")), f"{name}.gates must be frozen")
        start = _parse_date(stage.get("from"), f"{name}.from", errors)
        end = _parse_date(stage.get("to"), f"{name}.to", errors)
        parsed[name] = (start, end)
        if start and end:
            require(start <= end, f"{name} starts after it ends")
        if isinstance(symbols, list) and isinstance(stage.get("symbols"), list):
            require(set(stage["symbols"]).issubset(set(symbols)),
                    f"{name}.symbols must be a subset of execution.symbols")

    dev_from, dev_to = parsed.get("development", (None, None))
    conf_from, conf_to = parsed.get("confirmation", (None, None))
    if dev_to and conf_from:
        require(conf_from > dev_to, "confirmation period must start strictly after development period")

    policy = manifest.get("decision_policy", {})
    require(policy.get("no_posthoc_rescue") is True, "no_posthoc_rescue must be true")
    require(policy.get("confirmation_locked_until_dev_pass") is True,
            "confirmation_locked_until_dev_pass must be true")
    require(policy.get("invalid_run_is_not_strategy_reject") is True,
            "invalid_run_is_not_strategy_reject must be true")

    results = manifest.get("results", {})
    confirmation = stages.get("confirmation", {})
    dev_result = results.get("development")
    if dev_result is None:
        require(confirmation.get("status") in {"UNOPENED", "LOCKED"},
                "confirmation must remain unopened/locked before a development result exists")

    return errors


def execution_readiness(manifest: dict[str, Any]) -> list[str]:
    """Return blockers that prevent the deterministic runner from executing MT5."""
    blockers = validate_manifest(manifest)
    source = manifest.get("source", {})
    if source.get("complete_repository_source") is not True:
        blockers.append("canonical complete repository source is not ready")
    if not source.get("source_sha256"):
        blockers.append("source_sha256 is not frozen")
    return blockers


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Guardian experiment manifests")
    parser.add_argument("command", choices=("validate", "ready"))
    parser.add_argument("experiment", help="D037, manifest path, or unique D0xx prefix")
    args = parser.parse_args()

    try:
        path, manifest = load_manifest(args.experiment)
        errors = validate_manifest(manifest) if args.command == "validate" else execution_readiness(manifest)
    except ManifestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    marker = "EXPERIMENT_MANIFEST_OK" if args.command == "validate" else "EXPERIMENT_READY"
    print(f"{marker} {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
