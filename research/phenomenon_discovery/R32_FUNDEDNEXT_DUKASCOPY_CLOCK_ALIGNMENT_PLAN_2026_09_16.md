# R32 — FundedNext vs Dukascopy M5 clock alignment diagnostic — 2026-09-16

## Purpose

Determine the actual clock mapping between the canonical FundedNext Phase I-B
M5 feed and the pinned Dukascopy true-UTC M5 feed, independently of strategy
PnL.

This exists because frozen R6 session 00:00-08:00 is defined in the canonical
FundedNext server-time coordinate, while R30 applied 00:00-08:00 directly to
Dukascopy UTC.

## Inputs

FundedNext raw M5 2024-2025:
SHA256 ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66

Dukascopy R30 yearly M5 2024 and 2025:
must be loaded through the PASS R30 manifest whose source index SHA256 is
d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566.

## Alignment metric

For each calendar month in 2024-2025:

1. Compute close-to-close M5 returns only when each feed has a contiguous
   300-second prior bar.
2. For FundedNext timestamp shifts from -4h to +4h in whole-hour increments,
   align FundedNext return timestamps to Dukascopy timestamps.
3. On matched timestamps, compute Pearson return correlation.
4. Require at least 500 matched return observations for a candidate shift.
5. Report the highest-correlation shift, runner-up, matched count and
   correlation gap.

Definition:
aligned_fundednext_time = fundednext_timestamp + shift_hours.

If the best shift is -2h, FundedNext displayed/server clock is interpreted as
UTC+2 for that month. If best shift is -3h, server clock is UTC+3.

No strategy PnL or R6 signal is computed in R32.

## Interpretation

A stable seasonal -2h/-3h pattern with high return correlation establishes the
clock conversion needed for a corrected Dukascopy R6 long-history test.

If no stable high-correlation mapping exists, feed construction differences
must be investigated before using Dukascopy to characterize R6.

No 2026 access. No parameter tuning. No live action.
