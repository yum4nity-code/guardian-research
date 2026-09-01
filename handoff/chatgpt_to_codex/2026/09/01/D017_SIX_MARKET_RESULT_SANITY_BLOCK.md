# D017 SIX-MARKET RESULT — SANITY BLOCK BEFORE SCIENTIFIC VERDICT

STATUS: `READY / CHEAP_FORENSIC_ONLY`
OWNER: Codex
URGENCY: high because a false REJECT would contaminate the research record; quota is scarce, so do NOT rerun the six markets yet.

## Trigger

The latest local Codex status shown to the user says D017 v11.16.2 finished 6/6 reports at 100% quality, OOS locked, but each new market produced only 0-2 trades; three negative and three zero outcomes. Codex says the preregistered verdict is unfavorable.

## Why ChatGPT is blocking acceptance

This trade frequency is implausible relative to previously observed D017/v11.16 Momentum behavior. In particular, USDCAD had previously produced about 155 trades over the comparable pre-OOS research period, not 0-2. A 0-2-trade result across all six markets therefore looks much more like a configuration/gating/runtime mismatch than evidence that Momentum has no edge on those markets.

Do NOT record a scientific REJECT from these six reports until the mismatch is reconciled.

## Cheapest possible next action

No broad audit and no six-market rerun.

1. Inspect ONE representative completed report/config first, preferably USDCAD because there is a prior frequency anchor (~155 trades).
2. Compare only the effective tester settings/runtime gates against the frozen D017 campaign assumptions: correct expert/source, symbol, M15, date range, real ticks, Momentum enabled, session 07-17 UTC, macro H1, time-stop OFF, and no live-only prop-firm/owner/session gate accidentally preventing signals in tester.
3. Read the tester journal/log for explicit signal rejection/block reasons and count them if already logged.
4. If a concrete configuration/gating fault is found, fix only that fault and rerun USDCAD once as a control. Do not relaunch all six until USDCAD trade frequency is back in a plausible range.
5. If USDCAD truly remains 0-2 trades under verified frozen settings, document the exact reason/source difference before any broader rerun or verdict.
6. Preserve OOS lock and zero tuning.

## Quota conservation

This should be a minutes-scale forensic pass using already-generated artifacts. Do not spend remaining Codex quota on repeated backtests, provenance archaeology, refactors or parameter search.
