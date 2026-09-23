# Guardian — Project Planning & Time Log

Last reconstructed: 2026-09-08 Europe/Paris
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
- FundedNext Quick Strike requirement added, then corrected after user clarification: failed initial manual-trade SL placement does **not** auto-close the manual trade; Guardian attempts once and the user currently places the SL manually. Quick Strike must be handled separately for profitable <30s Guardian-managed exits without weakening protection.

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

## 2026-09-06 — D035 verdict, cross-strategy autopsy, D17 closure, D023 restart handoff and v1.08 harness recovery

**Work / decisions — early session**
- User returned the complete `D35 OUTPUT.zip` from the frozen D035 2024-2025 development run.
- D035 data quality was strong: 5,558 merged BTC/ETH source events, 38,622 target-event rows, nine FundedNext crypto CFDs, complete loaded Binance metrics/1m archive QA, and 114/114 server->UTC calibration weeks usable with mean correlation ~0.996.
- Frozen D035 primary gate closed **REJECT 4/8**: pooled executable SHORT +15m -25.448 bps; event-control differential +5.179 bps; bootstrap differential [+3.033,+7.385] bps; pooled executable +30m -25.438 bps; BTC-only differential -3.281 bps vs ETH-only +3.283 bps.
- Post-hoc audit found that the superficially strong `BTCUSD+ETHUSD` subgroup leaked future information if interpreted from the first source timestamp. A causal E1 was preregistered with the signal moved to the later/second shock and XLMUSD frozen as primary.
- User returned `D35 CASUAL.zip`. D035-E1 completed with 973 causal dual events. XLMUSD primary n=870: mean executable +15m **+6.705bps**, median **0.000bps**, event-control differential **+13.490bps**, raw bootstrap **[+1.996,+11.549]**, differential bootstrap **[+8.793,+18.302]**, +30m **+3.697bps**, 2024 **+4.104bps**, 2025 **+9.935bps**.
- Frozen E1 gate closed **6/8 -> E1_DO_NOT_ADVANCE** because mean executable +15m failed >=15bps and median was not >0. ETH/BTC diagnostics looked better but were not the frozen primary and were not promoted. 2026-H1 remains untouched. D035 family closed for immediate development.
- Cross-strategy edge-decay autopsy completed. Main conclusion: short-window profitability versus long-history decay reflects regime dependence, raw-signal vs managed-system/account-state mismatch, multiple testing, CFD cost drag and data provenance. D032 remains proof that the stricter protocol can still confirm a large edge.
- META-A1 Momentum v1.00 was prepared from v11.16.19 with Momentum thresholds unchanged and RSI disabled for the experiment, logging raw/filtered/actual/management layers. Static QA passed; MQL5 compile remains external/mandatory.

**Work / decisions — later research session**
- Short-window reruns and file confusion showed that v11.16.19 could not be treated as the sole authoritative D17 lineage anchor without a non-regression match.
- Guardian Finder located multiple historical Momentum candidates. GitHub inspection confirmed `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` and the documented v11.16.5→v11.16.11 lineage.
- Source inspection preserved the D17 native manager lineage: TP1 2R / 25%, true-net BE around 1.25R and 1.75 ATR trailing that only moves the stop in the risk-reducing direction.
- Cross-market D17 attribution was subsequently completed across BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD and USDCAD. Broad D17 Momentum in its present form is now **closed as a current alpha candidate**; keep only lineage and Manager Evidence Ledger evidence. Do not tune or rescue D17 on inspected samples.
- Manager evidence remains mixed but useful: the native ratchet helped 5/7 D17 markets and hurt 2/7, which argues against a universal manager and supports testing management weakness on an independent strategy family before any Manager Lab.
- Guardian Core v12.01 was compile-validated by the user in MetaEditor at 0 errors / 0 warnings and is now the stable pure infrastructure baseline; keep it out of strategy research.
- FundedNext request/retry pathology remains unresolved and separate from alpha research; FundedNext AUTO stays OFF until request budgeting/dedup/retry/backoff behavior is bounded.

**Work / decisions — restart / D023 harness session**
- A new canonical takeover entrypoint `START_HERE_NEXT_AI.md` was adopted at commit `ce2b28c1fb3524d2e989995f09df8f571930df68`, with `GUARDIAN_MASTER_MANDATE.md` and the Sep-6 restart handoff as governing documents.
- Active P0 was reconciled to **D023 USDJPY London ORB**, not D17. D023 remains a serious candidate after FundedNext/DST-aware 2024-2026 conformance: n=482, mean net ~+0.0915R/trade, cumulative ~+44.10R, PF ~1.176, positive 2024/2025/2026 H1 but weakening through time.
- Untouched 2023 gates remain frozen: n>=150, mean net R>0, PF>=1.10, 5-day moving-block bootstrap lower 5% bound >0, and positive result at 1.5x commission. No direction/day/indicator rescue filters and no manager experiment before scoring.
- The exact historical local v1.07 2023 harness was recovered from the user's ChatGPT Library. Its measured SHA256 `34ce816eef241c662d6b9fa3be3caea62bc67a25d034bf6cb86e9c67903fff01` exactly matches the restart-handoff SHA, establishing provenance.
- The v1.07 defect was confirmed directly: malformed `"\Files\"`-style path literal plus stale `v1.06` log labels. v1.07 remains untrusted and was not run.
- New `D023_USDJPY_LondonORB_M15_v1_08_FUNDEDNEXT_2023_HARNESSFIX_20260906.mq5` created with harness/output-only changes and SHA256 `10e86306d87b6d5f1c507ae724c629c972be0f53c3e586f2fd700691fadc1de4`.
- Static non-regression comparison confirms calendar/DST/cost/state, `WriteTrade`, and complete `OnTick` strategy logic are byte-identical to recovered v1.07. No ORB entry/stop/spread/commission/time-exit rule was intentionally changed.
- v1.08 fixes path escaping, requires M15 and CSV output, creates/flushed STATS `INIT` before TRADES, writes `READY` only after both files exist, records `FATAL_TRADES_OPEN` on output failure, writes source/version/symbol/timeframe/cost/paths, and flushes `FINAL` counters.
- Static lexical sanity passed, but this is **not** a MetaEditor compile. Compile status remains UNKNOWN until real FundedNext MetaEditor evidence exists.
- v1.08 source committed in `b0fb0bc6b557aea5c58cd56a041856a3a0bccd7b`.
- Static audit committed in `41b85bf753b3f7d7c89081f2773f907573a9ef96`.
- Local compile/smoke request committed in `561a9018ca9afb7452b5a0b8fbf3c86a1d1cdea3` and queued unread for Codex.
- `CURRENT_QUEUE.json` updated so D023 is `WAITING_CODEX`; full 2023 is explicitly blocked until compile/smoke/direct-output checks pass.
- `CURRENT_PROJECT_HANDOFF.md` rewritten to align all future resumes with the Sep-6 D023 P0 state rather than older D17/Banger execution orders.
- Short smoke interval frozen for harness validation: USDJPY M15 Every tick, 2023-03-13 through 2023-03-31. This crosses the US-vs-UK DST mismatch and UK DST transition. Expected server-London offset: 3h through 2023-03-24 weekdays, 2h from 2023-03-27.
- Inherited CSV convention documented: `TIME_1600` uses the close of the 15:45-16:00 London bar but records the bar-open timestamp 15:45 in `exit_time_*`; manual smoke verification must not misread that as an economic 15:45 exit.

