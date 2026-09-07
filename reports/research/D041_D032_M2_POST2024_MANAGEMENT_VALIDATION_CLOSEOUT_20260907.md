# D041 / D032-M2 POST2024 management validation — closeout

Date: 2026-09-07

## Scientific identity

D041 is only the operational wrapper for the preregistered D032-M2 management-validation experiment. It does not alter the already-confirmed D032 Bullish Doji Star H1 entry.

Frozen candidate:
- catastrophe stop at -3.5 source-R before +24h;
- no TP/trail before +24h;
- at +24h, close full position if net ex-swap PnL <= 0;
- otherwise run the full position with net-BE floor and 1.5 source-R trailing distance;
- hard timeout +48h.

Frozen reference: same event, no hard stop, full executable BID exit at +24h.

Formal window: POST2024 signal timestamps 2024-01-01 through 2026-06-23, tester extended through 2026-06-27 for full path completion. Historical model limitation remains Model=1 / 1-minute OHLC as preregistered.

## Engineering result

Smoke PASS on already-seen PRE2024 data. Formal POST2024 batch completed with integrity and produced 77 eligible paired events.

## Frozen verdict

**REJECT_MANAGEMENT**

Metrics:
- aggregate eligible events: 77 (gate >= 40 PASS)
- reference mean net R: +0.6664364026
- candidate mean net R: +0.3283826494 (absolute candidate gate > +0.20 PASS)
- paired mean candidate-minus-reference delta: **-0.3380537662R** (FAIL)
- paired total delta: **-26.03014R**
- positive-delta symbols: **0 / 3** (FAIL)
- month-block bootstrap, 20,000 deterministic resamples: median -0.3389149086R; 95% interval **[-0.5330353344, -0.1216969679]** (lower-bound-positive gate FAIL; even the upper bound is negative)

Per symbol paired mean delta:
- BTCUSD: -0.069782R, n=32
- ETHUSD: -0.5714113R, n=30
- DOGUSD: -0.4436518R, n=15

Exit counts:
- TIMEOUT_48H: 4
- TRAIL_OR_BE_STOP: 41
- CLOSE_H24_NONPOS: 20
- CATASTROPHE_STOP_PRE24: 12

Authoritative immutable score event:
`backtests/d041/live/events/development/score/20260907T085054Z`

Paired analytics event:
`backtests/d041/live/events/development/rich-score/20260907T085054Z`

## Post-score tooling error

After score and paired analytics were already valid and published, the original D041 workflow called the generic strategy bundle publisher. That publisher requires the generic entry-strategy score/rich schema, while D041 intentionally uses a paired-management schema. It therefore emitted:

`ERROR: decision score does not match experiment/stage`

This was a post-verdict archive-tool incompatibility only. It does not invalidate the batch, score, paired analytics, or scientific verdict, and it does not justify an MT5 rerun. The D041 specialized workflow was subsequently corrected to avoid the generic publisher.

## Policy

- D032-M2 candidate management is rejected permanently on this POST2024 validation.
- Do not retune the -3.5R / H24 / 1.5R / H48 candidate using this now-seen validation sample and call it confirmation.
- This rejection is about the tested management rule, not the previously confirmed D032 entry edge.
- No D041 confirmation/production-boundary stage is opened.
