# Guardian v11.16.13B — Minimal fix rebuilt from true v11.16.12

Date: 2026-09-02

## Baseline actually used

- Source: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5`
- SHA256: `9307f5daf09c243b4997fb59f82a71e5baa85992a5f348fd3bf9e5f841b8122b`
- Lines: 5900

The previous v11.16.14 / v11.16.15 experimental files were **not** used as a source.

## New candidate

- Source: `Guardian_D017_PropFirmAuto_v11_16_13B_MINIMAL_FIX_FROM_TRUE_12.mq5`
- SHA256: `774f05df72a2b5bc716c393c0e67197f3f23923cc6894be49525259f39b5e8c2`
- Lines: 5957

## Scope — only two functional fixes

### 1. Consecutive-loss cooldown really OFF when input = 0

- Default `InpConsecutiveLossCooldown` changed from `3` to `0`.
- `GetAccountCooldownUntil()` returns 0 when cooldown is OFF.
- New `GetCryptoCooldownUntil()` returns 0 when cooldown is OFF.
- Both Momentum and RSI new-entry guards use the getter rather than directly honoring stale `CRYPTO_CD` state.
- Strategy Tester also deletes stale `CRYPTO_CD` on init.
- Live init zeroes persisted account/crypto cooldown globals when the setting is OFF.

No other account-risk guard was removed.

### 2. Manual BUY under RSI30 routed to the correct symbol instance

The v11.16.12 bug was that the unique account-wide manual owner called `RSITryAdoptManualEntry()` using its own `_Symbol`. A manual USDJPY BUY could therefore be evaluated from an ETHUSD owner instance and fail RSI adoption.

The patch keeps the unique account-wide manual owner, but allows the owner of the traded symbol to process only the RSI adoption decision for a Magic-0 entry on that symbol.

Expected live behavior with Guardian instances running on ETHUSD and USDJPY:

- manual USDJPY BUY arrives;
- unique manual owner emits the existing manual-entry notification once;
- USDJPY symbol owner evaluates `RSITryAdoptManualEntry()` with `_Symbol == USDJPY`;
- if RSI M1 USDJPY < 30 and the existing v11.16.12 adoption conditions pass, the existing `M-BUY1` cycle is created;
- the **existing unchanged** RSI cycle code then handles BUY2, RSI50/TP1, BE/trailing, RSI70/TP2 and runner;
- account-wide manual periodic management already skips positions tagged `RSI`, so the two management logics do not compete;
- if there is no live Guardian instance for the traded symbol, the v11.16.12 generic MANUAL fallback remains.

## Functions verified byte-identical to v11.16.12

- `CheckSignals()` — Momentum signal generation
- `ManagePositionsAndManualTrades()`
- `RSIDrawMarker()` — historical/chart markers
- `RSIUpdateDynamicDisplay()`
- `RSIExecuteAutoBuy()` — auto BUY1/BUY2 sizing/fill logic
- `RSITryAdoptManualEntry()` — existing M-BUY1 strategy behavior itself
- `RSIStartAutoBuy1()`
- `RSIDoTP1()`
- `RSIDoTP2()`
- `RSIProcessNewM1Bar()`
- `RSIHUDText()`

Therefore this candidate does **not** widen the BUY1 stop, change RSI thresholds, change BUY2 logic, change TP logic, change Momentum strategy, or redesign charts/log wording.

The startup/HUD title changes only `v11.16.12` -> `v11.16.13`; its structure is otherwise unchanged.

## Explicitly NOT included

- no 0.50 ATR BUY1 experiment;
- no hard-disable of Momentum;
- no timeframe changes;
- no changes to BUY1/BUY2 thresholds;
- no changes to RSI50/RSI70 exits;
- no changes to marker colors/labels/layout;
- no changes to Momentum entry logic;
- no research optimization.

## Validation still required in MetaEditor / MT5

This environment does not contain MetaEditor, so compilation cannot be honestly claimed here.

Required validation sequence:

1. Compile this exact file: expect 0 errors / 0 warnings.
2. Start one clean RSI-only backtest with Momentum OFF: `Short Trades` must be 0.
3. Check Journal: existing `RSI_SNIPER | ARMÉ | BUY1 RECROSS | BUY2 | TP1 | TP2` wording must look like v11.16.12.
4. With cooldown input 0, search Journal for `CRYPTO_COOLDOWN` and `COOLDOWN_LOSSES`: there must be no new-entry blocks with either reason.
5. Live/manual test: BUY on a symbol different from the manual-owner chart while that symbol's RSI M1 < 30; expect `RSI_MANUAL_ADOPTED` / `M-BUY1`, then normal RSI cycle management.

Do not proceed to the wider-SL experiment until these five checks pass.
