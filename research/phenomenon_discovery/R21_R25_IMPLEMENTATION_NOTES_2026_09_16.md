# SUPERSEDED — INDEPENDENT COLD AUDIT FAIL

The v1.00 implementation documented below failed independent cold audit at commit `f0213f86dc74a2e2955224143d2b1405b969efa9` and MUST NOT be executed or used for scientific inference. See `R21_R25_COLD_AUDIT_FAIL_AND_V101_FIXES_2026_09_16.md` and the v1.01 files for the corrective candidate. Generation 81 is archived and disabled.

---

# R21-R25 implementation notes — v1.00 candidate — 2026-09-16

This document records implementation choices for the already-preregistered `R21_R25_XAU_RESEARCH_PLAN_2026_09_14.md`. It does not change scientific hypotheses.

## Safety / stage locks

- Discovery ends 2019-06-30.
- Confirmation is 2019-07-01 through 2024-12-31.
- 2025 pre-OOS is deliberately **not executable in v1.00**. A later explicit version/authorization is required after confirmation and economics.
- Any 2026+ input row hard-fails before stage filtering.
- No PnL, sizing, SL, TP, trailing, parameter search or live order logic exists in this engine.

## Shared implementation

- Input uses the canonical XAUUSD M5 contract already used by R16-R20.
- A new stage-slice builder reads the immutable R15 master payload index but opens only payload dates inside the requested scientific window.
- Forward returns require exact contiguous 300-second M5 spacing.
- Outputs contain event-level data, naive statistics, day-clustered intercept-only CR1 t-statistics, and yearly sign summaries.
- New York anchors use IANA `America/New_York` and are DST-aware.

## R21

- Anchor is the M5 bar timestamped 08:20 New York.
- Primary response is close-to-close return from the 08:20 anchor close to three M5 bars later.
- 30/60/120 minute responses are descriptive only.

## R22

- Event-bar volatility is the sample stdev of the 48 contiguous close-to-close M5 returns strictly before the event bar.
- The current event-bar return is excluded.
- Percentiles use valid prior-48 statistics from the previous 20 available UTC trading/data days, excluding the current day.
- Bottom-10% and bottom-20% states are sampled independently: first qualifying observation per UTC hour for each state.
- Same-clock baseline is mean absolute forward return at the same UTC minute-of-day and horizon within the current scientific stage.
- Bottom-10% and bottom-20% inference is reported separately, never pooled.
- If R22 survives discovery, the independent reviewer must explicitly freeze how the discovery baseline is carried into confirmation before confirmation is opened.

## R23

- Pre-NY move is close-to-close from 00:00 UTC on the anchor UTC date to the 08:20 New York close.
- Zero pre-NY moves are excluded because direction is undefined.
- 30m and 60m continuation/reversal are primary; 15m/120m remain descriptive.

## R24

- Opening range is exactly the 08:20, 08:25 and 08:30 New York M5 bars and completes at 08:35.
- Breakout search begins at 08:35 and ends at 10:00 New York inclusive.
- First M5 close strictly outside the range is the single daily event.

## R25

- Previous close is the final observed M5 close of the previous available UTC trading/data day.
- Gap direction is sign(anchor close / previous close - 1).
- `toward_*` means movement toward the previous close; `away_*` means gap continuation.
- Fill/crossing flags are descriptive only.

## Current verification

- Python bytecode compilation: PASS.
- Synthetic R21-R25 implementation test suite: PASS.
- Synthetic stage-sliced M5 builder test suite: PASS, including proof that an out-of-stage 2025 payload is not opened.
- Required independent cold audit by a separate reviewer: **PENDING**.
- Real historical discovery execution: **NOT RUN**.
- 2025: **NOT OPENED**.
- 2026+: **NOT OPENED**.
