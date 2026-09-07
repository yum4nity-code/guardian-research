# Guardian Challenge Probability Lab v1.00 — Implementation Report

Date: 2026-09-07 Europe/Paris
Status: **IMPLEMENTED / LOCAL TEST SUITE PASS / REAL GUARDIAN CSV-SCHEMA SMOKE PASS**
Scope: research infrastructure only; no Guardian Core trading mutation.

## Objective

Answer the operational question that PF/expectancy alone do not answer:

> What is the probability that a realised strategy process reaches the challenge profit target before a daily or overall drawdown rule is breached?

The optimizer therefore selects risk for **challenge pass probability**, not for terminal profit.

## Files

- `research/challenge_probability_lab/challenge_probability_lab_v1_00.py`
  - Git blob: `0fbe86213b5d42dd4d8a6202e4e246ae2ed6ee75`
- `research/challenge_probability_lab/test_challenge_probability_lab_v1_00.py`
  - Git blob: `800808538f1c2013cabb3a48c3ddaa787fb81853`
- `research/challenge_probability_lab/guardian_reference_profile_v1_00.json`
  - Git blob: `8b2bab8ef4c649262e24ee3444d762f9fd5451b9`
- `research/challenge_probability_lab/README.md`
  - Git blob: `db22cec76dd62ddce86a09c17053faa79d13e1dd`

## Frozen v1.00 default risk grid

`0.10% / 0.15% / 0.20% / 0.25% / 0.33% / 0.50%` per trade.

## Simulation design

- one or more real Guardian trade CSVs;
- realised result in R (`net_r` auto-detected, override supported);
- calendar-day grouping with optional explicit normalized `--day-column`;
- circular moving-block bootstrap of contiguous calendar days, default 5 days;
- no iid trade shuffle;
- common random day paths across risk levels for lower-noise paired risk comparisons;
- risk sizing against initial/reference balance by default, with current-balance mode available;
- configurable target, daily loss, max loss, static-initial or trailing-EOD max-loss anchor;
- explicit Monte-Carlo timeout horizon;
- optional signed adverse excursion in R for improved intratrade DD checks;
- deterministic seed and SHA256 input provenance in JSON output.

## Outputs per risk

- pass probability and Wilson 95% CI;
- daily-DD violation probability;
- max-DD violation probability;
- any-DD violation probability and simultaneous-limit diagnostic;
- timeout probability;
- median/P25/P75/P90 days to pass;
- median/P90 trades to pass;
- median/P90/P95/P99/worst-observed max drawdown;
- selected risk whose objective is maximum pass probability.

Each run writes JSON + CSV + Markdown.

## Validation evidence

Local Python validation on the exact engine blob above:

- `python -m py_compile ...` -> PASS;
- 8/8 unit tests -> PASS:
  - deterministic all-winner pass path;
  - deterministic all-loser max-DD path;
  - daily-DD reset across days;
  - same-day cumulative daily breach;
  - signed adverse-R can trigger a breach hidden by final trade P/L;
  - deterministic/common-random-path reproducibility;
  - pass-probability risk selection;
  - Guardian CSV loader compatibility.

A compatibility smoke was also executed against an 18-row excerpt taken directly from the real D037 `backtest-results/backtests/d037/development/20260906T215334Z/trades_compact.csv` schema. The engine loaded all 18 rows and all six default risk levels and produced JSON/CSV/Markdown successfully.

**No scientific performance conclusion is drawn from that 18-row smoke excerpt.** It was only a real-schema integration check.

## Important exactness boundary

Ordinary trade-level `net_r` is not enough to reconstruct exact prop-firm floating equity.

Without synchronized mark-to-market data, v1.00 is an **atomic/closed-equity challenge simulator**. It can understate a daily/max DD breach that occurs intratrade or from overlapping open positions.

If a signed per-trade adverse-R observation is supplied, v1.00 checks it, but simultaneous adverse excursions of concurrent positions are still not reconstructible from isolated trade summaries.

For exact future challenge compliance simulation, the preferred research export extension is:

1. a prop-firm-normalized `challenge_day` key;
2. signed intratrade MAE/adverse R;
3. ideally synchronized portfolio floating-equity / mark-to-market snapshots.

The report must never call the current atomic model exact when those data are absent.

## Scientific boundary

The Lab is downstream decision infrastructure. It must not be used to rescue a strategy that failed alpha/OOS gates. A high pass probability produced by leverage cannot turn negative expectancy into valid alpha.

Use the Lab after the underlying strategy/portfolio evidence is acceptable, then choose risk for the challenge objective.
