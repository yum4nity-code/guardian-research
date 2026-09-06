# D023 USDJPY London ORB — FundedNext clock/cost conformance control — 2026-09-06

Source: user MT5 CSV `D023_USDJPY_ORB_V104_FUNDEDNEXT_CONFORMANCE.csv` from v1.04 FundedNext standalone diagnostic.

Frozen strategy semantics unchanged from D023 V0:
- London opening range 08:00–09:00 local, four M15 bars;
- first M15 close breakout 09:00–11:00;
- entry next M15 open;
- stop opposite range edge;
- exit stop or 16:00 London;
- max one trade/day;
- no filters/tuning.

Conformance corrections in v1.04:
- FundedNext server GMT+2/GMT+3 handling with US DST schedule;
- Europe/London DST-aware conversion;
- FundedNext Stellar 1-Step/2-Step Forex commission = USD 5/lot/side;
- isolated CSV.

## Result 2024-01-02 to 2026-06-24

n = 482
Gross mean = +0.155996 R/trade
Commission mean = 0.064493 R/trade
Net mean = +0.091503 R/trade
Net sum = +44.104641 R
Gross PF = 1.3253
Net PF = 1.1759
Net win rate = 41.70%

By year net mean:
- 2024: n=198, +0.152603 R/trade, PF 1.2653
- 2025: n=200, +0.055060 R/trade, PF 1.1202
- 2026 through June: n=84, +0.034254 R/trade, PF 1.0635

Direction:
- LONG: n=257, +0.134395 R/trade
- SHORT: n=225, +0.042512 R/trade
Direction differences are descriptive only; no direction filter is authorized.

1.5x commission stress:
- pooled mean +0.059257 R/trade
- pooled PF 1.1095
- 2024 +0.117049 R/trade
- 2025 +0.029946 R/trade
- 2026 -0.007177 R/trade

5-day moving-block bootstrap on zero-filled weekdays, net daily mean:
- point daily mean about +0.06796 R/day
- lower 5% bound about -0.03265 R/day
Therefore current 2024-26 evidence is positive but not statistically decisive under the preregistered block-bootstrap criterion.

Interpretation:
- Correct FundedNext clock/cost conformance does NOT destroy the USDJPY ORB clue.
- Edge decays from 2024 to 2026 and pooled bootstrap lower bound remains below zero.
- This is not production validation.
- The correct next action is untouched 2023 confirmation under frozen rules, no manager tuning first.
