#!/usr/bin/env python3
"""Single entrypoint for the deterministic Guardian research pipeline."""

from __future__ import annotations

import argparse
import json
import sys

import batch
import diagnostics
import experiment
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
        print(json.dumps(pipeline_run(args.experiment), indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (runner.RunnerError, tester.TestError, diagnostics.DiagnosticError, score.ScoreError, experiment.ManifestError, KeyError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
