#!/usr/bin/env python3
"""R26 XAUUSD independent confirmation engine v1.00.

New study, preregistered after the R24 discovery-side sign inversion:
- exact reviewed R24 opening-range breakout event extractor
- response sign: reversal against breakout
- joint primary horizons: 2b and 4b
- PASS only if both means > 0 and both day-clustered t > +2.0
- 1b/8b/16b and continuation metrics are descriptive only

The immutable 2019-07-01..2024-12-31 confirmation slice builder previously
audited for R21 is reused without modification. 2025 and 2026+ are inaccessible.
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

r26_event_extractor = discovery.r24_comex_opening_range_breakout
_metric_summary = discovery._metric_summary

CANONICAL_OUTPUT_DIR = Path(
    "D:/MT5_Backtests/Research/Autonomous/r26_xau_confirmation_v100"
)
CANONICAL_OUTPUT = CANONICAL_OUTPUT_DIR / "confirmation.json"
CANONICAL_PROGRESS = CANONICAL_OUTPUT_DIR / "progress.json"


def _validate_artifact_path(path: Path, expected: Path, label: str) -> Path:
    if not path.is_absolute() or path.absolute() != expected.absolute():
        raise RuntimeError(f"{label} must use its canonical R26 confirmation path")

    root = CANONICAL_OUTPUT_DIR.absolute()
    if root.parent.resolve(strict=True) != root.parent.absolute():
        raise RuntimeError("canonical R26 confirmation output parent is redirected")

    root.mkdir(parents=True, exist_ok=True)
    if root.resolve(strict=True) != root:
        raise RuntimeError("canonical R26 confirmation output directory is redirected")

    if path.is_symlink() or (
        path.exists() and path.resolve(strict=True) != path.absolute()
    ):
        raise RuntimeError(f"canonical R26 confirmation {label} file is redirected")

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
            "research": "R26",
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
    """Remove only local transient artifacts from interrupted R26 confirmation."""
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
    for p in temp_base.glob("guardian_r26_confirmation_v100_*"):
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


def _confirmation_gate(summary: dict) -> dict:
    metrics = summary["metrics"]
    observed = {}
    passed = True

    for name in ("reversal_2b", "reversal_4b"):
        clustered = metrics[name]["clustered"]
        mean = clustered.get("mean")
        cluster_t = clustered.get("cluster_t")
        mean_positive = _finite_number(mean) and float(mean) > 0.0
        t_above_2 = _finite_number(cluster_t) and float(cluster_t) > 2.0

        observed[name] = {
            "mean": mean,
            "day_clustered_t": cluster_t,
            "mean_positive": mean_positive,
            "day_clustered_t_above_2": t_above_2,
        }
        passed = passed and mean_positive and t_above_2

    return {
        "primary_metrics": ["reversal_2b", "reversal_4b"],
        "joint_gate": "ALL_REQUIRED",
        "frozen_requirements": {
            "each_mean_gt": 0.0,
            "each_day_clustered_t_gt": 2.0,
        },
        "observed": observed,
        "status": "PASS" if passed else "FAIL",
        "yearly_stability_is_descriptive_only": True,
        "descriptive_metrics_cannot_rescue_primary": [
            "reversal_1b",
            "reversal_8b",
            "reversal_16b",
            "continuation_1b",
            "continuation_2b",
            "continuation_4b",
            "continuation_8b",
            "continuation_16b",
        ],
    }


def run_from_index(index_path: Path, progress_path: Path) -> dict:
    progress_path = _validate_progress_path(progress_path)
    if CANONICAL_OUTPUT.exists():
        raise RuntimeError(
            "existing R26 confirmation result detected; refusing scientific overwrite"
        )

    cleaned = _cleanup_stale_transients()

    _write_progress(
        progress_path,
        phase="starting",
        fraction=0.0,
        confirmation_opened=False,
        cleaned_transients=cleaned,
    )

    # Reuse the audited R15 provenance admission from R21 confirmation.
    index_content = stage._read_canonical_r15_index(index_path)

    def builder_progress(state: dict) -> None:
        completed = int(state["completed"])
        total = int(state["total"])
        fraction = 0.80 * (completed / total if total else 0.0)
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
        prefix="guardian_r26_confirmation_v100_"
    ) as td:
        verified_index = Path(td) / "verified_r15_index.csv"
        verified_index.write_bytes(index_content)

        generated_csv = Path(td) / "sealed_confirmation_m5.csv"
        receipt = sealed_builder.build(
            verified_index,
            generated_csv,
            progress_callback=builder_progress,
        )

        # Reuse the audited exact-coverage receipt validator and M5 loader.
        stage._validate_builder_receipt(receipt, generated_csv)

        _write_progress(
            progress_path,
            phase="load_m5",
            confirmation_opened=True,
            fraction=0.84,
            builder_receipt=receipt,
        )
        bars = stage.load_generated_confirmation_bars(generated_csv)

        _write_progress(
            progress_path,
            phase="analyze_R26",
            confirmation_opened=True,
            fraction=0.90,
            rows=len(bars),
        )
        raw_events = r26_event_extractor(bars)
        events = [
            {**event, "research": "R26", "origin_research": "R24"}
            for event in raw_events
        ]
        summary = {
            "research": "R26",
            "origin_event_definition": "R24 frozen opening-range breakout",
            "event_count": len(events),
            "day_count": len({e["cluster_day"] for e in events}),
            "metrics": _metric_summary(
                events,
                ("reversal_", "continuation_"),
            ),
        }
        gate = _confirmation_gate(summary)

        _write_progress(
            progress_path,
            phase="serialize",
            confirmation_opened=True,
            fraction=0.99,
            rows=len(bars),
            event_count=len(events),
            gate_status=gate["status"],
        )

        return {
            "schema": 1,
            "research": "R26",
            "version": "1.00",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "confirmation",
            "origin": (
                "new preregistered study inspired by R24 discovery-side "
                "continuation-sign inversion"
            ),
            "independence_disclosure": (
                "2019-07-01..2024-12-31 payload bytes were previously opened "
                "for R21 only; no R24/R26 confirmation metric was computed or "
                "viewed before R26 preregistration"
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
                "first close outside completed 08:20-08:35 NY opening range "
                "is followed by reversal against breakout direction"
            ),
            "doctrine": (
                "joint 2b+4b confirmation; no horizon rescue; "
                "no PnL optimization"
            ),
            "cleaned_transients": cleaned,
            "confirmation_gate": gate,
            "result": {
                "summary": summary,
                "events": events,
            },
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
        event_count=payload["result"]["summary"]["event_count"],
        gate_status=payload["confirmation_gate"]["status"],
    )

    observed = payload["confirmation_gate"]["observed"]
    print(
        json.dumps(
            {
                "research": "R26",
                "stage": "confirmation",
                "gate_status": payload["confirmation_gate"]["status"],
                "reversal_2b": observed["reversal_2b"],
                "reversal_4b": observed["reversal_4b"],
                "events": payload["result"]["summary"]["event_count"],
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
