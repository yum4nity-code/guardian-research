# V111 C8 EURUSD H11 SHORT 120m — FTMO Production-Readiness Audit

Date: 2026-09-23
Status: FROZEN / ANALYZE-ONLY / NO NEW MARKET DATA
Parent: V111 EURUSD H11 SHORT 120m fresh OOS + FTMO execution audit

## Purpose

Determine whether the already-confirmed / execution-surviving EURUSD calendar mini-edge has enough economic and operational margin to justify forward shadowing.

This audit MUST reuse the existing 2023-2025 FTMO execution ledger. It must not open 2026 market data and must not change timing, direction, horizon or signal selection.

## Frozen strategy

- EURUSD
- SHORT
- source H11 entry
- source H13 exit
- hold 120 minutes
- FTMO clock alignment already frozen at +2h from prior audit
- executable entry = first FTMO BID at/after mapped entry boundary
- executable exit = first FTMO ASK at/after mapped exit boundary

No TP, SL, indicator, session filter, news filter, retiming or subgroup selection is introduced here.

## Current FTMO operating facts used

Commission:
- Forex commission introduced across all accounts: USD 2.50 per lot per side
- round trip: USD 5.00 per lot
- source: FTMO Trading Update, 25 Sep 2025

Volume Bands:
- extended to all active FTMO Accounts, Challenges, Verifications and Free Trials from 20 Apr 2026
- actual execution tier depends on order volume
- FTMO published EURUSD example: band 1 (0,1] lots, band 2 (1,15], band 3 (15,30], band 4 (30,50]
- published prices were illustrative, so this audit MUST NOT call them current guaranteed fills

News:
- during FTMO Evaluation (Challenge / Verification), selected-news restriction does not apply
- on a Standard FTMO Account, targeted instruments cannot be opened or closed from 2 minutes before until 2 minutes after selected releases
- Swing accounts are exempt from this news restriction

## Primary diagnostics

Using the existing FTMO execution ledger:

1. Exact per-event commission:
   - for one EURUSD lot, commission USD 5 round trip
   - normalized commission bps = 5 / (entry_bid * 100000) * 10000
   - because both PnL and commission scale linearly with lots, commission bps is lot-size invariant.

2. Net return after observed spread + commission.

3. Stability:
   - mean / median / win rate
   - yearly means
   - monthly means
   - month-block bootstrap q2.5 / q10 / p(mean<=0)
   - trim best 1 / 2 / 5 percent
   - remove best 10 / 20 trades
   - max drawdown in cumulative bps
   - maximum consecutive losing trades

4. Extra-friction budget:
   - grid 0.0 to 1.5 bp round-trip beyond observed spread and commission
   - break-even extra bp
   - break-even pips at mean entry price

5. Volume-band diagnostic:
   Published 2025 EURUSD example implied approximately:
   - band 1 illustrative extra: 0.0 pips round trip
   - band 2 illustrative extra: 0.4 pips round trip
   - band 3 illustrative extra: 0.8 pips round trip
   - band 4 illustrative extra: 1.2 pips round trip
   These are scenario stresses only, NOT claims about today's exact platform bands.

## Classification

- FORWARD_SHADOW_WORTHY:
  mean after current commission > 0
  AND month-block q10 > 0
  AND trim-best-1% > 0.

- FRAGILE_FORWARD_SHADOW:
  mean after current commission > 0 but one or more robustness conditions above fail.

- ECONOMICALLY_REJECTED:
  mean after current commission <= 0.

No production deployment is authorized by this audit.

## Firewalls

- 2026 market data: BLOCKED
- signal retiming: BLOCKED
- alternate horizon: BLOCKED
- news-based alpha filter: BLOCKED
- volume-dependent parameter optimization: BLOCKED
- live deployment: BLOCKED
