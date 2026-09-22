# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100
Frozen forward/shadow package. Ranks 7/9. 2026 protected.

## Rates lineage
V101 interactions closed at validation.
V102 produced five validated standalone-rate candidates.
V103 final pre-OOS forensic passed 0/5.
Rates locked OOS was not opened.

## V104 — CFTC VALIDATED PRE-OOS

Run: GEF104-20260922-145941
- engine: V104.1
- finite CFTC tests: 5,872
- discovery frozen: 200
- replication survivors: 65
- robustness survivors: 39
- validation survivors: 7
- final SHA256: 428ce6c9f5bd5b4acaaf4fbc619b1d07fd0c6abd5ec716403d6b2b4e01a9b68e
- 2023-2025 not accessed
- 2026 not accessed

Seven frozen survivors include repeated information sources:
- USDCAD commercial z52 LO -> USDJPY SHORT and AUDUSD SHORT
- WTI commercial level HI -> NSXUSD LONG and SPXUSD LONG
- USDCHF commercial z52 HI -> USDCHF SHORT
- USDCAD commercial level LO -> AUDUSD SHORT
- EURUSD commercial level HI -> USDCHF SHORT

## V105 — ACTIVE

Final pre-OOS forensic of exactly those seven V104 survivors.

Key difference from earlier intraday forensics:
CFTC is weekly information. V105 explicitly maps every eligible target observation back to the latest distinct CFTC report AVAILABLE_AT and evaluates one signal per report, in addition to the original frozen intraday semantics.

Diagnostics/gates include:
- tail removal;
- best month and leave-one-year-out;
- horizon non-overlap;
- first signal per distinct CFTC report;
- remove best 3/5 reports;
- first-per-report year stability;
- first-per-report month-block bootstrap;
- first signal per contiguous state episode;
- z0.9/z1.1;
- source availability delayed +1/+2 calendar days;
- 1/2/3/5 bp diagnostics;
- signal overlap and return correlation.

No portfolio optimization.
No 2023-2025.
No 2026.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV105.ps1 -Root D:\MT5_Backtests

Regardless of result, STOP after V105.
