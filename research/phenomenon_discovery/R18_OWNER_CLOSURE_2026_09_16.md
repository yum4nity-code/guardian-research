# R18 owner closure — 2026-09-16

## Status

R18 XAUUSD volatility-shock mean reversion remains a statistically confirmed historical phenomenon under the frozen R16-R20 study, but it is **not promoted as a Guardian/EA production candidate**.

Canonical repository evidence already established:
- discovery PASS;
- independent confirmation PASS;
- economic gate only reached an interim state because the available spread/slippage budget was very small;
- the repository contains an observation logger and an EA MVP, neither of which constituted production approval.

The owner subsequently confirmed that R18 was retested and did not produce a sufficiently useful exploitable result. That later retest was not canonically reflected in the autonomous control-plane/status artifacts, which is why stale status could still make R18 look active.

## Decision

- R18 scientific phenomenon: **CLOSED / CONFIRMED PHENOMENON**.
- R18 executable edge / EA candidate: **NOT PROMOTED**.
- R18 Guardian integration: **NOT AUTHORIZED**.
- R18 live/real deployment: **PROHIBITED**.
- Do not reopen R18 by tuning the shock threshold, lookback, direction, horizon, session, overlap handling, SL/TP, or costs after seeing the prior results.
- A future R18-inspired study must be a separately preregistered hypothesis with a new identifier.

## Control-plane consequence

Any autonomous queue/status record that still presents R18 as an active production candidate is stale and must be superseded rather than resumed.
