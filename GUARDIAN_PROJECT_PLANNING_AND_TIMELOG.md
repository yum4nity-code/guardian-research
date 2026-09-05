# Guardian — Project Planning & Time Log

Last reconstructed: 2026-09-05 Europe/Paris
Status: LIVING FILE — update during each material Guardian work session

## Purpose

This file tracks two things in one place:

1. **Project chronology / planning** — what was built, tested, rejected, retained, and what comes next.
2. **Human time spent** — work time attributable to the Guardian project, day by day.

Historical entries before GitHub are reconstructed from prior ChatGPT conversations. GitHub-era entries additionally use repository commits/reports. The historical time column is intentionally conservative: when only message timestamps are available, it records an **observed activity span**, not a claim of continuous active work.

From 2026-09-04 onward, time should be logged more precisely.

## Time-accounting rules

- `CONFIRMED SPAN` = first/last timestamped Guardian activity found for that day/session. It may contain pauses and is not equal to pure keyboard time.
- `MINIMUM OBSERVED` = only a small timestamped fragment is recoverable; actual work was longer.
- `NOT QUANTIFIED` = Guardian work is confirmed but available evidence is insufficient for a responsible duration.
- Backtests/collectors running unattended are **not** counted as human work time. Their runtime can be noted separately if useful.
- From now on: split sessions after a long break; record human active time separately from unattended MT5/Codex/collector runtime.
- Never manufacture precise historical hours merely to fill the ledger.

---

# Historical reconstruction

## 2026-08-14 — origin of the manual-trade manager

**Work / decisions**
- Initial concept: MT5 bot to manage manual trades.
- Fixed-risk approach around 0.5% of capital.
- Minimum R/R concept, BE after +1R, partial profit and runner toward +3R or more.
- Architecture discussed: detect Magic 0 manual positions, derive size/risk from SL, multi-symbol management.

**Time evidence**
- Retrieved conversation timestamps: approximately 17:58 -> 18:04.
- `MINIMUM OBSERVED: >= 0h05`; actual session length unknown.

## 2026-08-16 — transition toward a full FTMO EA

**Work / decisions**
- Project framed as FTMO 2-Step 100k EA.
- Fixed risk cap accepted at $500/trade independent of equity.
- Challenge +10%, Verification +5%, Funded no target; 10% total / 5% daily loss limits used as core constraints.
- Profit-management preference: TP1/TP2, BE/protection, 20–30% runner, ATR trailing; commissions intended in later net/backtest work.
- `FTMO_Crypto_Activity_EA_v1_0.mq5`, later renamed `VSRB50.mq5`, produced with breakout + EMA20/50 + RSI + ATR, M15, long/short, partials, runner, BE/trailing, time-stop and FTMO guards.
- BTC frequency analysis started; 26,504 raw signals reported in the retrieved conversation record.

**Time evidence**
- Retrieved timestamps: ~17:21 -> 18:29.
- `CONFIRMED SPAN: ~1h08`.

## 2026-08-17 — compile fixes / FTMO safety layer

**Work / decisions**
- FTMO drawdown handling refined.
- Internal safety margins discussed below official limits; equity/floating P&L awareness reinforced.
- Compile fix on `buymobile_v3_fixed_compilefix2.mq5` (`MoveToBE(states[idx])`, static-buffer correction) without intentionally changing strategy logic.

**Time evidence**
- Retrieved timestamps around 07:04 -> 07:06.
- `MINIMUM OBSERVED: >= 0h02`; actual work unknown.

## 2026-08-20 — 10k risk-guard framing

**Work / decisions**
- FTMO 10K safeguards discussed: $500 daily loss / $1,000 max loss official context.
- Internal trade/global/symbol risk limits explored as Guardian protection concepts.

**Time evidence**
- Guardian activity confirmed around 12:07.
- `NOT QUANTIFIED`.

## 2026-08-21 — execution guard / management mechanics

**Work / decisions**
- Existing management baseline documented: SL around 1.60× ATR(14) M15, TP1 0.75R / 50% partial, BE net-zero +1 tick, runner logic.
- FTMO execution-guard integration audited against a large existing EA source.
- Plan to protect auto-entry / TP1 / BE / runner / close paths while preserving manual-entry behavior.
- Early signs that Guardian must be separated conceptually from strategy logic.

**Time evidence**
- Retrieved timestamps: ~09:47 -> 11:29.
- `CONFIRMED SPAN: ~1h42`.

## 2026-08-22 — reusable Guardian core before strategy

