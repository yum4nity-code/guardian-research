# Manager Evidence Ledger

Purpose: track cross-strategy / cross-market evidence that exit management itself may be a reusable source of improvement.

Policy:
- Manager tuning is NOT forbidden.
- What is forbidden is tuning a manager on one inspected sample and then calling that same sample validation.
- A manager study becomes justified when the same management weakness appears across multiple independent sleeves or markets.
- When justified, freeze a finite candidate family, tune only on a designated development sample, then confirm on genuinely untouched data / markets.
- Prefer reusable manager components over strategy-specific rescue rules.

## Current evidence — 2026-09-06

### D17 BTCUSD 2024-2025
- NATIVE_RATCHET improved gross outcome over FIXED_3R by about +0.031R/trade.
- Manager delta bootstrap crossed zero; improvement not statistically established.
- Strategy remained negative after crypto costs.

### D17 ETHUSD 2024-2025
- NATIVE_RATCHET improved outcome over FIXED_3R by about +0.088R/trade.
- Delta bootstrap was positive in the prior audit.
- Strategy still remained negative after crypto costs.

### D17 USDJPY 2024-2025 — preliminary v1.100 diagnostic
- 524 entries.
- FIXED_3R gross = 0.000R/trade.
- NATIVE_RATCHET gross = +0.0338R/trade.
- Preliminary current-FTMO cost estimate put Native near flat, but v1.100 did not model non-crypto commission inside true-BE and logged non-crypto cost_r=0.
- Therefore this is evidence for manager relevance, NOT a final profitability verdict.

Decision:
- Cross-market evidence is now sufficient to keep a dedicated manager-study hypothesis alive.
- Do not tune the 1.75 ATR trail yet while the current D17 non-crypto attribution batch is incomplete.
- After the remaining Forex/XAU tests, if the manager delta remains recurrent, launch a preregistered manager experiment rather than demanding a perfect entry with frozen exits forever.
