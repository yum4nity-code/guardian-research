# D032-M2 — Bullish Doji Star H1 realistic management — POST2024 validation

Date: 2026-09-05
Status: PREREGISTERED BEFORE POST2024 >24H MANAGEMENT OUTCOMES ARE INSPECTED
Classification: MANAGEMENT_VALIDATION_POST2024

## Purpose
Validate one complete, operationally plausible management rule for the already confirmed D032 Bullish Doji Star H1 entry using the still-unseen POST2024 >24h path. The PRE2024 D032-M1 management-development outcomes have been inspected and may be used only to choose this one frozen candidate.

This experiment does not re-confirm the entry edge. It validates management only.

## Frozen entry
Unchanged from D032-C1:
- Bullish Doji Star H1, same TA-Lib-default numerical implementation;
- strict 144-hour SMA downtrend `MA[t-6] > ... > MA[t]`;
- LONG at first executable ASK after signal;
- source volatility unit `1R = 2 * sample stdev(previous 24 H1 returns)`.

Primary cohort: BTCUSD, ETHUSD, DOGE/DOGUSD only.

## Frozen complete management candidate
1. Immediately after entry, hard catastrophe stop at **-3.5 source-R** from executable entry.
2. Position sizing in any later production implementation must size the monetary risk to the full -3.5R stop distance; -3.5 source-R does NOT mean 3.5x the allowed account risk.
3. No TP before +24h and no trailing before +24h.
4. If the catastrophe stop is hit before +24h, exit at the first executable BID crossing; record gap slippage if applicable.
5. At exact +24h, if the trade remains open and net ex-swap PnL <= 0, close the full position.
6. At +24h, if net ex-swap PnL > 0, convert the full position to a runner.
7. Runner has no TP.
8. Runner floor is net breakeven (entry ASK plus configured round-turn commission translated to price).
9. Runner trailing distance = **1.5 source-R** from the highest BID observed after +24h.
10. Effective runner stop = `max(net-BE floor, post24 peak BID - 1.5R)`.
11. Runner hard timeout = **+48h** from the original signal.
12. Weekend/feed gaps are retained; stop gaps use first executable BID, never synthetic fill at the requested stop price.

## Why this candidate was frozen
PRE2024 D032-M1 discovery showed:
- the preregistered 1.0R post-24h trail added essentially zero pooled value and failed bootstrap/stability gates;
- the frozen diagnostic 1.5R post-24h trail had positive point-estimate paired delta on all three core symbols (+0.109R pooled), but its PRE2024 bootstrap remained inconclusive;
- continuous PRE2024 MAE showed that a -3.5R catastrophe threshold would have been traversed by about 5.9% of eventual +24h winners versus about 46.4% of +24h losers. This is discovery evidence only and motivates, but does not validate, the -3.5R stop.

No other stop/trail combination may be substituted after POST2024 outcomes are opened.

## Untouched validation window
Use only signal timestamps:
`2024-01-01 00:00:00` through `2026-06-23 23:00:00` server time.

The original D032 discovery inspected returns only through +24h. The >24h runner outcomes and the complete -3.5R/1.5R management path for this window have not been inspected before this preregistration.

Do not mix PRE2024 management-development outcomes into the formal POST2024 validation gate.

## Reference comparators
For the same POST2024 events report:
- confirmed reference: no hard stop, full exit at +24h;
- management candidate: -3.5R catastrophe stop + H24 loser close / H24 winner 1.5R runner to H48.

The primary metric is paired candidate-minus-reference result in source-R per event.

## Costs
ASK entry / BID exit embeds the tester spread model. Explicit commission must be configurable in bps/side and deducted. Exact historical swap is not reconstructed by the virtual tester; report net ex-swap and separately stress the applicable FundedNext long swap/weekend/triple-swap schedule before production.

## Tester limitation
Historical FundedNext real ticks are unavailable for much of the period. Use M1 + `1 minute OHLC` if required. Positive results remain provisional for intraminute stop ordering and need later real-tick/live-forward confirmation.

## Formal management validation gate
Candidate passes only if on POST2024 BTC/ETH/DOG core:
1. at least 40 clean eligible events pooled;
2. pooled paired mean delta versus +24h reference > 0;
3. month-block bootstrap 95% lower bound of paired delta > 0;
4. at least 2 of 3 core symbols have positive paired mean delta;
5. no single core symbol contributes >60% of total positive incremental result;
6. candidate pooled mean net result remains > +0.20R/event before exact historical swap stress.

If minimum count fails, result is inconclusive. If any other gate fails, candidate is rejected; do not tune on POST2024.

## Production boundary
Even a PASS does not authorize Guardian integration yet. A passing candidate must next undergo explicit FundedNext swap/cost stress, weekend policy test, portfolio overlap/risk test, then Guardian/non-regression validation.