**Work / decisions**
- Explicit architectural decision: build reusable `FTMO_GUARDIAN_100K` core before adding more strategy complexity.
- Separate Guardian/risk/compliance from strategy.
- Real FTMO Standard conditions requested from the outset, including weekend/mandatory closures.
- Request-budget concept included, along with daily/max loss, sessions/news, exposure/correlation and ALLOW/BLOCK/REDUCE/FORCE_CLOSE states.
- User explicitly preferred continued research before blindly coding strategy.

**Time evidence**
- Retrieved timestamps: ~07:25 -> 07:30.
- `MINIMUM OBSERVED: >= 0h05`.

## 2026-08-24 — real FTMO challenge context

**Work / decisions**
- FTMO/MT5 time-reset behavior discussed in the context of live overnight Forex/crypto positions.
- Guardian planning increasingly tied to actual challenge constraints rather than generic backtest assumptions.

**Time evidence**
- Guardian/FTMO activity confirmed around 20:25.
- `NOT QUANTIFIED`.

## 2026-08-25 — 10k 2-Step operational targets

**Work / decisions**
- FTMO 2-Step 10k objectives/limits reviewed: Phase 1 +$1,000, Phase 2 +$500, daily loss $500, max loss $1,000, minimum trading-day constraint, unlimited duration.
- User objective: complete the challenge as quickly as possible while Guardian must keep risk from violating the prop rules.

**Time evidence**
- Retrieved timestamps: ~05:28 -> 05:30.
- `MINIMUM OBSERVED: >= 0h02`.

## 2026-08-26 — systematic strategy research / TSMOM rejected

**Work / decisions**
- Multi-market strategy work across BTCUSD, XAUUSD, WTI, Forex, indices and crypto.
- TSMOM added experimentally without changing Guardian protections, backtested, then explicitly abandoned; returned to the initial architecture.
- Structural audit identified issues around engine attribution/order, timeframe design, ORB/ATR usage, SL/TP1/BE/trailing/time-stop, caps, manual-SL behavior, and preservation of FTMO safeguards.
- Research direction shifted toward documented, robust, multi-market strategies rather than indicator stacking / blind optimization.

**Time evidence**
- Retrieved timestamps: ~16:03 -> 17:36.
- `CONFIRMED SPAN: ~1h33`.

## 2026-08-27 — Guardian 11.10 crypto work / major debugging day

**Work / decisions**
- `FTMO_Guardian.11.10` crypto strategy work: Liquidity Sweep -> Reclaim -> confirmation, ATR SL, R-based TP logic.
- Initial crypto build hit 14 undeclared `InpCryptoSweep...` identifiers.
- Repeated stale/same-filename delivery problem identified; policy changed to distinct filenames for modified builds.
- Recovery build `FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2.mq5` created.
- Manual/protective SL behavior and inherited-position lifecycle examined.
- Partial-close accounting corrected so management/restructuring would not be miscounted as a consecutive loss/cooldown event.
- Crypto entry gating/time-stop/recovery behavior iterated.
- Multi-market backtest results began separating Momentum from weaker engines.

**Time evidence**
- Retrieved activity from ~13:50 to at least ~16:25.
- `CONFIRMED SPAN: ~2h35`.

## 2026-08-28 — Codex-assisted research / Momentum becomes primary lead

**Work / decisions**
- Resumed `FTMO_Guardian.11.10` with Codex.
- Breakout, Pullback, Sweep and Momentum analyzed as separate engines.
- Breakout/Pullback/Sweep rejected in their current forms; Momentum retained as the serious line of research.
- Backtest/research automation expanded under `D:\MT5_Backtests` with multi-symbol data and anti-curve-fitting mandate.
- User began using Codex more autonomously for backtests/adaptation while preserving scientific constraints.
- CPU/runtime limits and distributed-compute ideas discussed because the experiment matrix had become large.

**Time evidence**
- Retrieved timestamps include ~06:07 -> 07:02, with additional Guardian work later in the day not fully timestamp-reconstructed.
- `MINIMUM OBSERVED: >= 0h55`; actual day substantially longer is plausible but not asserted.

## 2026-08-29 — PropFirmGuard / compliance automation / D017 reconstruction

**Work / decisions**
- FTMO crypto maintenance event exposed need for operational/compliance monitoring.
- PropFirmGuard direction accepted: multi-prop-firm, multi-account/terminal watcher, temporary events, Codex backlog integration.
- v0.1 -> v0.3 iterations added HALT/review handling, Codex queue and terminal-wide `REVUE` signaling; email alert idea later removed in favor of Codex processing and chart alert only when dangerous/ambiguous/non-integrable/stale.
- D017 lineage reconstruction linked back to `FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2.mq5` and Momentum research.
- Guardian/PropFirmGuard architecture became broader than one EA: compliance watcher + trading Guardian + research workflow.

