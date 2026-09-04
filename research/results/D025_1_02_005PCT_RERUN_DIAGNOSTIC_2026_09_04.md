# D025 Trading 1.02 — 0.05% rerun diagnostic

Date: 2026-09-04

## Scope

User supplied cumulative `d025_ler_trading_1_02_trades(1).csv` and `...outcomes(1).csv` after reruns with `InpRiskPercent=0.05` over 2024-2025.

New 0.05% sessions identified:
- XAUUSD: 798 trades
- ETHUSD: 544 trades
- BTCUSD: 490 trades
- GBPUSD: 708 trades
- EURUSD: 726 trades
- USDJPY: 791 trades

Earlier 0.50% sessions remain present in the cumulative files and were excluded from the statistics below.

## Coverage versus prior separate-year D025 1.01 sessions

Expected counts from the already measured 2024 + 2025 separate-year 1.01 sessions versus new 1.02 0.05% two-year runs:

| Symbol | Prior 2024+2025 count | 1.02 0.05% count | Coverage |
|---|---:|---:|---:|
| BTCUSD | 1117 | 490 | 43.9% |
| ETHUSD | 1172 | 544 | 46.4% |
| GBPUSD | 769 | 708 | 92.1% |
| USDJPY | 866 | 791 | 91.3% |
| XAUUSD | 849 | 798 | 94.0% |

Conclusion: lowering live risk to 0.05% did not remove execution/account-state selection for BTC and ETH. Their trade sets remain far too incomplete for a clean path-management inference. This is consistent with real-order dependence/minimum-volume and account evolution continuing to affect which signals become opened trades. Forex/XAU coverage is much closer but still not mathematically identical to a pure signal observer.

## New logger validation

The 1.02 logger successfully produced the new fields:
- `hit05_utc`
- `be_after1_utc`
- `be_after1_ambiguous_same_m1`

Using only the new 0.05% sessions and counting positive target touches before original stop:

| Symbol | +0.5R | +1R | +2R | +3R |
|---|---:|---:|---:|---:|
| BTCUSD | 65.7% | 49.8% | 29.4% | 18.4% |
| ETHUSD | 61.0% | 43.0% | 25.9% | 18.2% |
| GBPUSD | 66.5% | 48.9% | 29.1% | 18.1% |
| EURUSD | 67.8% | 49.9% | 30.6% | 18.7% |
| USDJPY | 62.5% | 45.1% | 28.1% | 17.8% |
| XAUUSD | 64.9% | 45.4% | 26.8% | 17.3% |

Among trades that had already reached +1R, excluding same-M1 BE-path ambiguities, the share reaching +2R before first return to entry was approximately:
- BTCUSD 47.1%
- ETHUSD 48.9%
- GBPUSD 47.2%
- EURUSD 49.6%
- USDJPY 47.6%
- XAUUSD 43.9%

These path numbers confirm the new measurement works, but BTC/ETH must not be treated as representative because the 0.05% real-order run captured under half of the prior signal population.

## Required correction

For the management-path study, the next EA should be **virtual/observer-only** after VALID_SIGNAL:
- keep D025 V0 entry transitions frozen;
- keep structural stop definition frozen;
- derive entry from modeled bid/ask at signal time;
- do not send market orders;
- do not depend on account equity, lot minimums, margin, or realized P/L;
- continue recording +0.5R, +1R..+5R, original stop, and BE-after-+1R ordering.

This removes the account/execution feedback loop and ensures every qualifying D025 signal is measured.

## Scientific verdict

- 1.02 instrumentation: **VALID**.
- 1.02 real-order two-year path sample at 0.05%: **NOT CLEAN for BTC/ETH**.
- Do not use the incomplete BTC/ETH 1.02 runs to choose a management rule.
- Build a virtual-only path diagnostic before the final management comparison.
