# D17 / Banger Lab — global audit 2026-09-06

STATUT: ACTION_REQUISE

## CONSTAT

1. **D17 Native Ratchet remains the correct P0**, but Banger Lab V1 contains one material ambiguity that must be corrected before the attribution run: the `TIMEBOX` counterfactual is described as closing at the native trade's maximum lifecycle/time boundary, while the GitHub `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` source explicitly has `InpEnableStrategyTimeStop=false`; its `InpMomentumMaxMinutes=60` and `InpMomentumMinProgressR=0.40` are marked legacy/inactive. Do not silently use 60 minutes as a native D17 exit.

2. Direct source audit confirms the Momentum manager values currently documented in the handoff:
   - TP1 `2.00R`, close `25%`;
   - true-net BE trigger `1.25R`;
   - ATR trail `1.75`;
   - trail only modifies the SL when the candidate improves the existing SL and is broker-valid;
   - trail updates are gated by the setup bar (`GetProfileSetupTF("PORTFOLIO")`), not continuously on every tick.

3. The user supplied the exact EA currently used on FTMO: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5` (source header reports property version `11.17`). It contains exactly two embedded auto-strategy enums, Momentum and RSI Sniper. Treat this uploaded source as the current live-reference source for lineage reconciliation; do not infer live authority from v11.16.19 merely because it is later.

4. There remains a **production-line provenance gap** in GitHub. `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md` and `production/guardian/GUARDIAN_V11_16_11_STRATEGY_SWITCHES_NOTES.md` identify `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5` as an earlier baseline, but that source is not present under `production/guardian/` on the current default branch. Reconcile the newly supplied live source against GitHub `MOMENTUM_PROD` and the documented v11.16.11 branch before calling the attribution `EXACT SOURCE-BEHAVIOR`.

5. **Correction to the earlier audit:** Pure Guardian Core v12.01 was recovered from the user's ChatGPT file library. The recovered `Guardian_Core_Base_v12_01_CANDIDATE.mq5` has SHA256 `6a74d4187e04a02f9924c48ef34a1f0eb946da0f64d66a4839701154d6ad1176`, exactly matching `CURRENT_PROJECT_HANDOFF.md`. It is a 1,700-line strategy-neutral core with no embedded RSI/Momentum. A compile pack has been prepared with an empty `GuardianCore/Guardian_StrategyRegistry_v1.mqh` and a module template. Static delimiter/hook/no-embedded-strategy checks pass. **MetaEditor compile remains pending user validation.** Do not call it production-validated or push it as canonical until the user reports the compile result; after successful compile, archive the exact source + companion files and hashes in GitHub.

6. Governance files were desynchronized; `CURRENT_QUEUE.json` has now been corrected to make `D017-NATIVE-RATCHET-LINEAGE-ATTRIBUTION` the active P0. `docs/RESEARCH_STATUS.md` and `docs/STRATEGY_DECISIONS.md` still need Sep-6 reconciliation when Codex resumes.

7. External check supports the Deribit hypothesis as a legitimate research candidate, not production evidence. The 2026 Finance Research Letters paper exists and reports the option-expiry reversal, high ATM-OI concentration, 2021-01-01 through 2023-12-31 sample of 1,059 expiry days, ATM within ±2.5% at 07:00, and after-cost annualized Sharpe 0.92 for the 08:00 switch. There remains a source-text inconsistency: narrative says the post-expiry long closes at 09:00 while the Table 6 caption says 10:00. Keep our first target-CFD implementation labelled `ADAPTATION`; do not choose 09:00 vs 10:00 post hoc based on performance.

## IMPACT

- The scientific direction remains **attribution before more strategy hunting**.
- A D17 attribution run launched before exact live/source lineage reconciliation could answer the wrong question.
- A `TIMEBOX=60m` implementation would be a newly invented manager, not a native D17 counterfactual.
- Core v12.01 provenance is now recovered and hash-matched, but compile validation and GitHub archival are still pending.
- Stale status/decision files remain an agent-coordination risk even though the current queue/handoff point to the right P0.

## ACTION_CODEX

1. When quota returns, use the newly supplied live FTMO source as the primary runtime/source reference and record its exact local filename/SHA256/preset/inputs where available.
2. Compare that live branch against GitHub `MOMENTUM_PROD` and the documented v11.16.11 lineage. Establish whether entry selection + manager semantics match before running attribution.
3. Correct/preregister the third D17 counterfactual **before results are opened**. Preferred: omit TIMEBOX V0 and compare NATIVE vs FIXED-3R plus raw path diagnostics, unless an independently justified exogenous horizon is preregistered. Never resurrect the inactive 60-minute constant as native.
4. Preserve exact native trail cadence/ratchet semantics in the attribution implementation, including setup-bar gating and true-net BE.
5. After the user reports MetaEditor compile success for Core v12.01, archive `Guardian_Core_Base_v12_01_CANDIDATE.mq5`, the empty registry and template on GitHub with their hashes and update the handoff to COMPILE PASS / smoke pending.
6. Reconcile `docs/RESEARCH_STATUS.md` and `docs/STRATEGY_DECISIONS.md` with the Sep-6 handoff before executing an old research family.
7. Start/continue the Deribit read-only forward observer only after a live network smoke on the local machine; preserve the 09:00/10:00 source discrepancy as a preregistration issue, not a tunable exit.

## NE_PAS_FAIRE

- Do not tune `2R/25%`, `1.25R` or `1.75 ATR` on inspected D17 samples.
- Do not run the v11.16.19 META-A1 long test merely because the old handoff once called it authoritative.
- Do not implement `TIMEBOX=60m` as "native" while `InpEnableStrategyTimeStop=false`.
- Do not treat the user's live observation that the ratchet behaves well as statistical validation.
- Do not replace the live FTMO two-strategy EA with the pure Core merely for compile validation.
- Do not promote USDJPY ORB without untouched confirmation.
- Do not call Deribit 0DTE validated on FTMO/FundedNext before provenance-clean historical replication and target-CFD bid/ask/cost transfer.
