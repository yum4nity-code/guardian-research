# Guardian EIB V1 — MT5 Multi-Consumer Gate PASS — 2026-09-04

Status: **PASS**

## Purpose
Validate that two genuinely distinct MetaTrader 5 terminals consume the same `FILE_COMMON` Guardian Shared Intelligence stream at the same time.

The verifier was hardened to reject stale probe files. V1.1 observes active writers for 6 seconds and requires distinct live terminals, distinct servers, distinct data paths, and multiple common `generation_id` values.

## Observed live evidence

```text
probe_dir=C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files\GuardianSharedIntelligence\probes
[VERIFY] observing active writers for 6s...
[VERIFY][PROBE] probe_T19F0275C_v102.csv terminal_id=T19F0275C server=FundedNext-Server 2 rows=91 latest_gen=1788513680659
[VERIFY][PROBE] probe_T68A8692D_v102.csv terminal_id=T68A8692D server=FTMO-Demo rows=137 latest_gen=1788513680659
[VERIFY][OK] pair=probe_T19F0275C_v102.csv / probe_T68A8692D_v102.csv servers=FundedNext-Server 2 / FTMO-Demo
[VERIFY][OK] distinct_active_terminals=2 common_generations=91
[VERIFY][OK] latest_common_generation=1788513680659
[Guardian] FULL GATE MT5 MULTI-CONSUMER V1.1: PASS.
```

## Conclusion
Confirmed in live use:

- FundedNext and FTMO are two distinct active MT5 consumers.
- Both read the same Guardian Shared Intelligence stream via MT5 `FILE_COMMON`.
- Both observed **91 common generations** during the verification window.
- Their latest observed generation matched exactly: `1788513680659`.
- The previous false-positive risk from stale probe files is closed by the v1.02 probe schema and V1.1 active-writer verifier.

This validates the intended architecture: **one collector + one shared feature/state engine + one FILE_COMMON bridge per PC, consumed by multiple MT5 terminals without duplicated external collection or feature computation.**

## Next gate
Integrate a read-only Shared Intelligence consumer into a Guardian candidate while preserving complete independence of hard risk, SL/protection, drawdown and prop-firm compliance logic. External Intelligence must remain advisory/research-only until strategy-specific OOS evidence is available.
