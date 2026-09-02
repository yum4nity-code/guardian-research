# EURUSD — RSI Sniper only — Jul/Aug 2026

Source: MT5 Strategy Tester screenshot supplied by user on 2026-09-02.
Guardian baseline: v11.16.11 STRATEGY_SWITCHES.
Mode: RSI only (`InpEnableMomentum=false`, `InpEnableRSISniper=true`).

## MT5 summary

- Initial deposit: 100,000.00
- Total net profit: -4,705.33
- Gross profit: 13,131.75
- Gross loss: -17,837.08
- Profit Factor: 0.74
- Expected payoff: -18.10
- Recovery Factor: -0.96
- Sharpe Ratio: -5.00
- Balance DD maximal: 4,791.66 (4.79%)
- Equity DD maximal: 4,902.15 (4.89%)
- Total trades: 260
- Short trades: 0
- Long trades: 260 (58.85% won)
- Profit trades: 153 (58.85%)
- Loss trades: 107 (41.15%)
- Largest profit trade: +426.24
- Largest loss trade: -219.24
- Average profit trade: +85.83
- Average loss trade: -166.70
- Maximum consecutive wins: 12 (+1,056.09)
- Maximum consecutive losses: 6 (-1,153.82)

## Interpretation

This isolated result is negative despite a 58.85% win rate because the payoff distribution is unfavorable: the average loss (-166.70) is almost twice the average win (+85.83). On this EURUSD sample, RSI Sniper is not viable in its current form as a standalone engine.

Do not tune from this single result. Compare with EURUSD Momentum-only over the identical period, then repeat isolated-engine tests on other markets before changing RSI rules.
