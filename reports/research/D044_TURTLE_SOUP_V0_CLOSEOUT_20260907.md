# D044 — Turtle Soup 20-Day Failed-Break Reversal V0 closeout

Date: 2026-09-07 Europe/Paris
Formal development verdict: **REJECT_V0**
Confirmation: **UNOPENED**

## Frozen experiment

D044 tested the source-aligned Turtle Soup entry structure with a deterministic Guardian transport:

- prior completed 20-D1-bar extreme;
- most recent occurrence of the prior extreme at least four sessions old;
- current executable penetration beyond that prior extreme;
- fixed five-trade-tick re-entry after executable reversal crossing;
- structural stop one trade tick beyond the current broker-day executable excursion;
- no TP, BE, partial, trailing, re-entry or regime filter;
- structural stop or first executable liquidation tick at +24h;
- H24 was explicitly a Guardian entry-alpha reference and not claimed to replicate the source's discretionary management.

Source identity SHA256: `98f4b6d2f2ca0e48a6d795a2409f3cf05c936a9c882316420ee578f82ed0a1f0`.

## Engineering smoke

October 2023 smoke on USDJPY, XAUUSD and BTCUSD passed compile, lifecycle, evidence and native Trade Path integrity. Five trades were observed in total and all were opened/closed cleanly. Smoke profitability was not interpreted.

## Development 2024–2025

Authoritative score event:
`backtests/d044/live/events/development/score/20260907T114545Z`

- aggregate n: 192
- BTCUSD n 34, total -16.01335154R
- ETHUSD n 31, total -4.94495731R
- EURUSD n 31, total -36.73975315R
- GBPUSD n 37, total -47.39792728R
- USDJPY n 28, total -42.55876396R
- XAUUSD n 31, total -18.04185600R
- aggregate mean net: **-0.8630031731R/trade**
- aggregate PF: **0.3967689014**
- positive symbols: **0/6**
- aggregate total: **-165.69660924R**
- 1.5x commission-stress total: **-209.26286371R**
- 2024 total: **-30.09993157R**
- 2025 total: **-135.59667767R**
- integrity events: **0**

Count gates passed. Economic gates for mean, PF, positive-symbol breadth, 2024, 2025 and commission stress all failed.

## Decision

D044 V0 is permanently **REJECT_V0**. No 2026 H1 confirmation is opened.

The result is not borderline and D044 is not selected for Market Transport Lab V1. Testing many additional symbols after a 0/6, strongly negative development result would be a poor use of the transport screen and would create avoidable rescue/fishing pressure.

This closeout does not make a general claim that every discretionary Turtle Soup implementation is unprofitable. It rejects this frozen, source-aligned entry transport plus the preregistered H24 Guardian reference on the tested FundedNext 2024–2025 universe.

## Policy

- Do not retune the five-tick offset on seen 2024–2025 data.
- Do not add filters or alternative management and call them D044 confirmation.
- Keep 2026 H1 unopened.
- Any materially different Turtle Soup interpretation must be a new preregistered experiment with a new scientific identity.
