# Market Transport Lab V1 — Closeout

Date: 2026-09-07 Europe/Paris
Status: **CLOSED / NO BROAD TRANSPORT PASS**

## Scope

Frozen preregistration:
`research/campaigns/MARKET_TRANSPORT_LAB_V1_PREREGISTRATION_2026_09_07.md`

Frozen new-market universe:
AUDUSD, USDCAD, USDCHF, EURJPY, GBPJPY, AUDJPY, SPX500, NDX100, GER30, US30, XAGUSD, XPTUSD.

Parent verdicts remain unchanged. This lab was a separate market-transport study and never a rescue of rejected/unconfirmed parent experiments.

## Results

### D047 — D038 NR7 transport

- status: `TRANSPORT_NO_BROAD_PASS`
- n = 903
- mean net R = -0.0266508R/trade
- PF = 0.931415
- total = -24.0657R
- stress total = -30.5539R
- 2024 = -10.7948R
- 2025 = -13.2709R
- positive symbols = 6/12: GBPJPY, SPX500, NDX100, GER30, US30, XAGUSD
- integrity events = 0

Important discovery-only pattern: all four equity indices were positive. Their combined D047 2024-2025 result was 299 trades, +31.66879718R total, +0.10591571R/trade. This subgroup was identified after opening V1 development data and is therefore not a V1 pass. It may only motivate a separately preregistered hypothesis on untouched future data.

### D048 — D039 Inside-Day transport

- status: `TRANSPORT_NO_BROAD_PASS`
- n = 805
- mean net R = -0.0400952R/trade
- PF = 0.887230
- total = -32.2767R
- stress total = -37.2645R
- 2024 = -29.2065R
- 2025 = -3.0701R
- positive symbols = 3/12: USDCHF, NDX100, XAGUSD
- integrity events = 0

### D049 — D045 Donchian 20/10 transport

Formal status: `MARKET_TRANSPORT_ENGINEERING_INCOMPLETE`.

XPTUSD repeatedly ended `FINAL_INVALID_REFERENCE` while a trade was open. The exact source deliberately treats that condition as fatal rather than inventing a substitute reference/exit. XPTUSD was not silently removed from the frozen formal universe.

The 11 valid markets were scored descriptively only:

- n = 276
- mean net R = -0.0198714R/trade
- PF = 0.955785
- total = -5.4845R
- stress total = -6.0986R
- 2024 = +6.2995R
- 2025 = -11.7841R
- positive symbols = 5/11: USDCHF, EURJPY, GBPJPY, SPX500, XAGUSD
- max positive-symbol contribution share = 38.54%
- integrity events on the 11 valid markets = 0

These descriptive results provide no economic reason to keep retrying XPTUSD or to open confirmation. D049 remains formally engineering-incomplete, not rejected, but is operationally closed with no confirmation authorized.

### D050 — D040 NR4 comparator

- status: `COMPARATOR_NO_BROAD_PASS`
- n = 1567
- mean net R = -0.0499294R/trade
- PF = 0.861525
- total = -78.2393R
- stress total = -88.2671R
- 2024 = -35.7045R
- 2025 = -42.5349R
- positive symbols = 4/12: SPX500, NDX100, GER30, XAGUSD
- integrity events = 0

D040 remains permanently `UNCONFIRMED`; this comparator result cannot alter the parent verdict.

## Formal Lab decision

No primary Market Transport V1 candidate passed the preregistered broad 12-market development gates.

- D047: no broad pass
- D048: no broad pass
- D049: engineering-incomplete; descriptive valid-market economics also fail broadly
- D050: comparator no broad pass

No V1 confirmation window is opened for D047, D048, D049 or D050 under the original broad-transport hypotheses.

## Discovery boundary and next hypothesis

The strongest coherent discovery is not a single cherry-picked symbol but an asset-class cluster inside D047: **all four equity indices were positive under NR7** in 2024-2025, with 299 trades and +31.6688R total.

This does **not** rescue D038 or D047. It creates a new hypothesis:

> NR7 volatility-contraction breakout may have an equity-index-specific transport edge that is diluted or reversed when pooled with the broader FX/metals transport universe.

If pursued, that hypothesis must be preregistered separately before inspecting the untouched 2026 index outcomes, use all four frozen indices (SPX500, NDX100, GER30, US30), preserve the D047 signal/management/cost semantics, and accept failure without symbol removal or parameter retuning.

## Policy

- Parent verdicts unchanged.
- Market Transport Lab V1 closed.
- No post-hoc broad-universe rescue.
- XPTUSD engineering failure is not converted into a strategy loss/reject.
- Individual/subgroup winners remain discovery only until separately preregistered and tested on untouched data.
