# D028 — INTRADAY SESSION MOMENTUM V0

Date: 2026-09-05
Status: PREREGISTERED / NOT YET RUN

## Why this family

Peer-reviewed literature documents an intraday time-series momentum effect in which an early-session return predicts a late-session return.

Primary research basis:
- Gao, Han, Li & Zhou (2018), *Journal of Financial Economics*, "Market intraday momentum", DOI 10.1016/j.jfineco.2018.05.009.
- Elaut, Frömmel & Lampaert (2018), *Journal of Financial Markets*, "Intraday momentum in FX markets: Disentangling informed trading from liquidity provision", DOI 10.1016/j.finmar.2016.09.002.
- Jin, Kearney, Li & Yang (2020), *Journal of Futures Markets*, "Intraday time-series momentum: Evidence from China", DOI 10.1002/fut.22084.

Important counter-evidence: Rosa (2022), *Journal of Futures Markets*, reports that one related overnight-to-last-half-hour implementation loses predictability out of sample. D028 therefore treats this as a falsifiable hypothesis, not an assumed edge.

## Frozen V0 universe

Exactly four markets:
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Timeframe: M15.
Session clock: Europe/London, DST-aware.
First campaign: 2024-01-01 through 2025-12-31 when run manually in MT5. OOS >= 2026-06-28 remains locked in any pre-OOS research pipeline.

## Frozen signal and trade rule

For each London weekday:
1. Early-session signal window = exactly 08:00-08:30 London (two M15 bars).
2. Early return = close of 08:15-08:30 bar divided by open of 08:00-08:15 bar minus 1.
3. If early return > 0, late-session direction = LONG.
4. If early return < 0, late-session direction = SHORT.
5. If early return = 0 or either signal bar is missing, no trade.
6. Entry = open of the 16:30-16:45 London M15 bar, executable side if bid/ask is available.
7. Exit = close of the 16:45-17:00 London M15 bar, executable opposite side.
8. Exactly one trade maximum per symbol/day.

V0 has NO magnitude threshold. No volatility, volume, RSI, EMA, ADX, news, day-of-week, spread or Guardian selection filter may be introduced before the first verdict.

Rationale for this strict form: the literature's core claim is directional predictability from early to late session. Adding a signal-strength threshold before seeing our data would add a tuning degree of freedom.

## Costs

Observed bid/ask spread must be included whenever possible. Commission is added according to the research broker/prop-firm schedule in force for the dataset. A second result stresses non-financing execution costs x1.5.

Because the holding window is only 30 minutes, a cost-free positive result is insufficient.

## Mandatory diagnostics

Per symbol, year, side and aggregate:
- trade count;
- gross and net return;
- net PF;
- win rate;
- mean/median net trade return;
- return normalized by same-day ATR for cross-asset comparison;
- long vs short;
- 2024 vs 2025;
- monthly contribution concentration;
- 1.5x cost stress;
- block-bootstrap lower confidence bound on mean daily strategy return.

## Frozen cheap-fail gates

V0 may become CANDIDATE only if:
- >= 180 trades on EACH symbol and >= 800 aggregate;
- >= 3 of 4 symbols have positive net result;
- aggregate net PF >= 1.15 (short holding horizon makes R-based PF less directly comparable to stop-defined strategies);
- aggregate net expectancy remains positive after costs x1.5;
- one-sided 95% moving-block-bootstrap lower bound of mean daily net return > 0;
- no single positive symbol contributes > 60% of total positive contribution;
- 2024 and 2025 are both non-negative aggregate, with no severe sign flip.

The user's production standard remains much stricter than mere statistical significance. A tiny edge may validate the anomaly but will not automatically justify Guardian production.

Failure => REJECT_V0. No post-result threshold search.
