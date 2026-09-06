# D023 USDJPY London ORB — FundedNext conformance + untouched confirmation lock

Date: 2026-09-06
Status: PREREGISTERED / WAITING MT5 CONTROL

## Why this branch exists

The broad four-market D023 V0 failed its original multi-market gate, but USDJPY was the strongest independent clue: n=489, gross mean about +0.1499R/trade and approximate commission-adjusted mean about +0.1179R/trade, positive in 2024, 2025 and pre-OOS 2026.

The user clarified on 2026-09-06 that the MT5 account/feed used for current research runs is FundedNext, not FTMO. Therefore all new D023 transport/conformance controls must use FundedNext server-clock and commission semantics.

## Frozen signal — NO CHANGES

Timeframe M15. Europe/London local clock.

1. Opening range = high/low of exactly four M15 bars 08:00 inclusive to 09:00 exclusive London.
2. First M15 close strictly above OR high or below OR low from 09:00 inclusive to 11:00 exclusive.
3. Entry = next M15 bar open on executable side of observed spread.
4. Stop = opposite edge of opening range.
5. No take-profit in original V0.
6. Exit = stop or final M15 close ending at 16:00 London, whichever comes first.
7. Max one trade per symbol/day; no reversal after first breakout.
8. No EMA, RSI, ATR filter, day-of-week filter, range-size filter, news filter or direction bias.

## FundedNext clock conformance

FundedNext server is GMT+2 outside US daylight-saving time and GMT+3 during US DST. London is UTC/UTC+1 on UK DST. Therefore broker->London conversion cannot be a fixed server-minus-two-hours transform during the US/UK DST gap weeks.

Prepared control EA:
`D023_USDJPY_LondonORB_M15_v1_04_FUNDEDNEXT_CONFORMANCE_20260906.mq5`
SHA256 `ebe7d0ce492550410d57ad62cc9de425005dfd393ae0f2ae884c2721c7fd40da`

No strategy changes vs D023 v1.02. Changes are clock/cost conformance and isolated CSV naming only.

## FundedNext cost model

Forex commission is model-selectable in the diagnostic:
- Stellar 1-Step / 2-Step: USD 5 per lot per side.
- Stellar Instant: USD 7 per lot per side.
- Stellar Lite: USD 7 per lot per side.

Observed historical spread remains in executable entry/exit pricing.

## Stage A — inspected-period conformance control

Run USDJPY M15 on FundedNext feed, Every tick, 2024-01-02 through 2026-06-26, using the correct FundedNext account-model commission.

Purpose only: determine whether the old USDJPY clue survives corrected London clock + FundedNext costs. This is not a new discovery sample and cannot be used as untouched confirmation.

If the corrected net result is non-positive or materially unstable, stop and reject the branch.

## Stage B — manager development on ALREADY INSPECTED data

Only if Stage A preserves a meaningful positive clue.

Use 2024-2025 only for a small, preregistered manager comparison on identical ORB entries. Do not change entry rules. Candidate management families may include the original 16:00 exit, simple fixed-R exits, and the existing Guardian ratchet geometry. Any exact manager grid must be frozen before execution.

Goal: choose at most ONE candidate manager for confirmation, based on robustness rather than best in-sample point estimate.

## Stage C — untouched 2023 confirmation

2023 USDJPY remains sealed until Stage A and any authorized Stage B manager choice are complete.

Frozen confirmation period: 2023-01-02 through 2023-12-29.

Original ORB confirmation gates:
- n >= 150;
- mean net R > 0;
- net PF >= 1.10;
- one-sided 5% moving-block-bootstrap lower bound of daily mean R > 0;
- positive under 1.5x execution-cost stress.

If a manager candidate was selected in Stage B before opening 2023, evaluate it on the same untouched 2023 entries alongside original ORB. Do not select or retune a different manager after seeing 2023.

## Research rule

Manager tuning is allowed. Validation circularity is not. The purpose is not to wait for a perfect strategy with a frozen manager forever; it is to develop management on inspected data and then demand a separate untouched confirmation.