**Time evidence**
- Retrieved timestamps: ~11:57 -> ~19:09.
- `CONFIRMED ACTIVITY SPAN: ~7h12` — this is a day-span and may include breaks; do not treat as 7h12 continuous active work.

## 2026-08-30 — continuation / live-rule and market-availability checks

**Work / decisions**
- Guardian-related market-availability / FTMO crypto-close behavior continued to be investigated.
- No sufficiently complete historical timestamp set was recovered in this reconstruction to quantify the day responsibly.

**Time evidence**
- `NOT QUANTIFIED`.

## 2026-08-31 — production-owner model / manual management / RSI direction

**Work / decisions**
- Deployment/preflight and FTMO tests active; D017 EURUSD/GBPUSD and crypto strategy research continued.
- Owner-instance architecture accepted: multiple Guardian instances may auto-trade per symbol, but one owner manages account-wide Magic 0 manual positions; others standby for manual management.
- `Guardian_D017_PropFirmAuto_v11_15.mq5` and `FTMO_D017_v11_15_SAFE.set` produced in this phase.
- Manual-range management research defined: RSI 70/30 idea, partial profit, BE, runner; must be backtested before integration.
- Anti-reentry/reset requirement added for repeated RSI/manual signals.
- Mobile requirement added: ability to disable the micro-EA / notifications easily from phone.
- Codex autonomous research/backtest mandate continued.

**Time evidence**
- Retrieved timestamps: ~06:28 -> ~07:36 for one confirmed session; additional work later that day exists in conversation history but is not fully reconstructed here.
- `MINIMUM OBSERVED: >= 1h08`.

## 2026-09-01 — RSI Guardian / production-line continuation

**Work / decisions**
- RSI Guardian resumed after lunch; RSI(14) M1 line moved toward implementation beside Momentum.
- Continued Guardian 11.16 production evolution, risk sizing and strategy separation work.
- Research/document continuity became increasingly important as Codex and ChatGPT both touched the project.

**Time evidence**
- Retrieved timestamp confirms RSI Guardian resumed around 12:03; complete session endpoints not recovered.
- `NOT QUANTIFIED`.

## 2026-09-02 — RSI Sniper integration / reproducibility work

**Work / decisions**
- Guardian production line advanced through v11.16.5 -> v11.16.11.
- RSI Sniper integrated as independent M1 sleeve beside Momentum.
- BUY1/BUY2 lifecycle, RSI-specific spread/SL guard, fill recovery, partial-close idempotence, BE NET, lifecycle notifications, under-risk max-volume handling, explicit BUYBLOCK diagnostics and strategy switches added across successive versions.
- Telegram/WebRequest removed from baseline.
- Same BTC two-month combined backtest reproduced after technical patches: +17,499.93 USD, PF 1.35, max equity DD 3.76%, 628 trades.
- BTC RSI-only baseline: +9,451.57 USD, PF 1.19, DD 4.20%, 621 trades.
- EURUSD RSI-only Jul-Aug result recorded in GitHub.
- Reproducibility ledger / Jun-Jul comparison framework established.

**Time evidence**
- GitHub commits recovered from ~13:57 to ~16:32 local, plus conversation work outside that commit window.
- `CONFIRMED REPO ACTIVITY SPAN: ~2h34`; actual human work longer, not precisely reconstructed.

## 2026-09-03 — FundedNext rules / request-budget protection / live-account adaptation

**Work / decisions**
- FundedNext terms/rules integrated into Guardian planning.
- Server-request budget architecture designed by prop firm/challenge rather than one universal cap.
- Guardian HUD request counter added/planned with graduated protection states and reserve for safety operations.
- Requirement: cut nonessential RSI requests before exhausting allowance while preserving Momentum/protection headroom.
- DOGE entry behavior and willingness to accept smaller profitable trades discussed.
- RSI management preference included leaving a 10% runner.
- Guardian code/live account configuration continued toward FundedNext compatibility.

**Time evidence**
- `NOT QUANTIFIED` from current reconstruction.

## 2026-09-04 — Shared Intelligence + D025 LER + request anomaly + path diagnostics

