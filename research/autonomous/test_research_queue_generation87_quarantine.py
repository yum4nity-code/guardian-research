#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location(
    "orch_g87", HERE / "guardian_research_orchestrator_v1_00.py"
)
orch = importlib.util.module_from_spec(SPEC)
sys.modules["orch_g87"] = orch
SPEC.loader.exec_module(orch)


def main() -> int:
    queue = orch.load_queue(REPO)
    orch.validate_queue(queue)
    assert queue["generation"] == 87
    assert queue.get("human_approved_2026") is False
    jobs = queue.get("jobs", [])
    assert len(jobs) == 3
    assert [job for job in jobs if job.get("enabled")] == []
    assert all(job["id"].startswith("R21-R25-") for job in jobs)
    assert all(job["revision"] == 4 for job in jobs)
    discovery = next(job for job in jobs if job["id"] == "R21-R25-XAU-DISCOVERY")
    assert discovery["enabled"] is False
    assert discovery["data_window"]["end_exclusive"] == "2019-07-01T00:00:00Z"
    assert queue.get("human_approved_2026") is False
    print("PASS: generation 87 quarantine is globally fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
