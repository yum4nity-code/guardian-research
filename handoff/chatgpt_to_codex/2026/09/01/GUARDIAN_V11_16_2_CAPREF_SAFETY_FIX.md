# Guardian v11.16.2 — CAPREF safety fix

STATUT: URGENT / SUPERSEDE v11.16.1 RISKFIX FOR RUNTIME

A live FTMO 100k run of v11.16.1 RISKFIX exposed a second safety divergence: the HUD showed `Capital Référence : 10000 $` and an absurd daily remaining margin >90k on a 100k account.

Root causes found in source:
1. `InpInitialCapitalOverride` can still force stale template values in live because `DetectInitialCapitalRobust()` returned the override before auto-detection.
2. Daily-reference reconstruction subtracted all history deals, including BALANCE/CREDIT style account-funding operations; this can reconstruct an impossible ~10k daily reference on a new 100k account.
3. A bad same-day daily reference persisted in account GlobalVariables until the day changed.

ChatGPT repaired this directly in a new file:
`Guardian_D017_PropFirmAuto_v11_16_2_RISKFIX_CAPREF.mq5`
local SHA256: `7194e569eeb170358566228431b82c52bfeec5069b3fa10043345f5fb8c1c4c3`
internal version: `11.162`.

Changes only:
- live ignores `InpInitialCapitalOverride`; override remains tester-only;
- invalid live account balance/equity no longer silently falls back to 10k;
- daily-reference reconstruction counts BUY/SELL trading deals only, not BALANCE/CREDIT account-funding operations;
- same-day stored daily reference <50% of detected base capital is automatically rebuilt/repaired and persisted;
- startup diagnostic logs `CAPITAL_REFERENCE_AUTO ... detected=...`;
- existing 0.25% minimum-risk self-test remains.

Codex instruction when quota resumes:
- allow data imports already running to finish if they are import-only;
- do NOT launch any strategy backtest with v11.16.1 RISKFIX;
- once the user places v11.16.2 on the PC, do one normal compile; if 0/0 and startup on 100k shows detected=100000 plus sane daily margin, use v11.16.2 for the six-market pre-OOS workers;
- no extra audit/rerun gate; no OOS.