**Time evidence**
- Early Guardian activity is confirmed from approximately 06:53 Europe/Paris through at least 07:57.
- Later Guardian work continued through multiple sessions during the day, including the restart/harness work through approximately 15:05 Europe/Paris.
- `CONFIRMED ACTIVITY SPAN: ~06:53 -> ~15:05 Europe/Paris`, but this includes breaks and separate sessions.
- `Human active total: NOT QUANTIFIED`; do not infer continuous work from the span.
- Strategy Tester / collectors / unattended compute are excluded from human time.

**Next**
- P0: sync exact D023 v1.08, verify SHA256, compile in the relevant FundedNext MetaEditor and require **0 errors / 0 warnings**.
- If compile passes, run only the short smoke `2023-03-13` through `2023-03-31`; verify STATS `INIT -> READY -> FINAL`, both deterministic outputs, `csv_trade_rows == trades_closed`, nonzero counters, at least three ORB sessions and both DST regimes.
- Do **not** run full `2023-01-02` through `2023-12-29` until compile + smoke + direct CSV/manual verification PASS.
- Only then run untouched 2023 once and score against the frozen gates. If it fails, do not rescue-filter the same sample.
- D17 remains closed as current alpha; preserve only manager/lineage evidence.
- Keep Guardian Core v12.01 stable and FundedNext AUTO off until the request/retry pathology is separately resolved.

### 2026-09-06 late session — AutoSync v1.04 runtime proof and D023 untouched 2023 rejection

**Work / decisions**
- FundedNext local execution path was clarified: research source/versioning remains under `D:\MT5_Backtests\guardian-research`, while FundedNext MT5 compile/backtest EAs are executed from `D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch`.
- D023 v1.08 compiled successfully in the user's FundedNext MetaEditor.
- Initial smoke attempts exposed an MT5 Strategy Tester selection/cache issue repeatedly loading the example Moving Average EA despite selecting D023; the test was corrected without changing D023 strategy semantics.
- D023 v1.08 smoke `2023-03-13` through `2023-03-31` completed and produced deterministic FILE_COMMON STATS/TRADES outputs.
- AutoSync engineering was repaired through v1.04. v1.02 failed because `$Args` collided with PowerShell automatic `$args`; v1.03 fixed that but Windows PowerShell treated normal Git stderr such as `From https://...` as terminating under `$ErrorActionPreference='Stop'`; v1.04 isolates native Git stdout/stderr and trusts the process exit code.
- AutoSync v1.04 was installed with Windows Startup and successfully auto-published the smoke to `backtest-results` without any per-backtest `-Once` command. Provenance, row counts and Windows username redaction passed.
- Smoke DST behavior passed: before the UK DST transition, FundedNext server UTC+3 vs London UTC+0; from 2023-03-27, London UTC+1 and server-London offset reduces from 3h to 2h as expected.
- The untouched full 2023 confirmation was then run exactly once on USDJPY M15 using the frozen D023 v1.08 strategy and auto-published successfully.
- Frozen 2023 confirmation result: n=195; total net R **-38.644330**; mean net **-0.198176R/trade**; net PF **0.708428**; 5-day moving-block bootstrap lower 5% bound of zero-filled weekday daily mean **-0.268783R/day**; 1.5x commission stress **-44.512458R total / -0.228269R/trade**.
- D023 passes only the sample-size gate: **1/5 frozen gates -> REJECT / UNCONFIRMED**. This is a material failure, not a borderline miss.
- Per preregistration, D023 is closed as current P0 alpha. Do not remove SHORT, add day/direction/EMA/RSI/ATR/news rescue filters, or tune on 2023.
- Canonical result persisted at `research/results/D023_USDJPY_2023_UNTOUCHED_CONFIRMATION_RESULT_2026_09_06.md`; `CURRENT_PROJECT_HANDOFF.md` and `CURRENT_QUEUE.json` updated accordingly.

**Time evidence**
- Late-session user/ChatGPT work is confirmed around the 16:00 Europe/Paris hour through this result/persistence phase.
- `Human active total: NOT QUANTIFIED`; do not infer continuous activity from the day's broad span.
- Strategy Tester runtime and watcher polling are unattended compute and excluded from human time.

**Next**
- Do not rerun or rescue D023.
- Reconcile the research slate and select the next independent preregistered strategy family.
- Keep AutoSync v1.04 as the proven D023 transport baseline; no per-backtest PowerShell command should be required.
- Keep Guardian Core v12.01 stable and FundedNext AUTO off until the separate request/retry pathology is bounded.

