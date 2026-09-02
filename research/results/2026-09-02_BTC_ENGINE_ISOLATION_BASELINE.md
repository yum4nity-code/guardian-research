# BTC engine isolation baseline — 2026-09-02

Same BTC test period and tester environment as the 2026-09-02 control runs. Guardian baseline: v11.16.11 strategy switches.

## Combo — RSI + Momentum
- Total Net Profit: +17,499.93 USD
- Profit Factor: 1.35
- Equity DD max: 4,004.32 USD (3.76%)
- Balance DD max: 3,685.10 USD (3.47%)
- Total trades: 628
- Win rate: 61.15%
- Average win: +174.78 USD
- Average loss: -203.35 USD
- Recovery factor: 4.37

## RSI-only
- Total Net Profit: +9,451.57 USD
- Profit Factor: 1.19
- Equity DD max: 4,454.22 USD (4.20%)
- Balance DD max: 4,185.94 USD (3.96%)
- Total trades: 621
- Win rate: 61.51%
- Average win: +153.64 USD
- Average loss: -206.01 USD
- Recovery factor: 2.12

## Momentum-only
- Total Net Profit: +7,353.28 USD
- Profit Factor: 1.68
- Equity DD max: 1,819.76 USD (1.80%)
- Balance DD max: 1,514.01 USD (1.50%)
- Total trades: 115
- Win rate: 53.04%
- Average win: +296.96 USD
- Average loss: -199.28 USD
- Recovery factor: 4.04
- Short trades: 38 (55.26% win)
- Long trades: 77 (51.95% win)

## First-order interpretation
- RSI is profitable on its own but with lower PF and higher DD than Momentum-only.
- Momentum-only trades far less often but has markedly better payoff asymmetry and PF.
- Combo outperforms either sleeve alone and also exceeds the simple sum of isolated net profits by about 695 USD; this must not be interpreted as pure additivity because shared Guardian cooldowns, trade caps and timing interactions change the path.
- Next crypto A/B: Momentum-only baseline uses `InpCryptoPostShockBars=2`; compare only against identical BTC run with `InpCryptoPostShockBars=0` before considering 1 or 4.
- Forex note: `POST_SHOCK` is a crypto-regime filter and is not a meaningful EURUSD variable.

## Planned short tests
- EURUSD Momentum-only, last month.
- EURUSD RSI-only, same last-month window.
- Other short Forex isolation checks before broadening.
