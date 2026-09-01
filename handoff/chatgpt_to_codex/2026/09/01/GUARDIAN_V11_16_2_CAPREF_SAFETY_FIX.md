# Guardian v11.16.2 — CAPREF safety fix

STATUT: CONFIRMED / READY_FOR_CODEX

A live FTMO 100k run of v11.16.1 RISKFIX exposed a second safety divergence: the HUD showed `Capital Référence : 10000 $` and an absurd daily remaining margin >90k on a 100k account.

Root causes found in source:
1. `InpInitialCapitalOverride` could force stale template values in live because `DetectInitialCapitalRobust()` returned the override before auto-detection.
2. Daily-reference reconstruction subtracted all history deals, including BALANCE/CREDIT style account-funding operations; this could reconstruct an impossible ~10k daily reference on a new 100k account.
3. A bad same-day daily reference could persist in account GlobalVariables until the day changed.

ChatGPT repaired this directly in:
`Guardian_D017_PropFirmAuto_v11_16_2_RISKFIX_CAPREF.mq5`
SHA256: `7194e569eeb170358566228431b82c52bfeec5069b3fa10043345f5fb8c1c4c3`
internal version: `11.162`.

Changes only:
- live ignores `InpInitialCapitalOverride`; override remains tester-only;
- invalid live account balance/equity no longer silently falls back to 10k;
- daily-reference reconstruction counts BUY/SELL trading deals only, not BALANCE/CREDIT account-funding operations;
- same-day stored daily reference <50% of detected base capital is automatically rebuilt/repaired and persisted;
- startup diagnostic logs `CAPITAL_REFERENCE_AUTO ... detected=...`;
- existing 0.25% minimum-risk self-test remains: 10k=25 USD, 100k=250 USD.

USER RUNTIME CONFIRMATION 2026-09-01:
- v11.16.2 was compiled/loaded on the new FTMO Demo 100k account;
- user confirmed the corrected runtime now works and the 100k capital/daily-risk display is coherent;
- candidate file has also been placed under `D:\MT5_Backtests\ProductionCandidates\Guardian_D017_PropFirmAuto_v11_16_2_RISKFIX_CAPREF.mq5` for Codex/workers.

Codex instruction at next GO:
- consume this note and treat v11.16.2 CAPREF as the current candidate; v11.16.1 is superseded and must not be used for strategy tests;
- inspect real worker/import state first and do not duplicate anything already active/completed;
- if worker-side compile of v11.16.2 is needed, perform only the normal compile/sanity check; no long repair/audit gate;
- then resume the authorized frozen pre-OOS generalization on AUDUSD, EURJPY, NZDUSD, USDCAD, USDCHF and XAUUSD using idle workers, zero tuning, common end date 2026-06-28, OOS locked;
- harvest any finished imports before launching tests;
- MiMo may continue independently and D021 MICRO-REV remains READY.
