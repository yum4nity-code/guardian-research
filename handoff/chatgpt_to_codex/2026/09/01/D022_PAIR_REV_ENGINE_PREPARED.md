# D022 — pair-reversion engine prepared by ChatGPT

STATUT: IMPLEMENTATION PREPARED / WAITING FOR USER-PC DATA

ChatGPT has already implemented the preregistered D022 cheap-fail engine locally as:
`d022_pair_rev_eventstudy.py`

Expected user-PC destination:
`D:\MT5_Backtests\automation\d022_pair_rev_eventstudy.py`

SHA256 of the prepared script:
`f3e84a8ce27fe7a55a378882f7564dce7f0654ebf8fa5dbb83eaf6e040228486`

The script was syntax-compiled and exercised end-to-end on synthetic M15 MT5-style data. The synthetic run produced valid trades, two-leg spread/commission costs, pair summaries, aggregate summary, CSV trades and JSON verdict output. Synthetic results are ONLY a software self-test, not market evidence.

Implemented frozen D022 semantics:
- universe only AUDUSD/NZDUSD and EURUSD/GBPUSD;
- M15;
- OLS of log prices over 1920 lagged bars (20*24*4), never current bar;
- z-score of current residual against lagged regression residual variance;
- threshold crossings at +2 / -2 only;
- next-bar-open entry;
- zero-cross exit, |z|>=3.5 statistical stop, 192-bar max hold;
- one active event per pair and reset only after |z|<1;
- beta frozen at entry for synthetic two-leg PnL;
- spread costs on both legs plus FTMO commission default $2.50/lot/side;
- explicit COST_MODEL_INCOMPLETE if no spread data and no fallback spread supplied;
- hard pre-OOS cutoff at 2026-06-28;
- pair + aggregate metrics and preregistered cheap-fail verdict.

Codex should NOT rewrite this engine from scratch if the file is present on the PC. At next capacity:
1. locate the script on D:;
2. locate/export compatible M15 OHLC + spread files for AUDUSD, NZDUSD, EURUSD, GBPUSD from the already available pre-OOS data;
3. run the script once with the frozen V0;
4. publish `D022_trades.csv` and `D022_summary.json` under the normal research results area;
5. do not tune thresholds/windows and do not open OOS.

If MT5 data format differs, only write the thinnest deterministic adapter needed to produce timestamp/open/close/spread input. Do not alter strategy semantics.