**Work / decisions**
- External Intelligence Bus / Shared Intelligence matured from Bybit-only research toward Bybit + Binance multi-venue collection.
- Raw/derived read-only architecture validated: spot/perp, OI, funding, liquidations, market-state features, FILE_COMMON bridge, multi-consumer behavior.
- Autostart task / resilient shared runtime established; Shared Intelligence remains read-only and cannot alter Guardian trading decisions.
- Guardian v11.17.x observer lineage audited for multi-venue read-only intelligence.
- D025 Liquidity Exhaustion Reclaim V0 rules locked before implementation.
- D025 observer built; canonical handoff and live-status continuity channel created.
- Attempts to automate FundedNext Strategy Tester through wrappers V1-V4 were ultimately suspended after unreliable targeting/launcher behavior; policy changed back to normal manual MT5 testing rather than making the user debug shell wrappers.
- D025 Trading 1.01 built for manual single-symbol tests.
- Long BTC/ETH tests showed the original `structural SL + no TP + forced 48h exit` construction was bad; analysis correctly separated exit failure from entry-quality question.
- First-touch diagnostics expanded across BTC/ETH/EUR/SOL/DOGE/LNK/ETC/XMR/GBP/USDJPY/XAU.
- 2024 and 2025 replication isolated recurring branches: ETH RETEST, BTC SHORT, GBP SHORT, promising-but-less-mature SOL SHORT; universal D025 fixed-TP edge rejected.
- D025 1.02 path diagnostic added +0.5R and BE-after-1R instrumentation.
- Real-order 0.05% rerun exposed strong BTC/ETH sample-selection bias from account/execution/min-volume effects; conclusion: real-order logger unsuitable for clean crypto path population.
- D025 1.03 Virtual Path Diagnostic created to remove lot/margin/account/order dependence entirely. User began 2024-2025 reruns; requested outputs are events + trades + outcomes.
- Scientific standard tightened: do not accept tiny pre-cost edges; seek broad recurring advantage before adding spread/commission/slippage stress.
- FundedNext live Guardian request anomaly identified (~5629/2000 HUD vs FTMO ~32/2000). Structural suspect: repeated protection/BE retries; FundedNext Algo Trading kept OFF pending bounded retry/backoff/dedup fix.
- FundedNext Quick Strike requirement added, then corrected after user clarification: failed initial SL placement does **not** auto-close the manual trade; Guardian attempts once and the user currently places the SL manually. Quick Strike must be handled separately for profitable <30s Guardian-managed exits without weakening protection.

**Time evidence**
- Repository commit activity visible from ~08:54Z to ~17:33Z, i.e. roughly 09:54 -> 18:33 Europe/Paris on the current UTC+1 day.
- `CONFIRMED REPO ACTIVITY SPAN: ~8h39`, plus user conversation immediately around/after that window. This span includes automation/test waiting and is not equivalent to 8h39 uninterrupted keyboard time.

## 2026-09-05 — evidence-first strategy marathon / pure core / D035 lead-lag preparation

**Work / decisions**
- Strategy-neutral Pure Guardian Core v12.01 static candidate prepared and handed off; production/live replacement still requires MetaEditor compile/smoke.
- Broad research slate executed with setup-first and preregistration discipline. Distinct families worked today included RSI legacy, D017 Momentum, D022 pair reversion, D023 London ORB, D027 NR7, D028 session momentum, D031 Piercing/Dark Cloud, D032 crypto reversal/Doji, D030 H4 engulfing, D029 TSMOM, D033 Double Top/Bottom and D034 abnormal-return Gold/Oil.
- RSI, broad Momentum, D022, D023, D027, D028, D030, D029, corrected D033 and D034 GOLD failed their applicable broad/frozen gates. OIL remains untested because unavailable on the target account. D031 remains non-validated rather than production evidence.
- D032 Bullish Doji Star H1 produced the one confirmed entry signal of the day on untouched PRE2024 BTC+ETH+DOG data, but all tested management/localization variants remain unsolved; retain only as a sparse research sleeve.
- Scanner QA rules were tightened after implementation defects: column-count/index QA, immediate flush, runtime output checks and source-algorithm conformance review before asking the user to spend time on reruns.
- D029 full eight-market TSMOM gate closed rejected; no RSI/SMA/ATR rescue mining.
- D033 corrected M2 Double Top/Bottom EURUSD M5 closed rejected 0/7 gates.
- D034 XAU abnormal-return Strategy 1 closed rejected 3/7; long-only clue remained below the preregistered economic gate and was not rescued.
- User requested exotic approaches and selected only the cross-venue crypto leverage idea. D035 was preregistered: Binance BTC/ETH downside price+OI deleveraging shocks -> delayed FundedNext crypto CFD response.
- D035 freezes 2024-2025 development and reserves 2026-H1 untouched confirmation; source shock uses strictly-prior 30d 10th-percentile price/OI thresholds, 30m cooldown, +15m primary executable short response and matched prior control. Same-sample rescue mining is forbidden.
- D035 MT5 M1 quote exporter v1.01 prepared and committed; Python historical Binance Vision analyzer prepared, syntax-checked and synthetic-smoke-tested, including server->UTC clock calibration.
- Daily time-log maintenance was made an explicit mandatory rule for ChatGPT, Codex and future agents in `AGENTS.md`, `README.md` and `CURRENT_PROJECT_HANDOFF.md`.