## 2026-09-07 — Challenge Probability Lab v1.00 and current-state reconciliation

**Work / decisions**
- New `Challenge Probability Lab` implemented as strategy-independent research infrastructure under `research/challenge_probability_lab/`; production Guardian Core was not modified.
- Objective frozen to challenge passage: estimate probability of reaching the profit target before daily/max drawdown violation, rather than maximize terminal profit.
- Default frozen risk grid: 0.10%, 0.15%, 0.20%, 0.25%, 0.33%, 0.50% per trade.
- Simulator consumes real R-based trade logs and resamples circular moving blocks of contiguous calendar days (default five days), preserving observed clustering/short regime persistence instead of iid-shuffling trades.
- Common random day paths are reused across risk levels for paired comparisons.
- Outputs include pass probability + Wilson 95% CI, daily/max/any DD violation probabilities, timeout, median/P25/P75/P90 days to pass, trades-to-pass and median/P90/P95/P99/worst-observed max DD, plus risk selected specifically for pass probability.
- Rules are external configuration; initial/reference-capital risk sizing is default, with static-initial or trailing-EOD max-loss anchors available.
- Optional `--day-column` supports a prop-firm-normalized challenge day; optional signed adverse-R supports stronger intratrade checks.
- Exactness boundary explicitly preserved: without synchronized floating-equity/mark-to-market data, v1.00 is an atomic/closed-equity simulator and can understate real floating DD breaches, especially with overlapping/multi-day positions.
- Engine and tests were locally validated: `py_compile` PASS and 8/8 unit tests PASS. A real-schema smoke using an 18-row excerpt of D037 `trades_compact.csv` loaded successfully and generated JSON/CSV/Markdown; no scientific performance conclusion was drawn from the tiny smoke.
- Validated engine Git blob: `0fbe86213b5d42dd4d8a6202e4e246ae2ed6ee75`; validated test blob: `800808538f1c2013cabb3a48c3ddaa787fb81853`.
- Implementation report persisted at `research/results/CHALLENGE_PROBABILITY_LAB_V1_00_IMPLEMENTATION_REPORT_2026_09_07.md`.
- Current-state reconciliation found `main` metadata lagging far behind the live result mirror. `backtest-results` shows D053 formal verdict `D053_REJECT_V0` and D054 latest confirmation status `D054_UNCONFIRMED_CLOSE`; no D055 directory was present when checked.
- `CURRENT_PROJECT_HANDOFF.md` was rewritten so stale D036 text no longer masquerades as the active P0. No new alpha P0 was invented; next alpha family must be independently selected/preregistered.

**Time evidence**
- This ChatGPT/Guardian session is confirmed from approximately 19:45 through 21:04 Europe/Paris.
- `CONFIRMED ACTIVITY SPAN: ~1h19`; this includes tool execution/testing and is not a claim of 1h19 continuous human keyboard time.
- `Human active total: NOT QUANTIFIED`.
- No unattended Strategy Tester/collector runtime is counted in this entry.

**Next**
- Do not use Challenge Probability Lab to rescue D053/D054 or any strategy that failed alpha/OOS gates.
- Run the Lab on the next strategy/portfolio only after its underlying trade evidence survives the normal scientific gates; use 20,000+ paths for a decision run with frozen seed/profile/block length/horizon.
- Extend future standardized harness exports with normalized `challenge_day`, signed MAE/adverse R, and ideally synchronized portfolio floating-equity snapshots to move from atomic DD estimation toward exact prop-firm DD simulation.
- Reconcile `CURRENT_QUEUE.json` when the next independent alpha family is formally selected.

## 2026-09-08 — preregistered Challenge pipeline v1.01 / queue reconciliation

**Work / decisions**
- Inspected a real frozen scorer (`analyze_d037_williams_prevday_range_v0_v1_00.py`) and deliberately **did not modify it**. Historical scorers remain frozen; post-result Challenge integration must be external.
- Added `post_validation_pipeline_v1_00.py` as a fail-closed scorer-to-gate bridge and validated its eligibility logic locally (6/6 policy checks PASS).
- Identified a remaining ex-post degree of freedom in selecting accepted verdict/stage/seed/risk grid after scorer observation.
- Added canonical `post_validation_pipeline_v1_01.py`, which requires a **pre-registered policy JSON** and refuses ad-hoc post-result choices for verdict acceptance, stage, Monte-Carlo path count, seed, risk grid or challenge-profile identity.
- Added `test_post_validation_pipeline_v1_01.py`; local prereg policy checks: **6/6 PASS**.
- Added `challenge_pipeline_policy_template_v1_00.json`; placeholders are intentionally rejected at runtime and must be replaced/committed before protected OOS/confirmation evidence is opened.
- v1.01 pins the challenge profile by SHA256 and writes scorer/policy/profile provenance into `challenge_lab_eligibility.json` before calling the lower-level gate.
- Integration smoke PASS: valid `CONFIRM` path propagates six risk levels, 20,000 paths and deterministic seed to the lower-level gate.
- Integrity smoke PASS: byte-level challenge-profile tampering causes SHA256 mismatch and fails closed.
- Updated `README.md`, `CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md` and `docs/RESEARCH_PROTOCOL.md` so the preregistered v1.01 pipeline is the scientific default.
- Reconciled `CURRENT_QUEUE.json`: removed stale D036 active-primary state, set `active_primary=null`, represented D053 rejected and D054 closed/unconfirmed, and marked Challenge Probability Lab Pipeline v1.01 as validated infrastructure.
- Updated `CURRENT_PROJECT_HANDOFF.md` to remove the stale queue warning and make the v1.01 flow canonical.
- Guardian Core v12.01 and production trading semantics were not modified.

**Time evidence**
- This session resumed during the early hours of 2026-09-08 Europe/Paris and continued through the repository reconciliation work.
- `Human active total: NOT QUANTIFIED`; do not infer exact active minutes from tool/commit timestamps.
- No unattended MT5/collector compute is counted here.

