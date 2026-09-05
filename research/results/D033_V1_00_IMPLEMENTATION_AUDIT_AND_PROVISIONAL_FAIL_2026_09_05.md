# D033 v1.00 — implementation audit and provisional result

Date: 2026-09-05
Status: **V1.00 RESULT NOT ACCEPTED AS FINAL SOURCE-FAITHFUL VERDICT**
Classification: IMPLEMENTATION_AUDIT / BUGFIX_REQUIRED

## Supplied EURUSD 2024-2026 run
User returned `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv` for `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_00.mq5`.

Observed output:
- 127 resolved events total;
- DT: n=69, mean -0.288864R, median -1.270718R, 34.78% positive;
- DB: n=58, mean -1.130671R, median -1.424674R, 15.52% positive;
- pooled mean -0.673311R;
- pooled median -1.382488R;
- pooled mean executable return -0.929607 bps;
- one formation-gap event, no trade-gap events;
- clean no-gap n=126, mean -0.657055R, median -1.378348R;
- year means: 2024 -0.829616R, 2025 +0.064470R, 2026 -1.314087R;
- month-block bootstrap 95% interval for pooled mean R approximately [-1.063, -0.246]R;
- positive-R concentration: largest winner about 11.88% of total positive R, above the frozen <=10% gate.

The v1.00 output therefore fails almost every frozen advancement criterion. Source-like midpoint profitability also does not reproduce: DT mean source-mid return about +0.085 bps, DB about -0.846 bps, pooled about -0.340 bps.

## Why this is NOT being accepted as the final D033 verdict
A post-run audit against Appendix B.2 of Ben Omrane & Van Oppens identified a deterministic implementation mismatch in the M2 extrema alternation routine.

Source Appendix B.2 constructs the alternating series by:
1. selecting the chronologically first extremum (maximum wins if max/min occur at the exact same first moment);
2. if the selected extremum is a maximum, selecting the chronologically first later minimum;
3. if the selected extremum is a minimum, selecting the chronologically first later maximum;
4. same-type extrema occurring before the required opposite type are skipped.

v1.00 instead replaced an already selected extremum by a later **more-extreme extremum of the same type** before the opposite type appeared. That changes the M2 sequence and therefore pattern eligibility. This is not a research threshold choice and was not derived from performance; it is a source-fidelity implementation error.

The source paper explicitly describes the first-opposite-type construction in Appendix B.2. Therefore the v1.00 run is archived as a useful provisional negative diagnostic but **must not be called a valid close-replication rejection**.

## Correction lock
`D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_01.mq5` changes only the M2 alternation procedure to match Appendix B.2:
- chronological sort, with maximum first on exact-time tie;
- keep the first selected extremum;
- skip later same-type candidates;
- append the first later opposite-type extremum;
- repeat.

No pattern equation, equality tolerance, 36-bar window, kernel rule, pretrend condition, TP, SL, timeout, spread handling, signal window, or feature rule is changed.

v1.01 SHA-256: `8281951c4b7745dac0f9660808294dc447c351a20cd2679d116b5384551796b3`.

Because the correction is mechanically dictated by the source and frozen before opening v1.01 outcomes, rerunning the same 2024-2026 development interval is treated as an implementation-correction rerun, not post-hoc strategy tuning.

## Required next action
Compile and rerun **EURUSD only**, same tester settings and same dates, with v1.01. The original D033 advancement gate remains unchanged. Do not interpret or tune the passive feature fields unless/until the corrected primary rule is decided.
