# D017 v11.17 Momentum — cost-aware noncrypto attribution batch

Date: 2026-09-06
Period: 2024-01-01 -> 2025-12-31
Diagnostic lineage: D017_Momentum_LiveV1117_Attribution v1.101 COSTFIX
No orders; virtual attribution; same frozen entry events under NATIVE_RATCHET vs FIXED_3R.

Important file-handling note: v1.101 corrected noncrypto costs/true-BE but accidentally retained the v1.100 CSV filenames and `D017M100` session prefix. The uploaded ZIP therefore accumulated prior runs. Sessions were isolated by exact session_id and, for noncrypto, by nonzero cost_r. No data were lost.

Current FTMO cost model used by v1.101:
- Forex: 2.50 USD/lot/side
- Metals CFD: 0.0007% notional/side
- 0.7% currency-conversion adjustment when profit currency differs from account currency
- swap/slippage not invented

## Pooled results

| Symbol | N | Native gross | Native cost | Native net | Native PF | Fixed net | Native-Fixed |
|---|---:|---:|---:|---:|---:|---:|---:|
| EURUSD | 300 | -0.0318R | 0.0446R | -0.0764R | 0.869 | -0.2713R | +0.1949R |
| GBPUSD | 429 | -0.0840R | 0.0338R | -0.1178R | 0.810 | -0.0734R | -0.0443R |
| USDJPY | 524 | +0.0341R | 0.0430R | -0.0089R | 0.985 | -0.0455R | +0.0366R |
| XAUUSD | 676 | -0.0426R | 0.0066R | -0.0492R | 0.915 | +0.0407R | -0.0899R |

Approximate paired bootstrap 95% CI for Native-Fixed:
- EURUSD: +0.065 .. +0.323R/trade
- GBPUSD: -0.153 .. +0.063R/trade
- USDJPY: -0.067 .. +0.138R/trade
- XAUUSD: -0.184 .. +0.005R/trade

## Year stability — Native
- EURUSD: 2024 -0.075R/trade; 2025 -0.079R/trade. Stable negative.
- GBPUSD: 2024 -0.179R/trade; 2025 -0.078R/trade. Negative both years.
- USDJPY: 2024 +0.117R/trade; 2025 -0.111R/trade. Strong regime flip.
- XAUUSD: 2024 -0.117R/trade; 2025 +0.014R/trade. Regime flip / near-flat 2025.

## Fixed 3R stability of notable cases
- USDJPY FIXED_3R: 2024 +0.199R/trade; 2025 -0.244R/trade.
- XAUUSD FIXED_3R: 2024 -0.102R/trade; 2025 +0.175R/trade.
Both pooled clues are therefore non-robust across years.

## One-position-at-a-time Native approximation
Using Native exit time as the symbol occupancy gate:
- EURUSD: n=255, -0.0847R/trade
- GBPUSD: n=365, -0.1168R/trade
- USDJPY: n=411, -0.0077R/trade
- XAUUSD: n=537, -0.0413R/trade
The live max-one-position-per-symbol constraint does not change the broad verdict.

## Decision
- EURUSD broad D17: reject as alpha source in current form.
- GBPUSD broad D17: reject as alpha source in current form.
- USDJPY broad D17: WATCHLIST / near-flat, not validated; strong 2024/2025 sign reversal forbids promotion.
- XAUUSD D17: WATCHLIST clue under FIXED_3R only, not validated; pooled +0.041R/trade is driven by 2025 and reverses in 2024.
- Manager evidence is material and heterogeneous: Ratchet helps EURUSD strongly but hurts XAUUSD. This supports formal manager research later, not one universal post-hoc trail tweak.
- USDCAD remains the missing exact v11.17 cost-aware noncrypto test.
