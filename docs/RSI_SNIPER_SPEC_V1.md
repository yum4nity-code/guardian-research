# RSI Sniper V1 — Canonical Strategy & Guardian Integration Specification

STATUS: DRAFT_CANONICAL
DATE: 2026-09-01
TARGET: Guardian v11.16 CAPREF cleaned/fixed baseline
SOURCE OF TRUTH: This file supersedes scattered chat fragments for RSI Sniper implementation.

## 0. IMPLEMENTATION ORDER — HARD REQUIREMENT

Do NOT implement RSI Sniper before the current Guardian v11.16 CAPREF baseline has been stabilized.

Required order:

1. Fix the CAPREF / signal-ranking conflict currently able to turn production into de facto A+-only behavior.
2. Compile and run a short control test.
3. Remove dead Breakout / Pullback / Sweep / Crypto Sweep production plumbing while preserving every dependency still used by Momentum.
4. Compile again and verify Momentum behavior/frequency is unchanged by cleanup.
5. Only then create the RSI Sniper integration branch/version.

RSI work must remain logically separated from CAPREF fixing and dead-code cleanup so regressions can be attributed to one change set.

---

## 1. STRATEGY INTENT

RSI Sniper is an M1 reversal-cycle strategy based on RSI(14).

It is NOT:
- `RSI low = buy`;
- uncontrolled averaging down;
- two unrelated trades;
- a filter layered onto Momentum;
- a reason for RSI code to modify arbitrary Guardian positions directly.

The core idea is:

`oversold episode -> confirmed recovery -> BUY1 -> optional LAST-CHANCE BUY2 -> RSI50 management -> trailing -> RSI70 management -> runner/exit`

The strategy is modeled as ONE STRATEGY CYCLE with up to two legs.

---

## 2. BASE V1 SIGNAL — CONFIRMED

### 2.1 Indicator

- Timeframe: M1
- RSI period: 14
- Oversold level: 30
- Reset level from standalone V1: 40

### 2.2 ARM state

When RSI crosses from >=30 to <30:

- create/arm one RSI episode;
- state becomes `ARMED`;
- record episode context, including at minimum minimum RSI and episode price low;
- display ONE orange `ARMÉ` marker at the beginning of the episode;
- do not repeat orange markers on every bar below 30.

No buy is triggered merely because RSI is below 30.

### 2.3 BUY1

BUY1 triggers when RSI recrosses above 30 after the armed oversold episode.

Confirmed principle:

`RSI <30 episode -> confirmed recross >30 -> BUY1`

Display naming:

- automatic entry: `A-BUY1`
- manual entry adopted into the RSI cycle: `M-BUY1`

The strategy must not repeatedly generate BUY1 within the same episode.

---

## 3. MANUAL ENTRY ADOPTION

Manual and automatic RSI cycles must be visually and logically distinguishable.

### 3.1 Manual trade inside RSI context

A manual BUY entered while RSI M1 <30 may become the first leg of an RSI cycle and be labeled:

`M-BUY1`

Exact adoption semantics must be implemented conservatively so Guardian never captures unrelated manual trades by mistake.

### 3.2 Manual trade outside RSI context

If a manual BUY is opened while RSI M1 >=30:

- do NOT decorate it as an RSI cycle;
- do NOT apply RSI-specific exits merely because the RSI engine exists;
- Guardian uses normal asset/manual management;
- RSI HUD remains observation-only.

---

## 4. BUY2 — LAST CHANCE

### 4.1 Role

BUY2 is NOT a second independent signal and NOT generic DCA.

It is a second leg of the SAME RSI cycle:

- same `strategy_id = RSI_SNIPER`;
- same `cycle_id`;
- `leg_id = 2`;
- type/label = `LAST_CHANCE` / `BUY2 LAST`.

There is no BUY3.

### 4.2 Proposed trigger — CURRENT DESIGN CANDIDATE, NOT YET HARD-FROZEN

The preferred reconstruction is:

