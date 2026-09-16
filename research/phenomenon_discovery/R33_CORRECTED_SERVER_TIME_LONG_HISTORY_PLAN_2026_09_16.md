# R33 — Corrected FundedNext-server-time Dukascopy long history — 2026-09-16

## Trigger

R31 showed that the Phase I-A news exclusion is economically negligible for the
frozen R6B candidates on the same FundedNext feed.

R32 then established a strong seasonal clock mapping between FundedNext raw M5
and Dukascopy true-UTC M5:
- Jan/Feb/Nov/Dec: FundedNext server UTC+2
- Mar-Oct: FundedNext server UTC+3
for all 24 months in 2024-2025.

FundedNext documentation independently states server time is GMT+3 during DST
and GMT+2 otherwise.

The March result strongly supports the US/New-York DST calendar rather than the
European DST calendar.

Therefore R30's direct Dukascopy UTC00_08 session was not a faithful
characterization of the frozen R6 session, which is 00:00-08:00 in FundedNext
server-time coordinates.

## Purpose

Re-run R6B-347 and R6B-307 on pinned Dukascopy 2004-2025 after converting every
UTC market timestamp into a synthetic FundedNext server-time coordinate.

Before interpreting the long history, compare corrected Dukascopy 2024-2025
against the exact R31 FundedNext RAW results.

## Clock mapping

For a Dukascopy UTC instant t:

- if America/New_York is in daylight-saving time at t:
  server_time = t + 3 hours
- otherwise:
  server_time = t + 2 hours

The timezone library determines historical US DST transition rules, including
the pre-2007 rule change.

This mapping is infrastructure correction only. It is not selected by R6 PnL.

## Frozen candidates

R6B-347:
- LONG
- lookback 96 M5 rows
- buffer 0.10 ATR14
- session 00:00-08:00 synthetic FundedNext server time
- horizon 96 M5 rows

R6B-307:
- LONG
- lookback 96 M5 rows
- buffer 0.00 ATR14
- session 00:00-08:00 synthetic FundedNext server time
- horizon 48 M5 rows

## Source / execution

Pinned R30 yearly Dukascopy raw M1/M5 derived from R15 index
d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566.

Shift both M5 signal timestamps and M1 execution timestamps into the synthetic
server-time coordinate before replay.

Replay each synthetic server calendar year independently, matching original R6
year isolation.

Same frozen E1/STRESS cost model.

No historical news mask is applied because R31 demonstrated it has negligible
effect on FundedNext 2024-2025.

## Overlap fidelity diagnostic

For 2024 and 2025, compare corrected-Dukascopy results with exact R31 FundedNext
RAW results:
- trade count
- net
- expectancy bps
- PF
- 10,000-at-1x ending capital

This diagnostic determines how much cross-feed discrepancy remains after fixing
the clock.

## Long-history outputs

For 2004-2025:
- 10,000-at-1x ending capital
- total return
- CAGR
- trade-close max DD
- total trades
- PF / expectancy / win rate
- annual capital return / DD / trades
- positive full years 2005-2025

## Interpretation

If corrected 2024-2025 Dukascopy moves materially toward FundedNext and the long
history improves, R30 was materially confounded by clock mismatch.

If corrected overlap remains far from FundedNext, broker/feed construction is a
major dependency and Dukascopy cannot be treated as a faithful substitute for
FundedNext R6.

No parameter tuning, no leverage search, no 2026 access, no live action.
