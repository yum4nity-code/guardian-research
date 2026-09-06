# D036 v1.01 harness PnL integrity repair — preregistration

Date: 2026-09-06

## Trigger

During frozen `D036_DEV_2024_2025`, EURUSD and GBPUSD v1.00 outputs ended with `trades_opened=476`, `trades_closed=475`, `csv_trade_rows=475`, while `invalid_risk=0`. The generic AutoSync correctly rejected both pairs because one opened simulated trade was absent from each trade ledger.

Static inspection of `D036_DonchianTrendBreakout_H1_v1_00_FUNDEDNEXT_HARNESS_20260906.mq5` identified a harness-integrity failure mode in `WriteTrade()`: when `MoneyPnL()` / `OrderCalcProfit()` fails, the code prints a fatal message and calls `ResetTrade()` without incrementing `trades_closed`, without writing a CSV row, and without marking the entire run invalid. This can silently discard an opened trade.

## Frozen repair scope

Create a distinct source version/file `v1_01`; never overwrite v1.00.

The repair MUST NOT change any D036 strategy semantics or parameters:
- H1 timeframe;
- 20-bar close breakout entry rule;
- next-H1-open executable-side entry;
- ATR(20) initial stop at exactly 2.0 ATR;
- 10-bar opposite Donchian exit;
- no TP, no BE, no trailing, no pyramiding, no filters;
- same FundedNext commission model;
- same development dates and universe.

The repair is limited to output/PnL integrity:
1. `OrderCalcProfit()` remains the primary P/L method.
2. For EURUSD and GBPUSD only (USD quote currency, 1-lot research calculation), if exit-side `OrderCalcProfit()` returns false, use the exact quote-USD fallback `contract_size * signed(exit-entry)` for one lot.
3. If neither primary nor allowed fallback produces a finite P/L, increment a dedicated `pnl_calc_failures` counter and mark the run invalid; never silently discard the trade and never emit a valid `FINAL`.
4. Add observability for PnL calculation failures to STATS.
5. Existing strict AutoSync validation (`opened == closed == CSV rows`) remains unchanged.

## Rerun rule

Only the two rejected/incomplete ledgers, EURUSD and GBPUSD, need to be rerun under v1.01. BTCUSD, ETHUSD, USDJPY and XAUUSD v1.00 outputs already passed strict transport/integrity validation and are not rerun merely because of this non-semantic harness repair.

The EURUSD/GBPUSD v1.00 incomplete ledgers MUST NOT be used for alpha scoring.

No outcome-driven parameter changes are permitted after the repaired runs are observed.
