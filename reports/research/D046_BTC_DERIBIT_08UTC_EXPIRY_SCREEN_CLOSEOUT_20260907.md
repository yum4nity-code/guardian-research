# D046 — BTC Deribit 08:00 UTC expiry reversal screen closeout

Date: 2026-09-07 Europe/Paris
Formal development verdict: **INCONCLUSIVE_COUNT**
Operational disposition: **CLOSED / NO CONFIRMATION**

## Formal result

The frozen 2024-01-01 through 2025-12-31 D046-A unconditional screen completed with valid engineering evidence and automatic publication.

- paired eligible days: 513
- frozen minimum: 600 -> count gate failed
- PRE_SHORT mean net: -13.439734 bps/day
- POST_LONG mean net: -8.891994 bps/day
- combined mean net: -22.331729 bps/day
- combined total net: -11,456.176783 bps
- combined Profit Factor: 0.394048
- 1.5x commission-stress total: -15,560.176783 bps
- 2024 total: -6,923.866280 bps
- 2025 total: -4,532.310503 bps
- month-block bootstrap 95% interval: [-26.793830, -17.821944] bps/day
- integrity failures: 0
- one ineligible row and one unpaired eligible day; 513 complete paired days remained.

Authoritative event:
`backtests/d046/live/events/development/expiry-finalize/20260907T105525Z`

## Count-gate design error

The preregistered minimum of 600 paired days was not attainable on the observed FundedNext BTC trading calendar. The engineering smoke itself produced 21 paired days in December 2023, consistent with a weekday-style trading calendar rather than 7-day crypto trading. Across 2024-2025 the valid development run produced 513 paired days.

Because the 600 threshold was frozen before development outcomes were opened, it must not be changed retroactively. Therefore the formal verdict remains `INCONCLUSIVE_COUNT` rather than being rewritten as `REJECT_UNCONDITIONAL_SCREEN`.

This count-gate mistake is a methodology/calibration error, not a reason to rerun MT5. The already-observed development outcomes remain valid evidence.

## Scientific interpretation

The count failure does not create a plausible positive interpretation. Every substantive economic gate failed:

- PRE_SHORT mean <= 0;
- POST_LONG mean <= 0;
- combined mean <= 0;
- PF < 1.10;
- 2024 total <= 0;
- 2025 total <= 0;
- stress total <= 0;
- bootstrap lower bound <= 0.

The month-block bootstrap upper 95% bound was still negative (-17.821944 bps/day), so the unconditional 07:00-08:00 short + 08:00-09:00 long pattern is strongly negative in this executable FundedNext sample.

Confirmation is therefore not opened. This is not a post-hoc rejection verdict; it is an operational decision that the preregistered condition for advancement (`UNCONDITIONAL_EXPIRY_SCREEN_PASS`) was not met and the observed economics are decisively adverse.

## High-OI boundary

D046-A did **not** test the paper's high-ATM Deribit option-OI subgroup. The historical Deribit OI mechanism remains untested. Binance/Bybit live OI and slope-ATR telemetry remain prospective context only and must not be used to rewrite D046-A after the fact.

Historical Deribit ATM-OI acquisition is not authorized by D046-A because the preregistered screen did not pass. A future high-OI experiment would require an independent preregistration and independent justification/data source.

## Policy

- Do not rerun D046-A to repair the count gate.
- Do not retune 07:00/08:00/09:00 on the seen 2024-2025 data.
- Do not add weekday, volatility, OI or slope-ATR filters and call it D046 confirmation.
- Keep 2026 H1 unopened.
