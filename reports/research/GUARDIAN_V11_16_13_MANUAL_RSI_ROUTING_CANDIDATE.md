# Guardian v11.16.13 — MANUAL RSI ROUTING candidate

Status: **CANDIDATE — compile + live validation required before production**.

Base: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5`.

Candidate artifact: `Guardian_D017_PropFirmAuto_v11_16_13_MANUAL_RSI_ROUTING.mq5`

SHA256 candidate source: `822f87eedb741714709125bc0d308fa1e554eab3e5144e966436893fff3ee660`

## Corrective scope

- Manual `Magic=0` entries are no longer RSI-evaluated by the account-wide MANUAL OWNER when that owner is attached to another symbol.
- The live Guardian owner of the **traded symbol** receives priority and evaluates adoption with that symbol's own RSI M1 / ATR / RSI cycle state.
- A valid manual BUY under RSI30 becomes `M-BUY1` and enters the existing full RSI lifecycle: optional BUY2 LAST, RSI50 TP1, BE/trailing, RSI70 TP2, runner, persistent recovery.
- If RSI adoption is not applicable, standard MANUAL management remains the fallback.
- If no live Guardian exists for the traded symbol, the account-wide MANUAL OWNER keeps immediate manual protection.
- Manual exits remain centralized by the MANUAL OWNER to avoid duplicate close processing/notifications.

## Consecutive-loss cooldown

- `InpConsecutiveLossCooldown=0` by default.
- OFF now means genuinely OFF in both Momentum and RSI entry gates.
- Persisted account/crypto cooldown Global Variables are reset/ignored when the input is 0.

## Explicitly NOT changed

No RSI threshold, BUY1/BUY2 rule, RSI stop distance, risk allocation, RSI TP, or Momentum strategy rule was changed.

The idea `wider BUY1 SL + smaller volume at constant dollar risk` remains a later A/B research experiment and is not part of this corrective candidate.

## Expected live validation

With Guardian running on USDJPY and another chart potentially holding the MANUAL OWNER, a manual USDJPY BUY while RSI M1 <30 should produce `RSI_MANUAL_ADOPTED ... M-BUY1` on USDJPY followed by `MANUAL_RSI_ROUTE ... M-BUY1 adopte | gestion RSI complete ACTIVE`. The position must then be excluded from classic MANUAL TP/BE logic and remain eligible for BUY2/RSI exits.

Static check performed: diff reviewed and `{}`, `()`, `[]` balanced. No MetaEditor compiler is available in the assistant environment, so local MT5 compilation is required before live use.
