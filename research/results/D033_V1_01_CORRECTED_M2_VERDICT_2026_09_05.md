# D033 v1.01 — EURUSD M5 Double Top / Double Bottom M2 corrected verdict

Date: 2026-09-05
Status: **REJECT**
Classification: `CLOSE_REPLICATION_CFD_TRANSFER`

Preregistration: `research/campaigns/D033_EURUSD_M5_DOUBLE_TOP_BOTTOM_M2_FEATURELAB_PREREGISTRATION_2026_09_05.md`
Preregistration commit: `1980970f343aa9d9536fea058b9dbab09b1337a1`

Scanner evaluated: `D033_EURUSD_M5_DoubleTopBottom_M2_FeatureLab_v1_01.mq5`
SHA-256: `8281951c4b7745dac0f9660808294dc447c351a20cd2679d116b5384551796b3`

v1.01 contains the Appendix B.2 source-fidelity correction only: after selecting an extremum, same-type later extrema are skipped and the first chronologically later opposite-type extremum is selected. No pattern threshold, equality tolerance, rolling window, kernel rule, pretrend, TP/SL, timeout, signal window, spread handling, or feature rule changed from the preregistered arm.

## Returned run
EURUSD, development signal window 2024-01-01 through 2026-06-30, M1 tester / 1-minute OHLC historical model.

Raw resolved events: 126.
Clean definition for the preregistered gate: `gap_formation=0` and `gap_trade=0`.
Clean events: 125. Only one event had a formation gap; no trade-path gaps were flagged.

### Clean pooled result
- n = 125
- mean executable result = **-0.817458R/trade**
- median executable result = **-1.415525R/trade**
- mean executable return = **-0.987138 bps/trade**
- win rate = **24.0%**
- exits: 34 TP, 91 SL, 0 timeout
- month-block bootstrap, 20,000 resamples across 29 calendar months: 95% interval approximately **[-1.248R, -0.345R]**; median bootstrap mean ~-0.815R

### Pattern split
- DT: n=69, mean **-0.565607R**, median **-1.420118R**
- DB: n=56, mean **-1.127774R**, median **-1.399945R**

Both source pattern directions are negative.

### Calendar-year split
- 2024: n=58, mean **-1.122742R**
- 2025: n=35, mean **+0.163927R**
- 2026: n=32, mean **-1.337520R**

Only one of the three calendar years is positive.

### Concentration
Largest positive event contributes about **12.35%** of total positive pooled R, above the preregistered maximum 10%.

### Scale / execution diagnostic
Median initial executable risk distance is only ~0.98 bps and median pattern height ~3.99 bps. The negative result is therefore not a hidden large raw-return edge distorted only by R normalization: the clean mean executable return itself is also negative at about -0.99 bps/trade.

Passive feature-lab fields are not mined because the frozen source arm already fails decisively; no RSI/SMA/ATR/session rescue is permitted on this development interval.

## Frozen gate
1. >=250 clean resolved trades — **FAIL** (125)
2. mean executable result > +0.15R/trade — **FAIL** (-0.817R)
3. median executable R >0 — **FAIL** (-1.416R)
4. month-block bootstrap 95% lower bound >0 — **FAIL** (~-1.248R)
5. DT mean R >0 and DB mean R >0 — **FAIL** (both negative)
6. at least two of 2024/2025/2026 positive — **FAIL** (1/3)
7. no single event >10% of positive pooled R — **FAIL** (~12.35%)

**Gate: 0/7 PASS.**

## Decision
**REJECT D033 exact corrected M2 arm.**

The source-faithful v1.01 correction does not rescue the strategy; the corrected run is worse than the already-negative provisional v1.00 run and fails every preregistered advancement criterion. Do not widen equal-extrema tolerance, alter the 36-bar window, change the kernel bandwidth, modify TP/SL fractions, add RSI/session filters, or otherwise tune this same 2024-2026 interval to rescue D033.

Move to the next independent strategy family. D032 Doji remains a separate sparse confirmed-entry research sleeve with unresolved management.