1. BUY1 is still alive;
2. RSI50 has NOT yet been reached / TP1 has not been triggered;
3. RSI falls below 30 again, creating a second oversold episode;
4. price revisits the lows and forms a new low or meaningful retest without invalidating the original cycle stop;
5. preferably the second RSI trough is higher / less weak than the first while price is equal/lower, creating bullish divergence / exhaustion evidence;
6. RSI recrosses >30 again on a closed M1 bar;
7. Guardian verifies the new common-stop proposal and total cycle risk remain within the cycle budget and portfolio limits;
8. only then execute BUY2 LAST.

Rationale: BUY2 must represent a genuine second reversal attempt with weakening selling pressure, not averaging merely because price moved against BUY1.

### 4.3 Unresolved before production

The exact BUY2 trigger is NOT yet final. Before coding production behavior, freeze:

- whether bullish RSI divergence is mandatory or preferred;
- exact price-low relation to the first episode;
- exact invalidation distance relative to BUY1 stop;
- whether any maximum elapsed time/bars applies between BUY1 and BUY2.

Do not invent these during implementation.

---

## 5. RSI CYCLE MODEL

A signal creates an `RSI_CYCLE_ID`.

Conceptual model:

```text
strategy_id = RSI_SNIPER
cycle_id    = 1842
leg_id      = 1 or 2
cycle_state = ...
```

BUY1 and BUY2 are two legs of one strategic bet.

The architecture must distinguish a valid planned second leg from:

- accidental same-signal re-entry;
- duplicate order;
- another strategy on the same symbol.

---

## 6. RISK MODEL — CYCLE LEVEL

Target cycle risk currently reconstructed as:

`0.25% of reference capital`

The hard principle is more important than any implementation detail:

`risk(BUY1 + BUY2 after common-stop calculation) <= RSI cycle risk budget`

BUY2 size is therefore NOT necessarily equal to BUY1 size.

Its allowed volume depends on:

- remaining cycle risk budget;
- BUY2 entry price;
- proposed common stop;
- current risk already carried by BUY1;
- Guardian account / portfolio limits.

A tighter valid stop after BUY2 may permit a larger second leg while keeping total cycle risk fixed.

Guardian remains final authority over actual tradable risk.

---

## 7. COMMON STOP AFTER BUY2

Before BUY2:

- BUY1 may use its initial structural RSI stop.

After BUY2:

- the RSI engine proposes ONE new cycle stop;
- Guardian validates it;
- all RSI legs in that cycle must share the same effective stop;
- BUY1 must not keep its older wider stop while BUY2 uses a new tighter stop.

Conceptual state:

```text
RSI cycle #1842
BUY1 ticket X
BUY2 ticket Y
common_stop = 100.24
```

The exact structural-stop formula is NOT yet frozen and must be specified before production coding.

---

## 8. PRU / BASKET ACCOUNTING

Once BUY2 exists, management is cycle-aware.

Guardian/RSI must know a synthetic basket entry / PRU across BUY1+BUY2, volume-weighted and usable for display and net break-even calculations.

The basket must not be merged with positions belonging to Momentum, ORB, or any other strategy even when they are on the same symbol and direction.

---

## 9. EXIT STATE MACHINE

Target chronology:

`ARMÉ -> BUY1 -> optional BUY2 LAST -> TP1 RSI50 -> TRAIL -> TP2 RSI70 -> RUNNER / EXIT`

### 9.1 TP1 at RSI50 — CONFIRMED TARGET

When RSI reaches/crosses 50 according to the final frozen event semantics:

- close 40% of TOTAL RSI cycle volume;
- mark `TP1 DONE 40%`;
- calculate basket BE NET including relevant fees/commissions;
- activate trailing management on the remainder.

Important: this is cycle-level management, not arbitrary 40% of each ticket independently if doing so produces an incorrect basket result.

### 9.2 BE NET

After TP1:

- compute a net break-even level for the remaining basket;
- fees/commissions must be included;
- display it explicitly.

### 9.3 Trailing

After TP1:

- trailing is active;
- trailing must never move backward / loosen;
- price chart shows the current trailing level with one moving line;
- do not print a new text label on every trailing adjustment.

Exact trailing formula remains TO_BE_FROZEN.

### 9.4 TP2 at RSI70

RSI70 triggers the second profit-management stage.

Confirmed display/state intent:

`TP2 RSI70`

The reconstructed target mentions a final `RUNNER 20%`, but the exact percentage closed at RSI70 and exact runner exit rule are NOT yet fully reconstructed.

