# D017 BTC SELL Momentum +2.5R — FTMO Fresh-2023 / Transport-2024-2025

Date: 2026-09-23
Status: FROZEN BEFORE FTMO 2023 OUTCOME

## Preserved branch

Frozen source:
- research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5
- BTCUSD only
- SELL only
- target = +2.5R
- structural stop = frozen D017 v11.16 Momentum stop
- no threshold changes

Existing seen evidence:
- 2024 BTC SELL n=359, EV2.5 about +0.150R
- 2025 BTC SELL n=402, EV2.5 about +0.114R
- pooled n=761, EV2.5 about +0.131R before full costs

The +2.5R endpoint is frozen because it was one of the predeclared D017 diagnostic endpoints and showed the most stable 2024/2025 SELL result. This is a prospective hypothesis selection, not independent evidence by itself.

## Evidence split

FTMO 2023:
- fresh temporal test for the frozen SELL +2.5R branch

FTMO 2024-2025:
- feed transport / replication only because those years informed branch selection

2026:
- hard blocked

## Frozen signal

Use the D017 v11.16 Momentum signal exactly as encoded in the static-conformance diagnostic:
- setup M5, macro H1
- H1 EMA200 direction and normalized slope
- M5 ATR14 / ADX14 trend regime
- crypto shock state must be NORMAL
- setup EMA50 extension block
- ATR quality gate
- 72-bar Donchian anti-breakout
- bearish momentum candle logic
- crypto EMA50 direction confirmation
- structural SL +0.25 ATR buffer, floor 1.25 ATR, cap 3.5 ATR
- spread <=12% of SL-distance gate

Only SELL events are evaluated for the branch. BUY outcomes are retained only as telemetry and cannot rescue the SELL verdict.

## Endpoint

First-touch:
- target = +2.5R
- stop = original structural -1R
- maximum observation = 48h
- same-M1 target/stop ambiguity excluded
- unresolved events reported separately
- EV = mean(+2.5R target-first, -1R stop-first) over resolved non-ambiguous SELL events

## Tester

- exact currently connected FTMO terminal/account
- BTCUSD alias resolved from that terminal
- 2023-01-01 through 2025-12-31
- M1 chart
- 1 minute OHLC first-stage model

The signal itself is M5/H1 closed-bar logic. M1 path telemetry is sufficient for this first-stage target/stop validation with same-M1 ambiguity exclusions. If the branch survives, exact real-tick BID/ASK + commission/slippage is a separate production-readiness audit.

## V2 fresh-2023 label

- NEGATIVE if EV <= 0
- SPARSE_POSITIVE if EV > 0 but resolved n < 50
- POSITIVE_CONFIRMED if resolved n >= 50, EV > 0 and month-block q10 > 0
- POSITIVE_UNCERTAIN otherwise when EV > 0

## Execution caveat

The virtual diagnostic entry uses BID for SELL and M1 bar highs/lows for path telemetry. That is not an exact historical ASK-side short exit/stop simulation.

Therefore:
- fresh 2023 can establish signal/path existence;
- production readiness requires later exact real-tick BID/ASK + commission audit;
- no production claim is allowed from this stage alone.

## Firewalls

- 2026 blocked
- no BUY rescue
- no target sweep
- no threshold retuning
- no alternate market
- no manager substitution
