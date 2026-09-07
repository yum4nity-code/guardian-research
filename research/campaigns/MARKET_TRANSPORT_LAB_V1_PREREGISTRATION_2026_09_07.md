# Market Transport Lab V1 — preregistration

Date frozen: 2026-09-07 Europe/Paris
Status: **PREREGISTERED BEFORE ANY NEW-MARKET OUTCOME INSPECTION**

## Question

Are some Guardian strategy families that showed broad or near-broad edge on the original six-market universe more naturally expressed on other liquid FundedNext markets, without changing their signal or management rules?

This is a market-transport study, not a rescue of parent verdicts. Every parent verdict remains permanent.

## Frozen parent strategies

### Primary transport candidates

1. **D038 NR7 volatility-contraction breakout V0**
   - parent DEV n=459
   - mean net +0.179491R/trade
   - PF 1.5549
   - 5/6 parent symbols positive
   - 2024 and 2025 positive
   - stress positive
   - parent verdict remains REJECT_V0 because its frozen aggregate count gate failed.

2. **D039 Inside-Day breakout V0**
   - parent DEV n=441
   - mean net +0.149366R/trade
   - PF 1.5163
   - 5/6 parent symbols positive
   - 2024 and 2025 positive
   - stress positive
   - parent verdict remains REJECT_V0 because its frozen aggregate count gate failed.

3. **D045 D1 Donchian 20/10 benchmark V0**
   - parent DEV n=145
   - mean net +0.095909R/trade
   - PF 1.2012
   - 5/6 parent symbols positive
   - 2024 and 2025 positive
   - stress positive
   - parent verdict remains REJECT_V0 because frozen mean gate was 0.10R.

### Secondary comparator

4. **D040 NR4 volatility-contraction breakout V0**
   - parent DEV passed all gates and advanced to confirmation;
   - 2026 H1 confirmation failed PF and commission-stress gates;
   - parent verdict remains UNCONFIRMED permanently.
   - D040 is included only as a stability comparator. A positive market-transport result cannot rewrite or rescue D040.

### Explicit exclusion

**D044 Turtle Soup V0 is excluded before transport testing.** Its frozen 2024-2025 DEV produced n=192, mean -0.863003R/trade, PF 0.3968, 0/6 positive symbols, both years negative and stress negative. Adding many new symbols after such a result would create unnecessary rescue/fishing pressure.

## Frozen new-market universe

Exactly these 12 symbols, all outside the original six-market parent universe:

### Forex
- AUDUSD
- USDCAD
- USDCHF
- EURJPY
- GBPJPY
- AUDJPY

### Indices
- SPX500
- NDX100
- GER30
- US30

### Metals
- XAGUSD
- XPTUSD

No symbol may be added, removed or substituted after transport outcomes are inspected in V1.

## Why this universe

- liquid/non-exotic cross-section;
- meaningful diversification across FX, equity indices and metals;
- avoids exotic-FX spread regimes in V1;
- avoids small-crypto microstructure in V1;
- avoids oil commission/swap-model ambiguity in V1;
- all 12 are listed by FundedNext as tradable CFD symbols at preregistration time.

## Frozen time windows

### Engineering smoke
- 2023-10-02 through 2023-10-31
- one representative symbol from each new asset class: AUDUSD, SPX500, XAGUSD
- engineering only; no alpha interpretation.

### Transport development
- 2024-01-02 through 2025-12-31
- all 12 frozen new symbols
- outcomes on these strategy × symbol combinations have not been inspected before this preregistration.

### Future confirmation
- 2026-01-02 through 2026-06-30
- remains unopened for each strategy until its transport-development gates pass.
- the 2026 H1 D040 original-universe confirmation already seen does not make new-symbol 2026 outcomes seen, but D040 remains a comparator and cannot be promoted as a parent strategy through this lab.

## Signal and management freeze

For each parent strategy, transport must preserve its parent signal and management semantics exactly. The only permitted engineering adaptations are:

- extending symbol allowlists to the frozen V1 universe;
- generic asset-class identification for the new symbols;
- commission calculation required to represent the frozen transport cost model;
- symbol-safe PnL/risk calculation using MT5 contract specifications;
- output identifiers/names required to isolate transport evidence.

No entry threshold, lookback, stop, TP, time exit, trailing, partial, regime filter, day filter or direction rule may change.

## Frozen execution model

- FundedNext MT5 local terminal
- sequential execution only
- Strategy Tester Model=0 / Every Tick
- executable bid/ask prices
- USD account
- no parallel MT5
- native Trade Path retained where parent source already provides it.

## Frozen transport cost model

To preserve comparability with the parent research rather than silently rewrite old economics:

- Forex: **USD 5 per lot per side** (USD 10 round trip), matching the parent harness convention.
- Metals: **0.0016% of notional per side**, matching the parent harness convention.
- Indices: **zero explicit commission**, executable tester spread retained.
- commission stress: **1.5x explicit commission**.
- swaps remain unmodeled in V1; this is a limitation, especially for D045 multi-day holds, and must be reviewed before any production interpretation.

Current FundedNext public fee schedules may differ from the conservative parent conventions. V1 deliberately preserves parent-study cost conventions for cross-market comparability; it is not a claim of exact current live billing.

## Development gates — D038 and D039

Each strategy is judged independently across the 12 new symbols:

1. aggregate n >= 500;
2. at least 10/12 symbols have n >= 30;
3. aggregate mean net R > 0;
4. aggregate PF >= 1.10;
5. at least 8/12 symbols have positive total net R;
6. aggregate 2024 total net R > 0;
7. aggregate 2025 total net R > 0;
8. aggregate 1.5x commission-stress total > 0;
9. max contribution from one positive symbol <= 35% of total positive-symbol R;
10. integrity events = 0.

Pass -> `TRANSPORT_CANDIDATE_CONFIRM`.
Failure -> `TRANSPORT_NO_BROAD_PASS`.

## Development gates — D045

1. aggregate n >= 120;
2. at least 10/12 symbols have n >= 8;
3. aggregate mean net R > 0;
4. aggregate PF >= 1.10;
5. at least 8/12 symbols have positive total net R;
6. aggregate 2024 total net R > 0;
7. aggregate 2025 total net R > 0;
8. aggregate 1.5x commission-stress total > 0;
9. max contribution from one positive symbol <= 35%;
10. integrity events = 0.

Pass -> `TRANSPORT_CANDIDATE_CONFIRM`.
Failure -> `TRANSPORT_NO_BROAD_PASS`.

## D040 comparator reporting

D040 receives the D038/D039 transport gates for descriptive comparability, but its result label is always one of:

- `COMPARATOR_BROAD_PASS`, or
- `COMPARATOR_NO_BROAD_PASS`.

Neither label changes D040's permanent `UNCONFIRMED` parent verdict.

## No cherry-picked symbol promotion

A strategy that fails the broad V1 gates may show excellent results on one or several individual new symbols. Those individual outcomes are **discovery only**.

They may not be added to Guardian or called confirmed from this V1 screen. A future symbol-specific hypothesis would require a separate preregistration and untouched future data.

## Ranking

The lab summary ranks strategies lexicographically by:

1. broad gate pass status;
2. number of positive new symbols;
3. lower of 2024/2025 mean contribution sign consistency;
4. aggregate PF;
5. aggregate mean net R;
6. lower max-positive-symbol concentration;
7. strategy ID tie-break.

Ranking is descriptive; parent verdicts are unchanged.

## Interpretation boundary

The purpose is to answer whether alpha transports across a new market cross-section. It is not permission to search the 12 symbols and keep only winners after the fact.

No Market Transport V1 outcome existed when this document was frozen.