Do not guess them in code.

---

## 10. ANTI-REENTRY / RESET

Standalone V1 uses:

`IDLE -> ARMED -> COOLDOWN`

with reset when RSI >=40.

This is a useful proven baseline for preventing repeated BUY1 entries from one persistent signal.

However BUY2 must be a deliberate cycle transition and therefore cannot be blocked by a simplistic `same signal = reject` rule.

Required distinction:

- duplicate BUY1: BLOCK;
- planned BUY2 for existing eligible cycle: potentially ALLOW;
- BUY3: BLOCK.

---

## 11. TIMEBASE INTEGRATION

Guardian v11.16 Momentum currently evaluates entries on the active setup timeframe (typically M5 crypto / M15 classic).

RSI Sniper is M1 and therefore requires an independent M1 clock.

Required pattern in `OnTick()` conceptually:

```text
if new RSI M1 bar:
    process RSI state machine

if new Guardian setup bar:
    process Momentum CheckSignals()
```

Do NOT bury RSI Sniper inside the existing M5/M15-only `CheckSignals()` cadence.

---

## 12. STRATEGY / GUARDIAN RESPONSIBILITY SPLIT

Hard architecture principle:

### Strategy engines decide

- why a signal exists;
- whether BUY1 or BUY2 is strategically desired;
- desired strategic state transition;
- desired structural stop;
- desired TP/trailing state transitions.

### Guardian decides

- whether the account is allowed to take the risk;
- actual admissible volume;
- CAPREF / prop-firm compliance;
- account / portfolio exposure;
- whether a ticket belongs to the requesting strategy/cycle;
- actual broker execution and position modification.

Canonical principle:

`STRATEGY = intention`

`GUARDIAN = authorization + execution + safety`

RSI code should not directly modify Momentum/ORB/other-strategy tickets.

---

## 13. STRATEGY ID / CYCLE ID / LEG ID

Each engine needs its own strategy identity.

Minimum conceptual identity for RSI-managed legs:

```text
strategy_id = RSI_SNIPER
cycle_id    = <persistent id>
leg_id      = 1 | 2
```

Magic Number alone is insufficient to represent the full relationship between positions after restart.

Persistent/reconstructable cycle state should include at least:

```text
cycle_state
initial_risk
current_risk
synthetic_pru
desired/common_stop
tp1_done
tp2_done
leg/ticket ownership
```

Implementation may use comments/state storage/ledger as appropriate, but the relationship must survive restart or be deterministically reconstructable.

---

## 14. MULTIPLE STRATEGIES ON SAME SYMBOL

Example:

```text
Momentum LONG SOLUSD
RSI Sniper LONG SOLUSD
```

These remain TWO independent sleeves.

Do NOT merge:

- PRU;
- stops;
- TP logic;
- trailing;
- cycle state.

Guardian only aggregates their account/portfolio risk.

A common RSI stop may only modify positions owned by the corresponding RSI cycle.

---

## 15. OPPOSITE STRATEGY DIRECTION — OPEN POLICY QUESTION

Example:

```text
Momentum SHORT SOLUSD
RSI Sniper requests BUY SOLUSD
```

No production policy is frozen yet.

Candidates to test later:

- allow both sleeves;
- block the second;
- reduce new risk;
- net-exposure policy;
- strategy-priority policy.

Do not choose one ad hoc during RSI implementation.

---

## 16. HEDGING VS NETTING

Guardian must detect account margin mode at startup.

### Hedging account

BUY1 and BUY2 can naturally exist as separate broker tickets and be grouped by internal cycle metadata.

### Netting account

MT5 merges symbol exposure, so broker positions alone cannot preserve separate strategy sleeves/legs.

A different internal accounting layer is required if netting support is intended.

Do not assume hedging semantics on a netting account.

---

## 17. STANDALONE RSI VS FUTURE INTEGRATED RSI

Current standalone RSI can coexist beside Guardian using its dedicated Magic.

Future integrated architecture must NOT be implemented as a hack such as:

`Guardian also accepts RSI magic`

Instead use a real strategy-to-Guardian request model.

Conceptual request:

