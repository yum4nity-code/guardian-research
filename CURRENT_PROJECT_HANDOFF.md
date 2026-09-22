# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## V100
Frozen forward/shadow package. Ranks 7/9. 2026 protected.

## Rates lineage — CLOSED
V102 produced five validation survivors; V103 final pre-OOS forensic passed 0/5.
Locked OOS not opened.

## CFTC lineage — CLOSED
V104 run GEF104-20260922-145941:
- 5,872 finite tests
- 200 discovery frozen
- 65 replication survivors
- 39 robustness survivors
- 7 validation survivors

V105 run GEF105-20260922-151045:
- 7 candidates audited
- 5 unique information families
- 0 final pre-OOS passes
- several large intraday means collapsed to only 1-4 distinct CFTC reports
- 2023-2025 not accessed
- 2026 not accessed

Decision: close standalone CFTC lineage before locked OOS.

Canonical closure:
research/results/GEF105_CFTC_CLOSURE_2026_09_22.json

## V106 — ACTIVE SOURCE AUDIT

Do not jump blindly to another alpha scan.

V106 inventories the remaining local causal sources and existing V85 taxonomy for:
- financial conditions / stress
- Treasury auctions
- FOMC/Fed event material
- ALFRED/vintage macro
- CFE volume/open interest
- remaining Cboe volatility provenance

V106 runs ZERO edge trials.
It does not read 2023+ market returns.

It outputs FAMILY_READINESS.csv and recommends the next family only when source coverage and causal timing are defensible.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV106.ps1 -Root D:\MT5_Backtests