**Next**
- Select/preregister the next genuinely independent alpha family; do not rescue D053/D054.
- Build `challenge_day` + signed `adverse_r` into its export from the start.
- Before protected OOS/confirmation, instantiate and commit a campaign-specific policy from the Challenge pipeline template.
- After frozen scoring, run `post_validation_pipeline_v1_01.py` automatically. Failed alpha/OOS -> Lab skipped; successful alpha/OOS -> frozen Challenge pass-probability simulation.
- Later v2: synchronized portfolio mark-to-market/floating-equity snapshots for exact concurrent DD reconstruction.

---

# Current planning / backlog

## P0 — Next independent alpha family

- No current alpha P0 is promoted.
- D053 is formally rejected; D054 is closed unconfirmed.
- Select a genuinely independent family and preregister before opening protected evidence.
- Its future confirmation/OOS package must include the Challenge export contract and preregistered Challenge pipeline policy.

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

## P1 — Challenge Probability Lab

- Engine v1.00 + gate v1.00 + preregistered pipeline v1.01 are validated infrastructure.
- Default risk grid remains 0.10/0.15/0.20/0.25/0.33/0.50% and default decision run 20,000 paths/risk, but campaign policy must freeze these before protected results.
- Exact portfolio DD remains future work requiring synchronized mark-to-market/floating-equity snapshots.

## P1 — Manager evidence / D17 lineage

- D17 Momentum is closed as current alpha after broad seven-market attribution.
- Preserve exact lineage and paired Native-vs-Fixed manager results in `research/MANAGER_EVIDENCE_LEDGER.md`.
- Do not tune D17 to rescue inspected samples.
- A dedicated Manager Lab becomes justified only if a similar management weakness appears on an independent strategy family after entry confirmation.

## P1 — Shared Intelligence / Crypto+

- Keep Binance + Bybit collector running read-only.
- Continue accumulating BTC/ETH external history: spot/perp, OI, funding, liquidations, basis/dislocation and quality.
- D035 primary and D035-E1 are closed for immediate development. Preserve 2026-H1 untouched; do not consume it to rescue ETH/BTC diagnostics post hoc.
- Preserve `available_at <= event_time` for any forward EIB study.

## P1 — Guardian production continuity

- Guardian Core v12.01 remains the compile-validated pure infrastructure baseline.
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

## 2026-09-10 — Strategy factory r3 infrastructure repair

- Created immutable `strategy_factory_random_search_v1_02.py` from v1_01; only `atomic_json` changed: retry PermissionError on replace, six attempts, bounded delays 0.05/0.10/0.20/0.20/0.20 seconds, explicit exhaustion error chained to the cause. Other exceptions propagate immediately.
- Registered STRATEGY-FACTORY-MULTI-ASSET-RANDOM revision 3 in queue generation 31 with distinct strategy_factory_r3 output and RANDOM-R3 progress paths. r2 and its FAIL receipt remain intact.
- Scientific implementation and queue parameters unchanged: seed 260911, 250000 trials, same roots/limits, 2024 discovery, 2025 confirmation, thresholds, FDR and validation. No 2026 analysis or retuning. Existing publisher phase label remains unchanged because this repair only changes atomic writing.
- Seven focused regression tests PASS, including AST equality outside atomic_json and full normalized r2/r3 queue equality. Initial sandbox runs could not access Windows temporary directories; the same suite passed with normal Windows permissions.
- Process inventory before registration: no r2/r3 engine process; orchestrator PID 7580 active. r2 receipt confirms FAIL at 15:09:50 UTC on WinError 5. No manual engine launch and no live deployment.
- Next safe action: after commit/push, let the existing orchestrator fetch main and execute r3 once; observe its health/progress.
- Human active time: NOT QUANTIFIED. Automated test execution is not human time.

## 2026-09-11 — Issue #3 economic/execution gate BLOCKED

Queue-registration milestone: implementation published as a322ee9d99dcd456161d64db600b5ad52c9fe2a7; prepared generation 36 with one PRE-OOS-ECONOMIC-FEASIBILITY-SCREEN r1 job, prior jobs unchanged, no new automatic dependent. Existing orchestrator PID 7580 confirmed active; no matching full-run process/output/progress/receipt before registration. Final byte-identical-to-commit smoke 04 PASS (14.67 seconds, 1,148 ledger checks), after formatting-only feature-module normalization; no calibration. Next safe action is orchestrator-owned launch/status observation. Human active time NOT QUANTIFIED.

Later implementation milestone, same date: applied final owner decisions in a new v2 protocol; implemented validator v1_00 and pure R4 feature module. 43 synthetic tests PASS / 0 FAIL; final reduced smoke PASS, eight candidates and 1,148 functional ledger checks, no calibration. Fixed lazy NumPy loading and replaced future endpoint indexing with an actual causal source-bar counter before final smoke; retained attempts. Actual-code cold audit PASS for feasibility selection only. All four market reads match pre-2026 pins; source artifacts untouched. Owner authorized commit/push then a unique queue job if all PASS; next safe action is that registration and observation of existing orchestrator, never manual full launch. Human active time NOT QUANTIFIED; 22.55-second final smoke is automated runtime, not human time.

Subsequent owner-authorized scope update on the same date: prepared PRE-OOS ECONOMIC FEASIBILITY SCREEN v1 in `research/protocols/pre_oos_economic_feasibility_screen_v1/`. FundedNext optional/DISABLED; official FTMO fee component separated from fixed hypothetical execution budgets; four pre-2026 inputs hash-pinned using existing provenance metadata. Complete timing/overlap/sizing/eligibility/reporting/tests/smoke specification and separate future R4 recertification procedure prepared. Same-author cold audit PASS for the limited research-selection question only; implementation/runtime protection/tests/smoke NOT verified. No PnL, data-file reading, queue modification, economic job launch, commit or push. Queue generation 35 observed from external work; the generation 34 statement below describes the earlier preflight. Next safe action: present protocol and audit before queue work. Human active time NOT QUANTIFIED. Earlier BLOCKED evidence and R4/consolidation remain unchanged.

