# FundedNext / Guardian — server-request hyperactivity audit

Date: 2026-09-04
Status: **URGENT / REAL REQUEST-TRAFFIC RISK / ROOT CAUSE CANDIDATE IDENTIFIED**

## Trigger

User observed on live FundedNext Guardian HUD:

`Requêtes serveur : 5629/2000 (281.4%) | HARD LIMIT | PROTECTION ONLY`

## What the Guardian counter actually counts

The request-budget implementation introduced in v11.16.17 is account-wide, shared across Guardian instances for the same login/profile/day via MT5 Global Variables.

It is **not** a market-data/read counter and it is **not** affected by Shared Intelligence FILE_COMMON reads. It increments for Guardian-side outgoing CTrade requests and also deduplicated observed manual Magic-0 entries. Reservations happen **before** the CTrade send, therefore broker-rejected attempts remain counted.

It is still not FundedNext's proprietary server-side counter, so exact equality with FundedNext's internal total cannot be claimed.

## Why the value can keep rising after 2000

`ServerRequestPriorityAllowed()` deliberately never blocks `SRP_EMERGENCY` or `SRP_PROTECTION`. `ServerRequestTryConsumeN()` still increments the shared counter for those priorities. Therefore `HARD LIMIT / PROTECTION ONLY` blocks discretionary/new-risk traffic but does **not** mean zero further server traffic.

This architecture explains how a HUD can move from 2000 to 5629 while remaining in `PROTECTION ONLY`: protection/emergency requests and observed manual entries can continue to add to the count.

## Likely spam path found

A concrete high-risk retry path exists in the RSI lifecycle:

- after TP1, if BE NET is not yet successfully pushed, `RSIManageCycleTick()` evaluates `RSI_BE_RETRY` on every tick;
- if the desired stop is valid, it calls `RSIApplyCommonStop(..., SRP_PROTECTION, "RSI_BE_RETRY")`;
- `SRP_PROTECTION` bypasses the hard request budget;
- `RSIApplyCommonStop()` pre-reserves one request per eligible RSI leg, then sends `PositionModify()` for each leg;
- if modification fails, `g_rsi_be_push_done` remains false, so the same logic can retry on the next tick;
- there is no dedicated retry cadence/backoff visible on this BE-retry branch.

This is a plausible mechanism for hundreds or thousands of server messages during a persistent broker-side rejection/invalid execution condition.

By contrast, RSI runner trailing is lower priority and cadence-throttled, and discretionary RSI/Momentum traffic is progressively blocked before 2000. Momentum BE has a market-closed backoff on failure. Shared Intelligence is read-only and cannot generate broker requests.

## FundedNext rule checked 2026-09-04

FundedNext's current Help Center defines hyperactivity at **200 trades or 2,000 server messages in one day**, including frequent order modifications such as SL/TP and limit-order changes. First and second occurrences trigger warnings; a third occurrence breaches the account. A day with 15,000 messages can be force-disabled, and warnings can be skipped for extreme activity causing substantial server load.

## Immediate operational conclusion

- Treat 5629 as a serious Guardian-side warning, although it cannot be equated exactly to FundedNext's proprietary server count.
- Keep Algo Trading disabled on the FundedNext terminal until the request retry paths are patched and validated.
- Do **not** stop the Binance/Bybit Shared Intelligence collector for this reason; it is independent and read-only with respect to the broker.
- Do not cosmetically reset or lower the Guardian counter to hide the problem.

## Required code remediation

1. Add deduplication/cadence/backoff to `RSI_BE_RETRY` so a failed protective modification cannot resend on every tick.
2. Apply the same audit to every `SRP_PROTECTION` and `SRP_EMERGENCY` path because those priorities are intentionally allowed beyond the hard limit.
3. Preserve genuine safety authority, but make repeated identical protection requests state-aware and rate-limited.
4. Validate with a low request-limit override in a controlled environment before FundedNext live reactivation.
5. Keep the account-wide persistent counter and pre-send reservation semantics; the defect is retry traffic, not the existence of the counter.

## Evidence used

- `GUARDIAN_V11_16_17_REQUEST_BUDGET_RSI_MODE_MARGIN_AUDIT_2026_09_03.md`
- `Guardian_D017_PropFirmAuto_v11_17_05_SHARED_INTEL_OBSERVER_CANDIDATE.mq5`
- `GUARDIAN_V11_17_06_MULTIVENUE_INTEL_OBSERVER_STATIC_AUDIT_2026_09_04.md`
- FundedNext Help Center, Restricted/Prohibited Trading Strategies, checked 2026-09-04.
