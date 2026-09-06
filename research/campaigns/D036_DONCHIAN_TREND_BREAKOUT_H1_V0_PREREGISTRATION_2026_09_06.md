# D036 — DONCHIAN / TURTLE-INSPIRED TREND BREAKOUT H1 V0

Date: 2026-09-06
Status: PREREGISTERED / NOT YET RUN

## Why this family

D036 is an independent trend-following family based on the documented Donchian/Turtle breakout structure. The original Turtle systems used price breakouts, volatility-normalized risk (N/ATR concept), a 2N protective stop and breakout exits. D036 is **not** presented as a verbatim historical Turtle implementation: it is a deliberately simpler intraday H1 adaptation for Guardian/FundedNext research, chosen to preserve the core trend-following mechanism while producing a practical trade count.

No RSI, EMA, ADX, news, day-of-week or discretionary filter is allowed in V0.

## Frozen universe

Exactly six FundedNext CFD markets:
- BTCUSD
- ETHUSD
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Tester timeframe: **H1**.
One symbol per MT5 Strategy Tester run; results are aggregated afterward.

## Frozen V0 signal

At each new H1 bar, evaluate the just-closed bar S.

Entry channel:
- LONG signal iff close(S) is strictly above the highest HIGH of the 20 complete H1 bars immediately preceding S.
- SHORT signal iff close(S) is strictly below the lowest LOW of the 20 complete H1 bars immediately preceding S.
- Entry is the next H1 bar open on the executable spread side.
- At most one open D036 position per symbol.
- If an existing position exits on S and S simultaneously satisfies the opposite 20-bar breakout, reversal on the next H1 open is allowed.

## Frozen volatility / initial stop

- ATR period = 20 H1 bars using MT5 `iATR(PERIOD_H1,20)` at signal bar S.
- Initial stop distance = exactly **2.0 × ATR(20)** from executable entry.
- No trailing ATR stop and no BE rule in V0.
- No pyramiding / unit adding in V0.

This preserves the Turtle-style 2N risk concept while intentionally removing original pyramiding and prior-win skip logic so the first experiment tests the basic breakout family, not a large rule bundle.

## Frozen exit

Opposite Donchian exit channel = 10 complete H1 bars immediately preceding the just-closed bar.

For LONG:
- initial protective stop is active continuously;
- otherwise exit when the current H1 bar trades at/below the prior 10-bar LOW channel.

For SHORT:
- initial protective stop is active continuously on executable ask side;
- otherwise exit when the current H1 bar trades at/above the prior 10-bar HIGH channel.

Gap rule: if the bar opens beyond a stop/channel threshold, fill at the worse executable opening price rather than the threshold.

OHLC ambiguity rule: if both initial stop and channel exit are touched inside the same H1 bar and tick order cannot be reconstructed by the harness, choose the economically worse valid exit for the position. This is intentionally conservative.

No time exit and no take-profit.

## FundedNext execution-cost model frozen before testing

Target model: Stellar 1-Step / 2-Step.

Spread:
- use tester MqlRates spread on executable side for entry/exit.

Commission per side:
- Forex: USD 5 per lot per side;
- Metals: 0.0016% × lot size × contract size × side execution price;
- Crypto: 0.04% × lot size × contract size × side execution price.

Net R is computed from 1-lot `OrderCalcProfit` money P/L divided by 1-lot initial-stop money risk, then commission/R is deducted. Account currency must be USD for a valid run.

Cost stress after baseline: recompute each trade with commission ×1.5. Do not alter spreads post hoc.

## Frozen data sequence

### Smoke / harness validation
Use March 2025 only, not for alpha scoring:
- 2025-03-03 through 2025-03-31.
- Run one representative symbol from each commission class: USDJPY, XAUUSD, BTCUSD.
- Purpose: compile/output, signal chronology, ATR/stop/channel logic and cost-class validation only.

### Development / cheap-fail sample
Only after smoke PASS:
- 2024-01-02 through 2025-12-31.
- All six frozen symbols.
- This sample may only answer CONTINUE vs REJECT_V0. No parameter search is allowed after opening results.

### Untouched forward confirmation
Locked until development passes every gate:
- 2026-01-02 through 2026-06-30.
- Same six symbols, same code/semantics/cost model.
- Do not inspect or run this period to rescue a failed development result.

## Mandatory reporting

Future result reports must include, not merely a short verdict:
- aggregate and per-symbol trade count;
- total net R, mean/median net R, win rate and PF;
- long vs short contribution;
- 2024 vs 2025 contribution for development;
- stop vs channel-exit rates;
- best/worst symbol and concentration of profits;
- max trade gain/loss and largest losing streak where reconstructable;
- baseline vs 1.5× commission stress;
- stability interpretation and obvious failure mode;
- explicit conclusion: reject / continue to untouched confirmation / confirm;
- no post-hoc rescue suggestions on an opened failed sample.

## Frozen development gates

All must hold to unlock untouched 2026-H1 confirmation:
- aggregate n >= 180 trades;
- at least 20 trades on each of the six symbols;
- aggregate mean net R >= +0.08R/trade;
- aggregate net PF >= 1.15;
- at least 4 of 6 symbols have positive total net R;
- aggregate total net R is positive in both calendar 2024 and calendar 2025;
- aggregate total net R remains positive at 1.5× commission;
- no single symbol contributes more than 60% of total positive-symbol net R.

Failure of any development gate => **REJECT_V0**. No 20/10/ATR-multiple/timeframe/direction rescue tuning on 2024-2025.

## Frozen untouched confirmation gates

All must hold for CONFIRM:
- aggregate n >= 45 trades;
- aggregate mean net R > 0;
- aggregate net PF >= 1.10;
- at least 3 of 6 symbols have positive total net R;
- aggregate total net R remains positive at 1.5× commission.

Failure => UNCONFIRMED. No rescue mining of 2026-H1.

## Scientific boundary

D036 tests whether a simple, multi-market, price-only trend breakout with volatility-scaled initial risk transports to FundedNext CFD execution. It is independent of D023 London ORB, D017 Momentum and the rejected mean-reversion/event families. Management experiments are forbidden until entry/exit family validation is complete.
