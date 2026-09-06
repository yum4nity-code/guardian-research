# D017 v11.17 USDCAD attribution result — 2026-09-06

Period: 2024-01-01 -> 2025-12-31. Diagnostic: `D017_Momentum_LiveV1117_Attribution_v1_102_CSVFIX_20260906.mq5`. Every tick. Single clean v1.102 session `D017M102_USDCAD_1704067200_504314968`.

Population:
- 368 signal events
- 312 valid executable virtual entries
- 56 rejected by spread/SL validity
- 175 BUY / 137 SELL

## Main comparison

| Variant | n | Gross R/trade | Cost R/trade | Net R/trade | Net sum R | Net PF | Net win rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| NATIVE_RATCHET | 312 | -0.0375 | 0.0689 | -0.1064 | -33.21 | 0.828 | 41.99% |
| FIXED_3R | 312 | -0.0513 | 0.0714 | -0.1227 | -38.27 | 0.849 | 23.72% |

Paired Native - Fixed net delta = +0.0162R/trade, +5.06R total. Bootstrap 95% CI for paired delta ~= -0.116 .. +0.149R/trade, so the manager improvement is not statistically established on USDCAD.

Native net-mean bootstrap 95% CI ~= -0.251 .. +0.040R/trade; sample mean remains negative.

## Year split

Native:
- 2024: n=126, -0.2439R/trade net
- 2025: n=186, -0.0133R/trade net

Fixed 3R:
- 2024: -0.2765R/trade net
- 2025: -0.0184R/trade net

This is improvement toward flat in 2025, not robust two-year edge.

## Side split

Native:
- BUY n=175: -0.0902R/trade net
- SELL n=137: -0.1272R/trade net

No side is profitable pooled. Do not rescue one side post hoc.

## Manager mechanics

Fixed 3R had 74 +3R gross wins and 238 -1R gross losses.
- On the 238 fixed losers, Native recovered about +103.99R gross versus Fixed.
- On the 74 fixed winners, Native gave back about -99.70R gross versus Fixed.
- Net manager gain is therefore small, about +4.29R gross / +5.06R after differential costs across 312 trades.

Native had 10 positive months out of 24.
A simple one-position-at-a-time reading also remains negative (Native about -0.120R/trade across 257 selected trades), so overlap is not the explanation.

## Decision

USDCAD does not rescue D017 Momentum v11.17. With BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD and now USDCAD inspected under the current attribution campaign, there is no robust cross-period production alpha family to promote in current form.

The manager hypothesis remains separate and alive: the Native ratchet helps some markets and hurts others. This supports a future preregistered cross-strategy manager study, not post-hoc rescue of D017.
