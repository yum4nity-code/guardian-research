# Guardian — Project Planning & Time Log

Last reconstructed: 2026-09-06 Europe/Paris
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

## 2026-09-06 — D035 verdict, cross-strategy autopsy, E1 close, META-A1 preparation, D17 lineage reopening, Banger Lab V1

**Work / decisions — early session**
- User returned the complete `D35 OUTPUT.zip` from the frozen D035 2024-2025 development run.
- D035 data quality was strong: 5,558 merged BTC/ETH source events, 38,622 target-event rows, nine FundedNext crypto CFDs, complete loaded Binance metrics/1m archive QA, and 114/114 server->UTC calibration weeks usable with mean correlation ~0.996.
- Frozen D035 primary gate closed **REJECT 4/8**: pooled executable SHORT +15m -25.448 bps; event-control differential +5.179 bps; bootstrap differential [+3.033,+7.385] bps; pooled executable +30m -25.438 bps; BTC-only differential -3.281 bps vs ETH-only +3.283 bps.
- Post-hoc audit found that the superficially strong `BTCUSD+ETHUSD` subgroup leaked future information if interpreted from the first source timestamp. A causal E1 was preregistered with the signal moved to the later/second shock and XLMUSD frozen as primary.
- User returned `D35 CASUAL.zip`. D035-E1 completed with 973 causal dual events. XLMUSD primary n=870: mean executable +15m **+6.705bps**, median **0.000bps**, event-control differential **+13.490bps**, raw bootstrap **[+1.996,+11.549]**, differential bootstrap **[+8.793,+18.302]**, +30m **+3.697bps**, 2024 **+4.104bps**, 2025 **+9.935bps**.
- Frozen E1 gate closed **6/8 -> E1_DO_NOT_ADVANCE** because mean executable +15m failed >=15bps and median was not >0. ETH/BTC diagnostics looked better but were not the frozen primary and were not promoted. 2026-H1 remains untouched. D035 family closed for immediate development.
- Cross-strategy edge-decay autopsy completed. Main conclusion: short-window profitability versus long-history decay reflects regime dependence, raw-signal vs managed-system/account-state mismatch, multiple testing, CFD cost drag and data provenance. D032 remains proof that the stricter protocol can still confirm a large edge.
- META-A1 Momentum v1.00 was prepared from v11.16.19 with Momentum thresholds unchanged and RSI disabled for the experiment, logging raw/filtered/actual/management layers. Static QA passed; MQL5 compile remains external/mandatory.

**Work / decisions — later session**
- Short-window reruns and file confusion showed that v11.16.19 can no longer be treated as the sole authoritative D17 lineage anchor without a non-regression match. The earlier instruction to stop looking for older D17 sources is superseded by new evidence and user uncertainty.
- Guardian Finder located multiple historical Momentum candidates. GitHub inspection confirmed `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` and the documented v11.16.5→v11.16.11 lineage.
- `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md` records that v11.16.11 added top-level Momentum/RSI switches without changing strategy parameters. This becomes a useful lineage anchor rather than assuming the later monolith is exact.
- User reported that the D17 currently running on FTMO is behaving reasonably in practice, particularly the stop that ratchets upward/downward with favorable price. This is retained as operational evidence only, not a performance validation.
- Source inspection confirms the later D17 native Momentum manager uses TP1 2R / 25%, true-net BE around 1.25R and 1.75 ATR trailing that only moves the stop in the risk-reducing direction. Decision: preserve and attribute this manager before simplifying or tuning it.
- External literature review strengthened that decision: trailing/stop overlays can materially alter momentum risk-adjusted outcomes, with benefit depending on volatility, serial correlation and signal quality. This does not prove the D17 manager works on BTC, but makes exact management attribution scientifically necessary.
- **Guardian Banger Lab V1** created and committed (`research/results/GUARDIAN_BANGER_LAB_V1_2026_09_06.md`, commit `8786bb393c3641fcef0997452501a0af9e9d061f`). It proposes a multi-sleeve `GUARDIAN HYDRA V0` rather than an opaque super-score: D17 native-ratchet Momentum + frozen USDJPY London ORB after untouched confirmation + confirmed sparse D032 Doji reversal + new BTC Deribit 0DTE expiry sleeve after replication/CFD transfer.
- A predeclared **D17 Native Ratchet attribution** is now P0: exact same entries, compare only NATIVE vs FIXED-3R vs TIMEBOX; no parameter grid. Required outputs include exact SL ratchet path, TP1/BE events, MFE/MAE/touch ordering, full costs and Guardian/account-state blocks.
- New external candidate: **BTC Deribit 0DTE expiry reversal**. A 2026 Finance Research Letters study reports a high-ATM-OI expiry effect with negative return into 08:00 UTC and reversal afterward; the working-paper narrative gives short 07:00→08:00 then long 08:00→09:00 and an after-cost annualized Sharpe around 0.92. This is treated only as external source evidence; target-CFD validation is mandatory.
- Read-only forward observer `research/external_intelligence/deribit_expiry_observer_v1.py` created and committed (`51633a2ce1dece72a05c07e11b08bacd2b288825`). It collects public Deribit 0DTE ATM OI around 07:00 UTC and uses only prior observations for an expanding top-decile gate. Python `py_compile` PASS and deterministic self-test PASS. **Live Deribit network execution was NOT run in this environment.**
- A separate experimental **Liquidation Cascade Exhaustion Reclaim** hypothesis was frozen conceptually: extreme BTC 5m drop + OI contraction + cross-venue long-liquidation burst, wait for M5 reclaim, then long with cascade-low stop and 120m time exit. It is distinct from rejected D035 delayed-short lead/lag. Historical synchronized OI/liquidation data remain the bottleneck.
- `CURRENT_PROJECT_HANDOFF.md` updated to reflect D17 lineage reopening and Banger priorities (commit `7b76cb4d3ec259236d03ec6f6c8c8b6b0fcb32f3`).

