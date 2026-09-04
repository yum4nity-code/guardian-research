# D025 cross-asset first-touch diagnostic — 2026-09-04

Source: user-supplied `d025_ler_trading_1_01_trades` + `outcomes` CSV append files. Latest 2026-06-01 -> 2026-07-30 sessions isolated by session_id for each symbol.

## Important interpretation

This is a diagnostic / post-sample comparison, not a tuning authorization. The latest window extends beyond the prior 2026-06-28 pre-OOS cutoff and must not be used to silently optimize D025 thresholds.

A target is counted only when its hit timestamp is positive and occurs before `stop_utc` (or no stop was recorded). Raw post-stop MFE/MAE remains unsuitable because Trading 1.01 continues observational tracking after stop.

## Latest-window first-touch before SL

| Symbol | Trades | +1R | +2R | +3R | +4R | +5R |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 112 | 50.00% | 38.39% | 22.32% | 16.07% | 13.39% |
| ETHUSD | 102 | 52.94% | 40.20% | 28.43% | 16.67% | 11.76% |
| EURUSD | 55 | 52.73% | 23.64% | 16.36% | 7.27% | 5.45% |
| SOLUSD | 65 | 53.85% | 36.92% | 26.15% | 20.00% | 9.23% |
| DOGEUSD | 77 | 46.75% | 28.57% | 15.58% | 14.29% | 12.99% |
| LNKUSD | 83 | 43.37% | 25.30% | 18.07% | 14.46% | 10.84% |

## First-touch resolved target-vs-SL rate and simple pre-cost fixed-TP EV

The following EV is only the simple resolved first-touch construction: target at kR versus -1R stop, ignoring costs, unresolved 48h exits, slippage and path-dependent management.

| Symbol | P(target first) 1R | EV 1R | P(target first) 2R | EV 2R | P(target first) 3R | EV 3R |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSD | 50.9% | +0.018R | 39.1% | +0.173R | 24.3% | -0.029R |
| ETHUSD | 54.5% | +0.091R | 42.7% | +0.281R | 32.6% | +0.303R |
| EURUSD | 55.8% | +0.115R | 27.1% | -0.188R | 18.8% | -0.250R |
| SOLUSD | 53.8% | +0.077R | 38.7% | +0.161R | 28.8% | +0.153R |
| DOGEUSD | 47.4% | -0.053R | 31.4% | -0.057R | 18.2% | -0.273R |
| LNKUSD | 44.4% | -0.111R | 26.9% | -0.192R | 20.0% | -0.200R |

## Path split highlights

- ETHUSD RETEST: +1R 64.81%, +2R 50.00%, +3R 38.89% before SL.
- SOLUSD ACCEPTANCE: +1R 58.06%, +2R 45.16%, +3R 29.03%.
- EURUSD ACCEPTANCE: +1R 52.17%, +2R 39.13%, +3R 21.74%; EURUSD RETEST decays sharply after +1R (+2R 12.5%).
- DOGEUSD: RETEST is better than ACCEPTANCE at +1R/+2R/+3R, but aggregate fixed-TP EV remains weak in this sample.
- LNKUSD aggregate first-touch rates are weak; no positive simple fixed-TP construction is established.
- BTCUSD latest window shows ACCEPTANCE and RETEST almost identical around +1R, unlike the prior long-window split. Do not promote a BTC path-specific rule from one sample.

## Management implication

Current evidence argues against changing the locked structural SL first. The most defensible next management comparison remains a very small preregistered set:

1. full TP at +1R;
2. full TP at +2R;
3. partial at +1R (40-50%), BE on remainder, runner trail activated only after +2R with one fixed ATR rule.

The +0.5R first-touch timestamp is still the highest-value missing measurement before judging an earlier partial/TP.

Cross-asset conclusion: ETH and SOL show the strongest latest-window first-touch profile; BTC remains interesting; EURUSD looks more like an early-exit candidate than a runner candidate; DOGE and LNK do not yet show aggregate fixed-TP edge. This is diagnostic only and must be checked across additional symbols/windows before any production rule split.