The 500 published R4 survivors remain the reference population; 32 frozen are secondary only. Cold preflight is BLOCKED before economic implementation: conflicting official FundedNext commission-side descriptions and no positively identified account model; no executable Bid/Ask in the four HCC-derived XAUUSD M1/M5 datasets. M5 spread is from the last M1, not an entry quote. Historical R4 inventory includes two 2026 files and the loader reads before filtering, so the hardcoded untouched flag is not proof of no access; this audit did not open them. Source publication equality is verified after LF normalization; all four pre-2026 dataset hashes match Phase I-B provenance. No new PnL, retuning, engine, job, protected OOS or live changes.

Evidence: `research/results/issue_3_economic_preflight_v1/COLD_AUDIT.md` and `data_provenance_audit.json`. Autonomous queue remains generation 34. Next safe action: resolve exact FundedNext model/commission sides, verify symbol units and execution-feed convention, then complete frozen protocol, validator, tests, smoke and second cold audit before any queue activation. Human time NOT QUANTIFIED; automated audit time is not human time.


## 2026-09-11 — R4 causal audit, R5 transition and repository continuity cleanup

- Completed R4 causal-capture forensic audit r1: PASS_INTERPRETABLE. M5↔M1 mapping checks passed with zero OHLC mismatches on complete buckets. The B→C decomposition attributed about 99.5% of the adverse degradation to ENTRY_DELTA in both 2024 and 2025; R4 close-to-close family was therefore closed rather than retuned.
- Stopped the already-running obsolete two-state interaction r2 child after determining it used the old close-to-close target and did not answer the causal-capture question. Its forced-stop FAIL is infrastructure/operator-stop evidence, not a scientific verdict.
- R5 causal-next-open r1 preflight failed before market-data access on a read-only NumPy array assignment. Immutable r2 repaired only array writability; repaired preflight PASS 6/6. R5 r2 then launched under queue generation 44.
- Latest operator-provided R5 progress snapshot: 100,000 / 150,000 discovery trials, 4,088 2024 discovery candidates, still in discovery_2024_causal_next_open. These are not confirmed survivors; 2025 confirmation remains inside the same run after discovery completes.
- Queue generation 45 disables all append jobs so no new work should auto-start after the already-running R5 r2 child finishes. Do not re-enable automatically.
- Created canonical continuity handoff: handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md and pointed CURRENT_PROJECT_HANDOFF.md to it.
- Performed a non-destructive repository cleanup: archived the previous accumulated current handoff, simplified CURRENT_PROJECT_HANDOFF.md, refreshed START_HERE_NEXT_AI.md, added docs/REPO_MAP.md and handoff/README.md, refreshed README.md, and added a temporal-state warning to GUARDIAN_MASTER_MANDATE.md so historical D0xx status cannot be mistaken for current campaign state.
- Historical results, protocols, receipts, code and handoffs were intentionally preserved for provenance; no scientific evidence was deleted.
- Next safe action: let R5 r2 finish, then cold-audit its execution-reference semantics, exact input provenance, protected-2026 evidence, HAC/BH-FDR implementation and adjacent-quantile confirmation before enabling any new phase.
- Human active time: NOT QUANTIFIED. Autonomous R5 compute time is separate and does not count as human time.


### 2026-09-11 — Operator superseded temporary overnight pause

- Operator cancelled the earlier request to pause the autonomous append queue after the current R5 run.
- Queue generation 46 restores R5 preflight r2 and R5 r2 to enabled state; commit `b53e7e3e97c0518037732fbbb5945367151766c2`.
- The already-running R5 r2 child is not restarted or interrupted by this change.
- No new downstream research phase is authorized merely by restoring the existing R5 queue entries; R5 completion still requires the planned cold methodology/code/provenance audit before new research work is added.
- Operator intends to leave the PC running overnight and shut it down tomorrow.


## 2026-09-16 — R21–R25 third-audit corrections

- Owner requested implementation after cold audit FAIL on cd40d686e002792753dd5e1a4d562340108de04d.
- Fixed canonical R15 metadata-path admission and pinned its SHA256 against the existing PASS union manifest; the builder uses a private snapshot of verified bytes. Fixed R22 baseline/replication diagnostics for horizons without valid event labels.
- Added regression tests; native synthetic engine/dependency/builder/queue suites PASS. Effective generation 83 remains exactly 3 jobs, 0 enabled, human_approved_2026=false.
- No historical backtest, market payload access, data modification, deployment or live authorization. Only the R15 provenance manifest and index metadata were read to establish the pin.
- Next safe action: independent cold review of the corrective commit, before any later queue activation. Correcting-author tests are not an independent audit.
- Human active time: NOT QUANTIFIED. Automated execution time is not human time.

## 2026-09-16 — R21–R25 control-plane hardening

- Confirmed that the deployed orchestrator resets its checkout to `origin/main`; the then-current GitHub main queue was generation 80 with legacy enabled jobs and therefore remained unsafe to restart.
- Prepared generation 84 as an explicit replacement of the empty generation-83 base: exactly three R21–R25 jobs, all revision 4, all disabled, and `human_approved_2026=false`.
- Bound local dependency and completion receipts to exact job identity, revision and executing `main_commit`; receipts from another commit cannot unlock or suppress a job.
- Confined v1.02 output to the canonical R21–R25 discovery JSON and added redirect/symlink rejection. Persisted the metadata-only R15 PASS-manifest attestation and linked it to the engine pin.
- No orchestrator restart, historical backtest, market-payload access, job activation, confirmation, 2025/2026 access, deployment or live authorization.
- Next safe action: independent cold audit of the small control-plane diff. Discovery stays disabled until that audit passes and the owner separately authorizes it.
- After explicit owner authorization, GitHub `main` was fast-forwarded to `74a12f25e2b665d1019ddee947d906559c2d1395`. The branch, `origin/main` and the local HEAD matched; the effective queue was recalculated as generation 84 with 3 jobs, 0 enabled and no 2026 authorization. The orchestrator was not restarted.
- Human active time: NOT QUANTIFIED. Automated test runtime is separate.

