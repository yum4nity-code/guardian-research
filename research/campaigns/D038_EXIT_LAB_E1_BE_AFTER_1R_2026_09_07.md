# D038 Exit Lab E1 — Break-even after +1R

Date: 2026-09-07 Europe/Paris
Status: **HYPOTHESIS LOCKED / SEPARATE FROM D038 V0 VERDICT**

## Non-negotiable scientific separation

D038 V0 remains `REJECT_V0` because its frozen DEV count gate failed (459 < 480). Nothing in this Exit Lab can rescue, relabel or reopen D038 V0 confirmation.

D038's native Trade Path telemetry is now used only to generate a **new management hypothesis**.

## Why this test exists

D038 DEV path data showed:
- 459 trades;
- 250 (54.47%) touched +0.5R;
- 150 (32.68%) touched +1R;
- 40 (8.71%) touched +2R;
- 11 (~2.40%) touched +3R;
- 2 (~0.44%) touched +5R;
- among 233 losing trades, 44 (18.88%) had first reached +0.5R and 12 (5.15%) had first reached +1R;
- median loser MFE was ~+0.303R while median winner MFE was ~+1.173R;
- path ambiguity count was zero.

This suggests a concrete question: can protecting a trade only **after +1R has genuinely been earned** reduce full-stop giveback without destroying the fat-tail winners that carry the strategy?

The +1R threshold is chosen now and frozen. No 0.6R/0.8R/1.2R grid search is allowed.

## E1 policy

Entry population, direction, initial stop and costs are unchanged from D038 V0.

Management change only:
1. until first executable +1R touch: original D038 lifecycle;
2. after first executable +1R touch: move protective stop to the original entry price;
3. no partial profit;
4. no TP;
5. no trailing beyond break-even;
6. if BE never triggers, retain original stop/EOD exit;
7. no re-entry.

The actual future MT5 replay must execute BE using the correct liquidation side and real tester ticks. It may not assume a frictionless exact 0R fill.

## Phase A — existing DEV path replay is exploratory only

The already-recorded fields `reached_1r` and `min_r_after_first_1r_before_exit` allow a deterministic **classification** of whether the original path subsequently crossed back through 0R. A lightweight path replay may estimate E1 on the 459 DEV rows.

Limitations:
- exact BE crossing tick/price was not persisted;
- metal/crypto commission changes at the alternate exit price cannot be reconstructed exactly from the compact row;
- therefore Phase A cannot produce confirmation-grade P/L.

Phase A output is hypothesis diagnostics only.

## Phase B — future exact replay

If Phase A is not obviously destructive, create a dedicated E1 MT5 source that replays the same D038 entry rules with native +1R -> BE execution.

Because E1 was selected after viewing 2024-2025 D038 data, those years remain development only.

A prospective 2026 H1 E1 test may only be opened after:
- exact E1 source compiles and smoke passes;
- the E1 rules above remain unchanged;
- no additional management variants are selected from the DEV replay.

## What would count as useful

E1 is interesting only if it improves the loss/giveback profile while preserving a meaningful share of total net R and the rare large winners. Descriptive comparisons should include:
- total/mean net R;
- PF;
- realized close-curve drawdown R;
- fraction of original STOP losses converted to BE exits;
- fraction of original winners truncated by BE;
- top 1/5/10% contribution concentration;
- 2024 vs 2025 separately;
- per symbol;
- commission stress.

No single same-sample improvement is production evidence. Fresh confirmation remains mandatory.
