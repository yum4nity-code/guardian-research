# Guardian Core v12.01 — compile validation handoff

STATUT: BASELINE_VALIDEE_COMPILATION

The user compiled `Guardian_Core_Base_v12_01_COMPILEFIX_20260906.mq5` in MetaEditor and reported **0 errors / 0 warnings**.

Authoritative production note: `production/guardian/GUARDIAN_CORE_V12_01_COMPILE_VALIDATED_2026_09_06.md`.

Core SHA256: `c15c2f04da78f9a4841cc461224bd62db35a110e1c2ff3ed15c6a0fd9c27e826`.

Validated layout keeps `Guardian_StrategyRegistry_v1_EMPTY_20260906.mqh` beside the MQ5; do not relocate/reformat before committing the exact source snapshot. Pure-core invariant remains: no RSI, no Momentum, empty strategy registry.

When credits/work resume, recover the exact local/archived snapshot and commit the source files themselves under the stable production Core path while preserving the recorded hashes.
