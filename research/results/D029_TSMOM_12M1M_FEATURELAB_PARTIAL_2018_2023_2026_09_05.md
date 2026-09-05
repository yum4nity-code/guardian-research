# D029 — TSMOM 12M/1M Feature-Lab — partial 2018-2023 result

Date: 2026-09-05
Status: PARTIAL / PRIMARY UNIVERSE INCOMPLETE
Classification: CLOSE_REPLICATION_CFD_TRANSFER

## Supplied runs
Received 10 symbols:
- Primary requested and present: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, NZDUSD
- Non-primary substitute/exploratory: USDCNH
- Crypto adaptations: BTCUSD, ETHUSD, DOGUSD

Missing from frozen primary 8-market universe:
- USDCAD
- XAUUSD

Therefore the preregistered full primary-universe verdict cannot yet be finalized.

## Available six-primary FX pool
Six correct primary FX pairs provide 432 resolved monthly events (72 each).

Pooled event-level means:
- executable directional return: +1.98 bps/event
- source-vol-scaled monthly return: +0.312%/event

Temporal halves:
- 2018-2020: +0.455% source-scaled/event
- 2021-2023: +0.168% source-scaled/event

Positive mean source-scaled markets among the six:
- EURUSD +0.501%
- GBPUSD +0.604%
- USDJPY +0.826%
- AUDUSD +0.550%
- NZDUSD +0.149%

Negative:
- USDCHF -0.760%

Equal-weight monthly six-market portfolio:
- mean monthly source-scaled return ~+0.312%
- annualized mean ~+3.74%
- annualized volatility ~27.50%
- annualized Sharpe ~0.136
- 6-month moving-block bootstrap 95% interval for monthly mean approximately [-1.10%, +1.86%]

Thus the crucial preregistered bootstrap-lower-bound >0 gate currently FAILS on the six available primary markets. However USDCAD and XAUUSD were frozen primary markets and are missing, so the complete eight-market verdict remains formally open.

## Exploratory USDCNH
USDCNH n=72, mean executable +5.51 bps, mean source-scaled +0.275%/month. This does not replace USDCAD in the preregistered primary universe.

## Crypto adaptations — discovery only
BTCUSD:
- n=66 (history/warm-up limits early months)
- mean executable +454.7 bps/month
- mean source-scaled +2.858%/month
- median source-scaled ~-0.042%
- 50% positive months
- yearly source-scaled means: 2018 +5.88%, 2019 -3.59%, 2020 +7.11%, 2021 +3.16%, 2022 +6.19%, 2023 -0.10%
- 6-month block-bootstrap 95% interval of mean source-scaled return crosses zero, approximately [-0.91%, +6.38%]

ETHUSD:
- n=62
- mean executable +425.9 bps/month
- mean source-scaled +1.779%/month
- median source-scaled +1.248%
- 53.2% positive months
- yearly source-scaled means: 2018 +10.67% (n=2), 2019 +0.13%, 2020 -0.84%, 2021 +7.18%, 2022 +1.37%, 2023 -0.43%
- 6-month block-bootstrap 95% interval crosses zero, approximately [-1.85%, +4.79%]

BTC+ETH overlapping equal-weight monthly source-scaled portfolio (62 months):
- mean +2.42%/month
- annualized Sharpe ~0.70
- negative mean years 2019 and 2023
- 6-month block-bootstrap lower bound remains below zero (~-1.31% monthly mean)

DOGUSD has only 15 resolved events and mean source-scaled return -1.04%/month; no useful evidence.

Interpretation: BTC/ETH are interesting adaptation clues but are not confirmed. Their positive means are unstable and bootstrap lower bounds cross zero. Any 2024-2026 confirmation must be separately frozen before inspection.

## Feature-lab diagnostic
D1 feature fields are largely populated and usable. Across the available FX markets there is no strong, consistent cross-market monotonic relationship between the logged D1 diagnostics (RSI14, ATR14, short/medium returns, realized vol, SMA distances, z20, 252d range position, previous-month range) and next-month TSMOM outcome. Do not mine thresholds from 2018-2023.

Data-quality warning: on several symbols/older intervals the exported H4 RSI14 and H4 ATR14 values are exactly identical to D1 values for long blocks of months, indicating a tester/history-timeframe issue. H4 diagnostic fields from this v1.00 must NOT be used for research conclusions. This does not alter the TSMOM signal/result because H4 fields never filter or size trades.

Future feature-lab scanners should reconstruct H4 features internally from lower-timeframe history or add explicit timeframe-independence QA before accepting them.

## Immediate next action
Complete the frozen primary D029 universe with USDCAD and XAUUSD using the same v1.00 scanner, same 2017 warm-up / 2018-2023 signal window. Do not substitute USDCNH for USDCAD.

After those two runs:
- finalize the eight-market source-like gate;
- if broad D029 still fails, close it without same-sample feature tuning;
- BTC/ETH may separately spawn a preregistered 2024-2026 adaptation confirmation if desired, but they remain too slow to be the sole challenge engine.
