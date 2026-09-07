# D039-INSIDE-DAY-BREAKOUT-V0 — development

- Decision verdict: **REJECT_V0**
- Frozen gates passed: **False**
- Trades: **441**
- Mean net R: **0.14936574015873016**
- Profit Factor: **1.5163315683916527**
- Total net R: **65.87029141000001**
- Stress commission x1.5 total R: **61.6325712**
- Positive symbols: **5** — BTCUSD, EURUSD, GBPUSD, USDJPY, XAUUSD
- Failed frozen gates: **aggregate_n_min**

## Rich descriptive analytics

- Net-R median: -0.01318374
- Net-R p10 / p90: -1.0207766 / 1.28936364
- Win rate: 0.4965986394557823
- Average win / loss R: 0.8833055678995434 / -0.5746559818018018
- Payoff ratio: 1.5371032337120865
- Realized trade-close max drawdown: 12.111299370000005 R
- Longest winning / losing streak: 7 / 8
- Median trade duration: 1009.0 minutes

## Scientific boundary

The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.
D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.
