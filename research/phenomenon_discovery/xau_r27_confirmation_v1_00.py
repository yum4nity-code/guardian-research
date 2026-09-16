#!/usr/bin/env python3
"""R27 XAUUSD volatility-compression persistence confirmation v1.00.

New preregistered study inspired by the inverse of R22 discovery:
- exact reviewed R22 compression event extractor
- primary state: bottom10 only
- primary horizons: 4b and 8b only
- persistence_h = -R22 excess_abs_h
- complete-estimator delete-one-UTC-day jackknife reused unchanged
- PASS only if both persistence means > 0 and both jackknife t > +2.0

The audited immutable 2019-07-01..2024-12-31 confirmation builder and R15
provenance admission are reused. 2025 and 2026+ are inaccessible.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import build_xau_m5_r21_confirmation_slice_v1_00 as sealed_builder
import xau_edge_discovery_r21_r25_v1_03 as discovery
import xau_r21_confirmation_v1_00 as stage

r27_event_extractor = discovery.r22_volatility_compression
r27_complete_jackknife = discovery.r22_complete_estimator_day_jackknife

CANONICAL_OUTPUT_DIR = Path(
    "D:/MT5_Backtests/Research/Autonomous/r27_xau_confirmation_v100"
)
CANONICAL_OUTPUT = CANONICAL_OUTPUT_DIR / "confirmation.json"
CANONICAL_PROGRESS = CANONICAL_OUTPUT_DIR / "progress.json"


def _validate_artifact_path(path: Path, expected: Path, label: str) -> Path:
    if not path.is_absolute() or path.absolute() != expected.absolute():
        raise RuntimeError(f"{label} must use its canonical R27 confirmation path")

    root = CANONICAL_OUTPUT_DIR.absolute()
    if root.parent.resolve(strict=True) != root.parent.absolute():
        raise RuntimeError("canonical R27 confirmation output parent is redirected")

    root.mkdir(parents=True, exist_ok=True)
    if root.resolve(strict=True) != root:
        raise RuntimeError("canonical R27 confirmation output directory is redirected")

    if path.is_symlink() or (
        path.exists() and path.resolve(strict=True) != path.absolute()
    ):
        raise RuntimeError(f"canonical R27 confirmation {label} file is redirected")

    return path.absolute()


def _validate_output_path(path: Path) -> Path:
    return _validate_artifact_path(path, CANONICAL_OUTPUT, "output")


def _validate_progress_path(path: Path) -> Path:
    return _validate_artifact_path(path, CANONICAL_PROGRESS, "progress")


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _write_progress(
    progress_path: Path,
    *,
    phase: str,
    fraction: float,
    confirmation_opened: bool = False,
    **extra,
) -> None:
    fraction = max(0.0, min(1.0, float(fraction)))
    _atomic_json(
        progress_path,
        {
            "schema": 1,
            "research": "R27",
            "version": "1.00",
            "stage": "confirmation",
            "status": "PASS" if phase == "complete" else "RUNNING",
            "phase": phase,
            "fraction": fraction,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "confirmation_authorized": True,
            "confirmation_opened": bool(confirmation_opened),
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            **extra,
        },
    )


def _cleanup_stale_transients() -> list[str]:
    removed: list[str] = []

    root = CANONICAL_OUTPUT_DIR
    try:
        if root.exists() and root.resolve(strict=True) == root.absolute():
            for name in (
                "progress.json",
                "progress.json.tmp",
                "confirmation.json.tmp",
            ):
                p = root / name
                if (
                    p.exists()
                    and not p.is_symlink()
                    and p.resolve(strict=True).parent == root.absolute()
                ):
                    p.unlink()
                    removed.append(str(p))
    except OSError:
        pass

    temp_base = Path(tempfile.gettempdir())
    temp_root = temp_base.resolve()
    for p in temp_base.glob("guardian_r27_confirmation_v100_*"):
        try:
            if p.is_symlink():
                continue
            resolved = p.resolve(strict=True)
            if resolved.parent != temp_root:
                continue
            if p.is_dir():
                shutil.rmtree(p)
                removed.append(str(p))
        except OSError:
            pass

    return removed


def _finite_number(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def _persistence_stats(raw: dict) -> dict:
    """Sign-invert the frozen R22 excess estimator without changing its SE."""
    mean = raw.get("mean")
    cluster_t = raw.get("cluster_t")
    out = dict(raw)
    out["mean"] = -float(mean) if _finite_number(mean) else None
    out["cluster_t"] = -float(cluster_t) if _finite_number(cluster_t) else None
    out["sign_transform"] = "persistence = -excess_abs"
    return out


def _confirmation_gate(primary: dict) -> dict:
    observed = {}
    passed = True

    for name in ("persistence_4b", "persistence_8b"):
        stats = primary[name]
        mean = stats.get("mean")
        cluster_t = stats.get("cluster_t")
        mean_positive = _finite_number(mean) and float(mean) > 0.0
        t_above_2 = _finite_number(cluster_t) and float(cluster_t) > 2.0

        observed[name] = {
            "mean": mean,
            "complete_jackknife_t": cluster_t,
            "mean_positive": mean_positive,
            "complete_jackknife_t_above_2": t_above_2,
            "reason": stats.get("reason"),
            "required_replicates": stats.get("required_replicates"),
            "valid_replicates": stats.get("valid_replicates"),
            "undefined_delete_days": stats.get("undefined_delete_days"),
        }
        passed = passed and mean_positive and t_above_2

    return {
        "primary_state": "bottom10",
        "primary_metrics": ["persistence_4b", "persistence_8b"],
        "joint_gate": "ALL_REQUIRED",
        "frozen_requirements": {
            "each_mean_gt": 0.0,
            "each_complete_jackknife_t_gt": 2.0,
        },
        "observed": observed,
        "status": "PASS" if passed else "FAIL",
        "descriptive_metrics_cannot_rescue_primary": [
            "bottom10_1b",
            "bottom10_2b",
            "bottom10_16b",
            "all_bottom20",
            "yearly_stability",
            "naive_t",
        ],
    }


def _naive_primary(events: list[dict]) -> dict:
    bottom10 = [
        e
        for e in events
        if e.get("compression_state") == "bottom10"
    ]
    out = {}
    for h in (4, 8):
        key = f"excess_abs_{h}b"
        persistence = discovery.signed_stats(
            -float(e[key])
            for e in bottom10
            if isinstance(e.get(key), (int, float))
        )
        out[f"persistence_{h}b"] = persistence
    return out


def run_from_index(index_path: Path, progress_path: Path) -> dict:
    progress_path = _validate_progress_path(progress_path)
    if CANONICAL_OUTPUT.exists():
        raise RuntimeError(
            "existing R27 confirmation result detected; refusing scientific overwrite"
        )

    cleaned = _cleanup_stale_transients()

    _write_progress(
        progress_path,
        phase="starting",
        fraction=0.0,
        confirmation_opened=False,
        cleaned_transients=cleaned,
    )

    index_content = stage._read_canonical_r15_index(index_path)

    def builder_progress(state: dict) -> None:
        completed = int(state["completed"])
        total = int(state["total"])
        fraction = 0.75 * (completed / total if total else 0.0)
        _write_progress(
            progress_path,
            phase="build_m5",
            confirmation_opened=True,
            fraction=fraction,
            completed=completed,
            total=total,
            last_opened_payload_date=state.get("last_opened_payload_date"),
            decoded_m1=state.get("decoded_m1"),
            emitted_m5=state.get("emitted_m5"),
        )
        print(
            f"progress build days={completed}/{total} "
            f"m5={state.get('emitted_m5', 0)} fraction={fraction:.6f}",
            flush=True,
        )

    with tempfile.TemporaryDirectory(
        prefix="guardian_r27_confirmation_v100_"
    ) as td:
        verified_index = Path(td) / "verified_r15_index.csv"
        verified_index.write_bytes(index_content)

        generated_csv = Path(td) / "sealed_confirmation_m5.csv"
        receipt = sealed_builder.build(
            verified_index,
            generated_csv,
            progress_callback=builder_progress,
        )
        stage._validate_builder_receipt(receipt, generated_csv)

        _write_progress(
            progress_path,
            phase="load_m5",
            confirmation_opened=True,
            fraction=0.78,
            builder_receipt=receipt,
        )
        bars = stage.load_generated_confirmation_bars(generated_csv)

        _write_progress(
            progress_path,
            phase="extract_R27_events",
            confirmation_opened=True,
            fraction=0.82,
            rows=len(bars),
        )
        raw_events = r27_event_extractor(bars)
        events = [
            {**event, "research": "R27", "origin_research": "R22"}
            for event in raw_events
        ]
        bottom10_events = [
            e for e in events if e.get("compression_state") == "bottom10"
        ]

        _write_progress(
            progress_path,
            phase="jackknife_4b",
            confirmation_opened=True,
            fraction=0.88,
            rows=len(bars),
            bottom10_event_count=len(bottom10_events),
        )
        raw4 = r27_complete_jackknife(bars, raw_events, "bottom10", 4)
        p4 = _persistence_stats(raw4)

        _write_progress(
            progress_path,
            phase="jackknife_8b",
            confirmation_opened=True,
            fraction=0.94,
            rows=len(bars),
            bottom10_event_count=len(bottom10_events),
        )
        raw8 = r27_complete_jackknife(bars, raw_events, "bottom10", 8)
        p8 = _persistence_stats(raw8)

        primary = {
            "persistence_4b": p4,
            "persistence_8b": p8,
        }
        gate = _confirmation_gate(primary)
        naive = _naive_primary(events)

        _write_progress(
            progress_path,
            phase="serialize",
            confirmation_opened=True,
            fraction=0.99,
            rows=len(bars),
            event_count=len(events),
            bottom10_event_count=len(bottom10_events),
            gate_status=gate["status"],
        )

        return {
            "schema": 1,
            "research": "R27",
            "version": "1.00",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "confirmation",
            "origin": (
                "new preregistered inverse study inspired by R22 "
                "compression->expansion discovery failure"
            ),
            "independence_disclosure": (
                "2019-07-01..2024-12-31 payload bytes were previously opened "
                "for R21/R26 only; no R22/R27 confirmation metric was computed "
                "or viewed before R27 preregistration"
            ),
            "source_contract": (
                "audited sealed confirmation builder + canonical pinned R15 index"
            ),
            "source_index": str(index_path),
            "source_index_sha256": stage.CANONICAL_R15_INDEX_SHA256,
            "builder_receipt": receipt,
            "rows": len(bars),
            "first_epoch": bars[0].epoch,
            "last_epoch": bars[-1].epoch,
            "stage_boundaries": {
                "discovery_origin": "2004-11-08..2019-06-30",
                "confirmation_start": stage.CONFIRMATION_START.isoformat(),
                "confirmation_end": stage.CONFIRMATION_END.isoformat(),
                "preoos_2025": "INACCESSIBLE_IN_V1_00",
                "protected_2026_plus": "HARD_SEALED",
            },
            "confirmation_opened": True,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "frozen_hypothesis": (
                "bottom10 prior-48-M5 volatility compression remains quieter "
                "than the same-clock unconditional baseline at 4b and 8b"
            ),
            "doctrine": (
                "bottom10 only; joint 4b+8b complete-jackknife confirmation; "
                "no state/horizon rescue; no PnL optimization"
            ),
            "cleaned_transients": cleaned,
            "event_count_all_states": len(events),
            "event_count_bottom10": len(bottom10_events),
            "primary_complete_jackknife": primary,
            "primary_naive_descriptive": naive,
            "confirmation_gate": gate,
            "events": events,
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--index",
        required=True,
        type=Path,
        help="Canonical R15 index only; audited admission is enforced.",
    )
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--progress", required=True, type=Path)
    a = ap.parse_args()

    output = _validate_output_path(a.output)
    progress_path = _validate_progress_path(a.progress)

    payload = run_from_index(a.index, progress_path)
    _atomic_json(output, payload)
    _write_progress(
        progress_path,
        phase="complete",
        confirmation_opened=True,
        fraction=1.0,
        output=str(output),
        rows=payload["rows"],
        event_count=payload["event_count_all_states"],
        bottom10_event_count=payload["event_count_bottom10"],
        gate_status=payload["confirmation_gate"]["status"],
    )

    print(
        json.dumps(
            {
                "research": "R27",
                "stage": "confirmation",
                "gate_status": payload["confirmation_gate"]["status"],
                "persistence_4b": payload["confirmation_gate"]["observed"][
                    "persistence_4b"
                ],
                "persistence_8b": payload["confirmation_gate"]["observed"][
                    "persistence_8b"
                ],
                "bottom10_events": payload["event_count_bottom10"],
                "rows": payload["rows"],
                "pre_oos_2025_opened": False,
                "protected_2026_opened": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
