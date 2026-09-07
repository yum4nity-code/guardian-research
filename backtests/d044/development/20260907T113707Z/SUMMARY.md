# D044-TURTLE-SOUP-20D-FAILED-BREAK-REVERSAL-V0 — development

- Decision verdict: **REJECT_V0**
- Frozen gates passed: **False**
- Trades: **192**
- Mean net R: **-0.8630031731250001**
- Profit Factor: **0.3967689013765851**
- Total net R: **-165.69660924000002**
- Stress commission x1.5 total R: **-209.26286371**
- Positive symbols: **0** — 
- Failed frozen gates: **aggregate_mean_net_r_min, aggregate_pf_min, positive_symbols_min, aggregate_2024_positive, aggregate_2025_positive, aggregate_positive_at_commission_stress**

## Rich descriptive analytics

- Net-R median: -1.2785256399999998
- Net-R p10 / p90: -2.33943293 / -0.49238752799999674
- Win rate: 0.09375
- Average win / loss R: 6.054733303888889 / -1.5786310845402298
- Payoff ratio: 3.8354327133069894
- Realized trade-close max drawdown: 172.74800757999995 R
- Longest winning / losing streak: 2 / 43
- Median trade duration: 12.0 minutes

## Scientific boundary

The frozen decision score is authoritative for REJECT/CONFIRM. Rich analytics are descriptive only and do not rescue or modify the experiment verdict.
D037 does not contain intratrade MFE/MAE or first-touch +1R/+2R/+3R path data; those fields are required natively for future experiments.
