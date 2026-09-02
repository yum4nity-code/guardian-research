# Guardian v11.16.5 -> v11.16.11 — integration changelog

Date: 2026-09-02
Status: CURRENT_PRODUCTION_LINE / LIVE_VALIDATION
Baseline current: `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`

## v11.16.5 — RSI Sniper integration

- Integrated RSI Sniper as an independent M1 strategy sleeve beside Momentum.
- BUY-only RSI(14): oversold episode <30, confirmed closed-M1 recross >30 for BUY1.
- Manual BUY under RSI30 can be adopted as `M-BUY1`; manual BUY outside RSI context remains under normal Guardian manual management.
- Optional BUY2 LAST in the same cycle; no BUY3.
- Cycle risk target 0.25% of reference capital.
- TP1 at RSI50: close 40% of cycle, compute BE NET, trailing on.
- TP2 at RSI70; final runner retained.
- Hedging supported; RSI auto blocked on netting.

## v11.16.6 — RSI PATCH1

- Symbolized RSI logs.
- Explicit BUY1 recross confirmation logs.
- RSI-specific spread/SL guard 25%; Momentum kept at 12%.
- BUY1 can widen structural SL for spread constraints up to 1 ATR M1 while preserving risk sizing.
- BUY2 retest widened to 0.50 ATR; divergence still required.
- Rejected BUY2 candidate can retry later.
- BUY1 stop is not tightened before BUY2 actually executes.
- BUY2 common-stop failure rolls back leg2.
- Tester symbol-resolution spam reduced.

## v11.16.7 — audit fix

- M1 watermark consumed only after successful RSI processing; missed-bar risk hardened.
- Momentum signal watermark hardened similarly.
- Restart/owner recovery improved.
- True-fill retrieval improved with deal/position/fallback hierarchy.
- TP1/TP2 partial-close retry made latched/idempotent.
- BE NET became cycle-aware and includes realized partial PnL.
- Post-fill risk diagnostics added.
- LNKUSD classified as crypto.
- Live validation confirmed TP1 retry/recovery, BE NET, LNK crypto classification.

## v11.16.8 — clean pass / lifecycle notifications

- Exact cycle-id preservation/recovery hardened.
- Broker retcode + description added on partial TP failures.
- Compact MT5/mobile lifecycle notifications introduced for RSI and Momentum.
- Notification semantics frozen:
  - WHITE: entry.
  - GREEN: TP1; for RSI, TP1 + BE stage.
  - BLUE: TP2, BE/protected exit, SL/trailing after TP1/TP2.
  - RED: dry loss / SL before any TP, whatever the strategy.
- Strategy name is mandatory in messages.
- Telegram integration scheduled for full removal under current FundedNext policy.

## v11.16.9 — notifications + under-risk sizing

- Daily PnL added to lifecycle messages: dollars and percent.
- Manual trades brought into the same lifecycle notification scheme.
- Telegram/WebRequest code removed from Guardian baseline.
- Broker max-volume under-risk rule added:
  - target remains 0.25% cycle risk;
  - if broker `SYMBOL_VOLUME_MAX` prevents reaching target, entry may be accepted only if actual risk is >= 50 USD;
  - never increase beyond target risk;
  - below 50 USD remains blocked.
- Diagnostics distinguish `MAX_VOLUME_CAP_UNDERRISK` from lot-step rounding.
- Live validation: LNK ~32 USD blocked, SOL ~192 USD accepted at broker max 5 lots.

## v11.16.10 — BUYBLOCK diagnostics

- Silent `BUY1 BLOCK` paths eliminated.
- Every failure after `BUY1 RECROSS CONFIRMÉ` must log `RSI_ORDER_BLOCKED | symbol | BUY1 | exact_reason`.
- Same principle applied to BUY2.
- Graph marker now surfaces short block reason.
- Safety fallback `UNSPECIFIED_RETURN_FALSE` added if a false-return path still lacks a reason.
- Strategy rules unchanged.

## v11.16.11 — strategy switches

- Added two top-level strategy switches:
  - `InpEnableMomentum`
  - `InpEnableRSISniper`
- Supports RSI-only, Momentum-only, combo, or no-new-auto-entry modes without editing code.
- Disabling an engine blocks new entries but does not abandon management/protection of an already-open position/cycle.
- No strategy parameter changes.

## Live observations requiring research, not immediate production changes

### BUY2 vs BUY1 stop

Multiple live RSI cycles show a structural tension: the second oversold episode can form extremely close to the BUY1 structural stop, so BUY1 can be stopped before BUY2 receives a confirmed >30 recross. Another USDCAD case armed BUY2 and passed retest but failed the mandatory divergence filter immediately before SL. Measure before changing SL, divergence, or BUY2 timing.

### RSI very-tight-stop execution cost

USDCAD example: BUY1 12.45 lots, fill 1.39339, SL 1.39317, post-fill risk 258.85 USD. The trade displayed roughly -130 USD shortly after opening. Measure spread + commissions as a percent of initial risk for very short structural stops before modifying the 25% spread/SL guard.

### Momentum management

Current production Momentum baseline remains validated by existing backtests. Current observed management uses BE/trailing around +1.25R and TP1 at +2R with 25% partial close. Do not change from visual frustration alone; measure MFE and A/B any earlier profit lock.

### Backtest baseline 2026-09-02

Same BTC two-month combined backtest reproduced exactly after technical patches:
- Net Profit +17,499.93 USD
- PF 1.35
- Equity DD max 3.76%
- 628 trades

BTC RSI-only, same period:
- Net Profit +9,451.57 USD
- PF 1.19
- Equity DD max 4.20%
- 621 trades
- win rate 61.51%
- average win +153.64 USD
- average loss -206.01 USD

Momentum-only baseline is being run with current `InpCryptoPostShockBars=2`.

## Next technical/research items

1. True fast-path bypass: when Momentum OFF, skip Momentum-only indicator/signal computations; when RSI OFF, skip RSI-only work. Preserve shared Guardian calculations and exact results.
2. Add compact Strategy Tester end-summary so research does not depend on gigantic Journal files.
3. Correct startup wording `plancher risque effectif 250$` to mention the max-volume under-risk exception >=50 USD.
4. Correct BUY2 divergence log wording so the comparator printed matches the actual test.
5. Continue measuring BUY2 vs BUY1-stop incompatibility before changing either.
6. Momentum POST_SHOCK A/B: baseline 2 bars vs 0, then only 1/4 if the effect is material.
7. RSI research candidates after isolation: trailing activation after TP1; oversold depth 30/27.5/25; then BUY2/SL architecture.

## Anti-curve-fitting rule

Do not exhaustively optimize all inputs. Screen only a few structurally justified variables with broad interpretable values, require stable behavior across BTC/ETH/SOL, and reject isolated magic peaks.
