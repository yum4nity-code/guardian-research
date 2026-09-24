# D025 EURUSD SHORT +2R — FTMO Fresh-2023 Result

Date: 2026-09-24
Status: COMPLETE / FRESH RAW SLIGHTLY POSITIVE / ECONOMICALLY NEGATIVE / LINEAGE-TRANSPORT MISMATCH

## Run integrity

Artifact: GUARDIAN_D025_EURUSD_SHORT_2R_FTMO_20260924-051846.zip

- FTMO server: FTMO-Demo
- symbol: EURUSD
- tester window: 2023-01-01 through 2025-12-31
- model: 1 minute OHLC
- source: D025_LER_VirtualPath_1_03.mq5
- compile: 0 errors / 0 warnings
- protected 2026 accessed: false
- raw trades: 1,261 total, 607 SHORT candidate trades
- SHORT paths: RETEST + ACCEPTANCE
- duplicate candidate event IDs: none
- candidate entry range: 2023-01-04 through 2025-12-29

## Fresh 2023 result

Signals: 235
Resolved first-touch outcomes: 215

Raw:
- +2R target-first rate: 33.9535%
- raw EV: +0.018605 R/trade
- month-block q10: -0.130000 R
- P(raw mean <= 0): 45.19%

Predeclared cost-screen:
- mean entry-spread proxy: 0.015160 R
- mean normalized FTMO commission: 0.036533 R
- stressed EV: **-0.035605 R/trade**
- stressed month-block q10: -0.184538 R
- P(stressed mean <= 0): 62.70%

Path diagnostics only:
- ACCEPTANCE: raw -0.011364R; stressed -0.054199R
- RETEST: raw +0.039370R; stressed -0.022722R

Fresh label under the frozen preregistration:
**SIGNAL_POSITIVE_ECONOMIC_NEGATIVE**

Exact-tick follow-up is therefore NOT permitted by the frozen gate.

## 2024-2025 FTMO transport

Signals: 372
Resolved: 303
- raw EV: +0.099010R
- stressed EV: +0.029083R
- stressed q10: -0.074588R

Yearly:
- 2024 raw +0.040462R; stressed -0.037684R
- 2025 raw +0.176923R; stressed +0.117935R

## Important lineage caveat

The current FTMO harness does NOT numerically reproduce the previously preserved EURUSD SHORT summary that motivated this test (historically remembered around 2024 +0.146R, 2025 +0.122R, pooled +0.136R with different support counts).

Current FTMO 2024-2025:
- 372 signals / 303 resolved
- pooled raw +0.099010R

Previously preserved summary:
- roughly 337 total / 280 resolved
- pooled around +0.136R

Therefore:
1. this run is valid evidence against **this exact FTMO implementation/population**;
2. it must NOT be presented as a clean exact reproduction/falsification of the older branch until the old population definition/source artifact is recovered;
3. no post-hoc path or level-family selection is allowed from the opened 2023 result.

## Decision

Close the exact tested FTMO D025 EURUSD all-path SHORT +2R branch as economically negative on fresh 2023.

Do not rescue it by selecting RETEST, ACCEPTANCE, levels, sessions or alternate exits from this opened sample.

Separately preserve the historical lineage discrepancy as an audit issue only; do not use it to keep this exact tested branch alive.
