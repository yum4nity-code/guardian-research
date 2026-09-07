#!/usr/bin/env python3
"""Safe offline launcher for Guardian Management Benchmark V1.

The normal runner intentionally refuses non-active experiments. Management
Benchmark V1 is different: it is an offline cross-family replay over four
already-closed, already-seen datasets and must never activate or rerun them.

This launcher keeps the global runner safety invariant intact and relaxes the
active-experiment check only inside this process for an explicit immutable
allowlist. It also freezes the expected experiment IDs and compact row counts so
a later local rich-score output cannot silently replace the V1 evidence set.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import experiment
import management_benchmark as benchmark
import runner
import state_tools

FROZEN_DATASETS: dict[str, dict[str, Any]] = {
    "D038": {
        "experiment_id": "D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0",
        "stage": "development",
        "rows": 459,
    },
    "D039": {
        "experiment_id": "D039-INSIDE-DAY-BREAKOUT-V0",
        "stage": "development",
        "rows": 441,
    },
    "D040": {
        "experiment_id": "D040-NR4-VOLATILITY-CONTRACTION-BREAKOUT-V0",
        "stage": "development",
        "rows": 758,
    },
    "D045": {
        "experiment_id": "D045-D1-DONCHIAN-20-10-BENCHMARK-V0",
        "stage": "development",
        "rows": 145,
    },
}


class OfflineBenchmarkSafetyError(RuntimeError):
    pass


def _canonical_short(identifier: str) -> str:
    token = identifier.upper()
    if not token.startswith("D"):
        token = "D" + token
    return token


def archived_context(identifier: str):
    short = _canonical_short(identifier)
    frozen = FROZEN_DATASETS.get(short)
    if frozen is None:
        raise OfflineBenchmarkSafetyError(
            f"Management Benchmark V1 refuses non-frozen dataset {identifier!r}; "
            f"allowed={sorted(FROZEN_DATASETS)}"
        )

    state = state_tools.load_state()
    state_errors = state_tools.validate_state(state)
    if state_errors:
        raise OfflineBenchmarkSafetyError("invalid project state: " + "; ".join(state_errors))

    manifest_path, manifest = experiment.load_manifest(short)
    manifest_errors = experiment.validate_manifest(manifest)
    if manifest_errors:
        raise OfflineBenchmarkSafetyError(
            f"invalid archived experiment manifest {short}: " + "; ".join(manifest_errors)
        )

    expected_id = frozen["experiment_id"]
    actual_id = manifest.get("experiment_id")
    if actual_id != expected_id:
        raise OfflineBenchmarkSafetyError(
            f"archived manifest identity mismatch for {short}: expected={expected_id} actual={actual_id}"
        )

    stage = frozen["stage"]
    if stage not in manifest.get("stages", {}):
        raise OfflineBenchmarkSafetyError(f"frozen stage {stage!r} missing from {short} manifest")

    # Explicitly require that this launcher never targets an open/active science run.
    if actual_id == state.get("research", {}).get("active_experiment"):
        raise OfflineBenchmarkSafetyError(
            f"{short} is currently active; offline benchmark only accepts archived/closed evidence"
        )

    return state, manifest_path, manifest


def install_offline_guard() -> None:
    """Patch only this process; runner.py itself remains strict and unchanged."""
    original_dataset = benchmark._dataset

    def frozen_dataset(identifier: str, stage: str, workspace: Path) -> dict[str, Any]:
        short = _canonical_short(identifier)
        frozen = FROZEN_DATASETS.get(short)
        if frozen is None:
            raise OfflineBenchmarkSafetyError(
                f"Management Benchmark V1 refuses dataset {identifier!r}; allowed={sorted(FROZEN_DATASETS)}"
            )
        if stage != frozen["stage"]:
            raise OfflineBenchmarkSafetyError(
                f"Management Benchmark V1 stage mismatch for {short}: expected={frozen['stage']} actual={stage}"
            )

        ds = original_dataset(short, stage, workspace)
        actual_rows = len(ds["rows"])
        expected_rows = int(frozen["rows"])
        if actual_rows != expected_rows:
            raise OfflineBenchmarkSafetyError(
                f"frozen compact-row count mismatch for {short}: expected={expected_rows} actual={actual_rows}; "
                "refusing to silently substitute another rich-score dataset"
            )
        if ds["experiment_id"] != frozen["experiment_id"]:
            raise OfflineBenchmarkSafetyError(
                f"dataset experiment identity mismatch for {short}: expected={frozen['experiment_id']} "
                f"actual={ds['experiment_id']}"
            )
        return ds

    runner.load_context = archived_context  # type: ignore[assignment]
    benchmark._dataset = frozen_dataset  # type: ignore[assignment]


def main() -> int:
    install_offline_guard()
    return benchmark.main()


if __name__ == "__main__":
    raise SystemExit(main())
