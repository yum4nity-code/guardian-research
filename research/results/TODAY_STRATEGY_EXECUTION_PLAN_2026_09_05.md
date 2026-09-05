# Today Strategy Execution Plan — 2026-09-05

Status: READY FOR USER RETURN

## Target for today

Test **4 independent V0 strategy families**. Do not expand to ten variants.

Reason: enough breadth to stop betting the day on one idea, but still small enough to audit inputs, costs, year splits and failures without creating a multiple-testing swamp.

## Order

1. **D023 London ORB M15** — price-only directional breakout, daily opportunity.
2. **D022 Relative-Value Pair Reversion M15** — two-leg mean reversion, economically different from D023.
3. **D027 NR7 Contraction Breakout** — volatility contraction -> expansion.
4. **D028 Intraday Session Momentum** — early London direction -> late London direction.

Optional only after those: **D029 classic TSMOM benchmark**.

## Data reuse

D023, D027 and D028 can all use the same exact M15 four-symbol dataset:
- EURUSD
- GBPUSD
- USDJPY
- XAUUSD

Required research input contract for repo-side engines:
- UTC timestamp;
- bid open/high/low/close;
- spread in PRICE UNITS;
- chronological M15 bars.

This means one clean data extraction can feed three different strategy families without rerunning separate raw-history generation.

D022 separately requires synchronized M15 data for:
- AUDUSD / NZDUSD
- EURUSD / GBPUSD

Official FundedNext CFD documentation currently lists AUDUSD and NZDUSD among available Forex instruments, but the user's actual MT5 Market Watch remains authoritative for the specific account/server. Do not substitute a different pair after seeing availability/results.

## Prepared code

D023 repo-side independent conformance implementation:
`research/analysis/analyze_d023_orb_v1.py`
Local pre-commit SHA256: `d588d21621d80fb24308bbdabaa2987d132e68690ec245b14e13373600d094d1`

D027 + D028 shared engine:
`research/analysis/analyze_d027_d028_price_action_v1.py`
Local pre-commit SHA256: `627a4202d0af971c530c737241ab4f192d6a9ca7babc53326799b97d7160d376`

Both implementations passed Python syntax compile and four-symbol synthetic end-to-end smoke tests. Synthetic PnL is meaningless; only plumbing was tested.

## Cost rule

A strategy cannot receive a fully costed candidate verdict unless the engine receives a round-trip commission equivalent in price units for every symbol. Spread is read from each M15 input and a second run is automatically stressed at 1.5x spread + commission.

If commission conversion is not yet reliable, output remains `COST_MODEL_INCOMPLETE` rather than being called profitable.

## Kill discipline

No rescue tuning after first outcomes:
- no different OR window for D023;
- no z-score/window grid for D022;
- no NR4/NR7 cherry-pick after D027;
- no early-return threshold optimization for D028.

A rejected V0 can motivate a separately preregistered V1 only if there is a scientific reason independent of the observed best-performing threshold.

## Expected frequency

D023: up to ~1 trade/day/symbol, but only days with a breakout trigger.
D022: event-driven; frequency depends on spread z-score crossings.
D027: materially lower frequency than D023 because only NR7 contraction days qualify, but four markets should provide a meaningful 2-year sample.
D028: almost exactly one trade/day/symbol when all required bars exist, so this is the fastest high-count falsification test.

## Decision standard

A statistical pass is not enough. User production preference remains approximately >= +0.15R/trade and ideally +0.20R+ for stop-defined strategies, robust across years/regimes and after costs. Small positive anomalies can remain research notes without becoming Guardian auto-trading engines.
