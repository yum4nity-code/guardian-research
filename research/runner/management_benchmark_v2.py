#!/usr/bin/env python3
"""Guardian Management Benchmark V2: late-protection cross-family replay.

Exploratory only. Reuses frozen compact Trade Path evidence and never changes
parent experiment verdicts or launches MT5.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import management_benchmark as v1
import publisher
import runner

PREREG = "research/management/MANAGEMENT_BENCHMARK_V2_PREREGISTRATION_2026_09_07.md"
BENCHMARK_ID = "management-v2"
DEFAULT_DATASETS = ("D038", "D039", "D040", "D045")
DEFAULT_STAGE = "development"

RULES: tuple[dict[str, Any], ...] = (
    {"name": "BASELINE_ORIGINAL", "kind": "baseline"},
    {"name": "BE_AFTER_3R", "kind": "floor", "milestone": 3.0, "suffix": "3r", "floor": 0.0},
    {"name": "LOCK1_AFTER_2R", "kind": "floor", "milestone": 2.0, "suffix": "2r", "floor": 1.0},
    {"name": "LOCK1_AFTER_3R", "kind": "floor", "milestone": 3.0, "suffix": "3r", "floor": 1.0},
    {"name": "LOCK2_AFTER_3R", "kind": "floor", "milestone": 3.0, "suffix": "3r", "floor": 2.0},
    {"name": "P25_AT_2R_REST_ORIGINAL", "kind": "partial", "milestone": 2.0, "suffix": "2r", "fraction": 0.25},
    {"name": "P25_AT_3R_REST_ORIGINAL", "kind": "partial", "milestone": 3.0, "suffix": "3r", "fraction": 0.25},
    {"name": "P25_AT_2R_LOCK1_REST", "kind": "partial_floor", "milestone": 2.0, "suffix": "2r", "fraction": 0.25, "floor": 1.0},
    {"name": "P25_AT_3R_LOCK2_REST", "kind": "partial_floor", "milestone": 3.0, "suffix": "3r", "fraction": 0.25, "floor": 2.0},
    {"name": "SL1_TP5", "kind": "fixed", "sl": 1.0, "tp": 5.0, "suffix": "5r"},
)

REQUIRED_V2_FIELDS = {
    "symbol", "gross_r", "commission_r", "net_r", "net_r_commission_x1_5",
    "path_ambiguous", "mae_r", "exit_reason",
    "reached_2r", "mae_before_2r", "min_r_after_first_2r_before_exit",
    "reached_3r", "mae_before_3r", "min_r_after_first_3r_before_exit",
    "reached_5r", "mae_before_5r",
}


class BenchmarkV2Error(RuntimeError):
    pass


def _f(row: dict[str, str], field: str) -> float:
    try:
        value = float(row.get(field, ""))
    except (TypeError, ValueError) as exc:
        raise BenchmarkV2Error(f"invalid {field}: {row.get(field)!r}") from exc
    if not math.isfinite(value):
        raise BenchmarkV2Error(f"non-finite {field}: {value}")
    return value


def _opt(row: dict[str, str], field: str) -> float | None:
    raw = row.get(field, "")
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise BenchmarkV2Error(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value):
        raise BenchmarkV2Error(f"non-finite {field}: {value}")
    return value


def _flag(row: dict[str, str], field: str) -> bool:
    raw = str(row.get(field, ""))
    if raw not in {"0", "1"}:
        raise BenchmarkV2Error(f"{field} must be 0/1, got {raw!r}")
    return raw == "1"


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _pf(values: list[float]) -> dict[str, Any]:
    wins = sum(x for x in values if x > 0)
    losses = abs(sum(x for x in values if x < 0))
    if losses == 0:
        return {"value": None, "infinite": wins > 0}
    return {"value": wins / losses, "infinite": False}


def _summary(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "mean": _mean(values),
        "median": _median(values),
        "total": sum(values),
        "profit_factor": _pf(values),
        "win_rate": (sum(1 for x in values if x > 0) / len(values)) if values else None,
    }


def validate_rows(rows: list[dict[str, str]], label: str) -> None:
    if not rows:
        raise BenchmarkV2Error(f"empty compact dataset: {label}")
    missing = sorted(REQUIRED_V2_FIELDS - set(rows[0]))
    if missing:
        raise BenchmarkV2Error(f"{label} missing V2 fields: {missing}")


def apply_rule(row: dict[str, str], rule: dict[str, Any]) -> tuple[float | None, str]:
    original = _f(row, "gross_r")
    if rule["kind"] == "baseline":
        return original, "ORIGINAL_EXIT"
    if _flag(row, "path_ambiguous"):
        return None, "EXCLUDED_PATH_AMBIGUOUS"

    kind = str(rule["kind"])
    suffix = str(rule.get("suffix", ""))
    reached = _flag(row, f"reached_{suffix}") if suffix else False

    if kind == "floor":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        low = _opt(row, f"min_r_after_first_{suffix}_before_exit")
        if low is None:
            return None, "EXCLUDED_MISSING_POST_TOUCH_PATH"
        floor = float(rule["floor"])
        if low <= floor:
            return floor, "LATE_FLOOR_THRESHOLD_PROXY"
        return original, "ORIGINAL_EXIT_NO_FLOOR_RETRACE"

    if kind == "partial":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        fraction = float(rule["fraction"])
        milestone = float(rule["milestone"])
        return fraction * milestone + (1.0 - fraction) * original, "LATE_PARTIAL_PLUS_ORIGINAL_REMAINDER"

    if kind == "partial_floor":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        low = _opt(row, f"min_r_after_first_{suffix}_before_exit")
        if low is None:
            return None, "EXCLUDED_MISSING_POST_TOUCH_PATH"
        fraction = float(rule["fraction"])
        milestone = float(rule["milestone"])
        floor = float(rule["floor"])
        remainder = floor if low <= floor else original
        reason = "LATE_PARTIAL_PLUS_FLOOR_PROXY" if low <= floor else "LATE_PARTIAL_PLUS_ORIGINAL_REMAINDER"
        return fraction * milestone + (1.0 - fraction) * remainder, reason

    if kind == "fixed":
        sl = float(rule["sl"])
        tp = float(rule["tp"])
        if reached:
            mae_before = _f(row, f"mae_before_{suffix}")
            if mae_before >= sl:
                return -sl, "SL_BEFORE_LATE_TP_THRESHOLD_PROXY"
            return tp, "LATE_TP_THRESHOLD_PROXY"
        mae = _f(row, "mae_r")
        if mae >= sl:
            if sl == 1.0 and str(row.get("exit_reason", "")) == "STOP":
                return original, "ORIGINAL_1R_STOP_FILL"
            return -sl, "SL_THRESHOLD_PROXY"
        return original, "ORIGINAL_EXIT_NO_THRESHOLD"

    raise BenchmarkV2Error(f"unknown V2 rule kind: {kind}")


def evaluate_dataset(ds: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    rows: list[dict[str, str]] = ds["rows"]
    validate_rows(rows, ds["identifier"])
    matrix: list[dict[str, Any]] = []
    deltas: dict[str, list[float]] = {}

    for rule in RULES:
        gross_values: list[float] = []
        net_values: list[float] = []
        stress_values: list[float] = []
        baseline_same: list[float] = []
        row_deltas: list[float] = []
        counts: dict[str, int] = {}
        excluded = 0
        for row in rows:
            gross, reason = apply_rule(row, rule)
            counts[reason] = counts.get(reason, 0) + 1
            if gross is None:
                excluded += 1
                continue
            commission = _f(row, "commission_r")
            baseline_net = _f(row, "net_r")
            net = gross - commission
            stress = gross - 1.5 * commission
            gross_values.append(gross)
            net_values.append(net)
            stress_values.append(stress)
            baseline_same.append(baseline_net)
            row_deltas.append(net - baseline_net)
        matrix.append({
            "dataset": ds["identifier"],
            "experiment_id": ds["experiment_id"],
            "stage": ds["stage"],
            "rule": rule["name"],
            "rule_kind": rule["kind"],
            "input_rows": len(rows),
            "eligible_rows": len(net_values),
            "excluded_rows": excluded,
            "gross_r_proxy": _summary(gross_values),
            "net_r_proxy": _summary(net_values),
            "commission_stress_1_5x_r_proxy": _summary(stress_values),
            "baseline_net_r_same_rows": _summary(baseline_same),
            "mean_net_delta_vs_baseline": _mean(row_deltas),
            "total_net_delta_vs_baseline": sum(row_deltas),
            "classification_counts": dict(sorted(counts.items())),
            "confirmation_grade": False,
        })
        deltas[str(rule["name"])] = row_deltas
    return matrix, deltas


def cross_family(matrix: list[dict[str, Any]], pooled: dict[str, list[float]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in matrix:
        grouped.setdefault(str(row["rule"]), []).append(row)
    results: list[dict[str, Any]] = []
    for rule in RULES:
        name = str(rule["name"])
        if name == "BASELINE_ORIGINAL":
            continue
        family_rows = grouped.get(name, [])
        family_deltas = [float(r["mean_net_delta_vs_baseline"]) for r in family_rows if r["mean_net_delta_vs_baseline"] is not None]
        pooled_values = pooled.get(name, [])
        results.append({
            "rule": name,
            "families_evaluated": len(family_deltas),
            "families_improved": sum(1 for x in family_deltas if x > 0),
            "families_degraded": sum(1 for x in family_deltas if x < 0),
            "families_flat": sum(1 for x in family_deltas if x == 0),
            "equal_family_mean_delta_r": _mean(family_deltas),
            "median_family_delta_r": _median(family_deltas),
            "worst_family_delta_r": min(family_deltas) if family_deltas else None,
            "best_family_delta_r": max(family_deltas) if family_deltas else None,
            "pooled_trade_weighted_mean_delta_r": _mean(pooled_values),
            "pooled_total_delta_r": sum(pooled_values),
            "family_deltas": {str(r["dataset"]): r["mean_net_delta_vs_baseline"] for r in family_rows},
            "confirmation_grade": False,
        })

    def key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            -int(item["families_improved"]),
            -float(item["worst_family_delta_r"] if item["worst_family_delta_r"] is not None else -1e9),
            -float(item["median_family_delta_r"] if item["median_family_delta_r"] is not None else -1e9),
            -float(item["equal_family_mean_delta_r"] if item["equal_family_mean_delta_r"] is not None else -1e9),
            -float(item["pooled_trade_weighted_mean_delta_r"] if item["pooled_trade_weighted_mean_delta_r"] is not None else -1e9),
            str(item["rule"]),
        )
    ranked = sorted(results, key=key)
    for i, item in enumerate(ranked, start=1):
        item["rank"] = i
    return ranked


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _write_matrix(path: Path, matrix: list[dict[str, Any]]) -> None:
    fields = [
        "dataset", "experiment_id", "stage", "rule", "input_rows", "eligible_rows", "excluded_rows",
        "mean_net_r_proxy", "total_net_r_proxy", "pf_net_r_proxy", "win_rate_net_r_proxy",
        "mean_stress_r_proxy", "mean_net_delta_vs_baseline", "total_net_delta_vs_baseline",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in matrix:
            pf = row["net_r_proxy"]["profit_factor"]
            writer.writerow({
                "dataset": row["dataset"],
                "experiment_id": row["experiment_id"],
                "stage": row["stage"],
                "rule": row["rule"],
                "input_rows": row["input_rows"],
                "eligible_rows": row["eligible_rows"],
                "excluded_rows": row["excluded_rows"],
                "mean_net_r_proxy": row["net_r_proxy"]["mean"],
                "total_net_r_proxy": row["net_r_proxy"]["total"],
                "pf_net_r_proxy": "INF" if pf["infinite"] else pf["value"],
                "win_rate_net_r_proxy": row["net_r_proxy"]["win_rate"],
                "mean_stress_r_proxy": row["commission_stress_1_5x_r_proxy"]["mean"],
                "mean_net_delta_vs_baseline": row["mean_net_delta_vs_baseline"],
                "total_net_delta_vs_baseline": row["total_net_delta_vs_baseline"],
            })


def _summary_md(payload: dict[str, Any]) -> str:
    lines = [
        "# Guardian Management Benchmark V2",
        "",
        "**Exploratory late-protection replay only — not confirmation-grade. V1 remains immutable.**",
        "",
        "Datasets: D038, D039, D040, D045 (1,803 frozen development trades)",
        "",
        "## Cross-family ranking",
        "",
        "| Rank | Rule | Improved | Worst ΔR | Median ΔR | Equal-family ΔR | Pooled ΔR/trade |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for item in payload["cross_family_ranking"]:
        lines.append(
            f"| {item['rank']} | {item['rule']} | {item['families_improved']}/{item['families_evaluated']} | "
            f"{item['worst_family_delta_r']:.6f} | {item['median_family_delta_r']:.6f} | "
            f"{item['equal_family_mean_delta_r']:.6f} | {item['pooled_trade_weighted_mean_delta_r']:.6f} |"
        )
    lines += [
        "",
        "## Boundary",
        "",
        "Results are R-threshold proxies using original round-turn commission. No V2 rule may alter parent verdicts or be treated as production evidence.",
        "Time exits, continuous trailing and exact 2.5R partials remain unsupported without richer path/MT5 replay.",
        "",
    ]
    return "\n".join(lines)


def publish(output_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    remote = publisher._run_git(["-C", str(runner.ROOT), "remote", "get-url", "origin"])
    event_id = output_dir.name
    clone_dir = workspace / "result_transport" / f"{event_id}_management_v2"
    target_rel = Path("benchmarks") / BENCHMARK_ID / "live" / "events" / event_id
    latest_rel = Path("benchmarks") / BENCHMARK_ID / "live" / "latest.json"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    try:
        publisher._run_git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", publisher.RESULT_BRANCH, remote, str(clone_dir)], timeout=300)
        target = clone_dir / target_rel
        if target.exists():
            existing = json.loads((target / "event.json").read_text(encoding="utf-8"))
            if existing.get("fingerprint_sha256") != payload["fingerprint_sha256"]:
                raise BenchmarkV2Error(f"event collision at {target_rel.as_posix()}")
            status = "BENCHMARK_PUBLISH_NOOP_ALREADY_PRESENT"
        else:
            target.mkdir(parents=True, exist_ok=False)
            for name in ("benchmark.json", "rule_matrix.csv", "SUMMARY.md"):
                shutil.copy2(output_dir / name, target / name)
            event = {
                "schema_version": 1,
                "benchmark_id": BENCHMARK_ID,
                "event_id": event_id,
                "status": "MANAGEMENT_BENCHMARK_V2_COMPLETE",
                "fingerprint_sha256": payload["fingerprint_sha256"],
                "top_rules": payload["cross_family_ranking"][:5],
                "files": {
                    name: {"sha256": runner.sha256_file(output_dir / name), "bytes": (output_dir / name).stat().st_size}
                    for name in ("benchmark.json", "rule_matrix.csv", "SUMMARY.md")
                },
                "autosync_used": False,
            }
            (target / "event.json").write_text(json.dumps(event, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
            status = "BENCHMARK_PUBLISH_PASS"
        latest = {
            "schema_version": 1,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "benchmark_id": BENCHMARK_ID,
            "event_id": event_id,
            "event_path": target_rel.as_posix(),
            "status": "MANAGEMENT_BENCHMARK_V2_COMPLETE",
            "fingerprint_sha256": payload["fingerprint_sha256"],
            "autosync_used": False,
        }
        latest_path = clone_dir / latest_rel
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        publisher._run_git(["add", "--", target_rel.as_posix(), latest_rel.as_posix()], cwd=clone_dir)
        if publisher._run_git(["status", "--porcelain"], cwd=clone_dir):
            publisher._run_git(["-c", "user.name=Guardian Research Runner", "-c", "user.email=guardian-runner@local", "commit", "-m", f"Record Management Benchmark V2 {event_id}"], cwd=clone_dir)
            commit_sha = publisher._run_git(["rev-parse", "HEAD"], cwd=clone_dir)
            publisher._run_git(["push", "origin", f"HEAD:{publisher.RESULT_BRANCH}"], cwd=clone_dir, timeout=300)
        else:
            commit_sha = publisher._run_git(["rev-parse", "HEAD"], cwd=clone_dir)
        return {"status": status, "branch": publisher.RESULT_BRANCH, "event_path": target_rel.as_posix(), "latest_path": latest_rel.as_posix(), "commit_sha": commit_sha, "autosync_used": False}
    except Exception as exc:
        return {"status": "BENCHMARK_PUBLISH_FAILED_LOCAL_RESULT_PRESERVED", "error": str(exc), "branch": publisher.RESULT_BRANCH, "autosync_used": False}
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir, ignore_errors=True)


def run_benchmark(dataset_ids: tuple[str, ...] = DEFAULT_DATASETS, stage: str = DEFAULT_STAGE, do_publish: bool = True) -> dict[str, Any]:
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    datasets = [v1._dataset(identifier, stage, workspace) for identifier in dataset_ids]
    matrix: list[dict[str, Any]] = []
    pooled: dict[str, list[float]] = {str(r["name"]): [] for r in RULES}
    for ds in datasets:
        local_matrix, local_deltas = evaluate_dataset(ds)
        matrix.extend(local_matrix)
        for name, values in local_deltas.items():
            pooled[name].extend(values)
    ranking = cross_family(matrix, pooled)
    created = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": BENCHMARK_ID,
        "created_at_utc": created.isoformat(),
        "preregistration": PREREG,
        "stage": stage,
        "scientific_role": "EXPLORATORY_SECOND_PASS_LATE_PROTECTION_PATH_REPLAY_NOT_CONFIRMATION_GRADE",
        "v1_is_immutable_seen_evidence": True,
        "datasets": [
            {k: ds[k] for k in ("identifier", "experiment_id", "manifest_path", "stage", "compact_path", "compact_sha256")} | {"rows": len(ds["rows"])}
            for ds in datasets
        ],
        "rules": list(RULES),
        "matrix": matrix,
        "cross_family_ranking": ranking,
        "limitations": {
            "threshold_fill_proxy": True,
            "original_roundturn_commission_r_reused": True,
            "continuous_trailing_supported": False,
            "time_exit_supported": False,
            "exact_2_5r_partial_supported": False,
            "wider_than_original_stop_supported": False,
            "parent_verdicts_changed": False,
            "confirmation_grade": False,
        },
        "autosync_used": False,
    }
    payload["fingerprint_sha256"] = _fingerprint(payload)
    out_dir = workspace / "management_benchmarks" / "v2" / created.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=False)
    (out_dir / "benchmark.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    _write_matrix(out_dir / "rule_matrix.csv", matrix)
    (out_dir / "SUMMARY.md").write_text(_summary_md(payload), encoding="utf-8", newline="\n")
    result = {
        "status": "MANAGEMENT_BENCHMARK_V2_COMPLETE",
        "benchmark_path": str(out_dir / "benchmark.json"),
        "matrix_path": str(out_dir / "rule_matrix.csv"),
        "summary_path": str(out_dir / "SUMMARY.md"),
        "fingerprint_sha256": payload["fingerprint_sha256"],
        "top_rules": ranking[:5],
        "autosync_used": False,
    }
    if do_publish:
        result["github_transport"] = publish(out_dir, payload)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Guardian Management Benchmark V2 without MT5")
    sub = ap.add_subparsers(dest="command", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    runp.add_argument("--stage", default=DEFAULT_STAGE)
    runp.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()
    try:
        result = run_benchmark(tuple(args.datasets), args.stage, not args.no_publish)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
