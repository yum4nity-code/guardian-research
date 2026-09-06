#!/usr/bin/env python3
"""Guardian project-state validation and compatibility-file generation.

This module deliberately uses only the Python standard library so it can run on a
plain Windows research machine and in lightweight CI.

GUARDIAN_STATE.json is authoritative. START_HERE_NEXT_AI.md and
CURRENT_QUEUE.json are compatibility views generated from it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "GUARDIAN_STATE.json"
START_PATH = ROOT / "START_HERE_NEXT_AI.md"
QUEUE_PATH = ROOT / "CURRENT_QUEUE.json"


class StateError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"missing required file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc


def _repo_path(relative: str | None, label: str) -> Path:
    if not relative:
        raise StateError(f"missing path in state: {label}")
    path = ROOT / relative
    if not path.exists():
        raise StateError(f"state points to missing {label}: {relative}")
    return path


def load_state() -> dict[str, Any]:
    return _read_json(STATE_PATH)


def load_active_manifest(state: dict[str, Any]) -> dict[str, Any]:
    manifest_path = _repo_path(state["research"].get("experiment_manifest"), "active experiment manifest")
    return _read_json(manifest_path)


def validate_state(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(state.get("authoritative") is True, "GUARDIAN_STATE.json must declare authoritative=true")
    require(state.get("schema_version") == 1, "unsupported GUARDIAN_STATE schema_version")

    migration = state.get("migration", {})
    require(migration.get("codex_required") is False, "active workflow must not require Codex")

    production = state.get("production", {}).get("guardian_core", {})
    require(production.get("change_during_research_refactor") is False,
            "Guardian Core must remain frozen during the research refactor")

    transport = state.get("transport", {})
    require(transport.get("legacy_runtime_status") == "UNTRUSTED_NEVER_RELIABLY_WORKED",
            "legacy AutoSync must remain explicitly untrusted")
    require(transport.get("legacy_scripts_role") == "REFERENCE_ONLY_NOT_FALLBACK",
            "legacy AutoSync scripts must never be an operational fallback")

    maman = state.get("non_guardian_projects", {}).get("maman_70_santorin", {})
    require(maman.get("preserve") is True, "maman-70-santorin must remain explicitly preserved")
    maman_path = maman.get("current_path")
    if maman_path:
        require((ROOT / maman_path).exists(), f"preserved maman project path is missing: {maman_path}")
    else:
        errors.append("maman-70-santorin current_path is missing")

    research = state.get("research", {})
    manifest_rel = research.get("experiment_manifest")
    if manifest_rel:
        manifest_path = ROOT / manifest_rel
        require(manifest_path.exists(), f"active experiment manifest is missing: {manifest_rel}")
        if manifest_path.exists():
            try:
                manifest = _read_json(manifest_path)
                require(manifest.get("experiment_id") == research.get("active_experiment"),
                        "active_experiment disagrees with experiment manifest experiment_id")
                prereg_path = manifest.get("preregistration", {}).get("path")
                if prereg_path:
                    require((ROOT / prereg_path).exists(), f"preregistration is missing: {prereg_path}")
                canonical = manifest.get("source", {}).get("canonical_path")
                complete = manifest.get("source", {}).get("complete_repository_source")
                if complete:
                    require(bool(canonical), "complete_repository_source=true but canonical_path is empty")
                    if canonical:
                        require((ROOT / canonical).exists(), f"canonical source is missing: {canonical}")
            except StateError as exc:
                errors.append(str(exc))
    else:
        errors.append("research.experiment_manifest is missing")

    return errors


def render_start_here(state: dict[str, Any], manifest: dict[str, Any]) -> str:
    research = state["research"]
    production = state["production"]["guardian_core"]
    transport = state["transport"]
    closed = research.get("closed_experiments", {})
    closed_text = ", ".join(f"{key}={value}" for key, value in sorted(closed.items())) or "none"

    return f"""# START HERE — GUARDIAN\n\n> **GENERATED COMPATIBILITY ENTRYPOINT. DO NOT EDIT BY HAND.**\n> Authoritative state: `GUARDIAN_STATE.json`.\n\nRead only what is needed, in this order:\n\n1. `GUARDIAN_STATE.json`\n2. `GUARDIAN_MASTER_MANDATE.md`\n3. `{research['experiment_manifest']}`\n4. `{manifest['preregistration']['path']}`\n5. `{production['reference_note']}`\n\n## Current P0\n\n- Experiment: **{research['active_experiment']}**\n- State: **{research['status']}**\n- Next action: **{research['next_action']}**\n\n## Operational truths\n\n- Codex required: **NO**\n- Guardian Core baseline: **{production['baseline']}** — do not modify during this research refactor.\n- Legacy AutoSync: **{transport['legacy_runtime_status']}** — reference only, never fallback.\n- AutoSync target: **{transport['target']}**.\n- Closed experiments: {closed_text}.\n\nIf this file ever disagrees with `GUARDIAN_STATE.json`, the state file wins and this file must be regenerated with:\n\n```powershell\npython research/runner/state_tools.py generate\n```\n"""


