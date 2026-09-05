# D029 — CLASSIC TIME-SERIES MOMENTUM BENCHMARK V0

Date: 2026-09-05
Status: PREREGISTERED / BENCHMARK / NOT PRIMARY CHALLENGE ENGINE

## Why this exists

Classic time-series momentum is one of the strongest documented systematic trading families in the academic literature. D029 is intentionally a benchmark rather than a promise of fast challenge completion.

Primary basis:
- Moskowitz, Ooi & Pedersen (2012), *Journal of Financial Economics*, "Time series momentum", DOI 10.1016/j.jfineco.2011.11.003. The paper documents significant time-series momentum across 58 liquid equity-index, currency, commodity and bond futures, with return persistence over roughly 1-12 months.
- Hurst, Ooi & Pedersen (2017), *Journal of Portfolio Management*, "A Century of Evidence on Trend-Following Investing", DOI 10.3905/jpm.2017.44.1.015, extending evidence across global markets back to 1880.

D029 is deliberately separate from D017 Momentum. D017 was an intraday impulse/continuation engine with EMA200, ADX, ATR regime, Donchian context and session filters. D029 is the literature-style slow sign-of-past-return benchmark.

## Frozen V0 universe

Use all accessible markets with reliable daily history, initially:
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD
- BTCUSD
- ETHUSD

No requirement that one common instrument set remain available forever; however the first V0 verdict is reported both per market and for the exact first frozen basket.

## Frozen signal

Daily close data, UTC day boundary for crypto and broker-independent 17:00 New York FX trading-day close when reliable timezone reconstruction is available. If a consistent trading-day definition cannot be reconstructed, fail closed rather than mix broker midnight conventions.

Primary signal at each daily close t:
- trailing 252-trading-day total return using data ending at t;
- LONG if trailing return > 0;
- SHORT if trailing return < 0;
- flat only if exactly zero or history incomplete.

Execution: next trading-day open.
Position is held until the signal sign changes, then reversed at next trading-day open.

No moving-average, volatility threshold, RSI, ADX, news, day-of-week or asset-specific direction filter.

## Risk normalization

For strategy comparison, report both unscaled directional returns and a volatility-normalized research portfolio using a fixed ex-ante 20-day realized-volatility estimator lagged by one full day. Volatility normalization is not a signal filter and must not use future information.

No leverage calibration may be selected after results.

## Diagnostics

- per-market annual return and drawdown;
- position changes / turnover;
- hit rate by day and by completed trend episode;
- long vs short contribution;
- 2024 and 2025 separately;
- equal-risk basket result;
- costs and 1.5x cost stress;
- correlation with D023/D027/D028 if those later produce candidates.

## Verdict use

D029 is NOT judged mainly by trades-per-day and is not intended to finish a prop-firm challenge quickly. Its purposes are:
1. verify that our research stack can reproduce a family with unusually strong long-horizon external evidence;
2. provide a slow diversifying sleeve if it survives our broker/cost constraints;
3. stop us from mistaking D017's failure for a rejection of the entire trend-following literature.

A negative 2024-2025 result does not refute the century literature; it only rejects this exact V0 for our current use. No parameter grid follows.