```text
RSI_SNIPER
cycle_id      1842
request       ADD_LEG
leg           2
direction     BUY
risk_budget   ...
desired_stop  100.24
state         WAIT_RSI50
```

Guardian validates and executes.

---

## 18. DISPLAY — PRICE CHART

Visual reference: current standalone `RSI_Sniper_Lab_M1_v1` behavior with orange armed marker and large green RSI BUY arrow is the baseline style.

The objective is readable/pedagogical, NOT a Christmas tree.

### 18.1 ARM marker

- one orange marker only;
- label `ARMÉ`;
- no repeated marker for every oversold M1 bar.

### 18.2 BUY1 marker

- large green arrow;
- automatic: `A-BUY1`;
- manual adopted RSI leg: `M-BUY1`;
- text slightly offset from candles to avoid overlap.

### 18.3 BUY2 marker

- visually distinct cyan/blue marker;
- label `BUY2 LAST`;
- clearly looks like leg 2 of the current cycle, not a new unrelated cycle.

### 18.4 Active price lines immediately after entry

On BUY1, show immediately:

- entry/PRU line: subtle grey/light-cyan;
- structural `SL CYCLE` line: red, clearly visible;
- compact next-action text such as `NEXT -> TP1 40% @ RSI50`.

Do NOT draw a fake horizontal price target for TP1 because TP1 is RSI-event based, not known-price based.

Optional visual enhancement:

- very light risk zone between PRU/entry and SL, only if it remains clean and unobtrusive.

### 18.5 After BUY2

Do not stack stale dynamic lines.

Keep BUY1 and BUY2 markers as historical markers, but active management becomes:

- ONE `PRU CYCLE` line;
- ONE `SL CYCLE` line.

Old individual active SL visualization disappears.

### 18.6 After TP1

Display:

- `TP1` historical marker near triggering candle;
- `TP1 40% | TRAIL ON` as concise event text;
- dotted `BE NET` line;
- distinct trailing line that only ratchets in the protective direction.

### 18.7 At RSI70

Display a clear historical marker:

`TP2 RSI70`

Runner percentage/status belongs primarily in HUD, not as additional price-chart clutter.

### 18.8 End of cycle cleanup

At cycle end remove dynamic lines:

- SL;
- PRU active line;
- BE;
- trailing;
- other temporary dynamic guides.

Keep only historical markers so the completed trade remains reconstructable:

`ARMÉ`
`BUY1`
`BUY2` if used
`TP1`
`TP2` / `EXIT`

---

## 19. DISPLAY — RSI SUBWINDOW

Use the RSI subwindow to visualize event thresholds because these are genuine RSI targets.

Desired thin, unobtrusive threshold guides:

```text
70  -------- TP2
50  -------- TP1 40%
30  -------- ARM / BUY
```

Suggested semantic colors:

- 30: orange;
- 50: yellow;
- 70: red/orange.

The price chart shows price risk/management; the RSI panel shows RSI event objectives.

---

## 20. DISPLAY — COMPACT HUD

HUD purpose: show what the engine thinks NOW and what happens NEXT.

Example before TP1:

```text
RSI SNIPER M1
RSI14       46.8
MODE        MANUAL RSI
CYCLE       #17
LEGS        2/2
PRU         101.24
RISQUE      0.17% / 0.25%
ETAT        ATTENTE RSI50
NEXT        TP1 @ RSI50
```

Example after TP1:

```text
ETAT        TRAILING
TP1         DONE 40%
BE NET      101.31
TRAIL       101.54
NEXT        TP2 @ RSI70
RUNNER      20%
```

Cycle-aware richer example:

```text
RSI SNIPER — CYCLE #1842
BUY1          100.95
BUY2          100.42
PRU           100.63
STOP COMMUN   100.24
RISQUE INIT   250 $
RISQUE ACT    163 $
LEGS          2/2
ETAT          ATTENTE RSI50
NEXT          TP1 40% @ RSI50
```

HUD must remain compact.

---

## 21. NO RSI DECORATION FOR NON-RSI MANUAL TRADES

For manual trades outside RSI context:

- no ARM/BUY1/BUY2/TP1/TP2 RSI decorations;
- no RSI-specific price lines;
- normal Guardian trade management only;
- RSI panel/HUD may remain observation-only.

