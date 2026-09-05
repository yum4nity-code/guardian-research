# D032-C1 Doji Star H1 — core confirmation complete

Date: 2026-09-05
Status: PRIMARY CONFIRMATION PASS / SECONDARY MANAGEMENT NOT CONFIRMED

Canonical result:
`research/results/D032_C1_DOJI_STAR_H1_CORE_CONFIRMATION_VERDICT_2026_09_05.md`

Preregistration:
`research/campaigns/D032_C1_DOJI_STAR_H1_CONFIRMATION_PREREGISTRATION_2026_09_05.md`

## Core confirmation
Pre-2024 confirmation, primary BTC/ETH/DOG cohort, clean n=79.

Aggregate executable +24h result:
- mean +133.52 bps/event
- median +93.43 bps
- win rate 64.56%
- mean +0.588R/event
- same-trend control mean +32.13 bps
- Doji-control differential +101.38 bps
- month-block bootstrap 95% lower bound ~+10.1 bps

All seven preregistered primary gates pass. Entry edge is confirmed under D032-C1, with caveats for historical bar quality, zero explicit commission input, and imperfect symbol/time uniformity.

Per core symbol:
- BTC: clean n=33, +139.46 bps, +1.111R, 69.7% positive
- ETH: clean n=32, +76.43 bps, +0.043R, 62.5% positive; 2022/2023 means negative, so note regime weakness
- DOG: clean n=14, +249.98 bps, +0.599R, 57.1% positive; broker history begins 2021-09-24

## Secondary management
Frozen `-1R stop / +3R target / else 24h` does not pass:
- pooled mean +0.118R/event (< +0.15R gate)
- month-block bootstrap lower bound negative (~-0.274R)
- generated M1 OHLC is not definitive for intraminute first-touch ordering

Do not use this management rule as validated production management.

## Transport
An additional ADAUSD run is a strong negative counterexample (clean n=16, mean -108.64 bps, -0.796R, 25% positive). ADA was not preregistered and must not alter the formal core gate. LINK/XRP confirmation may still be run as transport diagnostics only.

## Next research order
1. Finish LINK/XRP transport confirmations if user provides them; do not reopen the core gate.
2. Preserve Doji H1 +24h as the confirmed reference entry/exit benchmark.
3. Explicitly cost-stress and measure portfolio overlap/frequency before Guardian integration.
4. Management redesign must be a new frozen hypothesis and validated on untouched/future or independent feed data.
5. Continue D033 commodity setup research and prioritize a materially more active engine for challenge speed; Doji frequency is too low to be the sole challenge engine.
6. Guardian full-chassis integration only after standalone strategy/management and cost evidence is sufficient.