def build_queue(state: dict[str, Any]) -> dict[str, Any]:
    research = state["research"]
    runner = state["runner"]
    transport = state["transport"]

    items: list[dict[str, Any]] = [
        {
            "id": research["active_experiment"],
            "priority": 0,
            "status": research["status"],
            "owner": "DETERMINISTIC_RUNNER+USER",
            "type": "active_research_experiment",
            "goal": research["next_action"],
            "manifest": research["experiment_manifest"],
        },
        {
            "id": runner["target"],
            "priority": 1,
            "status": runner["status"],
            "owner": "DETERMINISTIC_LOCAL_TOOLING",
            "type": "research_orchestration",
            "goal": runner["principle"],
        },
        {
            "id": transport["target"],
            "priority": 5,
            "status": "DEFERRED_UNTIL_RUNNER_CORE_WORKS",
            "owner": "DETERMINISTIC_LOCAL_TOOLING",
            "type": "result_transport",
            "goal": "Build from scratch; legacy AutoSync is reference-only and never a fallback.",
        },
    ]

    for experiment_id, verdict in sorted(research.get("closed_experiments", {}).items()):
        items.append({
            "id": experiment_id,
            "priority": 99,
            "status": "CLOSED",
            "owner": "HISTORICAL",
            "type": "closed_research",
            "goal": verdict,
        })

    return {
        "schema_version": 2,
        "generated": True,
        "generated_from": "GUARDIAN_STATE.json",
        "updated_at": state["updated_at"],
        "active_primary": research["active_experiment"],
        "items": items,
        "notes": "Compatibility view only. GUARDIAN_STATE.json is authoritative. No operational item may wait on Codex.",
    }


def render_queue(state: dict[str, Any]) -> str:
    return json.dumps(build_queue(state), indent=2, ensure_ascii=False) + "\n"


def expected_outputs(state: dict[str, Any]) -> tuple[str, str]:
    manifest = load_active_manifest(state)
    return render_start_here(state, manifest), render_queue(state)


def check_generated(state: dict[str, Any]) -> list[str]:
    expected_start, expected_queue = expected_outputs(state)
    errors: list[str] = []
    if not START_PATH.exists() or START_PATH.read_text(encoding="utf-8") != expected_start:
        errors.append("START_HERE_NEXT_AI.md is stale; run state_tools.py generate")
    if not QUEUE_PATH.exists() or QUEUE_PATH.read_text(encoding="utf-8") != expected_queue:
        errors.append("CURRENT_QUEUE.json is stale; run state_tools.py generate")
    return errors


def cmd_validate(check_views: bool) -> int:
    state = load_state()
    errors = validate_state(state)
    if check_views:
        errors.extend(check_generated(state))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("GUARDIAN_STATE_OK")
    return 0


def cmd_generate() -> int:
    state = load_state()
    errors = validate_state(state)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    start_text, queue_text = expected_outputs(state)
    START_PATH.write_text(start_text, encoding="utf-8", newline="\n")
    QUEUE_PATH.write_text(queue_text, encoding="utf-8", newline="\n")
    print("GENERATED START_HERE_NEXT_AI.md CURRENT_QUEUE.json")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Guardian authoritative state utilities")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate state and generated compatibility views")
    validate.add_argument("--state-only", action="store_true", help="skip generated-view freshness checks")
    sub.add_parser("generate", help="regenerate compatibility views from GUARDIAN_STATE.json")
    args = parser.parse_args()

    try:
        if args.command == "generate":
            return cmd_generate()
        return cmd_validate(check_views=not args.state_only)
    except (StateError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
