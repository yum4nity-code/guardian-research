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

### D17 EURUSD 2024-2025
- Native net about -0.076R/trade vs Fixed about -0.271R/trade.
- Ratchet delta about +0.195R/trade.
- Manager helps strongly, but entry family remains negative.

### D17 GBPUSD 2024-2025
- Native net about -0.118R/trade vs Fixed about -0.073R/trade.
- Ratchet delta about -0.044R/trade.
- Manager hurts this market.

### D17 USDJPY 2024-2025
- Native net about -0.009R/trade vs Fixed about -0.045R/trade.
- Ratchet delta about +0.037R/trade.
- Native is near flat pooled but strongly regime-dependent: positive 2024, negative 2025.

### D17 XAUUSD 2024-2025
- Native net about -0.049R/trade vs Fixed about +0.041R/trade.
- Ratchet delta about -0.090R/trade.
- The current 1.75 ATR ratchet appears harmful on this market; Fixed 3R is mildly positive pooled but not year-stable.

### D17 USDCAD 2024-2025
- Native net -0.106R/trade vs Fixed -0.123R/trade.
- Ratchet delta +0.016R/trade; paired bootstrap CI crosses zero.
- 2024 strongly negative; 2025 near flat. No robust edge.

## Cross-market D17 snapshot

Approximate Native-minus-Fixed deltas:
- BTCUSD +0.031R/trade
- ETHUSD +0.088R/trade
- EURUSD +0.195R/trade
- USDJPY +0.037R/trade
- USDCAD +0.016R/trade
- GBPUSD -0.044R/trade
- XAUUSD -0.090R/trade

This is evidence against a single universal exit manager across all asset classes. The same Native manager helps 5 of 7 tested markets and hurts 2, with very different effect sizes.

Decision:
- Cross-market evidence is sufficient to keep a dedicated manager-study hypothesis alive.
- Do NOT tune D17 itself now to rescue inspected samples.
- Next useful test is across an independent strategy family (USDJPY London ORB), so the project can determine whether the same exit-management weakness repeats across strategies rather than merely across markets inside D17.
- If it does, launch a preregistered manager campaign with a finite candidate family and untouched confirmation data.
