# D034 — XAUUSD abnormal-return Strategy 1 verdict

Date: 2026-09-05
Status: **XAUUSD ARM REJECTED**
Classification: `ADAPTATION_CAUSAL_CFD_TRANSFER`

Primary source: Caporale & Plastun (2021), *Financial Markets and Portfolio Management* 35, 353–368, DOI `10.1007/s11408-021-00380-w`.

## Scope
The user could run XAUUSD only; no WTI/USOIL/XTI instrument was available on the target FundedNext account. Therefore this is the final verdict for the GOLD arm only. The OIL arm remains untested rather than failed.

Frozen signal window: 2024-01-01 through 2026-06-30.
Scanner: `D034_GoldOil_AbnormalReturn_Momentum_FeatureLab_v1_00.mq5`.

All 83 returned XAUUSD events were marked clean (`gap_trade=0`, `clean=1`) and had complete passive feature snapshots.

## Primary executable results
Pooled XAUUSD:
- clean n = 83;
- mean executable return = **+1.8925 bps/event**;
- median executable return = **+8.4451 bps**;
- win rate = **57.83%**;
- total executable return = +157.08 bps;
- mean source-mid return = +3.0246 bps/event;
- mean entry spread = ~0.8811 bps;
- mean MFE = +52.18 bps;
- mean MAE = -50.81 bps.

By direction:
- LONG positive-abnormal: n=37, mean **+9.6399 bps**, median +12.4762 bps, win 67.57%;
- SHORT negative-abnormal: n=46, mean **-4.3390 bps**, median +2.1980 bps, win 50.00%.

By year:
- 2024: n=32, mean **-1.4951 bps**;
- 2025: n=28, mean **-4.1560 bps**;
- 2026 through June: n=23, mean **+13.9691 bps**.

Month-cluster bootstrap of pooled executable mean, 20,000 resamples:
- approximate 95% interval = **[-7.95, +12.62] bps/event**.

Positive-return concentration:
- largest positive event / total positive executable bps = ~9.60%, below the frozen 20% cap.

## Frozen gate
Per-market advancement gate was:
1. >=40 clean resolved events;
2. mean executable >+15 bps/event;
3. median executable >0;
4. month-block bootstrap 95% lower bound >0;
5. both directions positive when each n>=10;
6. >=2 positive calendar years;
7. no one event >20% of positive pooled bps.

Result:
1. PASS — n=83;
2. **FAIL** — +1.89 bps << +15 bps target;
3. PASS — median +8.45 bps;
4. **FAIL** — bootstrap lower bound ~-7.95 bps;
5. **FAIL** — SHORT mean is negative;
6. **FAIL** — only 2026 is positive;
7. PASS — concentration ~9.60%.

**Gate = 3/7 -> REJECT.**

## Interpretation
The XAU signal has a weak positive pooled mean and a positive median, but the economically relevant mean is far below the project threshold, uncertainty crosses zero, the short side is negative, and the edge is not stable across years. Even the LONG subset is only +9.64 bps/event and is temporally inconsistent (negative in 2024, positive in 2025-2026), so it is not promoted as a separate strategy.

Do not rescue this same 2024-2026 sample by changing source timing hours, the 2-sigma threshold, 252-day lookback, direction, RSI/SMA filters, or by inventing an SL/TP. Passive feature fields remain diagnostic only.

OIL was unavailable on the target account and is simply untested.
