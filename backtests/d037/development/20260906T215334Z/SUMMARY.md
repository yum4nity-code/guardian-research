# D037-WILLIAMS-PREVDAY-RANGE-VOLATILITY-BREAKOUT-V0 — development

- Decision verdict: **REJECT_V0**
- Frozen gates passed: **False**
- Trades: **2377**
- Mean net R: **0.020111581320992847**
- Profit Factor: **1.0456845051767667**
- Total net R: **47.805228799999995**
- Stress commission x1.5 total R: **10.620232049999997**
- Positive symbols: **4** — BTCUSD, ETHUSD, USDJPY, XAUUSD
- Failed frozen gates: **aggregate_mean_net_r_min, aggregate_pf_min**

## Rich descriptive analytics

- Net-R median: -0.19495369
- Net-R p10 / p90: -1.0457525859999999 / 1.5968267000000003
- Win rate: 0.43331931005469077
- Average win / loss R: 1.0623556301262136 / -0.7768530588195991
- Payoff ratio: 1.3675116781292278
- Realized trade-close max drawdown: 88.97819435999995 R
- Longest winning / losing streak: 10 / 14
- Median trade duration: 480.0 minutes

## Scientific boundary

The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.
D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.
