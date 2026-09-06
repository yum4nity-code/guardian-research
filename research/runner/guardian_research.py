#!/usr/bin/env python3
"""Single entrypoint for the deterministic Guardian research pipeline."""

from __future__ import annotations

import argparse
import json
import sys

import batch
import diagnostics
import experiment
import publisher
import rich_score
import runner
import score
import tester


def pipeline_run(identifier: str) -> dict:
    # Compile always runs first. This deliberately creates a fresh trusted EX5
    # receipt instead of reusing an old binary merely because one exists.
    compile_rc = runner.cmd_compile(identifier)
    if compile_rc != 0:
        raise runner.RunnerError("compile stage failed")

    _, _, manifest = runner.load_context(identifier)
    stage = manifest["runner_contract"]["default_stage"]
    batch_result = batch.run_batch(identifier, stage)
    if stage != "development":
        return {
            "status": "BATCH_COMPLETE_SCORER_NOT_IMPLEMENTED_FOR_STAGE",
            "stage": stage,
            "batch": batch_result,
        }
    verdict = score.score(identifier, stage, batch_result["batch_path"])
    return {
        "status": "PIPELINE_COMPLETE",
        "stage": stage,
        "batch_path": batch_result["batch_path"],
        "verdict_path": verdict["verdict_path"],
        "verdict": verdict["verdict"],
        "all_gates_pass": verdict["all_gates_pass"],
    }


def finalize_existing(identifier: str, stage: str, batch_path: str | None = None) -> dict:
    """Finalize an already-completed batch without launching MT5.

    Frozen decision scoring remains authoritative. Rich analytics are generated
    separately, then a compact provenance bundle is published to
    backtest-results through an isolated temporary clone.
    """
    decision = score.score(identifier, stage, batch_path)
    rich = rich_score.rich_score(identifier, stage, decision["batch_path"])
    published = publisher.publish_bundle(
        identifier,
        stage,
        decision_path=decision["verdict_path"],
        rich_path=rich["rich_score_path"],
    )
    return {
        "status": "FINALIZE_PASS",
        "stage": stage,
        "decision_verdict": decision["verdict"],
        "all_gates_pass": decision["all_gates_pass"],
        "decision_score_path": decision["verdict_path"],
        "rich_score_path": rich["rich_score_path"],
        "publish_receipt": published["publish_receipt"],
        "published_branch": published["branch"],
        "published_path": published["target_path"],
        "published_commit_sha": published["commit_sha"],
        "autosync_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardian Research Runner")
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("doctor", "plan", "compile", "run"):
        p = sub.add_parser(command)
        p.add_argument("experiment")

    one = sub.add_parser("test-one")
    one.add_argument("experiment")
    one.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))
    one.add_argument("--symbol", required=True)

    recover = sub.add_parser("recover-one")
    recover.add_argument("experiment")
    recover.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))
    recover.add_argument("--symbol", required=True)

    diagnose = sub.add_parser("diagnose-invalid")
    diagnose.add_argument("experiment")
    diagnose.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))

    b = sub.add_parser("batch")
    b.add_argument("experiment")
    b.add_argument("--stage", default="development", choices=("smoke", "development", "confirmation"))

    s = sub.add_parser("score")
    s.add_argument("experiment")
    s.add_argument("--stage", default="development", choices=("development",))
    s.add_argument("--batch")

    rs = sub.add_parser("rich-score")
    rs.add_argument("experiment")
    rs.add_argument("--stage", default="development", choices=("development",))
    rs.add_argument("--batch")

    pub = sub.add_parser("publish")
    pub.add_argument("experiment")
    pub.add_argument("--stage", default="development", choices=("development",))
    pub.add_argument("--decision")
    pub.add_argument("--rich")

    final = sub.add_parser("finalize")
    final.add_argument("experiment")
    final.add_argument("--stage", default="development", choices=("development",))
    final.add_argument("--batch")

    args = parser.parse_args()

    try:
        if args.command == "doctor":
            return runner.cmd_doctor(args.experiment)
        if args.command == "plan":
            print(json.dumps(runner.plan(args.experiment), indent=2, ensure_ascii=False))
            return 0
        if args.command == "compile":
            return runner.cmd_compile(args.experiment)
        if args.command == "test-one":
            print(json.dumps(tester.run_one(args.experiment, args.stage, args.symbol), indent=2, ensure_ascii=False))
            return 0
        if args.command == "recover-one":
            print(json.dumps(tester.recover_latest(args.experiment, args.stage, args.symbol), indent=2, ensure_ascii=False))
            return 0
        if args.command == "diagnose-invalid":
            print(json.dumps(diagnostics.diagnose_latest_invalid(args.experiment, args.stage), indent=2, ensure_ascii=False))
            return 0
        if args.command == "batch":
            print(json.dumps(batch.run_batch(args.experiment, args.stage), indent=2, ensure_ascii=False))
            return 0
        if args.command == "score":
            print(json.dumps(score.score(args.experiment, args.stage, args.batch), indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        if args.command == "rich-score":
            print(json.dumps(rich_score.rich_score(args.experiment, args.stage, args.batch), indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        if args.command == "publish":
            print(json.dumps(publisher.publish_bundle(args.experiment, args.stage, args.decision, args.rich), indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        if args.command == "finalize":
            print(json.dumps(finalize_existing(args.experiment, args.stage, args.batch), indent=2, ensure_ascii=False, allow_nan=False))
            return 0
        print(json.dumps(pipeline_run(args.experiment), indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (
        runner.RunnerError,
        tester.TestError,
        diagnostics.DiagnosticError,
        score.ScoreError,
        rich_score.RichScoreError,
        publisher.PublishError,
        experiment.ManifestError,
        KeyError,
        OSError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
