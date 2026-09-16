# R26 — COMEX opening-range breakout reversal — preregistration 2026-09-16

## Origin and independence disclosure

R26 is a new study inspired by the R24 discovery result.

R24 itself is closed as a continuation hypothesis and is not being rescued or
relabelled. R26 receives a new research identifier before any R26 metric is
computed on the independent confirmation period.

The 2019-07-01 through 2024-12-31 market payload bytes were previously opened for
R21 confirmation. However:
- the R21 executor computed R21 only;
- no R24/R26 event extraction was executed on the confirmation period;
- no R24/R26 confirmation metric was viewed before this preregistration.

Therefore the confirmation period is outcome-unseen for R26, but it is not
virgin-byte data. This limitation must be disclosed in any later interpretation.

2025 remains reserved and unopened.
2026+ remains protected and unopened.

## Discovery-origin observation

Source:
- R21-R25 discovery r6
- discovery window 2004-11-08 through 2019-06-30
- 3,534 R24 opening-range breakout events

R24 preregistered continuation failed.

Symmetric reversal observations:
- reversal_2b:
  - mean +0.00004904292813144948
  - day-clustered t +1.8977738256000094
  - 8 positive / 8 negative years
- reversal_4b:
  - mean +0.00008173435133260174
  - day-clustered t +2.2952902975103644
  - 11 positive / 5 negative years

Longer horizons were stronger but are not promoted to primary because selecting
them after seeing discovery would be horizon cherry-picking:
- reversal_8b mean +0.00012886812429148252; t +2.6579003551869067
- reversal_16b mean +0.00023675530664637502; t +3.1805857226220584

## Frozen hypothesis

After the first M5 close outside the completed 08:20-08:35 New York COMEX
opening range, XAUUSD tends to reverse against the breakout direction over the
next 10 and 20 minutes.

## Frozen event definition

Exactly reuse the reviewed R24 event extractor from the R21-R25 discovery code.

- timezone: America/New_York
- opening-range bars opened at:
  - 08:20
  - 08:25
  - 08:30
- range completes at 08:35
- breakout search starts at 08:35
- last eligible breakout bar opens at 09:55 and closes at 10:00
- first M5 close strictly above range high or below range low
- one event per New York trading day
- any missing required M5 bar before the first breakout invalidates that day
- breakout direction:
  - +1 above range high
  - -1 below range low

No breakout-distance threshold.
No weekday filter.
No news filter.
No volatility filter.
No session sub-window.
No magnitude bucket.

## Frozen response sign

For each breakout event:

reversal_h = -breakout_direction * forward_return_h

Positive reversal means price moves against the original breakout direction.

## Primary confirmation metrics

Two joint primary metrics:
1. reversal_2b
2. reversal_4b

Both are required.

Frozen scientific confirmation gate:
- reversal_2b mean > 0
- reversal_2b day-clustered t > +2.0
- reversal_4b mean > 0
- reversal_4b day-clustered t > +2.0

If any one of these four conditions fails, R26 confirmation FAILS.

This joint rule is intentionally conservative because R26 was generated from an
observed discovery-side sign inversion.

## Descriptive only

The following may be reported but cannot rescue a failed primary gate:
- reversal_1b
- reversal_8b
- reversal_16b
- all continuation metrics
- yearly sign stability

No descriptive horizon can replace 2b or 4b after confirmation is opened.

## Confirmation window

Frozen:
- start: 2019-07-01
- end: 2024-12-31

The exact same sealed confirmation M5 builder already audited for R21 may be
reused because its only scientific function is immutable stage selection:
2019-07-01 through 2024-12-31.

## Data / provenance

- canonical pinned R15 XAUUSD Dukascopy BID M1 index only
- index SHA256:
  d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566
- derived M5 locally
- absolute 300-second grid required
- 2025 payload bytes must not open
- 2026+ remains hard sealed

## Promotion rule

PASS only if the full joint 2b + 4b gate passes unchanged.

On FAIL:
- no threshold rescue
- no 8b/16b promotion
- no anchor/session change
- no sign relabel
- no immediate 2025 inspection

On PASS:
- only then design an economic/tradability gate before considering 2025.

## Still prohibited

- PnL optimization during confirmation
- entry/SL/TP search
- Guardian integration
- live deployment
- 2025 inspection
- 2026+ inspection
