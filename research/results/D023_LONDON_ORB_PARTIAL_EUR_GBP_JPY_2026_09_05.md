# D023 London ORB M15 — partial real-data verdict — 2026-09-05

Source: user MT5 virtual-diagnostic CSVs, 2024-01-02 through 2026-06-26, D023 v1.02.

Important CSV semantics:
- observed bar spread is already reflected by the diagnostic entry/exit model;
- reported `gross_r` does NOT include commission;
- frozen comparison commission used here for an approximate research adjustment: FTMO-style USD 2.50 per standard lot per side = USD 5 round-trip;
- EURUSD/GBPUSD commission-equivalent price move approximated as 0.00005; USDJPY as `5*entry/100000`; no slippage stress applied here.

## EURUSD
n=516
Gross mean -0.0689R, gross PF 0.871, gross sum -35.55R.
Approx commission-adjusted mean -0.0985R, PF 0.821, sum -50.83R.
By year gross mean: 2024 -0.1135R; 2025 -0.0025R; 2026 pre-OOS -0.1069R.
Direction: LONG -0.0060R gross; SHORT -0.1418R gross.
Decision: REJECT.

## GBPUSD
n=523
Gross mean -0.0300R, gross PF 0.944, gross sum -15.71R.
Approx commission-adjusted mean -0.0532R, PF 0.903, sum -27.80R.
By year gross mean: 2024 -0.1134R; 2025 -0.0403R; 2026 pre-OOS +0.1491R.
Direction: LONG +0.1182R gross; SHORT -0.2062R gross.
Decision: REJECT broad V0; 2026/long-only behavior is descriptive/post-hoc only.

## USDJPY
n=489
Gross mean +0.1499R, gross PF 1.310, gross sum +73.28R.
Approx commission-adjusted mean +0.1179R, PF 1.234, sum +57.63R.
By year gross mean: 2024 +0.1963R; 2025 +0.1246R; 2026 pre-OOS +0.1009R.
Direction gross: LONG +0.1885R; SHORT +0.1064R.
Five-day moving-block bootstrap on zero-filled weekdays: gross lower 5% daily-mean bound about +0.013R/day; after approximate commission about -0.011R/day.
Decision: strongest clue in D023 so far and unusually stable by year, but below the user's desired >=~+0.15R/trade after costs; WATCHLIST ONLY, not production validation.

## Locked D023 V0 verdict already determined
The preregistered D023 gate requires at least 3 of 4 symbols to have positive net R contribution. EURUSD and GBPUSD are already negative. Therefore even if XAUUSD is positive, the exact four-market V0 can have at most 2 of 4 positive symbols and can no longer pass the frozen gate.

Hence D023 V0 is already REJECT_V0 on the locked multi-market criterion; XAUUSD is optional for completion/archival, not needed to decide the V0 verdict.

No post-hoc symbol selection or parameter tuning is authorized. USDJPY may only motivate a separately preregistered future confirmation experiment if desired.