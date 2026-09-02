# Guardian backtest reproducibility ledger

Started: 2026-09-02

Purpose: accumulate comparable Strategy Tester observations without optimizing between windows. Record exact metrics visible in screenshots, plus tentative hour/day/month patterns. Tentative patterns are NOT strategy decisions until they recur across independent windows/markets.

## Period handling

The MT5 **Backtest** summary screenshot does not display the exact `From` / `To` dates. The monthly histogram can identify active months, but exact boundaries are not guaranteed. Therefore:
- when exact dates are not visible, record the period as `inferred from month histogram`;
- one Settings screenshot with `From` / `To` can anchor a whole batch if settings stay unchanged;
- never invent exact start/end dates from bars/ticks alone.

## Current anchored batch — exact Settings screenshot

For the next cross-market reproducibility series, use this common window until the user shows a different Settings screen:

- Exact period: **2026-06-01 through 2026-07-31**
- EA: `Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.ex5`
- Chart/test timeframe: **M1**
- Forward: **No**
- Modelling: **Every tick**
- Delay: **5 ms**
- Deposit: **100,000 USD**
- Leverage: **1:100**
- Optimization: **Disabled**
- Intended symbols in this batch include at least: **ETHUSD, BTCUSD, SOLUSD, EURUSD, USDCAD, GBPUSD**, plus other symbols the user may send under unchanged Settings.
- Current testing convention: `InpConsecutiveLossCooldown = 0` unless a later Settings/Inputs screenshot shows otherwise.

All subsequent result screenshots are to be attributed to this exact 2026-06-01 → 2026-07-31 window if the user has not indicated a settings change.

## Current frozen observations

### BTCUSD — Jul/Aug 2026 inferred from month histogram

| Version / mode | Net | PF | Equity DD | Trades | Win rate | Avg win | Avg loss | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v11.16.11 combo baseline | +17,499.93 | 1.35 | 3.76% | 628 | 61.15% | +174.78 | -203.35 | 606 long / 22 short |
| v11.16.11 RSI-only | +9,451.57 | 1.19 | 4.20% | 621 | 61.51% | +153.64 | -206.01 | all long |
| v11.16.11 Momentum-only, PostShockBars=2 | +7,353.28 | 1.68 | 1.80% | 115 | 53.04% | +296.96 | -199.28 | 77 long / 38 short |
| v11.16.12 combo, consecutive-loss cooldown=0 | +17,448.01 | 1.35 | 3.77% | 628 | 60.83% | +175.56 | -201.70 | 606 long / 22 short; near-reproduction of combo baseline |

Initial reproducibility note: v11.16.12 + zero consecutive-loss cooldown reproduces v11.16.11 BTC combo closely (same 628 trades; net difference -51.92; PF essentially identical). This suggests the fill-reconcile patch and zero cooldown do not materially alter this historical BTC combo window.

Tentative visual patterns from the latest BTC combo screenshot (not yet validated): August appears materially stronger than July; some hour buckets differ strongly, with an especially strong profit bar around 05:00. Track recurrence before using as a filter.

### ETHUSD — Jul/Aug 2026 inferred from month histogram

| Version / mode | Net | PF | Equity DD | Trades | Win rate | Avg win | Avg loss | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| older combo baseline | -5,848.76 | 0.87 | 8.31% | 614 | 63.36% | +100.70 | -200.10 | RSI-dominated; 612 long / 2 short |
| v11.16.12 combo, consecutive-loss cooldown=0 | -5,827.80 | 0.87 | 8.29% | 615 | 63.09% | +100.77 | -197.92 | 613 long / 2 short; near-reproduction of old combo |

Initial reproducibility note: ETH combo is also almost unchanged after v11.16.12 + zero cooldown, strengthening the conclusion that the live asynchronous fill bug was not materially reshaping Strategy Tester history in this window.

Tentative visual patterns from latest ETH screenshot (not yet validated): both July and August are negative; Wednesday appears stronger than several other weekdays; a large positive hour bucket appears around 20:00. Track only as hypotheses.

### ETHUSD — exact 2026-06-01 → 2026-07-31 anchored batch

Mode is **not visible on the Backtest summary screenshot**, so do not label this RSI-only/Momentum-only/combo without separate Inputs evidence. Presence of 22 shorts proves Momentum activity was enabled somewhere in the run; RSI participation cannot be inferred from the summary alone.

| Net | Gross profit | Gross loss | PF | Equity DD | Trades | Win rate | Avg win | Avg loss | Long / short |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| -8,448.60 | +5,979.45 | -14,428.05 | 0.41 | 8.45% | 103 | 40.78% | +142.37 | -236.53 | 81 long / 22 short |

Additional exact metrics: expected payoff -82.03; recovery factor -1.00; largest win +648.60; largest loss -394.74; short win rate 54.55%; long win rate 37.04%; maximum consecutive wins 9 (+1,470.55); maximum consecutive losses 11 (-2,718.22).

Reproducibility interpretation: this June-July ETH window is dramatically worse than the prior Jul/Aug ETH window (PF 0.41 vs 0.87, win rate 40.78% vs 63.09%, net -8.45k vs -5.83k). This is evidence of substantial time-window sensitivity on ETH. It is not yet enough to identify which engine causes it because the engine mode is not visible in this screenshot.

Tentative visual patterns from this ETH June-July screenshot (hypotheses only): Friday appears roughly break-even/slightly positive while Monday, Tuesday and Saturday are strongly loss-dominated; Wednesday is much less bad than Monday/Tuesday/Saturday. Around 02:00 appears relatively favorable while several buckets around 05:00, 11:00 and 15:00 look strongly loss-heavy. Do not create filters from these observations unless they recur in other independent windows/markets.

### EURUSD — Jul/Aug 2026 inferred from month histogram

| Version / mode | Net | PF | Equity DD | Trades | Win rate | Avg win | Avg loss | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| v11.16.11 RSI-only | -4,705.33 | 0.74 | 4.89% | 260 | 58.85% | +85.83 | -166.70 | 260 long / 0 short |
| v11.16.11 Momentum-only | +363.97 | 1.14 | 1.75% | 24 | 54.17% | +230.41 | -239.22 | 13 long / 11 short |
| current combo screenshot | -3,780.20 | 0.80 | 4.58% | 262 | 58.78% | +95.29 | -170.88 | 254 long / 8 short; strongly RSI-dominated |

Interpretation to test, not yet a final decision: on this EURUSD window RSI-only is clearly negative while Momentum-only is only marginally positive. The combo remains negative and is dominated by long/RSI activity.

## Reproducibility protocol

1. Freeze code + inputs before changing the test window.
2. Test isolated engines first (RSI-only, Momentum-only), then combo.
3. Use equal-length sequential windows when possible.
4. Record: Net, PF, equity DD, trades, win rate, avg win/loss, long/short split.
5. Record hour/weekday/month observations only as `tentative` until they recur in independent windows.
6. Never create an hour/day filter from one profitable screenshot; require repeated out-of-sample evidence.
7. Keep market-specific results separate before looking for cross-market patterns.

## Live technical observations relevant to backtest interpretation

- v11.16.12 `RSI_FILL_RECONCILE` successfully reconciled an asynchronous USDCAD live fill: fallback 1.38900 -> true fill 1.38902, cycle retained, RSI management ACTIVE.
- Consecutive-loss cooldown has been set to `0` for current testing. Historical BTC/ETH combo reruns so far are nearly unchanged versus the prior baseline.
- BUY2-vs-SL remains an active structural research question: live USDCAD showed BUY2 armed, then SL before BUY2 execution.
