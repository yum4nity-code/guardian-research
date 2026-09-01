# FUNDEDNEXT FREE TRIAL — EA OPTION-AWARE FIX

STATUS: `READY / FOCUSED_RUNTIME_FIX`
OWNER: Codex
URGENCY: high operational blocker, but keep the pass narrow to conserve remaining Codex quota.

## Why this exists

Guardian v11.16.2 currently cannot reliably authorize EA execution on the user's current FundedNext Free Trial account.

Observed runtime symptoms:
- FundedNext firm detected, but profile may resolve as `UNKNOWN` when the account/server text does not contain `TRIAL`.
- HUD then shows `OBSERVATION` and Guardian does not manage the manual trade / place its SL.
- Even when the profile is forced to `PFG_FUNDEDNEXT_FREE_TRIAL`, the current source has a hardcoded block in `ResolvePropFirmContext()`.
- `RefreshPropFirmRulesRuntime()` can independently re-block execution when `rules.json` provides `ea_allowed=false`.

Relevant current source behavior in v11.16.2:
- `if(g_prop_profile==PFG_FUNDEDNEXT_FREE_TRIAL) { g_prop_execution_authorized=false; ... }`
- then generic FundedNext `InpFundedNextEAUsageAuthorized` gate.
- runtime rules parser reads `ea_allowed` and can set `g_prop_execution_authorized=false` again.

## Official-rule nuance checked by ChatGPT on 2026-09-01

Do NOT waste Codex quota on broad web research. The official FundedNext sources are nuanced:

1. Generic Free Trial rules page (dated 2026-04-08) still says EAs are not permissible by default in Free Trial:
   https://help.fundednext.com/en/articles/8902893-fundednext-free-trial-rules

2. Current general FundedNext EA article says EAs/bots are allowed on MT4/MT5 with an additional EA usage fee:
   https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext

3. Current Stellar Instant EA article explicitly notes that for free/BOGO account types the EA option is not included by default, but the trader may add it by paying the additional EA fee, after which the selected option is activated on the account:
   https://help.fundednext.com/en/articles/11641338-can-i-use-an-ea-in-stellar-instant

The user states the current FundedNext Free Trial is officially EA-eligible/activated. Therefore Guardian must be **option-aware**, not blanket `FREE_TRIAL => deny` and not blanket `FREE_TRIAL => allow`.

## Required focused fix

At next GO, after harvesting any already-completed worker output and without launching duplicates:

1. Inspect the real local `FILE_COMMON/PropFirmGuard` state (`profiles.json`, `rules.json`, relevant account mapping/option state) and the currently compiled v11.16.2 source.
2. Fix FundedNext Free Trial authorization so that an account with the EA option explicitly enabled is authorized, while a Free Trial without confirmed EA entitlement remains blocked.
3. Prefer authoritative account-specific/runtime state when available:
   - `ea_allowed known=true` => authorize.
   - `ea_allowed known=false` => block.
   - unknown entitlement => fail closed unless an explicit FundedNext EA authorization flag/account mapping confirms it.
4. Do NOT globally force `InpPropProfileOverride=PFG_FUNDEDNEXT_FREE_TRIAL`; FTMO and other servers must keep auto-detection.
5. Ensure the current FundedNext Free Trial account resolves to the correct profile through a narrow account/runtime mapping if the server/account text alone cannot identify `TRIAL`.
6. Keep FTMO/The5ers behavior unchanged.
7. Runtime acceptance test on FundedNext: HUD must show the correct FundedNext Free Trial profile and `EA / execution : AUTORISEE`, then a manual Magic0 test trade must be adopted by Guardian and receive the expected SL. Do not use a live-risky trade solely for testing if an existing/demo-safe trade can verify the path.
8. Compile once and do one focused runtime smoke test. No long regression campaign, no broad source audit, no strategy retuning.

## Versioning / research isolation

This is a prop-firm runtime/compliance fix, not a Momentum semantic change.

- Keep the existing D017 v11.16.2 research campaign provenance intact; do not invalidate or rerun strategy research solely because of this runtime eligibility fix.
- If source must change, create a clearly new production candidate version (e.g. v11.16.3) rather than silently mutating the historical v11.16.2 file.
- Do not spend quota re-running historical EURUSD/GBPUSD research for this fix.

## Codex quota conservation directive

Remaining Codex allowance is scarce. Use this order:
1. HARVEST completed/running work first; never duplicate workers/imports.
2. Apply this FundedNext fix in one narrow pass; compile + one smoke test only.
3. Resume/launch only already-preregistered research that can run mostly unattended on MT5/MiMo.
4. Do not execute D024 yet (still blocked by prerequisites).
5. No broad audits, no refactors, no parameter searches, no OOS access, no repeated compile/test loops unless the first focused pass actually fails.
6. Before quota expires, checkpoint/push exact state so MT5/MiMo work can continue without another reasoning pass.
