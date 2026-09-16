#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("orch_g82", HERE / "guardian_research_orchestrator_v1_00.py")
orch = importlib.util.module_from_spec(SPEC)
sys.modules["orch_g82"] = orch
SPEC.loader.exec_module(orch)


def main() -> int:
    queue = orch.load_queue(REPO)
    orch.validate_queue(queue)
    assert queue["generation"] == 82
    assert queue.get("human_approved_2026") is False
    enabled = [j for j in queue.get("jobs", []) if j.get("enabled")]
    assert enabled == []
    assert len(queue.get("jobs", [])) == 4
    assert all(j["id"].startswith("R21-R25-") for j in queue["jobs"])
    for job in queue["jobs"]:
        window = job.get("data_window")
        if window:
            assert "end_exclusive" in window
            assert "end_inclusive" not in window
            assert window["end_exclusive"] == "2019-07-01T00:00:00Z"
    print("PASS: effective generation 82 queue is globally fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
