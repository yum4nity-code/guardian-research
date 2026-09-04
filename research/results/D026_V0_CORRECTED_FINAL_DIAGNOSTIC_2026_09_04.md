# D026 Price Exhaustion Reclaim V0 — corrected BTC/ETH final diagnostic

Date: 2026-09-04
Status: V0 CORRECTED RUN COMPLETE / LARGE-EDGE STANDARD NOT MET / DO NOT PROMOTE

## Provenance

- Rules were locked before any D026 result: `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`.
- Initial 1.00 implementation had window-enforcement / RETEST-band conformance defects.
- 1.01 wrapper corrected implementation only, without changing locked thresholds.
- User then ran the standalone merged equivalent `D026_PriceExhaustionReclaim_Virtual_V0_1_02_STANDALONE_CONFORMANCEFIX.mq5`.
- Standalone SHA-256: `1b263fc14bc568e061afd0060cf5ad060f8cd400749cf88142c2e909d1acf9a2`.
- Corrected BTC/ETH sessions are content-identical to the earlier 1.00 sessions after removing only `session_id`. Therefore the implementation defects were not exercised by these specific BTC/ETH histories and the observed BTC/ETH V0 results are valid under the corrected lock.

## Data integrity

Corrected sessions:
- BTCUSD: 560 virtual signals = 283 in 2024 + 277 in 2025.
- ETHUSD: 618 virtual signals = 332 in 2024 + 286 in 2025.
- Total: 1,178 signals.
- No `VALID_SIGNAL_REJECTED_BAD_RISK`.
- No `VALID_SIGNAL_REJECTED_NO_SLOT`.
- Final 48h snapshot missing only for the last edge-of-window event on each symbol; 1h/4h/8h coverage is complete.

## Overall fixed-target first-touch EV, pre-cost

| symbol | target | resolved | EV | approx 95% EV interval |
|---|---:|---:|---:|---:|
| BTCUSD | +1R | 522 | +0.011R | -0.074 .. +0.097R |
| BTCUSD | +2R | 489 | -0.117R | -0.233 .. +0.009R |
| BTCUSD | +3R | 466 | -0.176R | -0.313 .. -0.020R |
| ETHUSD | +1R | 577 | -0.009R | -0.090 .. +0.073R |
| ETHUSD | +2R | 538 | -0.058R | -0.171 .. +0.064R |
| ETHUSD | +3R | 515 | -0.138R | -0.271 .. +0.012R |

Combined BTC+ETH:
- +1R: +0.001R on 1,099 resolved events.
- +2R: -0.086R on 1,027.
- +3R: -0.156R on 981.

No broad fixed-target edge exists.

## Year stability

BTCUSD:
- 2024: EV1 +0.015R / EV2 -0.187R / EV3 -0.253R.
- 2025: EV1 +0.008R / EV2 -0.042R / EV3 -0.093R.

ETHUSD:
- 2024: EV1 +0.025R / EV2 +0.027R / EV3 -0.053R.
- 2025: EV1 -0.049R / EV2 -0.162R / EV3 -0.241R.

No overall symbol result approaches the user's required large-edge threshold.

## Predeclared side/path splits

BTC 2025 SHORT is the only visually strong year-specific side:
- n=136
- EV1 +0.118R
- EV2 +0.160R
- EV3 +0.107R

But BTC SHORT 2024 contradicts it:
- n=157
- EV1 +0.040R
- EV2 -0.161R
- EV3 -0.259R

Therefore BTC 2025 SHORT is regime evidence only, not a recurring branch.

ETH RETEST also flips:
- 2024 RETEST n=200: EV1 +0.128R / EV2 +0.133R / EV3 +0.137R.
- 2025 RETEST n=184: EV1 -0.107R / EV2 -0.164R / EV3 -0.230R.

Therefore no predeclared side/path branch repeats with a large advantage across both years.

## Predeclared 40% @ +1R then BE runner

BTC:
- runner to +2R: -0.050R on 496 resolved paths.
- runner to +3R: -0.098R on 487.

ETH:
- runner to +2R: +0.008R on 547.
- runner to +3R: -0.034R on 530.

Combined:
- +2R runner: -0.020R.
- +3R runner: -0.065R.

This management family does not rescue D026 V0.

## Decision

**D026 V0 FAILS the large-edge research standard on BTCUSD and ETHUSD.**

Reasons:
1. broad +1R is essentially zero before costs;
2. +2R/+3R are negative;
3. the predeclared partial+BE management family is near-zero/negative;
4. apparently attractive side/path effects reverse across years;
5. because there is no robust pre-cost edge, spread/commission/slippage modeling cannot rescue the strategy.

Do not deploy and do not retune V0 thresholds post hoc.

## What remains scientifically legitimate

A future D026 V1 must be a genuinely new, pre-specified hypothesis rather than a threshold sweep over V0. The strongest descriptive clues worth preserving only as hypothesis-generation are:
- BTC SHORT behavior differs materially by year/regime;
- ETH RETEST behavior differs materially by year/regime.

Any V1 should explain that regime dependence mechanistically before testing, rather than selecting the winning year after the fact.
