# D026 Price Exhaustion Reclaim V0 — static audit + test protocol

Date: 2026-09-04
Status: SOURCE FROZEN / STATIC AUDIT PASS / METAEDITOR COMPILE NOT YET USER-CONFIRMED

## 1. Provenance order

Scientific order is preserved:

1. Rules locked first:
   - `research/campaigns/D026_PRICE_EXHAUSTION_RECLAIM_V0_RULES_LOCK_2026_09_04.md`
   - commit `1137ffbe669504b1aa6b518480b94598f98e3f0c`
2. EA source created only after the lock:
   - `research/ea/D026_PriceExhaustionReclaim_Virtual_V0_1_00.mq5`
   - creation commit `d4e55b0a61a152158a6de20e24b356eb3c0cdc23`
3. No D026 backtest result was inspected before the rule lock/source creation.

## 2. Static source audit

Local source used for audit:
- 678 lines;
- SHA-256 `653fe5ed9ecaf6419aa7bebf7ba6bd49939b0947ced19b0ba06919b75d9aa2da`.

Thresholds present in source exactly as locked:

- WATCH_ATR = 0.50
- SWEEP_MIN_ATR = 0.10
- STOP_BUFFER_ATR = 0.10
- DISP_RANGE_SHOCK = 1.25
- DISP_BODY_ATR = 0.20
- DISP_BODY_EFF = 0.55
- DISP_CLOSE_LOC_LONG_MAX = 0.30
- DISP_CLOSE_LOC_SHORT_MIN = 0.70
- EXHAUST_PROGRESS_FRAC = 0.20
- EXHAUST_RANGE_FRAC = 0.80
- RETEST_ATR = 0.15
- COOLDOWN = 4h

### Forbidden dependency scan

Executable source scan found:
- `tick_volume`: 0 references;
- `real_volume`: 0;
- `AccountInfoDouble`: 0;
- `OrderSend`: 0;
- `PositionOpen`: 0;
- `PositionModify`: 0;
- `PositionClose`: 0;
- Trade.mqh include: 0.

The only string `CTrade` is in a comment explicitly stating there is no CTrade include.

Therefore D026 V0 is structurally **price-only and virtual**.

### Syntax sanity checks

Textual balance check:
- parentheses: balanced;
- braces: balanced;
- brackets: balanced.

This is a static audit only. It is NOT a claim of successful MetaEditor compilation. User confirmation is still required for actual MQL5 compile/runtime validity.

## 3. State-machine conformance

Implemented states:

`IDLE -> WATCH -> SWEEP -> DISPLACEMENT -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`

Key conformance:
- same 8 objective level families as the D025 map;
- fresh sweep rule preserved;
- displacement may occur on the sweep bar or within next two M15 closed bars;
- no volume criterion exists;
- exhaustion uses outward-progress loss + M15 range contraction only;
- reclaim and retest/acceptance deadlines remain finite;
- structural SL uses worst sequence extreme plus 0.10 H1 ATR buffer;
- virtual entry uses validating CLOSED M15 close, not Ask/Bid;
- M1 path logger records +0.5R, +1..+5R, original SL, BE-after-1R and same-M1 ambiguity;
- overlapping virtual trades are allowed up to the diagnostic slot cap.

## 4. Event telemetry

Event CSV includes:
- session / event ids;
- UTC + server-bar-close timestamps;
- symbol / level / side / transition;
- level price / H1 ATR / sweep depth ATR;
- displacement range shock;
- directional body ATR;
- body efficiency;
- close location;
- displacement range;
- exhaustion extra-progress fraction;
- exhaustion range fraction;
- sequence elapsed minutes;
- reclaim delay minutes;
- sequence extreme / final validation path.

Output folder is separate from D025:
- `FILE_COMMON\GuardianResearch\D026\`

Files:
- `d026_per_virtual_v0_events.csv`
- `d026_per_virtual_v0_trades.csv`
- `d026_per_virtual_v0_outcomes.csv`

## 5. Predeclared analysis

Analyzer committed before D026 results:
- `research/analysis/analyze_d026_per_v0.py`
- commit `7495d3edc7d3ef6cd3c1b61c660299f72cd4760a`

The analyzer is restricted to:
- integrity/session counts;
- fixed +1R/+2R/+3R first-touch EV;
- year / side / path splits;
- Wilson-style uncertainty intervals;
- one narrow management family: 40% at +1R, remaining 60% at BE, runner fixed to +2R or +3R;
- ambiguous same-M1 paths excluded rather than guessed.

It does NOT optimize D026 thresholds.

The analyzer was schema-tested against existing D025 virtual CSVs only to verify code operation; those are not D026 results and cannot influence the frozen D026 V0 rules.

## 6. Manual MT5 test protocol — ONLY USER DEPENDENCY LEFT

Do not ask for broad market batches.

First pass needs only:

### Run 1 — BTCUSD
- EA: `D026_PriceExhaustionReclaim_Virtual_V0_1_00`
- tester timeframe: M1
- from: `2024-01-01`
- to: `2025-12-31`
- inputs: `48 / 1 / true`
- modelling: `Every tick` is sufficient for this V0 because entry logic uses closed M15 OHLC/ATR and path logic uses closed M1 high/low; real-tick mode is not required by any D026 rule.

### Run 2 — ETHUSD
Exactly the same settings and date range.

The output files append sessions, so the user can run BTC then ETH and send the final cumulative trio once both are complete:
- events;
- trades;
- outcomes.

No risk %, lot, magic, commission or account-balance input exists because V0 is a pure virtual path observer.

## 7. First-result gates

Before discussing profitability:

1. verify no `VALID_SIGNAL_REJECTED_NO_SLOT`;
2. verify no bad-risk data pathology;
3. verify event state counts look mechanically plausible;
4. split 2024 and 2025 before pooling;
5. inspect BTC and ETH separately;
6. preserve long/short/path symmetry unless results justify only a future hypothesis, not a V0 rewrite.

Production bar remains high:
- tiny positive EV is insufficient;
- prefer >= ~+0.15R pre-cost and ideally ~+0.20R+ on a recurring branch;
- later spread + commissions + slippage + cost stress are mandatory.

## 8. Current status

D026 autonomous preparation is now pushed as far as possible without the user's MT5 terminal:

- rules: DONE / locked;
- source: DONE / committed;
- static audit: DONE;
- analysis script: DONE / predeclared;
- BTC/ETH test protocol: DONE;
- actual compilation + BTC/ETH Strategy Tester runs: WAITING FOR USER when convenient.
