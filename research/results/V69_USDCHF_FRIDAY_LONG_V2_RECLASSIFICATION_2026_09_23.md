# V69 — USDCHF Friday LONG daily-close calendar edge — Doctrine V2 reclassification

Date: 2026-09-23
Status: FRESH LOCKED-OOS CONFIRMED MINI-EDGE CANDIDATE / NOT PRODUCTION READY
Family: 04_INTRADAY_CALENDAR_STRUCTURE
Source archive: GUARDIAN_MINI_EDGE_AUDIT_20260923-073103.zip

## Frozen candidate

- Market: USDCHF
- Mechanism: weekday
- Bucket: 4
- pandas weekday convention: 4 = Friday
- Direction: LONG
- Entry reference: Friday daily close
- Exit reference: next available daily close
- Practical interpretation: normally Friday close -> Monday close, subject to market calendar.

This is a calendar effect, despite the historical family name containing "intraday".

## Lineage

The lineage was progressively frozen before later samples were opened:

1. Replication 2014-2017 (V64)
   - 24 candidates tested
   - 10 replicated

2. Prevalidation robustness (V65)
   - 10 tested
   - 9 retained

3. Immutable freeze (V66)
   - 9 candidates frozen

4. Independent validation 2018-2022 (V67)
   - 9 tested
   - 2 passed: USDCHF and NSXUSD

5. Final pre-OOS forensic (V68)
   - both survivors remained OOS-eligible

6. Locked OOS 2023-2025 (V69)
   - 2 tested
   - 1 passed: USDCHF
   - 2026 not accessed
   - no retuning

## Independent validation 2018-2022

USDCHF:
- n = 259
- gross mean = +5.5543546233 bps/event
- hit rate = 66.795%
- positive-year fraction = 1.00
- mean after removing best 1% = +4.9441840563 bps
- mean after removing best 2% = +4.4491864776 bps
- mean after removing best 5 events = +4.6057597638 bps
- validation = PASS

## Locked OOS 2023-2025

Predeclared OOS gate:
- n >= 100
- gross mean > 0
- hit rate >= 50%
- positive-year fraction >= 2/3
- trim best 1% > 0
- trim best 2% > 0
- remove best 5 events > 0

USDCHF result:
- n = 155
- gross mean = +4.6390754812 bps/event
- hit rate = 69.6774%
- positive-year fraction = 1.00
- trim best 1% = +4.0694239442 bps
- trim best 2% = +3.6527139124 bps
- remove best 5 events = +3.4669865590 bps
- 2023 mean = +1.4293421155 bps
- 2024 mean = +5.9455466050 bps
- 2025 mean = +6.4806120814 bps
- OOS_PASS = TRUE

The competing NSXUSD survivor failed locked OOS tail robustness despite a positive gross mean, which is evidence that the gate was discriminating rather than automatically passing positive means.

## Doctrine V2 classification

- discovery/replication: SUPPORTED
- independent existence validation: SUPPORTED
- fresh locked OOS existence: CONFIRMED
- economic size: MINI_EDGE_CANDIDATE
- ensemble: NOT TESTED
- production: NOT PRODUCTION READY

This is stronger evidence than a same-sample historical near-miss: it survived an independent 2018-2022 validation and a separately locked 2023-2025 OOS.

## Critical execution caveat

All quoted returns are gross daily-close returns. The V69 gate did not deduct:
- real FTMO BID/ASK spread at Friday entry and next-close exit;
- swaps / weekend financing;
- any commission applicable to the instrument/account;
- slippage.

Because the gross OOS mean is only +4.64 bps/event, realistic weekend carry and execution cost must be measured before production interpretation.

## Next allowed work

Read-only / execution reconstruction:
1. compute exact historical drawdown and losing-run structure;
2. reconstruct FTMO-like Friday close -> next daily close execution with BID/ASK;
3. deduct realistic swap/roll and any commission;
4. check prop-firm weekend holding constraints and operational semantics;
5. assess incremental portfolio correlation against V112, D032-C1, D035, D017 and D025 candidates.

Do not open 2026 without a separate human gate.
Do not alter weekday, direction, entry/exit timing, or target and still call it V69 USDCHF.
