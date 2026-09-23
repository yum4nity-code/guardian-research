# V111-C1 XAGUSD H11 60m SHORT — Locked OOS V2

Date: 2026-09-23
Status: FROZEN / HUMAN AUTHORIZED
Human authorization: owner message "go" after explicit selection of V111 XAGUSD H11 60m SHORT.

## Frozen lineage

Source forensic run:
- V111: GEF111-20260922-163321
- candidate: C1
- target: XAGUSD
- cell: H11 / hour-only
- horizon: 60 minutes
- orientation: SHORT (-1)
- source convention: HistData M1 -> raw vendor timestamp +5h -> 5-minute right-labelled / left-closed series
- event: exact top-of-hour H11 label
- outcome: H11 -> H12, oriented SHORT

Historical 2018-2022 evidence is provenance only and must not be retuned:
- n about 1289
- mean about +3.126 bp
- net after nominal 1 bp about +2.126 bp
- leave-one-year-out minimum about +2.707 bp
- month bootstrap q2.5 about +1.164 bp
- historical V111 rejection was driven by trim-best-5% under the old doctrine.

## Fresh window

Open exactly:
- 2023-01-01 00:00 through 2026-01-01 00:00 exclusive

Do not open:
- any 2026 raw market data
- any alternate hour
- alternate horizon
- alternate market
- alternate direction
- rescue filter

## V2 interpretation frozen before outcomes

Existence:
- NEGATIVE if fresh mean <= 0
- POSITIVE_CONFIRMED if fresh mean > 0 and month-block one-sided 90% lower bound (q10) > 0
- POSITIVE_UNCERTAIN if fresh mean > 0 but q10 <= 0

Economic proxy on source data:
- report nominal net after 1/2/3 bp
- this is NOT FTMO execution evidence

Diagnostics only, not death gates:
- yearly means
- leave-one-year-out
- trim best 1/2/5%
- remove best 10/20
- median / win rate
- control mean and candidate-control differential

## Next action

If fresh mean is positive, do not optimize. Use the frozen event ledger for a separate FTMO BID/ASK time-alignment and execution audit.

2026 remains closed.
