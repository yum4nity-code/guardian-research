#!/usr/bin/env python3
"""Publish compact validated Guardian research bundles to backtest-results.

Publishing is intentionally isolated from the user's working tree. A temporary
single-branch clone is created under the runner workspace, populated, committed,
and pushed. Legacy AutoSync is never invoked.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import experiment
import runner


class PublishError(RuntimeError):
    pass


RESULT_BRANCH = "backtest-results"
MAX_COMPACT_CSV_BYTES = 5 * 1024 * 1024


def _run_git(args: list[str], cwd: Path | None = None, timeout: int = 180) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PublishError(f"git command could not run: git {' '.join(args)}: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise PublishError(f"git command failed rc={proc.returncode}: git {' '.join(args)} | {detail}")
    return proc.stdout.strip()


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishError(f"cannot read {label} {path}: {exc}") from exc


def _latest_file(base: Path, filename: str) -> Path:
    candidates = sorted(base.glob(f"*/{filename}"), reverse=True) if base.exists() else []
    if not candidates:
        raise PublishError(f"no {filename} found under {base}")
    return candidates[0]


def latest_decision_score(config: dict[str, Any], experiment_id: str, stage: str) -> Path:
    base = runner._expand_path(config["workspace_dir"]) / "scores" / experiment_id / stage
    return _latest_file(base, "verdict.json")


def latest_rich_score(config: dict[str, Any], experiment_id: str, stage: str) -> Path:
    base = runner._expand_path(config["workspace_dir"]) / "rich_scores" / experiment_id / stage
    return _latest_file(base, "rich_score.json")


def _safe_short_id(experiment_id: str) -> str:
    short = experiment_id.split("-", 1)[0].lower()
    cleaned = "".join(ch for ch in short if ch.isalnum() or ch in ("_", "-"))
    if not cleaned:
        raise PublishError(f"cannot derive safe experiment short id from {experiment_id!r}")
    return cleaned


def _summary_markdown(decision: dict[str, Any], rich: dict[str, Any]) -> str:
    metrics = decision.get("metrics", {})
    gates = decision.get("gates", {})
    analytics = rich.get("analytics", {})
    net = analytics.get("net_r", {})
    net_dist = net.get("distribution", {})
    equity = analytics.get("chronological_equity_r", {})
    duration = analytics.get("duration_minutes", {})
    failed = [name for name, passed in gates.items() if not passed]

    lines = [
        f"# {decision['experiment_id']} — {decision['stage']}",
        "",
        f"- Decision verdict: **{decision['verdict']}**",
        f"- Frozen gates passed: **{decision.get('all_gates_pass')}**",
        f"- Trades: **{metrics.get('aggregate_n')}**",
        f"- Mean net R: **{metrics.get('aggregate_mean_net_r')}**",
        f"- Profit Factor: **{metrics.get('aggregate_pf')}**",
        f"- Total net R: **{metrics.get('aggregate_total_net_r')}**",
        f"- Stress commission x1.5 total R: **{metrics.get('aggregate_total_stress_net_r')}**",
        f"- Positive symbols: **{metrics.get('positive_symbols_n')}** — {', '.join(metrics.get('positive_symbols', []))}",
        f"- Failed frozen gates: **{', '.join(failed) if failed else 'none'}**",
        "",
        "## Rich descriptive analytics",
        "",
        f"- Net-R median: {net_dist.get('median')}",
        f"- Net-R p10 / p90: {net_dist.get('p10')} / {net_dist.get('p90')}",
        f"- Win rate: {net.get('win_rate')}",
        f"- Average win / loss R: {net.get('average_win_r')} / {net.get('average_loss_r')}",
        f"- Payoff ratio: {net.get('payoff_ratio_avg_win_to_abs_avg_loss')}",
        f"- Chronological max drawdown: {equity.get('max_drawdown_r')} R",
        f"- Longest winning / losing streak: {equity.get('longest_winning_streak')} / {equity.get('longest_losing_streak')}",
        f"- Median trade duration: {duration.get('median')} minutes",
        "",
        "## Scientific boundary",
        "",
        "The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.",
        "D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.",
        "",
    ]
    return "\n".join(lines)


def build_bundle(identifier: str, stage: str, decision_path: str | None = None, rich_path: str | None = None) -> dict[str, Any]:
    _, manifest_path, manifest = runner.load_context(identifier)
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])

    decision_file = Path(decision_path).resolve() if decision_path else latest_decision_score(config, manifest["experiment_id"], stage)
    rich_file = Path(rich_path).resolve() if rich_path else latest_rich_score(config, manifest["experiment_id"], stage)
    decision = _read_json(decision_file, "decision score")
    rich = _read_json(rich_file, "rich score")

    for payload, label in ((decision, "decision score"), (rich, "rich score")):
        if payload.get("experiment_id") != manifest["experiment_id"] or payload.get("stage") != stage:
            raise PublishError(f"{label} does not match experiment/stage")
        if payload.get("manifest_source_sha256") != manifest["source"]["source_sha256"]:
            raise PublishError(f"{label} source SHA does not match active manifest")

    compact = rich.get("compact_trades", {})
    compact_path = Path(compact.get("path", ""))
    if not compact_path.is_file():
        raise PublishError(f"rich compact trades file missing: {compact_path}")
    if runner.sha256_file(compact_path) != compact.get("sha256"):
        raise PublishError("rich compact trades SHA mismatch")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = workspace / "publish_bundles" / manifest["experiment_id"] / stage / stamp
    bundle_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(decision_file, bundle_dir / "decision_score.json")
    shutil.copy2(rich_file, bundle_dir / "rich_score.json")
    compact_published = False
    if compact_path.stat().st_size <= MAX_COMPACT_CSV_BYTES:
        shutil.copy2(compact_path, bundle_dir / "trades_compact.csv")
        compact_published = True

    source_path = runner.ROOT / manifest["source"]["canonical_path"]
    evidence = rich.get("evidence", [])
    provenance = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "decision_verdict": decision.get("verdict"),
        "decision_all_gates_pass": decision.get("all_gates_pass"),
        "manifest_path": str(manifest_path.relative_to(runner.ROOT)),
        "source": {
            "path": manifest["source"]["canonical_path"],
            "version": manifest["source"].get("version"),
            "identity_sha256_mode": manifest["source"].get("source_sha256_mode"),
            "identity_sha256": manifest["source"]["source_sha256"],
            "raw_bytes_sha256": runner.sha256_file(source_path),
            "bytes": source_path.stat().st_size,
        },
        "batch_path_local": decision.get("batch_path"),
        "evidence": evidence,
        "published_files": {
            "decision_score.json": {"sha256": runner.sha256_file(bundle_dir / "decision_score.json")},
            "rich_score.json": {"sha256": runner.sha256_file(bundle_dir / "rich_score.json")},
            "trades_compact.csv": {
                "included": compact_published,
                "sha256": compact.get("sha256"),
                "bytes": compact.get("bytes"),
                "rows": compact.get("rows"),
                "size_limit_bytes": MAX_COMPACT_CSV_BYTES,
            },
        },
        "raw_policy": "Large/raw MT5 evidence remains on the research PC; GitHub stores compact derivatives plus SHA256/byte provenance.",
        "transport": "ISOLATED_GIT_CLONE_PUBLISHER",
        "autosync_used": False,
    }
    runner.write_receipt(bundle_dir / "manifest.json", provenance)
    (bundle_dir / "SUMMARY.md").write_text(_summary_markdown(decision, rich), encoding="utf-8", newline="\n")

    return {
        "bundle_dir": str(bundle_dir),
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "decision_verdict": decision.get("verdict"),
        "compact_trades_included": compact_published,
        "stamp": stamp,
    }


def publish_bundle(identifier: str, stage: str, decision_path: str | None = None, rich_path: str | None = None) -> dict[str, Any]:
    _, _, manifest = runner.load_context(identifier)
    config = runner.load_config()
    workspace = runner._expand_path(config["workspace_dir"])
    bundle = build_bundle(identifier, stage, decision_path, rich_path)
    bundle_dir = Path(bundle["bundle_dir"])

    remote = _run_git(["-C", str(runner.ROOT), "remote", "get-url", "origin"])
    if not remote:
        raise PublishError("origin remote URL is empty")

    short_id = _safe_short_id(manifest["experiment_id"])
    publish_root = workspace / "publisher"
    publish_root.mkdir(parents=True, exist_ok=True)
    clone_dir = publish_root / f"{bundle['stamp']}_{short_id}"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    try:
        _run_git(["clone", "--quiet", "--depth", "1", "--single-branch", "--branch", RESULT_BRANCH, remote, str(clone_dir)], timeout=300)
        target_rel = Path("backtests") / short_id / bundle["stamp"]
        target = clone_dir / target_rel
        if target.exists():
            raise PublishError(f"publish target already exists: {target_rel.as_posix()}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(bundle_dir, target)

        _run_git(["add", "--", target_rel.as_posix()], cwd=clone_dir)
        message = f"Publish {short_id.upper()} {stage} {bundle['decision_verdict']} {bundle['stamp']}"
        _run_git([
            "-c", "user.name=Guardian Research Runner",
            "-c", "user.email=guardian-runner@local",
            "commit", "-m", message,
        ], cwd=clone_dir)
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=clone_dir)
        _run_git(["push", "origin", f"HEAD:{RESULT_BRANCH}"], cwd=clone_dir, timeout=300)
    finally:
        if clone_dir.exists():
            shutil.rmtree(clone_dir, ignore_errors=True)

    receipt = {
        "schema_version": 1,
        "status": "PUBLISH_PASS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": manifest["experiment_id"],
        "stage": stage,
        "branch": RESULT_BRANCH,
        "target_path": (Path("backtests") / short_id / bundle["stamp"]).as_posix(),
        "commit_sha": commit_sha,
        "bundle_dir": str(bundle_dir),
        "decision_verdict": bundle["decision_verdict"],
        "compact_trades_included": bundle["compact_trades_included"],
        "transport": "ISOLATED_GIT_CLONE_PUBLISHER",
        "autosync_used": False,
    }
    receipt_path = workspace / "publish_receipts" / manifest["experiment_id"] / stage / f"{bundle['stamp']}.json"
    runner.write_receipt(receipt_path, receipt)
    return {"publish_receipt": str(receipt_path), **receipt}


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish a compact Guardian research bundle to backtest-results")
    parser.add_argument("experiment")
    parser.add_argument("--stage", default="development", choices=("development",))
    parser.add_argument("--decision")
    parser.add_argument("--rich")
    args = parser.parse_args()
    try:
        result = publish_bundle(args.experiment, args.stage, args.decision, args.rich)
    except (PublishError, runner.RunnerError, experiment.ManifestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
