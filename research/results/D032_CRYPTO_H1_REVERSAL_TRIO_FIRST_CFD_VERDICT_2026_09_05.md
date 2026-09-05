# D032 — Crypto H1 Reversal Trio — first CFD verdict

Date: 2026-09-05
Status: FIRST CFD SCAN COMPLETE / DOJI STAR BULLISH = DISCOVERY CANDIDATE / INVERTED HAMMER + HANGING MAN = NO BROAD EDGE
Classification: CLOSE_REPLICATION_CFD_TRANSFER

## Data received
User reran D032 v1.01 on 2024-01-01 through 2026-06-26 using MT5 real-tick testing. Frozen core symbols were BTCUSD, ETHUSD and DOGUSD; additional transport-only runs were supplied for LNKUSD and XRPUSD.

v1.00 had an output-only header-index bug that caused immediate runtime failure and BOM-only CSVs. v1.01 fixed only that output bug; signal/research logic was unchanged.

## Important analysis correction
`SUMMARY.csv` in v1.01 is not authoritative for 24h means because the accumulator adds 24h return only when the horizon exists but divides by all completed rows, including rows with missing horizons. Event-level CSVs are sufficient to recompute correctly, so no rerun is required for this campaign.

For the first verdict, only pattern rows with `feed_gap=0`, `missing_horizons=0` and a valid executable 24h return were treated as clean 24h observations. This leaves 380 clean frozen-core events out of 508 total core pattern events:
- Doji Star Bullish: 77 / 98 clean
- Inverted Hammer Bullish: 74 / 97 clean
- Hanging Man Bearish: 229 / 313 clean

The executable layer embeds tester bid/ask spread. `commission_bps_per_side` was 0 in the supplied runs, so no commission deduction is included.

## Frozen-core results — BTC / ETH / DOGE

### Bullish Doji Star — strong discovery candidate
Clean pooled events: 77.

Executable 24h mean return: **+111.6 bps**.
Source-close 24h mean return: **+127.6 bps**.
Executable median 24h return: **+79.7 bps**.
Executable 24h win rate: **61.0%**.
Mean executable 24h return expressed in the source-defined risk unit (`1R = 2*sigma24`): **+0.726R/event**.

By frozen core symbol, clean executable 24h mean:
- BTCUSD: +50.7 bps, n=32
- ETHUSD: +159.4 bps, n=30
- DOGUSD: +145.8 bps, n=15

By pooled year:
- 2024: +92.0 bps, n=18
- 2025: +132.7 bps, n=44
- 2026 pre-OOS slice: +72.9 bps, n=15

Broad same-trend/no-pattern downtrend controls were negative on the core pool. Doji Star executable differential versus the broad control mean at 24h is about **+138.7 bps/event**. As a sensitivity-only, post-result deterministic sigma/time-nearest matching also leaves a large positive differential (~+89 to +104 bps depending on 10/50/100 nearest controls). This matching sensitivity was not preregistered and is not formal validation.

The full executable response curve strengthens with horizon rather than depending on one isolated point:
- 1h +4.6 bps
- 2h +2.8
- 3h +1.6
- 6h +22.2
- 9h +39.5
- 12h +63.4
- 15h +81.9
- 18h +98.5
- 24h +111.6

Correct first-touch reconstruction using event timestamps (target must occur before -1R stop):
- 0.5R before stop: 64.9%
- 1R before stop: 48.1%
- 1.5R before stop: 35.1%
- 2R before stop: 32.5%
- 2.5R before stop: 27.3%
- 3R before stop: 23.4%

A purely diagnostic fixed-target calculation with -1R stop and 24h timeout is positive at larger targets, reaching about +0.318R/event at 3R on the seen sample. This is discovery only: selecting 3R now would be post-hoc and cannot be called validated.

Month-block bootstrap diagnostics:
- 24h executable mean 95% interval approximately +24.7 to +203.4 bps.
- 3R stop/target/time-exit expectancy 95% interval approximately -0.014R to +0.659R.
Thus the 24h directional anomaly is materially promising; the discovered 3R management rule is not yet independently validated.

### Bullish Inverted Hammer — no broad recurring edge
Clean pooled n=74.
Executable 24h mean +11.8 bps but median -27.8 bps; mean 24h in R is -0.123R because outcomes scale badly with the source-defined risk denominator. Strong sign flip by period: 2024 positive, 2025 negative, 2026 worse. Do not rescue/tune.

### Bearish Hanging Man — weak/inconsistent
Clean pooled n=229.
Executable 24h mean +10.9 bps, but mean 24h in R is -0.119R. ETH is negative, DOG/BTC weakly positive, and first-touch target/stop diagnostics are negative across the tested 0.5R..3R fixed-target ladder. Do not promote.

## Extension symbols
LNKUSD and XRPUSD were not part of the frozen first campaign and remain transport diagnostics only.
- LNKUSD is positive on several patterns, including Doji Star.
- XRPUSD is broadly negative on the trio.
They do not alter the frozen BTC/ETH/DOGE verdict.

## Methodological notes from v1.01
1. Pattern-event CSV timestamps allow proper `target_before_stop` reconstruction. Built-in summary hit rates count whether a target was ever touched within 24h, including after a prior -1R breach, so built-in hit-rate summaries must not be interpreted as first-touch probabilities.
2. Control pool is deterministic same-trend/no-selected-pattern, as preregistered. It is a baseline pool, not an already volatility/time-matched sample; matching must remain offline and sensitivity-labelled unless separately frozen before confirmation.
3. Roughly one quarter of frozen-core pattern events intersect CFD feed gaps/missing horizons. This is itself relevant transfer evidence from exchange-style crypto research to CFD execution.

## Decision
- `DOJI_STAR_BULLISH`: **PROMOTE TO NEW PREREGISTERED CONFIRMATION / MANAGEMENT-DESIGN EXPERIMENT.** Do not declare production edge yet.
- `INVERTED_HAMMER_BULLISH`: **REJECT broad D032 continuation.**
- `HANGING_MAN_BEARISH`: **REJECT broad D032 continuation.**
- Do not pick the observed best TP/horizon and validate it on the same 2024-2026 sample.
- Next Doji experiment must freeze management before touching confirmation results, preferably on untouched/future data and with corrected first-touch/control/summary accounting.
