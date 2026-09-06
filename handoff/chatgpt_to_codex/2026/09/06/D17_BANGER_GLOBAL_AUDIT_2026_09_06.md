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

3. There is a **production-line provenance gap** in GitHub. `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md` and `production/guardian/GUARDIAN_V11_16_11_STRATEGY_SWITCHES_NOTES.md` identify `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5` as the expected/current baseline and record its local SHA256, but that source is not present under `production/guardian/` on the current default branch. The candidate folder contains v11.16.1 RISKFIX and v11.16 MOMENTUM_PROD only. The exact live/local D17 source therefore still has to be reconciled before calling any attribution `EXACT SOURCE-BEHAVIOR`.

4. `CURRENT_PROJECT_HANDOFF.md` claims a Pure Guardian Core v12.01 candidate (`Guardian_Core_Base_v12_01_CANDIDATE.mq5`) plus `GuardianCore/Guardian_StrategyRegistry_v1.mqh` and template, but those paths were not found on the current default branch during this audit. Treat Core v12.01 as **local/unpublished until proven otherwise**; do not claim repo-backed compile/non-regression from it.

5. Governance files are desynchronized: `CURRENT_PROJECT_HANDOFF.md` (2026-09-06) correctly makes D17 lineage/native attribution P0, while `CURRENT_QUEUE.json` is still dated 2026-09-05 and names D023 London ORB as `active_primary`. `docs/RESEARCH_STATUS.md` and `docs/STRATEGY_DECISIONS.md` are also behind the Sep-6 state. This can send a future `GO` down the wrong branch.

6. External check supports the Deribit hypothesis as a legitimate research candidate, not production evidence. The 2026 Finance Research Letters paper exists and reports the option-expiry reversal, high ATM-OI concentration, 2021-01-01 through 2023-12-31 sample of 1,059 expiry days, ATM within ±2.5% at 07:00, and after-cost annualized Sharpe 0.92 for the 08:00 switch. There remains a source-text inconsistency: narrative says the post-expiry long closes at 09:00 while the Table 6 caption says 10:00. Keep our first target-CFD implementation labelled `ADAPTATION`; do not choose 09:00 vs 10:00 post hoc based on performance.

## PREUVE

- `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5`
- `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md`
- `production/guardian/GUARDIAN_V11_16_11_STRATEGY_SWITCHES_NOTES.md`
- `CURRENT_PROJECT_HANDOFF.md`
- `CURRENT_QUEUE.json`
- `research/results/GUARDIAN_BANGER_LAB_V1_2026_09_06.md`
- External primary article: Weiss, Gaudiosi, Zhou & Webb (2026), *Bitcoin option expiration, gamma exposure, and intraday price reversals*, Finance Research Letters 107, 110340, DOI 10.1016/j.frl.2026.110340.
- Deribit settlement documentation: expiry at 08:00 UTC; final delivery-price TWAP 07:30–08:00 UTC.

## IMPACT

- The scientific direction remains **attribution before more strategy hunting**.
- A D17 attribution run launched before exact live/source lineage reconciliation could answer the wrong question.
- A `TIMEBOX=60m` implementation would be a newly invented manager, not a native D17 counterfactual.
- Missing production/Core artifacts weaken reproducibility and make future non-regression claims unsafe.
- Stale queue/status files create agent-coordination risk even though the current handoff is correct.

## ACTION_CODEX

1. On the local PC/MT5, identify the EA actually attached to the FTMO D17 charts/account and recover the exact source if available; record filename, SHA256, relevant preset/inputs and, if only EX5 is available, the strongest available binary/runtime identity evidence.
2. Compare that live/local branch against GitHub `MOMENTUM_PROD` and the documented v11.16.11 lineage. Establish whether entry selection + manager semantics match before running attribution.
3. Correct/preregister the third D17 counterfactual **before results are opened**. Preferred options:
   - if the reconciled live source has no active time-stop, replace `TIMEBOX` with a clearly exogenous frozen horizon justified independently and label it as such; or
   - omit TIMEBOX V0 and compare NATIVE vs FIXED-3R plus raw path diagnostics. Do not resurrect the inactive 60-minute legacy constant as if native.
4. Preserve exact native trail cadence/ratchet semantics in the attribution implementation, including setup-bar gating and true-net BE.
5. Locate and push the exact v11.16.11/live production source if permitted/available, or explicitly record why it cannot be repository-backed.
6. Locate and push the claimed Pure Guardian Core v12.01 + `GuardianCore` socket/template, or change the handoff status to `LOCAL ONLY / NOT IN REPO` until they are committed.
7. Reconcile `CURRENT_QUEUE.json`, `docs/RESEARCH_STATUS.md`, and `docs/STRATEGY_DECISIONS.md` with the Sep-6 handoff before executing an old queued research family.
8. Start/continue the Deribit read-only forward observer only after a live network smoke on the local machine; preserve the 09:00/10:00 source discrepancy as a preregistration issue, not a tunable exit.

## NE_PAS_FAIRE

- Do not tune `2R/25%`, `1.25R` or `1.75 ATR` on inspected D17 samples.
- Do not run the v11.16.19 META-A1 long test merely because the old handoff once called it authoritative.
- Do not implement `TIMEBOX=60m` as "native" while `InpEnableStrategyTimeStop=false`.
- Do not treat the user's live observation that the ratchet behaves well as statistical validation.
- Do not promote USDJPY ORB without untouched confirmation.
- Do not call Deribit 0DTE validated on FTMO/FundedNext before provenance-clean historical replication and target-CFD bid/ask/cost transfer.
