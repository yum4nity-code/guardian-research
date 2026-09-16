#!/usr/bin/env python3
"""R21 XAUUSD independent confirmation engine v1.00.

Frozen study:
- R21 only
- 08:20 America/New_York M5 close anchor
- primary response: post_15m
- confirmation window: 2019-07-01 through 2024-12-31
- gate: mean > 0 AND day-clustered t > +2.0
- 30m/60m/120m descriptive only

The R21 event extractor and statistics are reused from the reviewed discovery
implementation. This wrapper changes only the physically sealed data stage.
2025 and 2026+ are inaccessible.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import build_xau_m5_r21_confirmation_slice_v1_00 as sealed_builder
import xau_edge_discovery_r21_r25_v1_01 as base

Bar = base.Bar
r21_comex_unconditional_drift = base.r21_comex_unconditional_drift
_metric_summary = base._metric_summary

CONFIRMATION_START = date(2019, 7, 1)
CONFIRMATION_END = date(2024, 12, 31)
PREOOS_START = date(2025, 1, 1)
PROTECTED_START = date(2026, 1, 1)

CANONICAL_R15_INDEX = Path(
    "D:/MT5_Backtests/Research/Autonomous/r15_dukascopy_xauusd_union_v1/"
    "xauusd_dukascopy_master_payload_index.csv"
)
CANONICAL_R15_INDEX_SHA256 = (
    "d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566"
)
R15_PIN_ATTESTATION = Path(__file__).with_name(
    "R15_INDEX_PIN_ATTESTATION_2026_09_16.json"
)

CANONICAL_OUTPUT_DIR = Path(
    "D:/MT5_Backtests/Research/Autonomous/r21_xau_confirmation_v100"
)
CANONICAL_OUTPUT = CANONICAL_OUTPUT_DIR / "confirmation.json"
CANONICAL_PROGRESS = CANONICAL_OUTPUT_DIR / "progress.json"


def _validate_pin_attestation() -> dict:
    try:
        attestation = json.loads(R15_PIN_ATTESTATION.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("R15 pin attestation missing or invalid") from exc

    required = {
        "status": "PASS",
        "phase": "r15-dukascopy-xauusd-boundary-union",
        "payload_count": 5518,
        "eligible_boundary_days": 5518,
        "known_missing_or_holiday_weekdays": 0,
        "payload_index_csv_sha256": CANONICAL_R15_INDEX_SHA256,
        "protected_2026_opened": False,
    }
    for key, expected in required.items():
        if attestation.get(key) != expected:
            raise RuntimeError(f"R15 pin attestation mismatch: {key}")
    window = attestation.get("window")
    if window != {"start": "2004-11-08", "end_exclusive": "2026-01-01"}:
        raise RuntimeError("R15 pin attestation window mismatch")
    return attestation


def _read_canonical_r15_index(index_path: Path) -> bytes:
    trusted = CANONICAL_R15_INDEX.absolute()

    if index_path.absolute() != trusted:
        raise RuntimeError("refusing to open non-canonical R15 index path")
    if index_path.resolve(strict=True) != trusted:
        raise RuntimeError("refusing redirected canonical R15 index path")

    _validate_pin_attestation()
    content = index_path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != CANONICAL_R15_INDEX_SHA256:
        raise RuntimeError("canonical R15 index SHA256 mismatch; builder not called")
    return content


def _validate_artifact_path(path: Path, expected: Path, label: str) -> Path:
    if not path.is_absolute() or path.absolute() != expected.absolute():
        raise RuntimeError(f"{label} must use its canonical R21 confirmation path")

    root = CANONICAL_OUTPUT_DIR.absolute()
    if root.parent.resolve(strict=True) != root.parent.absolute():
        raise RuntimeError("canonical R21 confirmation output parent is redirected")

    root.mkdir(parents=True, exist_ok=True)
    if root.resolve(strict=True) != root:
        raise RuntimeError("canonical R21 confirmation output directory is redirected")

    if path.is_symlink() or (
        path.exists() and path.resolve(strict=True) != path.absolute()
    ):
        raise RuntimeError(f"canonical R21 confirmation {label} file is redirected")

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
            "research": "R21",
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
    """Remove only local transient artifacts from interrupted R21 confirmation."""
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
    for p in temp_base.glob("guardian_r21_confirmation_v100_*"):
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


def load_generated_confirmation_bars(path: Path) -> list[Bar]:
    out: list[Bar] = []
    previous_epoch: int | None = None

    with path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        required = {"timeframe", "server_epoch", "open", "high", "low", "close"}
        missing = required - set(r.fieldnames or [])
        if missing:
            raise RuntimeError(f"missing columns: {sorted(missing)}")

        for row in r:
            epoch = int(row["server_epoch"])
            if epoch % 300 != 0:
                raise RuntimeError(f"off-grid M5 timestamp: {epoch}")
            if previous_epoch is not None and epoch <= previous_epoch:
                raise RuntimeError(
                    f"non-increasing timestamp: {epoch} <= {previous_epoch}"
                )
            previous_epoch = epoch

            dt = datetime.fromtimestamp(epoch, tz=timezone.utc)
            if not CONFIRMATION_START <= dt.date() <= CONFIRMATION_END:
                raise RuntimeError(
                    f"generated confirmation CSV escaped frozen window: "
                    f"{dt.isoformat()}"
                )

            tf = row["timeframe"].strip().upper()
            if tf != "M5":
                raise RuntimeError(f"R21 confirmation requires M5, got {tf}")

            o, h, l, c = map(
                float,
                (row["open"], row["high"], row["low"], row["close"]),
            )
            if not all(math.isfinite(x) and x > 0 for x in (o, h, l, c)):
                raise RuntimeError(f"invalid OHLC at {dt.isoformat()}")
            if h < max(o, c) or l > min(o, c) or h < l:
                raise RuntimeError(f"invalid OHLC geometry at {dt.isoformat()}")

            out.append(Bar(epoch, dt, tf, o, h, l, c))

    if not out:
        raise RuntimeError("no usable generated R21 confirmation rows")
    return out


def _validate_builder_receipt(receipt: dict, generated_csv: Path) -> None:
    expected = {
        "status": "PASS",
        "stage": "confirmation",
        "stage_start": CONFIRMATION_START.isoformat(),
        "stage_end_inclusive": CONFIRMATION_END.isoformat(),
        "confirmation_opened": True,
        "pre_oos_2025_opened": False,
        "protected_2026_opened": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RuntimeError(
                f"sealed builder receipt mismatch {key}: "
                f"{receipt.get(key)!r} != {value!r}"
            )

    if Path(str(receipt.get("output", ""))).resolve() != generated_csv.resolve():
        raise RuntimeError("sealed builder receipt output path mismatch")

    first_opened = receipt.get("first_opened_payload_date")
    last_opened = receipt.get("last_opened_payload_date")
    if first_opened and first_opened < CONFIRMATION_START.isoformat():
        raise RuntimeError("builder claims a pre-confirmation payload was opened")
    if last_opened and last_opened > CONFIRMATION_END.isoformat():
        raise RuntimeError("builder claims a post-confirmation payload was opened")


def _confirmation_gate(summary: dict) -> dict:
    metric = summary["metrics"]["post_15m"]["clustered"]
    mean = metric.get("mean")
    cluster_t = metric.get("cluster_t")

    mean_positive = isinstance(mean, (int, float)) and math.isfinite(mean) and mean > 0
    t_above_2 = (
        isinstance(cluster_t, (int, float))
        and math.isfinite(cluster_t)
        and cluster_t > 2.0
    )

    return {
        "primary_metric": "post_15m",
        "frozen_requirements": {
            "mean_gt": 0.0,
            "day_clustered_t_gt": 2.0,
        },
        "observed": {
            "mean": mean,
            "day_clustered_t": cluster_t,
        },
        "mean_positive": mean_positive,
        "day_clustered_t_above_2": t_above_2,
        "status": "PASS" if mean_positive and t_above_2 else "FAIL",
        "yearly_stability_is_descriptive_only": True,
        "descriptive_metrics_cannot_rescue_primary": [
            "post_30m",
            "post_60m",
            "post_120m",
        ],
    }


def run_from_index(index_path: Path, progress_path: Path) -> dict:
    progress_path = _validate_progress_path(progress_path)
    if CANONICAL_OUTPUT.exists():
        raise RuntimeError(
            "existing R21 confirmation result detected; refusing scientific overwrite"
        )
    cleaned = _cleanup_stale_transients()

    _write_progress(
        progress_path,
        phase="starting",
        fraction=0.0,
        confirmation_opened=False,
        cleaned_transients=cleaned,
    )

    index_content = _read_canonical_r15_index(index_path)

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
        prefix="guardian_r21_confirmation_v100_"
    ) as td:
        verified_index = Path(td) / "verified_r15_index.csv"
        verified_index.write_bytes(index_content)

        generated_csv = Path(td) / "sealed_confirmation_m5.csv"
        receipt = sealed_builder.build(
            verified_index,
            generated_csv,
            progress_callback=builder_progress,
        )
        _validate_builder_receipt(receipt, generated_csv)

        _write_progress(
            progress_path,
            phase="load_m5",
            confirmation_opened=True,
            fraction=0.84,
            builder_receipt=receipt,
        )
        bars = load_generated_confirmation_bars(generated_csv)

        _write_progress(
            progress_path,
            phase="analyze_R21",
            confirmation_opened=True,
            fraction=0.90,
            rows=len(bars),
        )
        events = r21_comex_unconditional_drift(bars)
        summary = {
            "research": "R21",
            "event_count": len(events),
            "day_count": len({e["cluster_day"] for e in events}),
            "metrics": _metric_summary(events, ("post_",)),
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
            "research": "R21",
            "version": "1.00",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "stage": "confirmation",
            "source_contract": (
                "sealed_confirmation_builder_from_canonical_sha256_pinned_r15_index"
            ),
            "source_index": str(index_path),
            "source_index_sha256": CANONICAL_R15_INDEX_SHA256,
            "builder_receipt": receipt,
            "rows": len(bars),
            "first_epoch": bars[0].epoch,
            "last_epoch": bars[-1].epoch,
            "stage_boundaries": {
                "discovery": "CLOSED",
                "confirmation_start": CONFIRMATION_START.isoformat(),
                "confirmation_end": CONFIRMATION_END.isoformat(),
                "preoos_2025": "INACCESSIBLE_IN_V1_00",
                "protected_2026_plus": "HARD_SEALED",
            },
            "confirmation_opened": True,
            "pre_oos_2025_opened": False,
            "protected_2026_opened": False,
            "frozen_hypothesis": (
                "positive unconditional XAUUSD return from the 08:20 "
                "America/New_York M5 close anchor to 15 minutes later"
            ),
            "doctrine": (
                "independent confirmation only; frozen R21 definition; "
                "no PnL optimization; no rescue"
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
        help="Canonical R15 index only; fixed path and SHA256 are enforced.",
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

    primary = payload["confirmation_gate"]["observed"]
    print(
        json.dumps(
            {
                "research": "R21",
                "stage": "confirmation",
                "gate_status": payload["confirmation_gate"]["status"],
                "post_15m_mean": primary["mean"],
                "post_15m_day_clustered_t": primary["day_clustered_t"],
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
