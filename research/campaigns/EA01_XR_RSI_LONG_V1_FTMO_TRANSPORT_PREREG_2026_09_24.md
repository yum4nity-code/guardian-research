# EA01-XR-RSI-LONG-V1 — FTMO XAUUSD execution transport

Date: 2026-09-24
Status: FROZEN BEFORE FTMO TRANSPORT
Purpose: answer the remaining economic question for the preserved EA01 XAU mini-edge.

## Existing frozen evidence

Canonical OOS ledger:
- Research/Autonomous/edge_atlas/EA01-XR-RSI-LONG-V1-OOS-2023-2025/signals.csv
- expected SHA256: 35ab88bb139a9b8c23f0ad28287718af9c1906af1eae6cfe78087464a255c3ac
- raw candidate signals: 944
- deterministic 60-minute non-overlap sample: 654
- source raw mean: +0.108563R
- published cost 0.10 mean: +0.062162R, PF 1.086827
- published cost 0.20 mean: +0.015762R, PF 1.021333

This test does NOT reopen discovery and does NOT regenerate or select signals.

## Frozen candidate mechanics

The canonical EA01 probe defines the parent signal from three consecutive same-direction M5 close-to-close moves, with causal Wilder ATR(14) M5 and RSI/context variables. The frozen candidate ledger already contains only EA01-XR-RSI-LONG-V1 signals.

For this transport:
- direction: LONG only
- entry timestamp: canonical ledger entry_time
- hold: 12 M5 bars = 60 minutes
- source 1R: canonical ledger risk (= 1.5 x source M5 Wilder ATR)
- no stop is introduced; this is the same endpoint candidate as the OOS ledger
- non-overlap: deterministic 60-minute rule, reproduced exactly

If ledger hash/schema/N/aggregate parity fails, stop before interpreting FTMO results.

## FTMO alignment

- target execution symbol: XAUUSD (exact or broker suffix-resolved)
- inspect integer offsets -4h..+4h
- require >=90% two-leg M1 coverage
- choose offset only by minimum median source-vs-FTMO entry/exit price distance
- PnL is forbidden from clock-offset selection

Source entry is an M5 bar OPEN, so alignment compares source entry to FTMO M1 OPEN at the mapped boundary.
Source exit is the 60-minute endpoint close, so alignment compares it to the FTMO M1 close immediately before the mapped exit boundary.

## Executable transport

LONG:
- entry = first FTMO ASK at/after mapped entry boundary, <=90s lookup window
- exit = first FTMO BID at/after mapped +60m boundary, <=90s lookup window
- observed spread is therefore embedded directly

R normalization:
- executable price PnL / canonical source risk price units

Commission:
- FTMO Metals CFD rate frozen at 0.0007% of notional per side
- decimal per-side rate = 0.000007
- actual FTMO XAU contract size is read from SymbolInfo
- commission R is calculated from entry+exit notional divided by canonical 1R cash value

FTMO published the 0.0007% Metals CFD per-side commission effective from 29 Sep 2025. This test treats that as the current economic model applied consistently to the historical execution sample.

## Diagnostics

- source-vs-FTMO price alignment
- source-vs-FTMO R correlation
- executable coverage
- mean/median/PF/win rate after observed spread + commission
- yearly net means
- month-block bootstrap q2.5/q10/P(mean<=0)
- trim best 1% / 2%

## Classification

- ECONOMICALLY_REJECTED_FTMO: mean net R <= 0
- FTMO_EXECUTION_POSITIVE_CONFIRMED: mean net R > 0, month q10 > 0, trim-best-1% > 0
- FTMO_EXECUTION_POSITIVE_UNCERTAIN: mean net R > 0 but at least one confirmation diagnostic fails

This is execution/economic transport, not a second independent OOS confirmation.

## Firewalls

- 2026 market data: BLOCKED
- signal regeneration: BLOCKED
- subgroup selection: BLOCKED
- RSI/extremity threshold changes: BLOCKED
- alternate horizon: BLOCKED
- stop/TP invention: BLOCKED
- retuning: BLOCKED
- live deployment: BLOCKED
