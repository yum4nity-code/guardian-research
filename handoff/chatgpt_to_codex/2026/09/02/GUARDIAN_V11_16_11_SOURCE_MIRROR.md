# Handoff — mirror exact live Guardian v11.16.11 source into GitHub

Date: 2026-09-02
Priority: HIGH / source-of-truth reconciliation
Target repo: `yum4nity-code/guardian-research`

## Required outcome

GitHub must contain the exact live/user-compiled source at:

`production/guardian/Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`

Do not regenerate, refactor, reformat or patch the file during this handoff.

## Exact source identity

- Filename: `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`
- SHA256: `d30ff21378331f972bea947a4c6c826b6f4a2547e58878947551199b9d01c495`
- Size: 272765 bytes
- Lines: 5729
- User state: compiled/deployed and used for current BTC engine-isolation backtests.

## Codex machine task

Codex has full PC access under the current mandate. Locate the exact live source on the user's machine. Search MT5/MQL5 Experts locations and the ChatGPT/Desktop transit locations as needed.

Before committing:

1. Compute SHA256 of every candidate with the exact filename.
2. Accept only the file whose SHA256 equals `d30ff21378331f972bea947a4c6c826b6f4a2547e58878947551199b9d01c495`.
3. If no exact match exists, STOP and report `SOURCE_MIRROR_BLOCKED_HASH_NOT_FOUND`; do not substitute an older/newer file.
4. If exact match exists, copy it byte-for-byte to `production/guardian/Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`.
5. Recompute SHA256 after copy and require the same hash.
6. Commit with a message equivalent to `production: mirror exact live Guardian v11.16.11 baseline`.
7. Update `production/manifests/GUARDIAN_CURRENT.json` status from `LIVE_BASELINE_PENDING_SOURCE_MIRROR` to `LIVE_BASELINE_SYNCED` and record the source commit SHA.
8. Update `docs/RESEARCH_STATUS.md` with the resulting commit SHA.

## Current semantics that must not be altered during mirror

- Two engine switches: `InpEnableMomentum`, `InpEnableRSISniper`.
- RSI Sniper integrated M1 sleeve.
- Max-volume under-risk exception: actual risk >=50 USD may trade when broker volume cap prevents target risk.
- Explicit BUY1/BUY2 block diagnostics.
- MT5/mobile lifecycle notifications with WHITE/GREEN/BLUE/RED semantics.
- Manual lifecycle notifications and daily PnL display.
- Telegram/WebRequest integration absent.

## Research state after mirror

Do not launch broad optimization from this handoff. Current manual research sequence:

1. BTC combo baseline already reproduced exactly: +17499.93 USD, PF 1.35, equity DD 3.76%, 628 trades.
2. BTC RSI-only: +9451.57 USD, PF 1.19, equity DD 4.20%, 621 trades.
3. BTC Momentum-only baseline with `InpCryptoPostShockBars=2` is being run by the user.
4. Next focused A/B is POST_SHOCK 2 vs 0 bars; only test 1/4 later if effect is material.
5. BUY2 vs BUY1 structural stop remains measurement-only; no patch until evidence is collected.

See:
- `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md`
- `docs/RSI_SNIPER_IMPLEMENTED_ADDENDUM_2026_09_02.md`
- `docs/STRATEGY_DECISIONS.md`
- `docs/RESEARCH_STATUS.md`
