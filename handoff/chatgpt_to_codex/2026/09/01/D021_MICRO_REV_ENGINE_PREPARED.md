# D021 MICRO-REV M1 V0 — engine prepared by ChatGPT

STATUT: IMPLEMENTATION PREPARED / DO NOT REWRITE

ChatGPT implemented the preregistered D021 cheap-fail engine directly as:

`d021_micro_rev_eventstudy.py`

SHA256: `62bb57dc54126190e68afdff2659e948ae87f9a8595228e9986449eec53821c8`

Expected local destination when user places it on D:\:

`D:\MT5_Backtests\automation\d021_micro_rev_eventstudy.py`

The implementation follows `research/campaigns/D021_MICRO_REV_M1_PREREGISTRATION.md`:
- BTCUSD_BT + ETHUSD_BT only;
- M1 reconstructed from executable BID/ASK ticks;
- canonical Wilder RSI(7) and ATR(14) with SMA seed, EMA(20);
- frozen 3-minute shock / 1.5 ATR, 1 ATR extension, RSI 25/75, 40% wick, 35% close-from-extreme, RSI confirmation delta 3;
- same-direction 10-minute suppression;
- first executable quote after confirmation close;
- +1/+3/+5/+10 minute outcomes, +5 primary;
- observed bid/ask plus crypto commission 0.0325%/side by default;
- 1.5x non-commission spread stress;
- executable +/-0.5 ATR barrier diagnostic within 10 minutes;
- MFE/MAE;
- stationary-block bootstrap, fixed seed, one-sided 95% lower bounds;
- frozen cheap-fail gates from preregistration;
- provenance hashes and coverage persisted;
- fail-closed global chronological tick-order check.

The program is deliberately two-pass so large tick histories do not need to fit RAM: pass 1 streams ticks into M1 bars and detects frozen events; pass 2 rereads only event windows for executable outcomes.

OOS guard is fail-closed: if any input timestamp >= 2026-06-28 is encountered, the script aborts and produces no research verdict. Therefore Codex should create/use physically prefiltered pre-OOS BTCUSD_BT and ETHUSD_BT tick files before execution rather than point it at an OOS-containing source.

Validation already performed by ChatGPT before handoff:
- Python syntax compilation passed;
- end-to-end run on synthetic BID/ASK tick files passed and produced deterministic reject output with no events;
- targeted synthetic shock test detected the expected LONG event;
- targeted executable outcome test produced favorable barrier + horizon returns;
- post-hardening smoke run passed after switching RSI/ATR to canonical Wilder seeding and adding chronological-source fail-close.

This validates implementation plumbing only, not market edge.

ACTION_CODEX at next available capacity:
1. Do not redesign or rewrite D021.
2. Locate valid local BTCUSD_BT and ETHUSD_BT tick histories.
3. Produce physically clipped PRE-OOS-only input files ending before 2026-06-28 if necessary.
4. Run this script once with the frozen inputs and persist `D021_events.csv`, `D021_outcomes.csv`, `D021_summary.json`.
5. Apply the verdict exactly as emitted; no threshold retuning and no OOS.

D017 six-market v11.16.2 work remains higher priority, but D021 no longer requires implementation work when capacity becomes available.