## 2026-09-16 — R34 signal/execution feed factorial

- Preregistered, independently cold-reviewed and executed immutable R34 v1.00 for frozen R6B-347, 2024–2025 only.
- Synthetic R34 and R33/R6/top2 regressions passed before launch. First cold review findings were corrected; second review found no blocker.
- Actual run completed: `SIGNAL_FEED_DOMINANT`, signal score 0.609622 versus execution 0.028650. FN signal produced 95/107 executed trades; Duka signal 163/168. Diagonals exactly reproduce R31/R33.
- Signal matching found zero pairs at exact, ±5 or ±10 minutes; no ex-post widening. Status COMPLETE, no tuning/live action, `protected_2026_opened=false`.
- Next safe action: independent result audit or separately preregistered feed-construction diagnostic; preserve R6B-347 unchanged.
- Human active time: NOT QUANTIFIED. Automated compute/review runtime is separate.
- Control-plane follow-up: generation 114 explicitly supersedes generation 113 and replaces all R33 jobs with an empty list. No R33/R34 calculation was relaunched and existing results were not modified.


## 2026-09-16 — R34 published-artifact independent audit

- Read pinned R34 source and published outputs. Independently recomputed eight year/cell ledger counts and E1/STRESS net/PF; nine Windows-source SHA256/size checks pass after explicit LF-to-CRLF reconstruction.
- Found all 95/107 FN signals at midnight versus zero Duka midnight signals; no ±10m pairs. Corrected '468 missing paired events' interpretation. Identified HCC record timeframe-admission weakness; real HCC contamination/availability is NOT yet established.
- Published read-only reproducible artifact auditor, measurements, source-diagnostic plan and ACTION_REQUISE handoff; inbox updated. No market replay, no R33/R34 rerun, no source/result/production changes, no 2026 access. Effective queue generation 114 remains untouched with no jobs.
- Next: Codex on the PC traces source records and causality under the frozen diagnostic. Local Windows access is unavailable in this session; no claim of running work there.
- Human active time: NOT QUANTIFIED. Automated audit runtime is separate.

## 2026-09-17 — Edge Atlas local-machine inspection

- Inspected Git state, canonical queue/checkpoints, real Windows processes and bounded filesystem/source metadata without launching any backtest, campaign, worker, MiMo task, cheap-fail or EA01–EA15 strategy.
- Persisted the four Edge Atlas inspection artifacts. Verdict `BLOCKED_PROCESS_ACTIVE`: orchestrator, external collector, synchronizers, PropFirmGuard, FundedNext terminal and MetaEditor are active; no metatester or research worker was observed.
- Admitted only the indexed pre-2026 raw Dukascopy `.bi5` union and price-only Binance 2017–2025 archives. Quarantined derived filled Dukascopy CSVs; blocked Bybit/OI and live external archives because their paths/coverage include 2026. FundedNext XAU remains excluded.
- Next safe action: reconcile active service ownership and stale checkpoints, then implement a read-only source admission gate; do not run Edge Atlas yet.
- Human active time: NOT QUANTIFIED. No automated research execution occurred.
- Read-only reconciliation completed without touching active services. Stale checkpoints/declared jobs were separated from real Guardian/live infrastructure; R33/R34/R35, MiMo, metatester and Edge Atlas workers were confirmed absent.
- Frozen admission manifest now allows only indexed Dukascopy BID M1 payloads through 2025 and exact-grid Binance spot M5 rows for 2024–2025. Bybit/OI, external 2026 archives, FundedNext XAU and artificial R30 CSVs are permanently excluded from this campaign.
- Shortlist revised before results: removed EA06/EA07/EA15; added catalogued EA09/EA16/EA20 using spot-only inputs. No cheap-fail launched. Next safe action is loader/preflight implementation, synthetic tests and independent cold review.


## 2026-09-17 - EA01 interruption recovery

- Inspected real processes, logs, receipt, quarantine, main queue and stale checkpoints without launching a job. Marker was already quarantined before this session; raw hash and receipt chronology verified.
- Rejected unsafe interrupted recovery draft; added offline-only recovery admission, Windows PID checks, exclusive statuses and persistent one-attempt guard. Preserved old receipt and BI5 error evidence.
- py_compile and 37 synthetic tests PASS; local cold review PASS. Checkpoint persisted before main publication. Only existing orchestrator may dispatch one recovery attempt.
- No protected 2026 payload opened; R33/R34/R35 unchanged. Next: observe single attempt receipt without manual rerun.
- Human active time: NOT QUANTIFIED; automated test time separate.


## 2026-09-22 — Return to crossed economic phenomena

- Audited the existing Guardian Edge Factory architecture and confirmed that the repository already contains the multi-resolution causal matrix, slow->fast as-of bridge, cross-family interaction machinery, conditional-edge machinery, and External Intelligence Bus needed for the original multi-source research vision.
- Explicitly avoided repeating V85's broad cross-family LO/HI conjunction search.
- Inventoried currently usable data: 13 core intraday markets, US nominal/real Treasury curves and breakevens/slopes, causal CFTC mappings/transforms, Treasury-auction archive, and BTC/ETH replayable external intelligence.
- Created and published GUARDIAN_CROSSED_PHENOMENA_MATRIX_V1_2026_09_22 with 16 historical phenomena and 3 forward-only crypto phenomena.
- Recommended Batch A: P01 real-yield+USD->gold, P04 oil->CAD residual, P06 NSX/SPX divergence x rates, P08 synthetic USD breadth divergence, P11 XAU/XAG relative value, P12 CFTC crowding x price shock.
- Explicitly blocked immediate mining of CBOE/CFE, financial conditions, FOMC, EIA and ALFRED where availability/provenance or architecture is not yet defensible.
- Preserved the V112 AUDUSD H21 120m SHORT locked-OOS result as a frozen separate lineage; no post-OOS optimization.
- No new edge trial was run and no 2026 data was accessed.
- Next safe action: preregister Batch A as separate economic-phenomenon lineages using the common causal infrastructure, before any computation.
- Human active time: NOT QUANTIFIED. No autonomous research compute is counted as human time.


