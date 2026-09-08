# Guardian Autonomous Research

This directory contains the unattended research control plane.

- `AUTONOMOUS_RESEARCH_MANDATE.md` — scientific and governance rules.
- `RESEARCH_QUEUE.json` — GitHub-authored execution queue.
- `guardian_research_orchestrator_v1_00.py` — local polling/execution/watchdog daemon.
- `test_guardian_research_orchestrator_v1_00.py` — isolated unit tests.

The local orchestrator uses a dedicated disposable deploy clone at `D:\MT5_Backtests\guardian-autonomous-main` and durable state at `D:\MT5_Backtests\Research\Autonomous`.

Long jobs should expose a heartbeat/progress JSON and use the adaptive timeout policy from the mandate. The executor records immutable `(job id, revision)` receipts, so a successful or failed job is not silently rerun after restart.

2026 is fail-closed unless `human_approved_2026` is explicitly changed after owner approval.
