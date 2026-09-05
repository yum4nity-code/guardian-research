# D035 — Binance deleveraging -> FundedNext crypto CFD lead-lag — PREPARED

Date: 2026-09-05 Europe/Paris
Status: **PREREGISTERED / MT5 CFD EXPORTER PREPARED / HISTORICAL ANALYZER PREPARED / NO RESULTS INSPECTED**

## Intent

User explicitly selected the exotic cross-venue idea only: detect BTC/ETH leverage/deleveraging shocks on Binance and test whether FundedNext crypto CFDs react with a measurable lag.

This is a research event study, not a Guardian strategy and not `OI down = short`.

## Frozen campaign

Canonical preregistration:
`research/campaigns/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_LEADLAG_PREREGISTRATION_2026_09_05.md`

Prereg commit: `050506aff39a321195a70ec79ed0008a2b736d7d`.

Development data: 2024-01-01 through 2025-12-31 UTC, with 2023-11-01 warm-up.
Reserved untouched confirmation: 2026-01-01 through 2026-06-30. Do not touch confirmation unless development passes all gates and a new confirmation preregistration exists.

Source shock V0: BTCUSDT/ETHUSDT USD-M 5m return AND 5m `sum_open_interest` change both <= their strictly-prior rolling 30-day 10th percentiles and both negative; 30m source cooldown; BTC/ETH events within 5m merged.

Primary response: executable target CFD SHORT return at +15m, BID entry / ASK exit. Frozen diagnostics: +1/+5/+30/+60/+120m. Matched prior 60d same-slot control. No SL/TP/R invented.

## Prepared MT5 exporter

Repo file:
`research/ea/D035_CFD_M1_Exporter_v1_01.mq5`

Commit: `0e8f923d1ae7529af7999f9b6e37970133e0fb19`.
Local/user-delivered SHA-256: `2bd349d44845cbe726c154c5f419e2ec36763700dd245f2da6964bcb05342a96`.

QA performed before delivery:
- no orders / no Guardian;
- static braces/parens/brackets balanced;
- EVENTS header and data row both exactly 19 fields;
- immediate header flush plus periodic data flush;
- MetaEditor compile NOT claimed.

User run protocol: Strategy Tester M1 / 1 minute OHLC, 2023-11-01 through 2025-12-31, BTCUSD mandatory plus every crypto CFD available on the target FundedNext account, no inputs.

## Historical analyzer

User-delivered artifact:
`D035_Binance_Deleveraging_LeadLag_v1_00.py`
SHA-256: `fa22fa6a7fe735436b381ef2ec7a58f7aed8e71d526e2b679073a6981dfad133`.

The readable analyzer was delivered as a ChatGPT conversation artifact; the frozen implementation is fully specified by the preregistration if the local artifact is unavailable to Codex.

Analyzer behavior:
- downloads/caches official Binance Vision monthly 1m USD-M klines and daily OI metrics;
- no forward-fill of gaps;
- exact 5m construction;
- mechanical weekly server->UTC calibration from BTCUSD vs BTCUSDT returns;
- event/target joins and matched controls;
- day-cluster bootstrap;
- default hard-locks discovery to 2024-2025;
- explicit `--confirm` required to touch 2026.

QA performed:
- `python -m py_compile`: PASS;
- synthetic core smoke: PASS;
- synthetic smoke recovered an injected UTC+2 broker-server offset, generated causal source shocks, built target returns/controls and produced a verdict without errors.

## Locked development gates

All 8 required: >=80 merged source events; >=2 non-source targets with >=40 events; pooled +15m executable >=+15bps; +15m event-control diff >=+10bps; day-cluster bootstrap lower >0; +30m executable >0; BTC-only and ETH-only +15m diffs both >0; max positive-month contribution <=35%.

No same-sample rescue with alternative percentiles, horizons, target shortlist, liquidation/funding/basis filters, RSI/ATR, source-specific thresholds or direction inversion.

## Next safe action

1. User compiles/runs the D035 CFD exporter on BTCUSD plus all available FundedNext crypto CFDs over the frozen period.
2. Collect/zip all `D035_CFD_M1_*.csv` outputs.
3. Run the frozen Python analyzer on the local PC (or hand the exports to the research workflow) without `--confirm`.
4. Archive the complete D035 development verdict and update `CURRENT_PROJECT_HANDOFF.md`.

Existing Binance+Bybit EIB remains read-only infrastructure and is not changed by D035.