### 2026-09-22 — Crossed phenomena Batch A preregistration

- Preregistered six economically defined lineages P01/P04/P06/P08/P11/P12 before compute.
- Frozen one common protocol: causal rolling beta 480 hourly observations / min 240; fast causal z min 250; slow daily-rate z min 126; event threshold |z|>=1.5; fixed 240m event cooldown; horizons 60/120/240m except P08 fixed 60/120m.
- Defined discovery 2010-2012 and untouched temporal holdout 2013. Batch-A discovery engine is physically restricted to V83B 2010-2013 artifacts and stops before any 2014+ read.
- Predeclared exactly 66 variants: P01 9, P04 6, P06 9, P08 6, P11 3, P12 33.
- Statistical inference uses cluster-robust OLS: UTC day clusters for continuous/event price phenomena, exact CFTC report-date clusters for P12.
- BH-FDR q<=0.05 is applied separately inside each economic lineage; only discoveries see the 2013 holdout. Holdout requires same frozen coefficient sign and one-sided cluster-robust p<=0.10.
- Added scripts/gef_crossed_batch_a_discovery.py plus run/watch PowerShell wrappers.
- No Batch-A edge computation has yet been run; no 2014+, 2023-2025 or 2026 market return was accessed by this implementation step.


### 2026-09-22 — Batch A V2 coverage-based temporal reset

- Source-only 2009-2022 coverage audit showed that 2010 was partial for UDX/index/oil-crossed phenomena while stable common coverage begins in 2011.
- V1 had already exposed invalid 2010-2012 coefficients/p-values, so V2 was defined as a fresh lineage without reusing those years for fitting.
- Coverage-only window rule selected warm-up 2012, discovery 2013-2016 and untouched 2017 holdout; future 2018-2019 replication and 2020-2022 validation were preregistered but are not opened by V2 discovery.
- Implemented V2 raw reconstruction from HistData M1, Treasury real-yield XML and CFTC Futures Only archives.
- Added mandatory 2013 parity against frozen V83/V83B price features and forward targets.
- V2 physically loads only 2012-2016 before discovery; 2017 is opened only after a BH discovery freeze; 2018+ is hard-forbidden.
- Same 66 economic variants and same thresholds/gates are retained. No V1 sign/result is inherited.


### 2026-09-22 — Batch A V2 support-collapse diagnosis

- Diagnosed GEFBA2-20260922-183722 after 0/66 valid tests.
- Confirmed the underlying crossed-state objects were healthy, while aligned forward targets collapsed to roughly 417/205/105 observations at 60/120/240m.
- Root cause 1: aligned_mask assumed nanosecond DatetimeIndex integer representation. Fixed by explicit conversion to numpy datetime64[m] before modulo.
- Root cause 2: REAL-rate as-of retained NaN z rows. Fixed to drop NaN z rows before merge_asof, matching V102/V103 semantics.
- No economic hypothesis, parameter, threshold, window, horizon or statistical gate was changed.
- 2017 and all later protected windows remained unopened by the failed run.
- Next step is read-only support revalidation before any new alpha scoring.


### 2026-09-22 — Batch A V2 scientific closure

- Final valid run: GEFBA2-20260922-193022, engine BATCH-A-V2-DISCOVERY-1.2.
- All 66 preregistered variants passed the minimum validity/support gate.
- Discovery 2013-2016 produced 2 BH discoveries, both in P11 XAU/XAG relative value.
- The two P11 candidates were frozen before 2017 was opened.
- Both failed the preregistered 2017 temporal holdout, leaving 0 survivors.
- P01/P04/P06/P08/P12 had no BH discovery; P11 failed holdout.
- Batch A V2 is therefore scientifically closed with no rescue or retuning.
- 2018+ / 2023-2025 / 2026 remained unopened.
- Next research wave: Batch B P02/P03/P05/P07/P09/P10/P13/P14.


### 2026-09-22 — Pivot to M5 Motion Topology Factory V1
- User reframed the target around M5 movement endings, local highs/lows, simultaneous movement, inter/intra-asset co-movement, repeated motifs and crossings.
- Existing Guardian families 5, 6, 21 and 22 plus P09/P10 overlap materially but had not been organized around execution-time M5 endpoint prediction.
- Frozen a new 12-family M5 topology campaign before compute.
- Added recurring tradability mask with close/reopen buffer to avoid session-gap artifacts.
- Frozen 2012-2014 discovery, 2015-2017 replication, 2018-2022 validation, 2023-2025 locked OOS, 2026 protected.
- Batch B macro parked, not discarded.


### 2026-09-22 — M5 Motion Topology V1 cache builder implemented
- Added a no-alpha phase-1 builder using only 2011-2014 HistData.
- Builder writes per-market M5 OHLC, intra-asset states, endpoint-score targets, recurring tradability masks and cross-market state cache.
- Tradability is inferred from recurring 5-minute slot availability in 2012-2014 with a 95% requirement and 30-minute close/reopen buffer.
- Endpoint target compares normalized reversal excursion vs continuation excursion for 15/30/60m established moves and 15/30/60m forward paths.
- Cross state includes breadth, dispersion, shock breadth, rolling-beta residuals, residual z, short-vs-long correlation break and 5/10/15m lagged pair returns.
- No edge trial or outcome association is performed.
- First builder hard-stops at 2014; 2015+ remains unopened.


### 2026-09-22 — M5 topology cache completed, integrity audit gate
- Cache run GEFM5T-20260922-200657 completed with 13 markets, 13 graph edges, 199 cross features and 117 endpoint objects.
- No alpha/edge trials were performed and no 2015+ outcomes were opened.
- Endpoint support is large (minimum 22,129 observations across L/H objects).
- Added a read-only integrity audit before M01-M08 preregistration, focused on recurring session-mask shape, OHLC integrity, target marginal distributions, joint graph support and cross-feature finite support.
- Special attention: SPXUSD, UDXUSD and BCOUSD masks are materially narrower than FX masks and must be verified as source/session structure rather than accidental overfiltering.


