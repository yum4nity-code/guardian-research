# Guardian v11.16.4 — FundedNext EA policy + final legacy cleanup

Date: 2026-09-01
Base: `Guardian_D017_PropFirmAuto_v11_16_3_CLEAN_MOMENTUM.mq5`
Output: `Guardian_D017_PropFirmAuto_v11_16_4_CLEAN_FUNDEDNEXT.mq5`

## FundedNext EA authorization

User confirmed directly with FundedNext that EA usage is allowed on Free Trial and wants EA permission explicitly allowed for all FundedNext programs.

Changes:
- removed `InpFundedNextEAUsageAuthorized` manual permission toggle;
- removed the hard block `FUNDEDNEXT FREE TRIAL: EA INTERDIT`;
- every resolved FundedNext profile is explicitly EA-authorized;
- a stale/incorrect PropFirmGuard runtime `ea_allowed=false` no longer blocks FundedNext EA execution;
- this override applies only to EA permission: risk, daily/overall drawdown, news restrictions and other compliance controls remain active;
- an unresolved prop-firm profile may still block auto-trading under `InpBlockAutoTradingOnUnknownPropProfile`, because that is a compliance-profile resolution issue, not an EA-permission issue.

## Final removal of legacy strategies

User confirmed there are no existing legacy auto positions.

Removed completely:
- Breakout/Pullback/Sweep enum entries;
- legacy Breakout/Pullback/Sweep exit constants;
- Sweep exit branch;
- Pullback TP1 branch;
- Breakout structural exit branch;
- legacy strategy parsing from position comments/state;
- `StrategyToString`, `GetPositionStrategy`, `StrategyBE_R`, `StrategyTrailATR`.

Auto position management is now Momentum-only. Momentum TP1/BE/trailing formulas are unchanged from v11.16.3.

## Preserved

- CAPREF fix from v11.16.2;
- Momentum entry logic and filters;
- Momentum TP1/BE/trailing parameters and behavior;
- manual Guardian management;
- PropFirmGuard risk/news/runtime infrastructure;
- FundedNext risk and news policies.

## Static checks

- removed-symbol scan: no legacy strategy references remain;
- delimiter balance: `{}`, `()`, `[]` all balanced;
- compile still required in MetaEditor.
