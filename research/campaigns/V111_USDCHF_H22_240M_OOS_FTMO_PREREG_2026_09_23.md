# V111 USDCHF H22 LONG 240m — Fresh OOS + FTMO Execution Pipeline

Date: 2026-09-23
Status: FROZEN BEFORE 2023-2025 OUTCOME

## Frozen provenance

Select exactly one row from V111 run GEF111-20260922-163321:
- target_market: USDCHF
- cell_type: hour
- H22
- horizon_min: 240
- orientation: +1 / LONG
- expected pre-OOS support: n = 1047
- historical mean approximately +1.693 bp
- historical net after nominal 1 bp approximately +0.693 bp
- historical trim-best-5% approximately +0.463 bp
- historical leave-one-year-out minimum approximately +1.080 bp
- historical month bootstrap q2.5 approximately +0.956 bp
- old rejection reason: one -5m timing-shift diagnostic

No parameter may be changed.

## Stage A — Fresh locked OOS

Window:
- 2023-01-01 00:00 through 2026-01-01 00:00 exclusive

Source semantics:
- HistData M1
- raw vendor timestamp +5h
- 5min resample, label=right, closed=left
- entry H22
- exit H02 next day
- LONG orientation

V2 existence:
- NEGATIVE: mean <= 0
- POSITIVE_CONFIRMED: mean > 0 and month-block q10 > 0
- POSITIVE_UNCERTAIN: mean > 0 and q10 <= 0

If fresh mean <= 0: stop.

## Stage B — FTMO execution, only if Stage A mean > 0

Clock alignment:
- integer offsets -8h..+8h
- >=90% two-leg M1 coverage
- choose minimum median absolute source-vs-FTMO two-leg price difference
- PnL forbidden from offset selection

Execution:
- first FTMO tick at/after mapped entry and exit boundaries
- LONG = buy ASK, sell BID
- observed spread embedded
- no invented historical commission/swap; output extra-cost grid

Important:
- this 4h hold may cross rollover depending on aligned FTMO clock;
- report current symbol swap metadata but do not use current swap as historical swap;
- if BID/ASK result is already negative, stop there.

## Firewalls

- 2026 raw market data: BLOCKED
- retuning: BLOCKED
- alternate hour/horizon/direction: BLOCKED
- PnL-based alignment: BLOCKED
- live deployment: BLOCKED
