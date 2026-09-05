# D032-C1 Doji Star H1 confirmation — COMPLETE

Date: 2026-09-05
Status: PRIMARY CORE CONFIRMATION PASS / TRANSPORT LIMITED / SECONDARY MANAGEMENT FAIL

Canonical preregistration:
`research/campaigns/D032_C1_DOJI_STAR_H1_CONFIRMATION_PREREGISTRATION_2026_09_05.md`

Core verdict:
`research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`

Transport detail:
- LINK: `research/results/D032_C1_CONFIRM_LINK_TRANSPORT_2026_09_05.md` if present from prior session; LINK result is a transport fail.
- XRP: `research/results/D032_C1_CONFIRM_XRP_TRANSPORT_2026_09_05.md` — transport fail.
- ADA: external unregistered diagnostic only; also negative.

## Core confirmation
Frozen BTC/ETH/DOG cohort, clean pre-2024 events:
- BTC: n=33, +139.46 bps, +1.111R, 69.70% positive
- ETH: n=32, +76.43 bps, +0.043R, 62.50% positive
- DOG: n=14, +249.98 bps, +0.599R, 57.14% positive
- pooled: n=79, +133.52 bps/event, +0.588R/event, 64.56% positive
- pooled same-trend control: +32.13 bps
- Doji-control differential: +101.38 bps
- month-block bootstrap 95% interval for pooled mean: approximately +10.1 to +273.4 bps

All seven preregistered primary gates pass.

**Decision: ENTRY EDGE CONFIRMED on the frozen BTC/ETH/DOG CFD cohort.**

## Secondary management
Frozen -1R/+3R/24h management:
- pooled core mean +0.118R
- bootstrap lower bound <0
- gate FAIL
- M1 OHLC is not authoritative for intraminute first-touch ordering

**Decision: do not adopt -1R/+3R management. Preserve +24h as the confirmed reference exit.**

## Transport results
- LINK/LNK: clean n=28, mean -118.68 bps, -0.690R, 39.29% positive — FAIL.
- XRP: clean n=38, mean -200.11 bps, -0.535R, 47.37% positive; same-trend control +15.25 bps; Doji-control -215.35 bps — FAIL.
- ADA external diagnostic: clean n=16, mean -108.64 bps, -0.796R, 25% positive — FAIL.

Conclusion: the effect is market-specific, not a universal crypto candlestick rule.

## Execution/data limitations
- Pre-2024 FundedNext real ticks unavailable; runs used M1 `1 minute OHLC`.
- This is acceptable for the H1 signal / +24h primary endpoint, but not definitive for intraminute stop/target first-touch management.
- Explicit commission input was 0 bps/side; spread is embedded by ASK entry / BID exit. Cost stress remains required before production.
- Historical data quality is imperfect and varies by symbol; retain monitoring/robustness checks.

## Next actions
1. Freeze a separate management/production-construction experiment around the confirmed +24h reference; do not tune the Doji definition or trend filter on the confirmation sample.
2. Run explicit cost stress, overlap/correlation and portfolio-risk diagnostics on BTC/ETH/DOG.
3. Because cadence is low, continue independent research for a substantially more active challenge engine in parallel.
4. Only after standalone strategy construction passes should the Doji sleeve enter Guardian/prop-firm non-regression testing.
