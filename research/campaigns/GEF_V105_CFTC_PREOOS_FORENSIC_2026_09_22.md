# GEF V105 — Final pre-OOS forensic for V104 CFTC survivors

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Frozen source

Exact V104 run:
- GEF104-20260922-145941
- final survivor SHA256: 428ce6c9f5bd5b4acaaf4fbc619b1d07fd0c6abd5ec716403d6b2b4e01a9b68e
- 7 validation survivors
- 2023-2025 not accessed
- 2026 not accessed

V105 audits exactly those seven rows. No replacement, rescue, threshold optimization or new candidate selection.

## Frozen seven

1. cftc_USDCAD_commercial_net_pct_oi_z52 | LO | USDJPY_fwd_240m | SHORT
2. cftc_WTIUSD_commercial_net_pct_oi_level | HI | NSXUSD_fwd_240m | LONG
3. cftc_USDCHF_commercial_net_pct_oi_z52 | HI | USDCHF_fwd_120m | SHORT
4. cftc_USDCAD_commercial_net_pct_oi_level | LO | AUDUSD_fwd_120m | SHORT
5. cftc_USDCAD_commercial_net_pct_oi_z52 | LO | AUDUSD_fwd_120m | SHORT
6. cftc_WTIUSD_commercial_net_pct_oi_level | HI | SPXUSD_fwd_240m | LONG
7. cftc_EURUSD_commercial_net_pct_oi_level | HI | USDCHF_fwd_240m | SHORT

## Core forensic issue

CFTC information is weekly. Intraday target opportunities created while one CFTC state is carried forward are not independent information events.

Therefore V105 must evaluate both:
- the original frozen intraday semantics;
- a de-duplicated information-event view: first eligible target observation per distinct CFTC report AVAILABLE_AT.

## Window

Primary audit: 2018-2022 only.
Earlier data may be read only for causal warmup/state reconstruction.
Forbidden: 2023-2025 and 2026+.

## Exact-source checks

- verify exact V104 run/status;
- verify exact FINAL_SURVIVORS.csv SHA;
- verify exactly seven rows;
- rebuild CFTC source with V82D/V104 parsing and next-Monday AVAILABLE_AT;
- preserve V83B canonical prefix for baseline state history.

## Candidate-level diagnostics

Original intraday view:
- N, mean, median, win rate;
- trim best 1%, 2%, 5%;
- remove best 5 and 10 events;
- remove best calendar month;
- leave-one-year-out minimum;
- horizon non-overlap;
- net after 1, 2, 3, 5 bp.

Information-event view:
- first eligible signal per distinct CFTC report AVAILABLE_AT;
- N reports;
- mean bp;
- positive-year fraction;
- remove best 3 reports;
- remove best 5 reports;
- remove best report-month;
- leave-one-year-out minimum;
- month-block bootstrap 2000 draws, deterministic seed 105.

State-persistence view:
- first eligible signal per contiguous TRUE-state episode.

Timing/threshold robustness:
- z threshold 0.9;
- z threshold 1.1;
- delay CFTC AVAILABLE_AT by +1 calendar day;
- delay CFTC AVAILABLE_AT by +2 calendar days.

Delay diagnostics must shift source availability before as-of reconstruction; do not emulate them by merely subtracting PnL.

## Dependency audit

For the seven frozen candidates:
- exact eligible-signal Jaccard;
- common-timestamp directional-return correlation where defined;
- feature-state signal family;
- upstream CFTC market family;
- target family.

WTI->NSX and WTI->SPX are not two independent information signals.
USDCAD z52 LO -> AUDUSD and -> USDJPY share one information source/state.
USDCAD level LO -> AUDUSD is related but a distinct transform.

No portfolio optimization.

## Final pre-OOS gate

Candidate passes only if all are true:
- baseline mean > 0;
- net 1 bp > 0;
- trim best 5% > 0;
- remove best 10 events > 0;
- remove best month > 0;
- leave-one-year-out minimum > 0;
- horizon non-overlap > 0;
- first-per-report mean > 0;
- first-per-report positive-year fraction >= 0.60;
- first-per-report remove-best-3 > 0;
- first-per-report remove-best-5 > 0;
- first-per-report remove-best-month > 0;
- first-per-report leave-one-year-out minimum > 0;
- first-per-episode mean > 0;
- z0.9 mean > 0;
- z1.1 mean > 0;
- +1d source-availability-delay mean > 0;
- +2d source-availability-delay mean > 0;
- first-per-report month-block bootstrap 2.5% lower bound > 0.

No gate relaxation after results.

## Stop

Regardless of result, STOP after V105.
Do not open 2023-2025.
Do not open 2026.

If any unique information family survives, the next step is a separately preregistered locked-OOS protocol plus human decision.
