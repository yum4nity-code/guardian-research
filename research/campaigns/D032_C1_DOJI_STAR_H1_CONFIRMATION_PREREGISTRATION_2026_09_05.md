# D032-C1 — BULLISH DOJI STAR H1 CONFIRMATION

Date: 2026-09-05
Status: PREREGISTERED BEFORE CONFIRMATION OUTCOMES
Classification: CONFIRMATION_CLOSE_REPLICATION_CFD_TRANSFER

## Purpose
Confirm or reject the D032 Bullish Doji Star H1 discovery on target MT5 CFD data that was not used in the 2024-01-01 through 2026-06-26 discovery scan. This is still a lightweight entry-edge/management confirmation, not a Guardian integration test and not a production EA.

## Seen discovery sample
The D032 first CFD scan already exposed 2024-01-01 through 2026-06-26. That interval is forbidden as confirmation evidence.

## Frozen confirmation window
Accept signal timestamps only from 2018-07-01 00:00 through 2023-12-30 23:00 server time. The final accepted signal therefore has a complete +24h outcome before 2024-01-01.

If a broker/feed has less pre-2024 history, use only the history genuinely available; do not extend the confirmation window into the seen 2024-2026 sample to increase count.

## Frozen cohorts
Primary confirmation cohort:
- BTC CFD
- ETH CFD
- DOGE/DOG CFD

Transport-only cohort, analyzed separately:
- LINK/LNK CFD
- XRP CFD

LINK/XRP may support or challenge transportability but do not change the primary BTC/ETH/DOG confirmation gate.

## Frozen signal
Bullish Doji Star only, same numerical TA-Lib default definition as D032:
- previous H1 candle has a long bearish real body relative to the prior 10 real bodies;
- current H1 candle is a doji using the default TA-Lib BodyDoji threshold (10% of prior 10 high-low ranges);
- current real body gaps below the previous real body.

No candle-shape threshold may be changed after confirmation outcomes are opened.

## Frozen trend filter
Same D032 interpretation:
- SMA window = 144 H1 observations (six days);
- qualifying downtrend only when seven consecutive hourly MA values satisfy `MA[t-6] > ... > MA[t]` strictly.

## Entry and primary endpoint
Signal time = end of H1 pattern candle.

Source entry = H1 pattern close.
Executable entry = first available ASK after signal.

Primary endpoint = executable LONG return at exactly +24h using BID exit, with spread therefore embedded. Commission is stored separately in bps/side and deducted in analysis when supplied.

Primary result must be reported in both bps and source-risk-normalized R.

## Frozen risk normalization
At signal time calculate sample standard deviation of the previous 24 hourly returns.

`1R = 2 * sigma_24h` as a fractional price move.

This definition is unchanged from D032.

## Secondary management hypothesis
The D032 discovery sample suggested a possible management rule. It is now frozen before confirmation outcomes and may be tested as a secondary hypothesis:

`LONG -> stop -1R -> target +3R -> otherwise exit at +24h`

First-touch ordering must be resolved from real tester ticks. Actual first-tick crossing R is recorded rather than silently forcing exactly -1R/+3R if the CFD gaps across a threshold.

This secondary rule does not replace the primary +24h confirmation endpoint.

## Diagnostic horizons
Retain source-return and executable-return observations at 1,2,3,6,9,12,15,18,24h. These are diagnostics only; no best-horizon selection may redefine the primary endpoint after results are opened.

## Control pool
For each symbol, create a deterministic pool of hours with the same qualifying downtrend but no Bullish Doji Star. Record the same source/executable horizon returns and risk normalization. Controls are used offline to test incremental setup edge relative to ordinary downtrend behavior.

## CFD feed handling
- Missing exact horizons are not interpolated.
- Any H1 discontinuity while an event is active sets `feed_gap=1`.
- Primary clean sample requires `feed_gap=0`, `missing_horizons=0`, valid executable +24h return and valid R.

## Primary confirmation gate
Analyze BTC/ETH/DOG only for the formal gate. Promote the Doji entry only if all of the following hold on the untouched pre-2024 sample:
1. at least 50 clean primary-cohort events in aggregate;
2. aggregate mean net executable +24h return > 0;
3. aggregate mean executable +24h return > +0.15R/event after available explicit costs;
4. month-block bootstrap 95% lower bound of aggregate net +24h return > 0;
5. at least 2 of the 3 core symbols have positive mean net executable +24h return;
6. aggregate Doji minus same-trend control differential at +24h > 0;
7. no single core symbol contributes more than 60% of total positive pooled net result when pooled net result is positive.

Failure of the minimum event-count gate makes the result inconclusive, not a pass.

## Secondary management gate
The frozen -1R/+3R/24h management hypothesis is considered independently. It may advance only if its aggregate clean primary-cohort mean is > +0.15R/event and a month-block bootstrap 95% lower bound is > 0, with at least 2/3 core symbols positive. Otherwise retain the entry result and reject/inconclusive the management rule separately.

## Output contract
Each Strategy Tester run writes under:

`FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_C1_CONFIRM_DojiStar_H1\<SYMBOL>\<RUN_TAG>\`

Files:
- `CONFIRM_EVENTS.csv`
- `CONTROL_POOL.csv`
- `SUMMARY.csv`
- `RUN_INFO.csv`

No orders are sent and Guardian is OFF.

## Execution instructions
Recommended Strategy Tester model: `Every tick based on real ticks`.
Recommended tester chart timeframe: M1. Signal logic remains H1 internally.
Recommended tester dates: 2018-07-01 through 2024-01-01, or the earliest available broker history through 2024-01-01. The code itself ignores any 2024+ confirmation signals.

## Scientific boundary
The 2024-2026 discovery sample remains discovery evidence only. Do not combine it with pre-2024 confirmation data to manufacture the formal confirmation gate. After the confirmation verdict is frozen, the two samples may be shown together only as separate discovery and confirmation evidence.
