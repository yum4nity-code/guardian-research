# D035-C1 — Fresh 2026-H1 confirmation preregistration under Doctrine V2

Date: 2026-09-23
Status: FROZEN BEFORE 2026-H1 ACCESS
Parent: D035-E1 causal dual-source XLMUSD
Purpose: independent fresh-sample test of whether the causal dual-source response persists.

## Frozen candidate

Sources:
- Binance Vision BTCUSDT and ETHUSDT USD-M
- original D035 causal single-source shock definitions unchanged
- each source: 5m return <= strictly-prior rolling 30d 10th percentile AND negative
- each source: 5m sum_open_interest change <= strictly-prior rolling 30d 10th percentile AND negative
- 30-minute per-source cooldown

Dual-source condition:
- both BTC and ETH qualifying shocks within <=5 minutes
- signal timestamp = later/second qualifying source event

Primary target:
- XLMUSD only

Direction:
- SHORT

Execution:
- entry at first available target BID at/after causal second-source timestamp
- exit at ASK
- primary horizon +15m
- diagnostic +30m only

Window:
- 2026-01-01 through 2026-06-30 UTC
- no Jul-Dec 2026 access

## Doctrine V2 evaluation

No +15 bps magnitude gate is used for edge existence.

Primary fresh-sample classifications:

NEGATIVE:
- executable +15m mean <= 0

POSITIVE_UNCERTAIN:
- executable +15m mean > 0 but one-sided 90% day-cluster lower bound <= 0

POSITIVE_CONFIRMED:
- executable +15m mean > 0 AND one-sided 90% day-cluster lower bound > 0

Support label:
- if fewer than 100 executable primary events, mark SPARSE and do not overinterpret uncertainty

Economic-size labels:
- MINI_EDGE if executable +15m mean > 0
- STANDALONE_CANDIDATE only if separately measured economic/production criteria are met later

Diagnostics only:
- median
- +30m mean
- month-by-month means
- concentration / trim-best 1%
- matched causal-control differential

These diagnostics do not become ex-post death gates.

## Prohibited

- no target substitution
- no BTCUSD/ETHUSD promotion
- no horizon change
- no source-threshold changes
- no direction change
- no 5m-window change
- no subgroup selection
- no Jul-Dec 2026
- no rescue after result

## Human gate

This file freezes the test but does NOT itself authorize reading 2026-H1.
Execution requires an explicit owner instruction after reviewing this preregistration.
