# D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0 — development

- Decision verdict: **REJECT_V0**
- Frozen gates passed: **False**
- Trades: **459**
- Mean net R: **0.17949124751633988**
- Profit Factor: **1.5549236197092462**
- Total net R: **82.38648261**
- Stress commission x1.5 total R: **77.18744327**
- Positive symbols: **5** — BTCUSD, EURUSD, GBPUSD, USDJPY, XAUUSD
- Failed frozen gates: **aggregate_n_min**

## Rich descriptive analytics

- Net-R median: -0.03931038
- Net-R p10 / p90: -1.02525954 / 1.4448859659999997
- Win rate: 0.4923747276688453
- Average win / loss R: 1.0214647231415928 / -0.637186887639485
- Payoff ratio: 1.6030849707621873
- Realized trade-close max drawdown: 20.300442860000032 R
- Longest winning / losing streak: 8 / 11
- Median trade duration: 967.0 minutes

## Scientific boundary

The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.
D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.