---

## 22. CAPREF INTERACTION

RSI integration must happen only after the current CAPREF issue is fixed.

Known issue to resolve first:

- base auto risk 0.25%;
- minimum auto-trade risk floor 0.25%;
- A/A-/B/C style risk scaling can reduce computed risk below the same 0.25% floor;
- result: only full-scale/A+ signals may pass.

For the cleaned Momentum baseline, intended direction is:

- score/grade may remain diagnostic/prioritization metadata;
- valid Momentum risk should not be accidentally killed by multiplying below the hard floor.

RSI cycle risk design must not inherit this same contradiction.

---

## 23. KNOWN UNRESOLVED ITEMS — MUST BE FROZEN BEFORE PRODUCTION

The following are intentionally NOT invented yet:

1. Exact BUY2 trigger:
   - divergence mandatory vs preferred;
   - low/retest definition;
   - maximum time between legs.
2. Exact initial RSI structural stop formula.
3. Exact common-stop formula after BUY2.
4. Exact trailing formula after RSI50.
5. Exact RSI crossing semantics for TP1/TP2 if needed (intrabar vs closed M1 bar; default should not be assumed silently).
6. Exact amount closed at RSI70.
7. Exact final runner exit rule.
8. Opposite-sleeve policy when another strategy holds the opposite direction on the same symbol.
9. Full netting-account implementation policy.
10. Exact conservative rules for adopting a manual BUY into an RSI cycle.

Any implementation task must surface these as explicit decisions instead of guessing.

---

## 24. ACCEPTANCE CRITERIA FOR INITIAL INTEGRATION

Before considering RSI Sniper integrated:

- Guardian cleaned CAPREF/Momentum baseline still compiles and control tests are stable.
- RSI state machine is driven by independent new M1 bars.
- One oversold episode produces one ARM marker and at most one BUY1.
- BUY2, if enabled, is uniquely tied to the existing cycle and can occur at most once.
- cycle risk never exceeds the configured RSI cycle budget after Guardian calculations.
- BUY2 creates one common stop for both RSI legs.
- RSI cycle management cannot modify non-RSI strategy tickets.
- TP1 at RSI50 acts on total cycle exposure and records 40% completed.
- BE NET is fee-aware.
- trailing never loosens.
- dynamic display cleans itself at cycle end.
- historical markers remain sufficient to reconstruct the completed cycle visually.
- manual non-RSI trades receive no RSI decoration.
- restart/recovery does not lose ownership between RSI legs and their cycle, or lack of recovery is explicitly blocked before production.

---

## 25. REFERENCE IMPLEMENTATION ARTIFACTS

Historical/reference files known from the project:

- `RSI_Sniper_Lab_M1_v1.mq5`
  - visual/reference baseline;
  - BUY-only standalone V1;
  - RSI(14) oversold episode -> confirmed recross >30;
  - state machine IDLE / ARMED / COOLDOWN;
  - standalone auto-trading is NOT the target execution architecture.

- old `FTMO_Crypto_Guardian_PRO_v9_71_RSI_*` files
  - historical RSI experiments only;
  - include an older time-priority concept (`<30`, wait, conditional entry);
  - must not be confused with the current RSI Sniper target.

---

## 26. CANONICAL SUMMARY

RSI Sniper is a two-leg maximum M1 reversal CYCLE.

BUY1 is created by a confirmed recovery from an RSI(14) oversold episode.

BUY2 is an optional, single LAST-CHANCE leg of the same cycle, intended to require a second oversold/recovery event with evidence of seller exhaustion rather than blind averaging.

Risk is budgeted at the CYCLE level.

After BUY2, both legs share one stop and one basket-management state.

RSI50 triggers TP1 on 40% of total cycle exposure, then BE NET + trailing.

RSI70 triggers the second management stage, with final runner details still to be frozen.

The RSI engine expresses strategy intentions; Guardian alone authorizes risk and executes/modifies broker orders.

Visual philosophy:

- price chart = entry/PRU, real stop, BE, trailing and sparse historical markers;
- RSI panel = true RSI event levels 30/50/70;
- HUD = current cycle state, risk, next action;
- no RSI decoration on unrelated manual trades.
