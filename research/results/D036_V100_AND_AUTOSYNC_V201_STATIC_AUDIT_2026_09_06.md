# D036 v1.00 + Generic AutoSync v2.01 — static audit — 2026-09-06

Status: STATIC-AUDITED / LOCAL RUNTIME VALIDATION PENDING

## D036 v1.00 harness

Source: `research/strategies/d036/D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5`

Static checks passed:
- hard H1 tester guard;
- frozen six-symbol universe guard;
- USD account-currency guard for the FundedNext commission model;
- 20-bar breakout excludes signal bar (`r[2..21]`), then enters next H1 bar (`r[0]`);
- ATR(20) is read at the closed signal bar (shift 1);
- initial stop is exactly 2.0×ATR from executable entry;
- 10-bar opposite channel excludes current exit-test bar (`r[2..11]`);
- long entries use ask-side spread; short exits/stops use executable ask side;
- gap fills use worse opening price;
- same-bar stop/channel ambiguity chooses the economically worse valid exit;
- no pyramiding, TP, time exit, EMA/RSI/news/day filters or strategy parameter search;
- development/smoke trade cannot be carried into a locked next stage; stage/test end is explicitly logged;
- money R uses 1-lot `OrderCalcProfit` initial-stop risk and realized P/L;
- FundedNext baseline commission is class-specific: Forex USD5/lot/side; metals 0.0016% notional/side; crypto 0.04% notional/side;
- 1.5× commission-stress net R is emitted per trade;
- deterministic FILE_COMMON STATS/TRADES names include stage and symbol;
- STATS lifecycle is INIT -> READY -> progress -> FINAL; FINAL counters expose opened/closed/CSV rows.

Runtime requirement remains mandatory: real FundedNext MetaEditor compile 0 errors / 0 warnings and three-class March-2025 smoke before any 2024-2025 alpha run.

## D036 scorer

Active scorer: `research/analysis/analyze_d036_donchian_v0_v1_01.py`.

It emits aggregate/per-symbol/per-year/per-side/exit diagnostics, concentration, max losing streak, baseline/stressed costs and frozen development/confirmation gates. v1.01 avoids JSON failure on mathematically infinite PF by using an explicit finite sentinel.

## Generic AutoSync v2.01

Source: `automation/Guardian_Backtest_CSV_AutoSync_v2_01_GENERIC_PUBLICSAFE.ps1`.

Static checks:
- supersedes/stops the D023 v1.04 and generic v2.00 startup/PID state on install;
- persistent Windows Startup watcher, no per-backtest `-Once` workflow;
- watches only new `Dxxx_V..._STATS.csv` files created/modified after installation and their exact `_TRADES.csv` companions;
- stable-pair delay before reading;
- requires INIT -> READY -> FINAL;
- validates source/version/symbol/timeframe and `trades_closed == csv_trade_rows == physical TRADES rows`;
- when available, also requires `trades_opened == trades_closed`;
- hashes inputs before/after validation;
- PUBLICSAFE redacts `C:\Users\<name>` from STATS and blocks obvious credentials/emails;
- deterministic run id and collision/restart recovery if Git push succeeded before local state write;
- native Git execution isolates stdout/stderr and uses exit code, retaining v1.04's validated fix;
- bounded retry and resident watcher loop;
- writes generic health/log/state/PID files.

v2.01 is static-audited only here because this environment has no Windows PowerShell runtime. Its first local installation must be followed by one health check; then it should remain resident/autostart for D036 and future Dxxx harnesses using the common STATS/TRADES contract.
