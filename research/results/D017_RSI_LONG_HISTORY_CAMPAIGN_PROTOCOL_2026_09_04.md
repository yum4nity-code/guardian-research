# D017 Momentum + RSI Sniper — long-history validation campaign

Date: 2026-09-04
Status: PREPARED / WAITING ONLY FOR MANUAL MT5 COMPILE + BTC/ETH RUNS

## Why this campaign now

Before inventing another strategy family, validate the two engines that previously produced the strongest short-window results.

Historical short-window reference from the 2026-09-02 BTC isolation baseline, Guardian v11.16.11:
- Momentum-only: +7,353.28 USD, PF 1.68, max equity DD 1.80%, 115 trades.
- RSI-only: +9,451.57 USD, PF 1.19, max equity DD 4.20%, 621 trades.
- combo: +17,499.93 USD, PF 1.35, max equity DD 3.76%, 628 trades.

The same RSI sleeve was negative on EURUSD Jul/Aug 2026: -4,705.33 USD, PF 0.74, 260 trades despite 58.85% wins. This already warns that short-window / symbol dependence may be large.

The question is therefore not whether the old screenshots were good. They were. The question is whether the underlying entries survive 2024 + 2025 without Guardian/account-state selection effects.

## Prepared artifacts

### Momentum
- `research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`
- rules lock: `research/campaigns/D017_MOMENTUM_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

### RSI
- `research/ea/RSI_Sniper_EntryPathDiagnostic_v11_16_11_1_01_STATIC_CONFORMANCE.mq5`
- rules lock: `research/campaigns/RSI_SNIPER_11_16_11_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`

### Analysis
- `research/analysis/analyze_long_history_signal_paths_v1.py`

Both EAs are virtual observers only: zero CTrade/order/position/account/margin dependency. The 1.01 static-conformance builds also retain the broker minimum-stop-distance check from production without adding any account-state selection.

## Scientific distinction

### Momentum observer
For BTC/ETH the entry core is copied from D017 v11.16 production and retains the deterministic signal filters and spread/SL gate. Account/prop-firm execution blockers are removed.

### RSI observer
The first test deliberately targets v11.16.11 CLOSED-BAR recross because that is the lineage of the spectacular short-window baseline. It is an entry-edge observer, not an exact recreation of runner concurrency after RSI50.

Do not mix its verdict with later v11.17 live-recross/cost-aware RSI without a separate test.

## Exact first test batch

No broad symbol matrix yet. Run only these four tests:

1. `D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE` — BTCUSD — M1 chart — 2024-01-01 to 2025-12-31 — Every tick.
2. same Momentum EA — ETHUSD — same period/settings.
3. `RSI_Sniper_EntryPathDiagnostic_v11_16_11_1_01_STATIC_CONFORMANCE` — BTCUSD — M1 — same period — Every tick.
4. same RSI EA — ETHUSD — same period/settings.

Inputs can remain at defaults. `InpMaxHoldHours=48`.

## Output files

Momentum folder `FILE_COMMON/GuardianResearch/D017Momentum/`:
- `d017_momentum_virtual_events.csv`
- `d017_momentum_virtual_trades.csv`
- `d017_momentum_virtual_outcomes.csv`

RSI folder `FILE_COMMON/GuardianResearch/RSILegacy111611/`:
- `rsi_111611_virtual_events.csv`
- `rsi_111611_virtual_trades.csv`
- `rsi_111611_virtual_outcomes.csv`

Files are cumulative and session IDs are unique. After BTC then ETH, send one cumulative trio per engine.

## Predeclared evaluation

Before looking at the new results:
- data integrity / session counts first;
- pooled + yearly 2024/2025;
- Momentum BUY/SELL;
- RSI BUY1/BUY2;
- fixed first-touch EV at +0.5R/+1R/+1.25R/+1.5R/+2R/+2.5R/+3R;
- BE@+1R -> +2R/+3R;
- BE@+1.25R -> +2R/+3R;
- RSI50/70 before structural stop;
- same-M1 ambiguity excluded rather than guessed;
- no threshold optimizer.

## Decision standard

- Broad or recurring branch around zero / a few hundredths of R: reject.
- ~+0.10R pre-cost: interesting clue, not enough for production.
- Prefer >= ~+0.15R/trade pre-cost, ideally +0.20R+, repeating in both 2024 and 2025 before cost/stress work.
- If a branch only appears in one year, label regime evidence, not edge.
- If no pre-cost edge exists, do not waste time on spread/commission/slippage modeling to rescue it.

## If Momentum survives

Then build an exact virtual emulator of its production manager:
- BE at +1.25R;
- 25% partial at +2R;
- 1.75 ATR setup-timeframe trailing, updated with production cadence;
- realistic costs + stress.

## If legacy RSI survives

Then build a separate CURRENT RSI v11.17 diagnostic, because production later changed materially:
- live-tick recross with hysteresis/confirmation;
- BUY1 stop buffer 0.50 ATR instead of 0.15;
- anti-late-entry RSI/drift rules;
- cost-aware entry filter;
- TP1 profitability gate;
- post-TP1 / post-TP2 runner behavior.

Do not assume survival of v11.16.11 automatically validates v11.17.

## If they fail

Reject the affected sleeve rather than tuning it to 2024-2025. Only then return to genuinely new strategy-family research.