**Time evidence**
- Earliest clearly attributable 2026-09-05 repository research commits are around 05:38Z (~07:38 Europe/Paris); Guardian work continued through this entry at approximately 20:36 Europe/Paris.
- `CONFIRMED ACTIVITY SPAN: ~07:38 -> 20:36 Europe/Paris` — includes breaks, backtest waiting and unattended compute; it is **not** a claim of ~13h active keyboard work.
- `Human active total: NOT QUANTIFIED` from available evidence; do not manufacture a precise duration.
- Unattended Strategy Tester / collector / analysis runtime: excluded from human time.

**Next**
- User runs D035 exporter on BTCUSD plus every crypto CFD available on the target FundedNext account, Strategy Tester M1 / 1 minute OHLC, 2023-11-01 through 2025-12-31.
- Collect all `D035_CFD_M1_*.csv`, run frozen D035 development analyzer without `--confirm`, archive verdict and update handoff.
- Keep D032 Doji as sparse research only; do not rescue rejected families on inspected samples.
- Pure Guardian Core v12.01 compile/smoke remains a separate prerequisite before any live replacement.

---

# Current planning / backlog

## P0 — D025 management research

- Finish **1.03 Virtual Path Diagnostic** clean 2024-2025 reruns.
- Priority symbols: BTCUSD, ETHUSD, XAUUSD, GBPUSD, USDJPY, EURUSD. SOL only if available again on the relevant FundedNext history/feed.
- For each run collect: `events`, `trades`, `outcomes`.
- Validate that virtual signal counts recover the missing BTC/ETH population and are no longer account/lot/margin filtered.
- Compare frozen management candidates without changing locked D025 V0 entries/structural SL.
- Treat same-M1 target/BE/stop ordering as ambiguous rather than inventing an order.
- Require a **large, recurring edge**, not a marginal pre-cost advantage.
- Only after structural edge is clear: apply realistic spread + commission + slippage and stress costs upward.

## P0 — FundedNext request-budget fix

- Audit every `SRP_PROTECTION` retry path, especially RSI BE/common-stop retry logic.
- Add bounded retry cadence/backoff, retcode-aware handling and identical-request deduplication.
- Preserve genuine emergency protection bypass.
- Validate request counts before FundedNext Algo Trading is re-enabled.
- Do not reset the live HUD counter merely to hide the problem.

## P0 — FundedNext Quick Strike handling

- Preserve current fact: failed initial manual-trade SL placement gets one Guardian attempt; user currently places SL manually if that fails.
- Add precise entry-time / elapsed-time / P&L-sign logging for Guardian-managed exits under 30 seconds.
- Evaluate FundedNext-specific early BE/SL behavior only if risk-neutral.
- Never hold an unsafe trade open simply to avoid Quick Strike classification.

## P1 — Shared Intelligence / Crypto+

- Keep Binance + Bybit collector running read-only.
- Continue accumulating BTC/ETH external history: spot/perp, OI, funding, liquidations, basis/dislocation and quality.
- D035 is now the frozen historical cross-venue lead-lag campaign; do not feed its development findings into Guardian before independent confirmation.
- Preserve `available_at <= event_time` for any forward EIB study.

## P1 — Guardian production continuity

- Keep `CURRENT_PROJECT_HANDOFF.md` as fast-resume canonical state.
- Keep this file as the historical/time/planning ledger.
- Update both on material architecture/research decisions.
- Maintain distinct filenames for modified user-facing EA versions to avoid stale-file/cache confusion.

---

# Daily log template from now on

```text
## YYYY-MM-DD
Session A: HH:MM -> HH:MM = XhXX active
Session B: HH:MM -> HH:MM = XhXX active
Human active total: XhXX
Unattended compute/runtime: optional, separate

Done:
- ...

Decisions / rejected:
- ...

Next:
- ...
```

## Historical-time caveat

The chronology above is much more reliable than the old time totals. Pre-GitHub conversations were not originally run as a stopwatch. Therefore old durations are deliberately labelled as observed spans/minimums/unknowns. Going forward this file can provide a substantially cleaner day-by-day work-time record.