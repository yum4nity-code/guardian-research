# D17 live v11.17 — BTC attribution result — 2026-09-06

STATUS: BTC FAILED NET / MANAGER IMPROVES PATH BUT DOES NOT CREATE ROBUST NET EDGE

## Scope
Frozen BTCUSD Every-tick run, 2024-01-01 through 2025-12-31, using `D017_Momentum_LiveV1117_Attribution_v1_100_20260906.mq5` on exact v11.17 Momentum entry semantics. No RSI. No 60m timebox. Two paired variants on identical accepted virtual signals: NATIVE_RATCHET vs FIXED_3R.

## Data integrity
- 2,324 signal events total.
- 1,739 VALID_SIGNAL virtual entries; 585 REJECT_SPREAD_OR_SL.
- 1,739 complete rows for each manager variant; no censored manager exits.
- Raw path diagnostics: 1H/4H/8H for all 1,739; 24H for 1,738; 48H for 1,736 plus 3 END_TEST.

## Primary results
### FIXED_3R
- n=1,739
- gross mean +0.04658R/trade
- mean cost 0.19352R/trade
- net mean -0.14694R/trade
- net sum -255.53R
- PF net 0.833
- win rate 26.16%
- max sequential cumulative DD in virtual event stream ~309R

### NATIVE_RATCHET
- n=1,739
- gross mean +0.07737R/trade
- mean cost 0.19350R/trade
- net mean -0.11613R/trade
- net sum -201.96R
- PF net 0.828
- win rate 42.67%
- max sequential cumulative DD in virtual event stream ~219R

### Paired manager attribution
- NATIVE minus FIXED = +0.03081R/trade, +53.57R total.
- IID bootstrap 95% CI for paired delta approximately [-0.033, +0.097]R/trade.
- Week-cluster bootstrap 95% CI approximately [-0.047, +0.110]R/trade.
- Therefore manager superiority is directionally positive but NOT statistically established.

Mechanism:
- 297 events that would have hit FIXED initial SL were rescued to NATIVE ratchet exits, adding about +506.09R versus FIXED.
- 455 FIXED +3R winners were clipped by NATIVE ratchet exits, costing about -452.52R versus FIXED.
- Net manager contribution = +53.57R.

## Stability
NATIVE net by year:
- 2024: -0.11055R/trade, n=1,004.
- 2025: -0.12376R/trade, n=735.

NATIVE net by side:
- BUY: -0.16532R/trade, n=966.
- SELL: -0.05466R/trade, n=773.

NATIVE by year/side:
- 2024 BUY -0.09489R/trade.
- 2024 SELL -0.13833R/trade.
- 2025 BUY -0.30489R/trade.
- 2025 SELL +0.01903R/trade (PF 1.028), the only slightly positive broad segment.

Only 7 of 24 calendar months are net positive for NATIVE. The 2025 SELL improvement is not enough to establish a stable cross-year side edge and must not be promoted post hoc.

## Important interpretation limit
The attribution diagnostic intentionally admits every valid virtual signal and excludes live account-state/position selection. The production EA has one-position-per-symbol/account constraints, so the -201.96R virtual sum is NOT an account PnL forecast. A supplementary one-position-per-symbol replay still remains negative (NATIVE approx -0.105R/trade on 1,299 accepted signals), so overlap does not reverse the verdict.

## Verdict
1. BTC live-v11.17 Momentum FAILS the current net-edge gate after frozen FTMO crypto fallback commission 0.0325%/side.
2. Native ratchet materially raises win rate and reduces path drawdown/losing streaks, but its mean incremental value (~+0.031R/trade) is too small and unstable to overcome costs.
3. Do NOT tune 2R/25%, 1.25R BE, 1.75 ATR trail, BNS threshold, cost threshold, or side filters on this inspected BTC sample.
4. Do NOT rescue with a post-hoc SELL-only 2025 rule.
5. Complete the preregistered ETHUSD 2024-2025 run with IDENTICAL code/settings. If ETH also fails net, close D17 live-v11.17 Momentum as an alpha candidate and preserve only the manager attribution evidence.

## Next action
Run ETHUSD, 2024-01-01 -> 2025-12-31, Every tick, identical diagnostic build and parameters. Return the same four CSVs. No parameter changes.
