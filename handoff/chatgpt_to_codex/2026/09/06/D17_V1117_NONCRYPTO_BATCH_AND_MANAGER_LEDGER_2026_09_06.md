# D17 v11.17 noncrypto batch + manager evidence — 2026-09-06

Read `research/results/D017_V1117_COSTAWARE_NONCRYPTO_BATCH_2026_09_06.md` and `research/MANAGER_EVIDENCE_LEDGER.md` before further D17 work.

Validated user-run v1.101 cost-aware results, 2024-01-01 -> 2025-12-31:
- EURUSD Native -0.076R/trade vs Fixed3R -0.271R; manager delta +0.195R.
- GBPUSD Native -0.118R vs Fixed3R -0.073R; manager delta -0.044R.
- USDJPY Native -0.009R vs Fixed3R -0.045R; 2024 positive / 2025 negative regime flip; watchlist, not validated alpha.
- XAUUSD Native -0.049R vs Fixed3R +0.041R; Fixed3R also flips from negative 2024 to positive 2025; clue only, not validated alpha.

Manager conclusion:
- Tuning is allowed as a research object; validation on the tuned sample is not.
- Ratchet helps 4/6 tested D17 markets (BTC, ETH, EUR, JPY) and hurts GBP/XAU, so a universal manager is not supported. Keep a formal manager-study hypothesis for later independent-strategy confirmation.

File-handling bug:
- v1.101 corrected costs but accidentally retained v1.100 CSV filenames and `D017M100` session prefix, so runs accumulated. ChatGPT isolated sessions safely; no data lost.
- Prepared local v1.102 CSV/session-fix candidate only changes output filenames/session prefix, not signal or manager logic. It has not been MetaEditor-compiled yet.

Next D17 test:
- USDCAD exact v11.17 cost-aware attribution, same frozen 2024-2025 protocol. This is the remaining previously relevant noncrypto market.
- After USDCAD, broad D17 attribution can close and research priority should move to an independent sleeve such as untouched USDJPY ORB confirmation.
