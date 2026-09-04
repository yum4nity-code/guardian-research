# Guardian Research — automated backtest results

This branch is reserved for compact machine-published backtest results.

Current automation:
- D025 Liquidity Exhaustion Reclaim V0 Core-only research;
- FundedNext MT5 session auto-detection;
- Strategy Tester M1, Model=4 (`Every tick based on real ticks`);
- BTCUSD + ETHUSD multi-symbol observer;
- no real or tester trading orders: virtual signals / MFE-MAE only;
- source thresholds remain those locked in `research/campaigns/D025_LER_V0_RULES_LOCK_2026_09_04.md` on `main`.

Each completed run is written under:

`backtests/d025/<RUN_ID>/`

Expected compact files:
- `SUMMARY.md` — human-readable funnel/outcomes;
- `summary.json` — machine-readable statistics;
- `manifest.json` — provenance, source/rules hashes, tester settings and raw-file hashes;
- `events_compact.csv` — one row per D025 event when the compact file remains <= 5 MB.

Large raw event/trade/outcome CSV files remain on the research PC under `D:\MT5_Backtests\Research\D025\Backtests\<RUN_ID>\raw\` to keep GitHub small. Their SHA256 and byte sizes are recorded in the manifest.

A fresh agent should read `main:CURRENT_PROJECT_HANDOFF.md`, then inspect the newest directory on this branch when a D025 backtest has completed.