**Time evidence**
- Early Guardian activity is confirmed from approximately 06:53 Europe/Paris through at least 07:57.
- A later Banger Lab session resumed at approximately 10:25 Europe/Paris and continued materially through this ledger update; exact active duration is not responsibly measurable from available evidence.
- `Human active total: NOT QUANTIFIED` for the day. Strategy Tester / collector / analysis waiting is excluded.

**Next**
- P0: resolve exact D17 source/non-regression using the GitHub `MOMENTUM_PROD` anchor and the live/local D17 branch, then run Native vs Fixed-3R vs Timebox attribution without retuning 2R/25%, 1.25R BE or 1.75 ATR trail.
- Run an untouched confirmation of frozen USDJPY D023 ORB before any promotion.
- Start Deribit 07:00 UTC forward OI snapshots; separately source provenance-clean historical Deribit option-chain OI for 2021-2023 replication and target-CFD transfer.
- Preserve D032 Doji as confirmed sparse sleeve; do not force frequency or rescue failed managers.
- Test Cascade Reclaim only when adequate synchronized OI/liquidation history exists.
- Activate D024 portfolio overlap/equity replay only when at least two sleeves independently validate.
- FundedNext Algo Trading remains OFF until request-budget/retry pathology is resolved and the clean replacement core is compiled/smoked.

---

# Current planning / backlog

## P0 — D17 Native Ratchet lineage + attribution

- Do not assume v11.16.19 is authoritative solely because it is later.
- Use the GitHub `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5`, v11.16.11 changelog, any matching local/live source and non-regression trade behavior to identify the actual D17 branch.
- Preserve native management while testing: TP1 2R/25%, true-net BE ~1.25R, 1.75 ATR one-way ratchet.
- Once entry behavior is fixed, compare only NATIVE / FIXED-3R / TIMEBOX on identical trades. No optimization grid.
- Attribute raw signal, strategy-local selection, Guardian/account-state selection, manager lift and cost drag separately.
- META-A1 v11.16.19 pack remains available as an instrumentation artifact but is not the mandatory next long backtest until lineage is matched.

## P0 — Guardian Banger Lab V1

- Hydra V0 candidate sleeves: D17 native-ratchet Momentum; USDJPY D023 after untouched confirmation; D032 confirmed Doji reversal; Deribit 0DTE expiry after historical replication/CFD transfer.
- Research-only frozen risk proposal before portfolio replay: 0.25% / 0.20% / 0.20% / 0.15%, account open-risk cap 1.00%, no dynamic performance sizing.
- Start Deribit forward OI collection now; historical option-chain OI provenance is required before a retrospective claim.
- Cascade Reclaim stays a separate experimental family and must not reuse D035 results as validation.

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
- D035 primary and D035-E1 are closed for immediate development. Preserve 2026-H1 untouched; do not consume it to rescue ETH/BTC diagnostics post hoc.
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