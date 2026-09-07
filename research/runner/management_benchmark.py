#!/usr/bin/env python3
"""Guardian Management Benchmark V1.

Exploratory cross-family path replay only. This tool never changes parent entry
verdicts and never claims confirmation-grade alternate-exit P/L.
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

import publisher
import runner

PREREG = "research/management/MANAGEMENT_BENCHMARK_V1_PREREGISTRATION_2026_09_07.md"
BENCHMARK_ID = "management-v1"
DEFAULT_DATASETS = ("D038", "D039", "D040", "D045")
DEFAULT_STAGE = "development"

RULES: tuple[dict[str, Any], ...] = (
    {"name": "BASELINE_ORIGINAL", "kind": "baseline"},
    {"name": "SL1_TP0_5", "kind": "fixed", "sl": 1.0, "tp": 0.5, "suffix": "0_5r"},
    {"name": "SL1_TP1", "kind": "fixed", "sl": 1.0, "tp": 1.0, "suffix": "1r"},
    {"name": "SL1_TP2", "kind": "fixed", "sl": 1.0, "tp": 2.0, "suffix": "2r"},
    {"name": "SL1_TP3", "kind": "fixed", "sl": 1.0, "tp": 3.0, "suffix": "3r"},
    {"name": "SL0_5_TP1", "kind": "fixed", "sl": 0.5, "tp": 1.0, "suffix": "1r"},
    {"name": "SL0_5_TP2", "kind": "fixed", "sl": 0.5, "tp": 2.0, "suffix": "2r"},
    {"name": "BE_AFTER_1R", "kind": "be", "tp": 1.0, "suffix": "1r"},
    {"name": "BE_AFTER_2R", "kind": "be", "tp": 2.0, "suffix": "2r"},
    {"name": "P50_AT_1R_REST_ORIGINAL", "kind": "partial", "tp": 1.0, "suffix": "1r", "fraction": 0.5},
    {"name": "P50_AT_2R_REST_ORIGINAL", "kind": "partial", "tp": 2.0, "suffix": "2r", "fraction": 0.5},
    {"name": "P50_AT_1R_BE_REST", "kind": "partial_be", "tp": 1.0, "suffix": "1r", "fraction": 0.5},
)

REQUIRED_BASE_FIELDS = {
    "symbol", "gross_r", "commission_r", "net_r", "net_r_commission_x1_5",
    "path_ambiguous", "mae_r", "reached_0_5r", "mae_before_0_5r",
    "reached_1r", "mae_before_1r", "reached_2r", "mae_before_2r",
    "reached_3r", "mae_before_3r", "min_r_after_first_1r_before_exit",
    "min_r_after_first_2r_before_exit",
}


class BenchmarkError(RuntimeError):
    pass


def _float(row: dict[str, str], field: str) -> float:
    raw = row.get(field, "")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise BenchmarkError(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value):
        raise BenchmarkError(f"non-finite {field}: {value}")
    return value


def _optional_float(row: dict[str, str], field: str) -> float | None:
    raw = row.get(field, "")
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise BenchmarkError(f"invalid {field}: {raw!r}") from exc
    if not math.isfinite(value):
        raise BenchmarkError(f"non-finite {field}: {value}")
    return value


def _flag(row: dict[str, str], field: str) -> bool:
    raw = str(row.get(field, ""))
    if raw not in {"0", "1"}:
        raise BenchmarkError(f"{field} must be 0/1, got {raw!r}")
    return raw == "1"


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _profit_factor(values: list[float]) -> dict[str, Any]:
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
        "profit_factor": _profit_factor(values),
        "win_rate": (sum(1 for x in values if x > 0) / len(values)) if values else None,
    }


def _is_ambiguous(row: dict[str, str]) -> bool:
    return _flag(row, "path_ambiguous")


def apply_rule(row: dict[str, str], rule: dict[str, Any]) -> tuple[float | None, str]:
    """Return alternate gross-R proxy and deterministic classification reason."""
    original = _float(row, "gross_r")
    if rule["kind"] == "baseline":
        return original, "ORIGINAL_EXIT"
    if _is_ambiguous(row):
        return None, "EXCLUDED_PATH_AMBIGUOUS"

    kind = rule["kind"]
    suffix = str(rule.get("suffix", ""))
    reached = _flag(row, f"reached_{suffix}") if suffix else False

    if kind == "fixed":
        sl = float(rule["sl"])
        tp = float(rule["tp"])
        if reached:
            mae_before = _float(row, f"mae_before_{suffix}")
            if mae_before >= sl:
                return -sl, "SL_BEFORE_TP_THRESHOLD_PROXY"
            return tp, "TP_THRESHOLD_PROXY"
        mae = _float(row, "mae_r")
        if mae >= sl:
            if sl == 1.0 and str(row.get("exit_reason", "")) == "STOP":
                return original, "ORIGINAL_1R_STOP_FILL"
            return -sl, "SL_THRESHOLD_PROXY"
        return original, "ORIGINAL_EXIT_NO_THRESHOLD"

    if kind == "be":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        low = _optional_float(row, f"min_r_after_first_{suffix}_before_exit")
        if low is None:
            return None, "EXCLUDED_MISSING_POST_TOUCH_PATH"
        if low <= 0.0:
            return 0.0, "BE_THRESHOLD_PROXY"
        return original, "ORIGINAL_EXIT_NO_BE_RECROSS"

    if kind == "partial":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        fraction = float(rule["fraction"])
        tp = float(rule["tp"])
        return fraction * tp + (1.0 - fraction) * original, "PARTIAL_THRESHOLD_PLUS_ORIGINAL_REMAINDER"

    if kind == "partial_be":
        if not reached:
            return original, "ORIGINAL_EXIT_NO_MILESTONE"
        fraction = float(rule["fraction"])
        tp = float(rule["tp"])
        low = _optional_float(row, f"min_r_after_first_{suffix}_before_exit")
        if low is None:
            return None, "EXCLUDED_MISSING_POST_TOUCH_PATH"
        remainder = 0.0 if low <= 0.0 else original
        return fraction * tp + (1.0 - fraction) * remainder, (
            "PARTIAL_PLUS_BE_THRESHOLD_PROXY" if low <= 0.0 else "PARTIAL_PLUS_ORIGINAL_REMAINDER"
        )

    raise BenchmarkError(f"unknown rule kind: {kind}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except OSError as exc:
        raise BenchmarkError(f"cannot read compact trades {path}: {exc}") from exc
    if not rows:
        raise BenchmarkError(f"compact trades is empty: {path}")
    missing = sorted(REQUIRED_BASE_FIELDS - set(rows[0]))
    if missing:
        raise BenchmarkError(f"compact trades missing V1 fields {missing}: {path}")
    return rows


def _latest_compact(workspace: Path, experiment_id: str, stage: str) -> Path:
    base = workspace / "rich_scores" / experiment_id / stage
    candidates = sorted(base.glob("*/trades_compact.csv"), reverse=True) if base.exists() else []
    if not candidates:
        raise BenchmarkError(f"no local rich-score compact trades for {experiment_id} {stage}: {base}")
    return candidates[0]


def _dataset(identifier: str, stage: str, workspace: Path) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    experiment_id = str(manifest["experiment_id"])
    compact = _latest_compact(workspace, experiment_id, stage)
    rows = _read_csv(compact)
    return {
        "identifier": identifier.upper(),
        "experiment_id": experiment_id,
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "stage": stage,
        "compact_path": str(compact),
        "compact_sha256": runner.sha256_file(compact),
        "rows": rows,
    }


def evaluate_dataset(ds: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, list[float]]]:
    rows: list[dict[str, str]] = ds["rows"]
    matrix: list[dict[str, Any]] = []
    deltas_by_rule: dict[str, list[float]] = {}

    for rule in RULES:
        alt_net: list[float] = []
        alt_gross: list[float] = []
        alt_stress: list[float] = []
        base_net_same: list[float] = []
        reasons: dict[str, int] = {}
        excluded = 0
        row_deltas: list[float] = []

        for row in rows:
            gross, reason = apply_rule(row, rule)
            reasons[reason] = reasons.get(reason, 0) + 1
            if gross is None:
                excluded += 1
                continue
            commission = _float(row, "commission_r")
            base_net = _float(row, "net_r")
            net_proxy = gross - commission
            stress_proxy = gross - 1.5 * commission
            alt_gross.append(gross)
            alt_net.append(net_proxy)
            alt_stress.append(stress_proxy)
            base_net_same.append(base_net)
            row_deltas.append(net_proxy - base_net)

        net_summary = _summary(alt_net)
        baseline_same = _summary(base_net_same)
        delta_mean = (_mean(row_deltas) if row_deltas else None)
        matrix.append({
            "dataset": ds["identifier"],
            "experiment_id": ds["experiment_id"],
            "stage": ds["stage"],
            "rule": rule["name"],
            "rule_kind": rule["kind"],
            "input_rows": len(rows),
            "eligible_rows": len(alt_net),
            "excluded_rows": excluded,
            "gross_r_proxy": _summary(alt_gross),
            "net_r_proxy": net_summary,
            "commission_stress_1_5x_r_proxy": _summary(alt_stress),
            "baseline_net_r_same_rows": baseline_same,
            "mean_net_delta_vs_baseline": delta_mean,
            "total_net_delta_vs_baseline": sum(row_deltas),
            "classification_counts": dict(sorted(reasons.items())),
            "confirmation_grade": False,
        })
        deltas_by_rule[rule["name"]] = row_deltas

    return matrix, deltas_by_rule


def cross_family(matrix: list[dict[str, Any]], deltas: dict[str, list[float]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in matrix:
        grouped.setdefault(str(row["rule"]), []).append(row)

    out: list[dict[str, Any]] = []
    for rule in RULES:
        name = rule["name"]
        if name == "BASELINE_ORIGINAL":
            continue
        family_rows = grouped.get(name, [])
        family_deltas = [float(x["mean_net_delta_vs_baseline"]) for x in family_rows if x["mean_net_delta_vs_baseline"] is not None]
        pooled = deltas.get(name, [])
        out.append({
            "rule": name,
            "families_evaluated": len(family_deltas),
            "families_improved": sum(1 for x in family_deltas if x > 0),
            "families_degraded": sum(1 for x in family_deltas if x < 0),
            "families_flat": sum(1 for x in family_deltas if x == 0),
            "equal_family_mean_delta_r": _mean(family_deltas),
            "median_family_delta_r": _median(family_deltas),
            "worst_family_delta_r": min(family_deltas) if family_deltas else None,
            "best_family_delta_r": max(family_deltas) if family_deltas else None,
            "pooled_trade_weighted_mean_delta_r": _mean(pooled),
            "pooled_total_delta_r": sum(pooled),
            "family_deltas": {
                str(x["dataset"]): x["mean_net_delta_vs_baseline"] for x in family_rows
            },
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

    ranked = sorted(out, key=key)
    for idx, item in enumerate(ranked, start=1):
        item["rank"] = idx
    return ranked


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
        "# Guardian Management Benchmark V1",
        "",
        "**Exploratory path replay only — not confirmation-grade and never a parent-strategy rescue.**",
        "",
        f"Datasets: {', '.join(x['identifier'] for x in payload['datasets'])}",
        f"Stage: {payload['stage']}",
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
        "Alternate fills use R-threshold and original-roundturn-commission proxies. A top-ranked rule is only a candidate for a separately frozen exact Exit Lab on fresh evidence.",
        "",
    ]
    return "\n".join(lines)


def _fingerprint(payload: dict[str, Any]) -> str:
    stable = {
        "schema_version": payload["schema_version"],
        "benchmark_id": payload["benchmark_id"],
        "stage": payload["stage"],
        "datasets": [{k: x[k] for k in ("identifier", "experiment_id", "compact_sha256")} for x in payload["datasets"]],
        "rules": payload["rules"],
        "matrix": payload["matrix"],
        "cross_family_ranking": payload["cross_family_ranking"],
    }
    raw = json.dumps(stable, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def publish(output_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    remote = publisher._run_git(["-C", str(runner.ROOT), "remote", "get-url", "origin"])
    event_id = output_dir.name
    clone_dir = workspace / "result_transport" / f"{event_id}_management_v1"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)
    target_rel = Path("benchmarks") / "management-v1" / "live" / "events" / event_id
    latest_rel = Path("benchmarks") / "management-v1" / "live" / "latest.json"
    try:
        publisher._run_git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", publisher.RESULT_BRANCH, remote, str(clone_dir)], timeout=300)
        target = clone_dir / target_rel
        if target.exists():
            existing = json.loads((target / "event.json").read_text(encoding="utf-8"))
            if existing.get("fingerprint_sha256") != payload["fingerprint_sha256"]:
                raise BenchmarkError(f"management benchmark event collision: {target_rel.as_posix()}")
            status = "BENCHMARK_PUBLISH_NOOP_ALREADY_PRESENT"
        else:
            target.mkdir(parents=True, exist_ok=False)
            for name in ("benchmark.json", "rule_matrix.csv", "SUMMARY.md"):
                shutil.copy2(output_dir / name, target / name)
            event = {
                "schema_version": 1,
                "benchmark_id": BENCHMARK_ID,
                "event_id": event_id,
                "status": "MANAGEMENT_BENCHMARK_V1_COMPLETE",
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
            "status": "MANAGEMENT_BENCHMARK_V1_COMPLETE",
            "fingerprint_sha256": payload["fingerprint_sha256"],
            "autosync_used": False,
        }
        latest_path = clone_dir / latest_rel
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        publisher._run_git(["add", "--", target_rel.as_posix(), latest_rel.as_posix()], cwd=clone_dir)
        changes = publisher._run_git(["status", "--porcelain"], cwd=clone_dir)
        if changes:
            publisher._run_git(["-c", "user.name=Guardian Research Runner", "-c", "user.email=guardian-runner@local", "commit", "-m", f"Record Management Benchmark V1 {event_id}"], cwd=clone_dir)
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
    datasets = [_dataset(identifier, stage, workspace) for identifier in dataset_ids]
    full_matrix: list[dict[str, Any]] = []
    pooled_deltas: dict[str, list[float]] = {r["name"]: [] for r in RULES}
    for ds in datasets:
        matrix, deltas = evaluate_dataset(ds)
        full_matrix.extend(matrix)
        for name, values in deltas.items():
            pooled_deltas[name].extend(values)
    ranking = cross_family(full_matrix, pooled_deltas)
    created = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": BENCHMARK_ID,
        "created_at_utc": created.isoformat(),
        "preregistration": PREREG,
        "stage": stage,
        "scientific_role": "EXPLORATORY_CROSS_FAMILY_MANAGEMENT_PATH_REPLAY_NOT_CONFIRMATION_GRADE",
        "datasets": [
            {k: ds[k] for k in ("identifier", "experiment_id", "manifest_path", "stage", "compact_path", "compact_sha256")}
            | {"rows": len(ds["rows"])}
            for ds in datasets
        ],
        "rules": list(RULES),
        "matrix": full_matrix,
        "cross_family_ranking": ranking,
        "limitations": {
            "threshold_fill_proxy": True,
            "original_roundturn_commission_r_reused": True,
            "continuous_trailing_supported": False,
            "time_exit_supported": False,
            "wider_than_original_stop_supported": False,
            "parent_verdicts_changed": False,
            "confirmation_grade": False,
        },
        "autosync_used": False,
    }
    payload["fingerprint_sha256"] = _fingerprint(payload)
    out_dir = workspace / "management_benchmarks" / "v1" / created.strftime("%Y%m%dT%H%M%SZ")
    out_dir.mkdir(parents=True, exist_ok=False)
    benchmark_path = out_dir / "benchmark.json"
    matrix_path = out_dir / "rule_matrix.csv"
    summary_path = out_dir / "SUMMARY.md"
    benchmark_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    _write_matrix(matrix_path, full_matrix)
    summary_path.write_text(_summary_md(payload), encoding="utf-8", newline="\n")
    result = {
        "status": "MANAGEMENT_BENCHMARK_V1_COMPLETE",
        "benchmark_path": str(benchmark_path),
        "matrix_path": str(matrix_path),
        "summary_path": str(summary_path),
        "fingerprint_sha256": payload["fingerprint_sha256"],
        "top_rules": ranking[:5],
        "autosync_used": False,
    }
    if do_publish:
        result["github_transport"] = publish(out_dir, payload)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Guardian Management Benchmark V1 without MT5")
    sub = ap.add_subparsers(dest="command", required=True)
    runp = sub.add_parser("run")
    runp.add_argument("--datasets", nargs="+", default=list(DEFAULT_DATASETS))
    runp.add_argument("--stage", default=DEFAULT_STAGE)
    runp.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()
    try:
        if args.command == "run":
            result = run_benchmark(tuple(args.datasets), args.stage, not args.no_publish)
        else:
            raise BenchmarkError(f"unsupported command {args.command}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
