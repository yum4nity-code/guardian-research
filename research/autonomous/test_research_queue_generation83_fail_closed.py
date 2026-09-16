#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location("orch_g83", HERE / "guardian_research_orchestrator_v1_00.py")
orch = importlib.util.module_from_spec(SPEC)
sys.modules["orch_g83"] = orch
SPEC.loader.exec_module(orch)


def main() -> int:
    queue = orch.load_queue(REPO)
    orch.validate_queue(queue)
    assert queue["generation"] == 83
    assert queue.get("human_approved_2026") is False
    jobs = queue.get("jobs", [])
    assert len(jobs) == 3
    assert [j for j in jobs if j.get("enabled")] == []
    assert all(j["id"].startswith("R21-R25-") for j in jobs)
    discovery = next(j for j in jobs if j["id"] == "R21-R25-XAU-DISCOVERY")
    assert discovery["executor"]["path"].endswith("xau_edge_discovery_r21_r25_v1_02.py")
    assert "--input" not in discovery["executor"]["args"]
    assert "--index" in discovery["executor"]["args"]
    window = discovery["data_window"]
    assert window["end_exclusive"] == "2019-07-01T00:00:00Z"
    assert "end_inclusive" not in window
    print("PASS: effective generation 83 queue is globally fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
