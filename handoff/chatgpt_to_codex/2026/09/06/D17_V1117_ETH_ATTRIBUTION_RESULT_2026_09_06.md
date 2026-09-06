# D17 v11.17 ETH attribution result — 2026-09-06

Status: COMPLETE / CRYPTO BRANCH NEGATIVE AFTER COSTS / MANAGER BENEFIT CONFIRMED

## Scope
Frozen v11.17 Momentum attribution on ETHUSD, 2024-01-01 through 2025-12-31, same diagnostic and rules as BTC run. No RSI. No parameter tuning. Same entry set compared between NATIVE_RATCHET and FIXED_3R.

## Data integrity
- ETH valid signals/trades: 1,141
- Variants: 2 per event = 2,282 rows
- No censored variant rows
- 876 additional signals rejected by spread/SL gate
- ETH data were appended to the same CSV files as the prior BTC session; analysis isolated symbol=ETHUSD and ETH session only.

## Results
### NATIVE_RATCHET
- n = 1,141
- gross mean = +0.034943 R/trade
- mean cost = 0.154041 R/trade
- net mean = -0.119097 R/trade
- net total = -135.8899 R
- net win rate = 43.12%
- net profit factor ≈ 0.8183
- bootstrap 95% CI for gross mean ≈ [-0.0590, +0.1358] R
- bootstrap 95% CI for net mean ≈ [-0.2135, -0.0175] R

### FIXED_3R
- n = 1,141
- gross mean = -0.053462 R/trade
- mean cost = 0.154051 R/trade
- net mean = -0.207513 R/trade
- net total = -236.7726 R
- net win rate = 23.66%
- net profit factor ≈ 0.7643

### Paired manager delta
- Native minus Fixed net = +0.088416 R/trade
- total paired improvement = +100.8827 R
- bootstrap 95% CI for paired mean delta ≈ [+0.0084, +0.1700] R

Interpretation: on ETH the Native ratchet manager is measurably better than fixed +3R, but it does not create a positive post-cost system. The negative Native net mean itself is also statistically supported by the bootstrap interval.

## Path attribution
Fixed +3R produced 270 +3R winners and 871 -1R losers.
- On the 871 fixed losers, Native improved aggregate gross outcome by +375.1791 R.
- On the 270 fixed winners, Native gave back -274.3086 R versus allowing the full +3R.
- Net manager effect = roughly +100.87 R gross / +100.88 R net versus Fixed.

## Stability
Native positive months: 5 / 24.
Native net mean by year:
- 2024: -0.1032 R/trade
- 2025: -0.1478 R/trade

Side/year diagnostics are mixed and must NOT be used for post-hoc rescue:
- 2024 BUY Native: -0.0181 R/trade
- 2024 SELL Native: -0.2133 R/trade
- 2025 BUY Native: -0.2694 R/trade
- 2025 SELL Native: -0.0761 R/trade

A conservative same-entry one-position-at-a-time approximation still remained negative for Native at about -0.0635 R/trade on 753 accepted events.

## Scientific verdict
1. ETH confirms the BTC conclusion that D17 v11.17 crypto Momentum does not provide sufficient alpha after actual crypto commission costs.
2. The Native ratchet manager itself remains useful research: it materially improves trade-path extraction versus fixed +3R, and on ETH its paired advantage is statistically positive.
3. Do NOT rescue by selecting 2025 SELL, BUY-only, months, or altered BNS/manager thresholds after viewing these results.
4. D17 crypto major branch (BTC + ETH) should be treated as REJECTED as a production alpha source in current form.
5. This verdict does NOT apply to Forex or XAU. Non-crypto transfer must be tested separately using instrument-appropriate FTMO cost models and exact v11.17 non-crypto entry semantics.

## Next
Promote D17 v11.17 non-crypto transfer test as the immediate continuation: USDJPY first, then EURUSD/GBPUSD and XAUUSD, without parameter tuning. Keep manager frozen at TP1 2R/25%, BE 1.25R, 1.75 ATR setup-bar-gated ratchet for attribution.
