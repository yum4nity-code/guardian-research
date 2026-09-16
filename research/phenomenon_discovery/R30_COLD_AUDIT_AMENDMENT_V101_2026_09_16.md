# R30 cold-audit amendment — builder v1.01 — 2026-09-16

## Trigger

R30-CODE-PREFLIGHT on main 172e4cf33e5afd6951636cc9c62a1388aa6105db
failed before any market-data execution.

Failure:
ModuleNotFoundError: build_xau_m5_from_r15_master_v1_00

Cause:
the R30 builder lives under research/autonomous while the reviewed R15 decoder
lives under research/phenomenon_discovery; Python script execution did not add
that sibling directory to sys.path.

## Fix

New immutable candidate:
- r30_build_dukascopy_xau_yearly_v1_01.py
- test_r30_r6b_dukascopy_long_history_v1_01.py

v1.01 adds only an explicit path insertion for:
research/phenomenon_discovery

before importing:
build_xau_m5_from_r15_master_v1_00

No market logic, decode logic, strategy rule, cost model, capital model, date
window or protection boundary changed.

## Verdict

PASS_TO_PREFLIGHT

All exact-main preflights must rerun on the final commit before any R30 market
data build starts.