### 2026-09-22 — M5 topology V1 cache audit and V1.1 session-mask amendment
- V1 cache audit passed OHLC integrity, endpoint distributions, joint graph support and cross-feature support.
- V1 recurring UTC-slot tradability mask failed session-shape plausibility: SPX/UDX/NSX/BCO were heavily fragmented.
- Since zero alpha/edge tests had been run, replaced only the session eligibility infrastructure before research.
- V1.1 uses date-specific observed continuity with 30m boundary buffers around gaps/closures and reopens/recoveries.
- All scientific target/state definitions and temporal firewall remain unchanged.
- Added V1.1 builder and integrity audit. M01-M08 remain blocked until V1.1 cache audit passes.


### 2026-09-23 — M01-M08 M5 topology discovery preregistered and implemented
- V1.1 cache audit passed session continuity, OHLC integrity, endpoint support, joint graph support and cross-feature support.
- Frozen 291 exact M01-M08 discovery variants before any outcome association.
- Restricted scales to 15->15, 30->30 and 60->60.
- Frozen 30m event cooldown, >=200 independent episodes, >=120 days, cluster-robust one-sided positive endpoint-score test and BH q<=0.05 within each family.
- Implemented discovery engine using V1.1 cache only through 2014; 2015+ remains inaccessible.
- No TP/SL or execution optimization is part of this stage.


### 2026-09-23 — M01-M08 discovery completed; M04 replication frozen
- Discovery run GEFM5D-20260923-052315 materialized all 291 preregistered variants; 262 met support validity.
- Six BH discoveries survived, all in M04 correlation break + recoupling and all involving UDX with EURUSD/GBPUSD/AUDUSD/USDCHF.
- Other M01-M08 families produced zero BH discoveries.
- 2015+ remained unopened during discovery.
- Frozen the exact six M04 survivors with parent survivor hash ba4323dabdb2e43c2a86d1ff6be53297a41847e00017f2098f328998ba195bb6.
- Preregistered exact 2015-2017 replication with no retuning: >=100 episodes, >=60 UTC days, positive endpoint effect, one-sided cluster p<=0.05.
- Replication engine reconstructs causal history from 2011 and requires pre-2015 parity against the discovery cache before scoring.
- 2018+ remains forbidden.


### 2026-09-23 — M04 replication 5/6; independent validation preregistered
- Exact 2015-2017 replication run GEFM5R-20260923-053206 passed pre-2015 parity for all four UDX/FX objects.
- Five of six frozen M04 discovery variants passed replication.
- AUDUSD/UDX L30 failed with negative mean endpoint and is closed without rescue.
- Remaining five variants are treated as correlated manifestations of one M04 UDX/FX recoupling family.
- Frozen independent 2018-2022 validation before access.
- Added stricter validation gates: year consistency, leave-one-year-out positivity and trim-best 1%/2% positivity, plus primary cluster significance.
- Family validation requires at least three of five exact variants to pass all gates.
- Added a separate pre-2018 reference freeze step so the validation engine must match the 2011-2017 replicated objects before scoring 2018-2022.
- 2023-2025 and 2026 remain unopened.


### 2026-09-23 — M04 validation gates simplified before 2018-2022 access
- Removed additional hard rejection gates introduced after replication.
- Restored validation to simple pre-outcome hard gates: support, positive mean endpoint and one-sided cluster significance.
- Year consistency, LOO, trim-best and placebo outputs remain diagnostics, not automatic rejection criteria.
- No 2018-2022 outcome had been accessed before this amendment.


### 2026-09-23 — M04 pre-2018 reference frozen
- Frozen reference run GEFM5P-20260923-055333 with 736,416 rows and SHA256 49eb9c029247ee2418cc06cac3cacd44c1a692e46b537e982c00b3ef0b016c84.
- Recomputed all published 2015-2017 replication aggregates with parity PASS; differences were floating-point epsilon only.
- No 2018+ outcome was accessed.
- M04 validation 2018-2022 is now ready under engine v1.1 and the simplified hard gates.


### 2026-09-23 — M04 validation: 2/5 primary passes
- Validation run GEFM5V-20260923-055623 tested the five frozen replication survivors on 2018-2022.
- EURUSD/UDX L15 and AUDUSD/UDX L15 pass the amended hard gates.
- GBPUSD L15 narrowly misses significance at p=0.053625; GBPUSD L30 and USDCHF L15 fail.
- EURUSD is robust to trim-best 1%/2%; AUDUSD is not and is tail-sensitive.
- +/-60m diagnostics show the effect is not narrowly localized to the exact recoupling timestamp, especially at -60m.
- No 2023-2025 or 2026 data opened. Campaign is at the human gate before locked OOS.


### 2026-09-23 — M04 locked OOS 2023-2025 prepared after human approval
- Owner approved proceeding to the locked OOS stage.
- Frozen exactly two validation survivors: EURUSD/UDX L15 and AUDUSD/UDX L15.
- Preregistered unchanged M04 signal/target and simple locked-OOS gates.
- Added a pre-2023 reference freeze using only 2011-2022 to reproduce validation before opening 2023.
- Added locked OOS engine restricted to 2011-2025 with 2026 hard-forbidden.
- No 2023-2025 or 2026 result has been opened by this implementation step.


### 2026-09-23 — M04 pre-2023 reference frozen
- Frozen reference run GEFM5LREF-20260923-061953 with 1,262,304 rows and SHA256 c5d64fa7d7e375fa1434a4989317c7b2eff92d0239e7a6c48709bd42d6c90c23.
- Reproduced the published 2018-2022 validation aggregates for EURUSD L15 and AUDUSD L15 with parity PASS; differences were floating-point epsilon only.
- No 2023-2025 or 2026 outcomes were accessed.
- Locked OOS 2023-2025 is now ready.
