# D037 execution deviation — smoke waived

Date: 2026-09-06

The preregistered D037 strategy semantics and development/confirmation gates remain unchanged.

Before any D037 result inspection, the user explicitly elected to waive the March-2025 technical smoke stage to avoid further elapsed time. This is an execution-process deviation only; it is not a strategy change, parameter change, symbol change, direction change, or scoring change.

Required before opening the development sample:
- MetaEditor compile: 0 errors / 0 warnings.
- Exact source identity: `D037_WilliamsPrevDayRangeBreakout_M15_v1_00_FUNDEDNEXT_DIRECT_20260906.mq5`.
- Timeframe M15.
- Stage `D037_DEV_2024_2025`.
- `InpWriteCSV=true`.

The six frozen development runs remain BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD over 2024-01-02 through 2025-12-31. Because smoke is waived, any integrity/lifecycle failure discovered in development invalidates that affected run and must be corrected under a new EA version before rerunning it. No alpha result from an invalid run may be used for tuning.
