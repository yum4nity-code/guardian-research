# V111 EURUSD H11 SHORT 120m — Fresh OOS + FTMO Execution Pipeline

Date: 2026-09-23
Status: FROZEN BEFORE 2023-2025 OUTCOME

Human decision:
- After XAGUSD C1 was execution-rejected, continue to the next remaining V111 calendar candidate: EURUSD H11 SHORT 120m.

## Frozen provenance

Select exactly one row from the existing V111 forensic run:
- source run: GEF111-20260922-163321
- target_market: EURUSD
- cell_type: hour
- H11
- horizon_min: 120
- orientation: -1 / SHORT
- expected pre-OOS support: n = 1295
- historical mean approximately +1.628 bp
- historical net after nominal 1 bp approximately +0.628 bp
- historical leave-one-year-out minimum approximately +1.180 bp
- historical month bootstrap q2.5 approximately +0.759 bp
- old rejection reason: trim-best-5% gate

No parameter may be changed.

## Stage A — Fresh locked OOS

Window:
- 2023-01-01 00:00 through 2026-01-01 00:00 exclusive

Source semantics:
- HistData M1
- raw vendor timestamp +5h
- resample 5min, label=right, closed=left
- entry H11
- exit H13
- SHORT orientation

V2 existence classification:
- NEGATIVE: mean <= 0
- POSITIVE_CONFIRMED: mean > 0 and month-block one-sided 90% lower bound q10 > 0
- POSITIVE_UNCERTAIN: mean > 0 and q10 <= 0

Report diagnostics:
- mean / median / win rate
- control and differential
- yearly means
- leave-one-year-out
- trims 1/2/5%
- remove best 10/20
- nominal source-cost sensitivity 1/2/3 bp

If fresh mean <= 0: stop. Do not run FTMO execution.

## Stage B — FTMO execution, only if Stage A mean > 0

Alignment:
- scan integer offsets -8h..+8h
- require >=90% two-leg M1 coverage
- choose minimum median absolute source-vs-FTMO two-leg price difference
- PnL is forbidden from offset selection

Execution:
- source right-labelled H11/H13 values correspond to the last M1 close before each boundary
- after clock offset is selected, executable entry = first FTMO tick at/after mapped H11 boundary
- executable exit = first FTMO tick at/after mapped H13 boundary
- SHORT = sell BID, cover ASK

Report:
- alignment coverage and price difference
- source-vs-FTMO return correlation
- FTMO BID gross
- observed entry/exit spreads
- executable BID/ASK expectancy
- yearly execution means
- extra-cost sensitivity

No retiming, no alternate exit, no rescue filter.

## Firewalls

- 2026 raw market data: BLOCKED
- alternate hours/horizons/markets/directions: BLOCKED
- PnL-based alignment selection: BLOCKED
- live deployment: BLOCKED
