# GEF V104 — Standalone CFTC positioning

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Prior closure

V102 standalone rates validated 5 candidates, but V103 final pre-OOS forensic passed 0/5.
Rates lineage is closed before locked OOS.
2023-2025 and 2026 remain unopened by V103.

## V104 question

Do standalone CFTC positioning states carry reproducible predictive information for the frozen Guardian target universe?

Eligible family:
- family == cftc in the frozen V85 catalog only.

No rates, price, implied-volatility or interaction condition is allowed in a V104 candidate definition.

## CFTC causal semantics

Use the same canonical semantics as V82D/V83:
- CFTC Futures Only reports.
- Prefer explicit decoded report date.
- Fallback YYMMDD zero-fill parse.
- AVAILABLE_AT = first Monday 00:00 UTC strictly after report/as-of date.
- This intentionally lags normal Friday publication and avoids DST/intraday ambiguity.
- Feature definitions exactly match V83:
  - commercial_net_pct_oi level
  - commercial_net_pct_oi d1w
  - commercial_net_pct_oi d4w
  - commercial_net_pct_oi z52
  - noncomm_net_pct_oi level
  - noncomm_net_pct_oi d1w
  - noncomm_net_pct_oi d4w
  - noncomm_net_pct_oi z52
- Exact canonical market mappings from V83 only.

Anchor all 2010-2013 selected CFTC feature values to V83B before state computation. Reconstructed states must exactly match V85 frozen state masks before replication is accepted.

## Temporal protocol

Discovery:
- 2010-2012
- min N 120
- direction from discovery mean only
- raw p <= 0.05
- BH q <= 0.10 across all finite eligible CFTC singleton tests

Internal confirmation:
- 2013
- min N 40
- same directional mean > 0

Freeze <= 200 candidates before 2014+.

Replication 2014-2017:
- N >= 60
- gross mean > 0
- net 1 bp > 0
- positive-year fraction >= 0.50
- trim best 1% > 0

Pre-validation robustness on 2014-2017:
- trim best 2% > 0
- remove best 3 events > 0
- non-overlap > 0
- z0.9 > 0
- z1.1 > 0
- +1 week information delay > 0

Freeze exact survivors before 2018+.

Validation 2018-2022:
- N >= 80
- gross > 0
- net 1 bp > 0
- positive-year fraction >= 0.60
- trim best 1% > 0
- trim best 2% > 0
- remove best 5 > 0
- non-overlap > 0

STOP after validation.
Do not open 2023-2025.
Do not open 2026.

If V104 has validation survivors, a separate final pre-OOS forensic is mandatory before any locked OOS.
