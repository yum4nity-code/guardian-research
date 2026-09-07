# D045-D1-DONCHIAN-20-10-BENCHMARK-V0 — development

- Decision verdict: **REJECT_V0**
- Frozen gates passed: **False**
- Trades: **145**
- Mean net R: **0.09590872331034482**
- Profit Factor: **1.2011785982494556**
- Total net R: **13.906764879999999**
- Stress commission x1.5 total R: **13.41851664**
- Positive symbols: **5** — BTCUSD, ETHUSD, EURUSD, USDJPY, XAUUSD
- Failed frozen gates: **aggregate_mean_net_r_min**

## Rich descriptive analytics

- Net-R median: -0.54444154
- Net-R p10 / p90: -1.00834072 / 1.7443811859999998
- Win rate: 0.3793103448275862
- Average win / loss R: 1.5096950479999998 / -0.7680718084444444
- Payoff ratio: 1.9655649789536545
- Realized trade-close max drawdown: 19.286709140000003 R
- Longest winning / losing streak: 8 / 9
- Median trade duration: 23755.0 minutes

## Scientific boundary

The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.
D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.
