# R15 v1.01 canonical closure — 2026-09-14

Status: CLOSED — clean scientific FAIL at independent confirmation.

## Final published evidence

Published phase:
`phenomenon-discovery/r15-xauusd-gld-intraday-momentum-v101/LATEST.json` on `backtest-results`.

Published result commit:
`53d29f03a3d754610e66d6bfbd6e65aab03ccdc1`.

Protected 2026 remained unopened.

## Data acquisition / provenance

- Dukascopy XAUUSD BID M1 daily source, 2004-11-08 through 2025-12-31.
- Owner-directed fastfill transition preserved the original sequential cache and completed the remaining dates in a separate cache.
- Strict two-cache union PASS.
- Payload count: 5518.
- Eligible R15 boundary days: 5518.
- Missing/holiday count in the final union: 0.
- Full M1 payload caches are retained as reusable XAUUSD historical source data; future XAU studies should reuse them before any remote redownload.

## Stage 1 — published-period near-replication

Window: 2004-11-08 through 2019-05-30.

Guardian XAUUSD result:
- n = 3799
- beta = 0.0410846635809882
- HAC t = 2.7606860681225456
- p = 0.005768009097887283
- R^2 = 0.0037166376006682045
- PASS

Published GLD benchmark:
- beta = 0.0436
- t = 3.03
- R^2 = 0.0049

Interpretation: Guardian recovered the historical published relationship very closely on XAUUSD despite the cross-instrument GLD -> XAUUSD limitation. This is strong validation that the clock mapping, source pipeline and regression harness are capable of recovering the intended historical phenomenon.

## Stage 2 — independent confirmation

Window: 2019-05-31 through 2024-12-31.

Result:
- n = 1458
- beta = -0.00841934508564918
- HAC t = -0.3639169652791975
- p = 0.7159200155945847
- R^2 = 0.00012066546620359553
- positive beta years among 2020-2024 = 2/5
- FAIL

Year betas:
- 2020: -0.037970819424024506
- 2021: -0.03098946664975216
- 2022: -0.012272346699972611
- 2023: +0.02269469881442906
- 2024: +0.05669974258261888

Interpretation: the historical relationship did not persist out of the published sample. The aggregate confirmation beta is slightly negative and statistically indistinguishable from zero. The later positive 2023-2024 coefficients do not justify retuning or rescue.

## Downstream gates

- Economic/execution stage: NOT OPENED because confirmation failed.
- 2025 pre-OOS: NOT OPENED because confirmation failed.
- 2026 protected final OOS: NOT OPENED.

Final funnel:
`replication_pass=1 -> confirmation_pass=0 -> economic_pass=0 -> preoos_survivors=0`.

## Canonical classification

R15 v1.01 is a clean scientific FAIL, not an infrastructure failure.

The correct scientific conclusion is:
- the published historical GLD-like intraday-momentum effect was successfully near-replicated on XAUUSD over the original sample;
- it did not survive independent later-period confirmation;
- no economic promotion, 2025 pre-OOS test, or 2026 final OOS test is justified;
- do not rescue or retune this exact hypothesis on the same confirmation sample.

The acquisition itself remains valuable: the full XAUUSD M1 history is a reusable research asset for future independent XAU hypotheses.
