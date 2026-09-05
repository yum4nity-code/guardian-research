# D032-C1 Doji Star H1 confirmation — prepared

Date: 2026-09-05
Status: PREREGISTERED / MQ5 DELIVERED TO USER / NOT YET COMPILED OR RUN

Canonical preregistration:
`research/campaigns/D032_C1_DOJI_STAR_H1_CONFIRMATION_PREREGISTRATION_2026_09_05.md`

Delivered MQ5 filename:
`D032_C1_CONFIRM_DojiStar_H1_v1_00.mq5`

Delivered file SHA-256:
`810df178b1e358d24ad4f872cb258f8c763297406bd1cbda6e39a08f2e68ced4`

## Frozen confirmation design
- Discovery interval already seen: 2024-01-01 through 2026-06-26. Never use it as confirmation evidence.
- Confirmation signals hard-locked in code to 2018-07-01 00:00 through 2023-12-30 23:00 server time.
- Primary cohort: BTC, ETH, DOGE/DOG CFDs.
- Transport-only: LINK/LNK and XRP CFDs.
- Signal: Bullish Doji Star H1 only, same TA-Lib-default numerical definition as D032.
- Downtrend: 144-hour SMA with strict `MA[t-6] > ... > MA[t]`.
- Primary endpoint: executable LONG return at +24h (ASK entry / BID exit), spread embedded.
- `1R = 2 * sample stdev(previous 24 H1 returns)`.
- Secondary hypothesis frozen before confirmation outcomes: first touch -1R stop / +3R target / otherwise 24h timeout.
- Controls: qualifying downtrend with no Doji Star.
- Guardian OFF, no orders.

## QA improvements over D032 v1.01
- No indexed header array; event/control headers are explicit.
- Runtime header-size QA aborts if files remain BOM-only/tiny.
- Event header/row contract statically checked before delivery: 60 columns = 60 columns.
- Control header/row contract statically checked before delivery: 38 columns = 38 columns.
- First-touch management is native rather than reconstructed after the run.
- Summary clean-event denominator requires valid 24h, no feed gap and no missing horizons.
- Secondary management summary deducts configured round-trip commission in R.

## User execution
Compile in MetaEditor first. Any warning/error must be compile-fixed only; do not alter methodology after results are opened.

Run Strategy Tester on M1 with `Every tick based on real ticks` for pre-2024 history, ideally 2018-07-01 through 2024-01-01. Run core BTC/ETH/DOG first, then LNK/XRP transport runs. Code ignores 2024+ confirmation signals even if tester interval extends later.

Collect each run folder under:
`FILE_COMMON\GuardianResearch\SETUP_SCANS\D032_C1_CONFIRM_DojiStar_H1\<SYMBOL>\<RUN_TAG>\`

Return zipped folders to ChatGPT for the preregistered confirmation analysis.
