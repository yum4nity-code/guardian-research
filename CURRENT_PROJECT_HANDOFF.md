# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-06 Europe/Paris
Status: **ACTIVE / D036 DONCHIAN H1 V0 PREREGISTERED / HARNESS V1.00 STATIC-AUDITED / GENERIC AUTOSYNC V2.01 STATIC-AUDITED / LOCAL COMPILE+SMOKE PENDING**

## Canonical resume

Read first:
1. `CURRENT_QUEUE.json`
2. this file
3. `START_HERE_NEXT_AI.md`
4. `GUARDIAN_MASTER_MANDATE.md`

Do not reopen rejected families merely because they remain in historical documents.

## Active P0 — D036 Donchian / Turtle-inspired Trend Breakout H1 V0

Preregistration:
`research/campaigns/D036_DONCHIAN_TREND_BREAKOUT_H1_V0_PREREGISTRATION_2026_09_06.md`

MT5 no-order harness:
`research/strategies/d036/D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5`

Scorer:
`research/analysis/analyze_d036_donchian_v0_v1_01.py`

Static audit:
`research/results/D036_V100_AND_AUTOSYNC_V201_STATIC_AUDIT_2026_09_06.md`

### Frozen strategy

Exactly six markets:
- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Tester timeframe: H1.

Signal at closed bar S:
- LONG iff close(S) > highest HIGH of the preceding 20 complete H1 bars;
- SHORT iff close(S) < lowest LOW of the preceding 20 complete H1 bars;
- enter next H1 open on executable spread side.

Initial stop:
- exactly 2.0 × MT5 ATR(20) measured at signal bar S.

Exit:
- protective initial stop, or
- opposite 10-complete-H1-bar Donchian channel;
- gap beyond threshold fills at worse executable bar-open price;
- if stop and channel are both touched in one OHLC bar and order is ambiguous, take the economically worse valid exit.

No pyramiding, TP, time exit, BE, trailing ATR, RSI, EMA, ADX, news/day/direction filters or parameter search.
One open D036 position per symbol max. Same-bar exit + opposite 20-bar signal may reverse at the next H1 open.

This is explicitly a **Turtle-inspired intraday adaptation**, not a claim to reproduce the historical Turtle system verbatim.

### FundedNext frozen costs — Stellar 1-Step / 2-Step

- Forex: USD 5/lot/side.
- Metals: 0.0016% × lot × contract size × execution price, per side.
- Crypto: 0.04% × lot × contract size × execution price, per side.
- Spread is tester MqlRates executable-side spread.
- Net R uses 1-lot `OrderCalcProfit` money P/L / initial-stop money risk.
- Harness emits baseline net R and net R with commission ×1.5 per trade.
- USD account currency required for valid frozen cost accounting.

## D036 data sequence — frozen before outcomes

### 1. Compile gate
Real FundedNext MetaEditor compile of exact v1.00 source: **0 errors / 0 warnings required**.

### 2. Smoke gate — no alpha scoring
Period: `2025-03-03` through `2025-03-31`.
Run exactly one representative symbol per FundedNext commission class:
- USDJPY — Forex
- XAUUSD — Metal
- BTCUSD — Crypto

Input stage must remain `D036_SMOKE_MAR2025`.
Purpose only: output lifecycle, channel chronology, ATR/stop logic, executable spread side and three commission classes.

Require:
- STATS ordered INIT -> READY -> FINAL;
- `trades_opened == trades_closed == csv_trade_rows == physical TRADES rows`;
- no PUBLICSAFE leak after AutoSync;
- plausible signal/entry chronology and cost values in all three classes.

### 3. Development / cheap-fail sample
Only after smoke PASS:
- `2024-01-02` through `2025-12-31`;
- all six symbols;
- stage `D036_DEV_2024_2025`.

Frozen continuation gates — all required:
- aggregate n >= 180;
- each symbol n >= 20;
- aggregate mean net R >= +0.08R/trade;
- aggregate net PF >= 1.15;
- >=4/6 symbols positive total net R;
- aggregate 2024 positive and aggregate 2025 positive;
- aggregate remains positive at 1.5× commission;
- no single symbol >60% of positive-symbol net-R contribution.

Any fail => **REJECT_V0**, no parameter/timeframe/direction rescue on opened 2024-2025 data.

### 4. Untouched confirmation — HARD LOCK until development passes
- `2026-01-02` through `2026-06-30`;
- all six same symbols;
- same code/semantics/cost model;
- stage `D036_CONFIRM_2026_H1`.

Frozen confirmation gates — all required:
- aggregate n >=45;
- mean net R >0;
- PF >=1.10;
- >=3/6 symbols positive total net R;
- positive aggregate at 1.5× commission.

Do not inspect 2026-H1 to rescue a failed development result.

## Reporting requirement for D036

Do not return only `N / expectancy / PF`.

Each scored D036 result must include:
- aggregate + per-symbol N, total/mean/median net R, win rate, PF;
- long vs short contribution;
- year contribution on development;
- stop vs channel exit share;
- strongest/weakest symbol and profit concentration;
- max gain/loss and largest losing streak where available;
- baseline vs 1.5× commission stress;
- stability/failure-mode interpretation;
- explicit decision and next action.

Keep the concise top line, but follow it with the richer diagnostic.

## Generic GitHub AutoSync — v2.01

Active prepared watcher:
`automation/Guardian_Backtest_CSV_AutoSync_v2_01_GENERIC_PUBLICSAFE.ps1`

Purpose: replace the D023-specific watcher with one persistent transport contract for future `Dxxx` harnesses.

On install it:
- stops/removes D023 v1.04 and generic v2.00 startup/PID state;
- installs one Windows Startup watcher;
- ignores historical CSVs older than installation time;
- watches new `Dxxx_V..._STATS.csv` + exact `_TRADES.csv` companion pairs;
- waits for stable files;
- requires INIT -> READY -> FINAL;
- validates source/version/symbol/timeframe, closed/CSV/physical rows and opened==closed when exposed;
- hashes before/after validation;
- redacts Windows username paths and blocks obvious secret/email leakage;
- uses native-Git exit-code handling inherited from the runtime-proven v1.04 fix;
- uses deterministic run identity and recovers push-before-state crashes;
- writes health/log/state/PID under `D:\MT5_Backtests`.

v2.01 is static-audited here but not yet Windows-runtime validated. After its first local install, only one health check is required. Normal later backtests must not require `-Once`.

## Local execution paths

Canonical Git repo/source/versioning:
`D:\MT5_Backtests\guardian-research`

FundedNext MT5 compilation/backtest EA folder:
`D:\MT5_FundedNext\MQL5\Experts\GuardianReasearch`

All FundedNext backtest `.mq5` execution copies go in that `GuardianReasearch` folder unless the user explicitly changes this convention.

## Closed alpha families — do not rescue

### D023 USDJPY London ORB
Untouched 2023: n=195, total -38.644330R, mean -0.198176R, PF 0.708428, 1/5 gates. **REJECTED / UNCONFIRMED.** Preserve evidence only.

### D17 Momentum
Closed after broad seven-market attribution. Preserve lineage and Manager Evidence Ledger only.

D022, D027, D028 and D029 are reconciled as closed/rejected legacy families in `CURRENT_QUEUE.json`; do not blindly relaunch them.

## Guardian production / compliance separation

Guardian Core v12.01 remains the stable compile-validated pure infrastructure baseline. Keep strategy research out of Core.

FundedNext request/retry hyperactivity remains a separate P1/P0 compliance-runtime problem. FundedNext AUTO stays OFF until request budgeting/dedup/backoff is bounded. Do not mix that issue into D036 alpha scoring.

## Next safe action

1. sync repo locally;
2. install Generic AutoSync v2.01 once and verify health;
3. copy exact D036 v1.00 source into the FundedNext `GuardianReasearch` execution folder;
4. compile 0 errors / 0 warnings;
5. if compile passes, run the three March-2025 smoke symbols only;
6. allow AutoSync to publish automatically;
7. audit smoke before opening 2024-2025 development.

No 2024-2025 alpha run before compile + smoke PASS.
