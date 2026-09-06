# GUARDIAN BANGER LAB V1 — 2026-09-06

Status: RESEARCH DESIGN / NO NEW PERFORMANCE CLAIM

## Executive decision

Do not search for one magical monolithic strategy. Build a multi-sleeve Guardian engine from mechanisms that already have independent evidence, then add one genuinely new event-driven crypto sleeve.

The strongest near-term architecture is **GUARDIAN HYDRA V0**:

1. **D17 Momentum + native ratchet manager** — preserve the live management exactly; attribution first, no cosmetic simplification.
2. **USDJPY London ORB** — keep the frozen D023 rule, but require untouched confirmation before portfolio promotion.
3. **Crypto Bullish Doji H1** — retain as sparse confirmed reversal sleeve; do not force frequency.
4. **BTC Deribit 0DTE expiry reversal** — new event-driven sleeve based on a 2026 peer-reviewed paper; start forward OI collection immediately and separately reproduce the paper rule on historical data when obtained.

A fifth microstructure idea, **liquidation-cascade reclaim**, remains experimental and must not reuse D035's rejected lead-lag interpretation.

---

## Why the D17 manager is now a first-class research object

The user reports that the D17 currently running on FTMO behaves usefully in practice, especially because its stop ratchets upward/downward with price. Source inspection is consistent with that observation: the Momentum manager uses TP1 at 2R for 25%, a true-net break-even trigger around 1.25R, and an ATR trailing stop at 1.75 ATR that only moves in the risk-reducing direction.

This is not just execution plumbing. There is external research showing that stop-loss / trailing-stop overlays can materially change momentum factor outcomes, and that the benefit depends on signal quality, volatility and serial correlation. Therefore, fixed-target raw-signal studies are insufficient to judge the full D17 system.

**Decision:** do not strip or retune D17's native manager. First test whether the exact native ratchet creates recurring lift over the same frozen entries.

---

# BANGER 1 — GUARDIAN HYDRA V0

Classification: PORTFOLIO ARCHITECTURE, not a new alpha claim.

### Sleeve M — D17 Momentum / Native Ratchet

- Universe first: BTCUSD only for attribution.
- Source lineage anchor: existing D17 Momentum production candidate / v11.16.x lineage.
- Entry: exact historical D17 Momentum rule; no threshold changes.
- Manager: exact native manager.
  - TP1: +2.00R, close 25%.
  - true-net BE trigger: +1.25R.
  - trailing: 1.75 ATR, ratchet only; never loosen SL.
- Research primary: ALL BTC entries and BTC SELL split reported independently.
- Current evidence: broad raw BTC is modest over 2024–2025, but BTC SELL is the persistent clue and the old full managed short-window system was materially better than the raw diagnostic.

### Sleeve O — USDJPY London ORB

Frozen D023 rule:
- M15.
- London opening range = 08:00–09:00 London, four bars.
- First M15 close outside range from 09:00–11:00.
- Entry next M15 open, executable bid/ask.
- Stop opposite edge of opening range.
- Exit stop or 16:00 London close.
- One trade/day; no reversal.
- No EMA/RSI/ATR/day-of-week/range-size/news filter.

Current evidence is discovery/watchlist only: USDJPY was positive while EURUSD/GBPUSD failed. It therefore needs untouched confirmation before Hydra can treat it as validated.

### Sleeve D — Bullish Doji Star H1 reversal

- Keep the exact confirmed D032 entry rule and natural R definition.
- No new filter.
- Do not promote any previously failed manager.
- Purpose in Hydra: sparse, structurally different reversal sleeve, not frequency engine.

### Sleeve E — BTC 0DTE expiry reversal

New event-driven sleeve described below. It is independent of EMA/Donchian/RSI logic and therefore attractive for portfolio diversification if it transfers to the target CFD feed.

### Hydra risk policy V0

Freeze before portfolio replay:
- M: requested risk 0.25%.
- O: requested risk 0.20%.
- D: requested risk 0.20%.
- E: requested risk 0.15% until independently reproduced on CFD.
- Account open-risk cap: 1.00%.
- No dynamic resizing from historical performance.
- In research, do not silently net simultaneous opposite signals. Log them and use the already-preregistered D024 overlap study.

Historical signal counts suggest the M+O+D combination could be in the rough order of several hundred entries/year before overlap if all branches survive validation. That is a frequency observation, not an expected-return claim.

---

# BANGER 2 — D17 NATIVE RATCHET ATTRIBUTION

Classification: EXACT SOURCE-BEHAVIOR ATTRIBUTION once the exact source/binary lineage is fixed.

## V0 question

For the exact same D17 Momentum entries, where is P/L created or destroyed?

Compare without changing entries:

A. **NATIVE** — exact D17 TP1/BE/trailing lifecycle.
B. **FIXED-3R** — initial SL, full exit at stop or +3R.
C. **TIMEBOX** — initial SL, no profit manager, close at the native trade's maximum allowed lifecycle/time boundary.

A/B/C are attribution counterfactuals, not parameter optimization. No alternate ATR multipliers, BE levels or partial percentages are allowed in V0.

## Mandatory outputs

Per trade:
- signal timestamp / executable entry;
- direction;
- initial_R_price;
- MFE_R / MAE_R;
- first-hit ordering 0.5/1/1.25/1.5/2/2.5/3R;
- actual SL ratchet path;
- TP1 timestamp/price;
- BE timestamp/price;
- final exit reason;
- gross R, spread, commission, slippage proxy, net R;
- Guardian/account-state blocks separately from strategy-local blocks.

## PASS signal

Do not require +0.15R from the manager itself. Manager lift is useful if:
- NATIVE net EV is positive in both independent blocks;
- NATIVE improves net EV or drawdown versus both counterfactuals without relying on a tiny number of runners;
- BTC SELL remains positive after full target-CFD costs;
- benefit is not concentrated in one month / one shock episode;
- bootstrap uncertainty is compatible with a genuine positive full-system edge.

If native manager does not add recurring lift, preserve the evidence and simplify later. Do not tune 1.75 ATR on the same sample.

---

# BANGER 3 — BTC DERIBIT 0DTE EXPIRY REVERSAL V0

Classification: CLOSE-MECHANISM ADAPTATION for CFD transfer. The source paper is on Bitcoin spot/Deribit data; target execution is a CFD.

## External mechanism

A 2026 Finance Research Letters study reports a repeatable intraday reversal around Deribit BTC option expiry. The effect concentrates on high at-the-money option open-interest days. The working-paper methodology defines ATM options as strikes within ±2.5% of BTC at 07:00 UTC, selects the top decile of ATM OI, and describes a simple high-OI-day trade: short at 07:00, reverse long at 08:00, close the long after the post-expiry reversal window. The paper reports an after-cost annualized Sharpe around 0.92 for its implementation.

Deribit currently expires daily BTC options at 08:00 UTC and computes final delivery price from a 07:30–08:00 UTC index TWAP, giving the event a mechanical clock.

## V0 rules — frozen for our first transfer test

Signal data: Deribit BTC option chain snapshot at **07:00:00 UTC ± 5 min**.

1. Identify options expiring at 08:00 UTC that day.
2. BTC reference = Deribit `btc_usd` index at snapshot time.
3. ATM set = strikes within **±2.5%** of index.
4. ATM_OI = sum of call + put open interest across that ATM set.
5. High-OI gate for a forward/live test = current ATM_OI >= **90th percentile of prior available 07:00 daily snapshots only**. No future/full-sample percentile. Warm-up minimum 30 prior expiry days; report percentile sample size.
6. If not HIGH_OI: no trade.
7. If HIGH_OI:
   - Leg 1: SHORT BTCUSD CFD at first executable quote at/after 07:00; close at first executable quote at/after 08:00.
   - Leg 2: LONG immediately after Leg 1 close; close at first executable quote at/after **09:00**.
8. No intraday indicator filters, no EMA/RSI, no discretionary skip.
9. No stop in the scientific V0 because the source mechanism is time-boxed; Guardian safety/drawdown protection still overrides in prop-firm replay and such overrides must be logged separately.
10. Costs: real bid/ask + commission; repeat at 1.5x realized cost stress.

Why 09:00: the paper narrative describes a reversal persisting roughly one hour after 08:00 and explicitly describes selling the long at 09:00. A scraped working-paper table contains a conflicting 10:00 description, so this V0 is labelled ADAPTATION rather than exact replication. The discrepancy must not be mined by choosing whichever exit looks better later.

## Cheap-fail gates

On historical replication data:
- >= 60 HIGH_OI event days total.
- both legs reported separately and combined.
- combined net mean > 0.
- combined net PF >= 1.20.
- 95% bootstrap lower bound of event-day net mean > 0.
- positive net result under 1.5x costs.
- at least 2 independent calendar blocks positive.
- target CFD result must retain at least 50% of the exchange/spot gross effect after its own costs, otherwise reject transfer.

## Data plan

- Start free forward collection now with `deribit_expiry_observer_v1.py` in this pack.
- For historical 2021–2023 replication, obtain minute/5-minute Deribit option chain OI snapshots from a source with provenance. Deribit trade history alone cannot reconstruct historical OI snapshots reliably.
- Do not use current Binance OI REST for this: its historical OI endpoint exposes only the latest 30 days.

---

# BANGER 4 — LIQUIDATION-CASCADE EXHAUSTION RECLAIM V0

Classification: ADAPTATION / NEW HYPOTHESIS.

This is deliberately NOT D035 lead-lag follow-through. D035 asked whether a BTC/ETH deleveraging shock predicted delayed shorts in other CFDs and the economic effect was too small.

The new causal story is **forced deleveraging exhausts itself, then price reclaims**.

## V0 — long side only to control trial count

Source universe: BTC perpetual data, Binance + Bybit, synchronized and available-at-time only.

At each closed M5 bar:
1. `ret_5m` <= rolling prior-30d 1st percentile.
2. `OI_change_5m` <= rolling prior-30d 5th percentile.
3. long-liquidation notional in the 5m window >= rolling prior-30d 99th percentile on BOTH venues, or both venues marked active with same-side liquidation burst.
4. Mark the cascade low. Do NOT enter immediately.
5. Entry only when a subsequent M5 bar closes back above the midpoint of the cascade bar, within the next 6 M5 bars.
6. Entry next executable ASK on BTCUSD CFD.
7. Stop = cascade low minus one target-CFD spread at signal time.
8. No TP optimization. Primary exit = 120 minutes after entry or stop, whichever first.
9. Export MFE/MAE and 0.5/1/1.5/2/2.5/3R touches as diagnostics only.
10. One event per cascade; no re-entry until price has printed 12 M5 bars after exit.

## PASS gates

- >= 150 trades across discovery+confirmation before production consideration.
- discovery and untouched confirmation each positive net.
- confirmation net EV >= +0.07R/trade for Tier-B consideration, or >= +0.15R for Tier-A-sized edge.
- bootstrap lower bound > 0 on confirmation.
- 1.5x cost stress remains positive.
- no single month > 35% of positive P/L.
- effect survives both exchange-source disagreement diagnostics and target-CFD transfer.

Historical data is the bottleneck. Binance's standard OI-history endpoint is only 30 days, so this must use our accumulated Shared Intelligence archive, a vetted archive/vendor, or a prospective sample. No fabricated long history.

---

# Test order

1. **D17 Native Ratchet attribution** — highest priority because it is already live, has historical evidence, and the management itself may explain the short-window/full-system mismatch.
2. **USDJPY D023 untouched confirmation** — cheapest existing branch to promote or kill.
3. **Start Deribit expiry OI collector immediately** — costs almost nothing and builds future untouched evidence while other tests run.
4. **Historical Deribit expiry replication/CFD transfer** when option-chain OI data is available.
5. **D032 Doji management** only after the above; preserve it as confirmed sparse alpha rather than overworking it.
6. **Cascade reclaim** when enough synchronized OI/liquidation history exists.
7. If at least two sleeves independently validate, activate D024 portfolio overlap/equity replay and then decide production caps.

## Things explicitly NOT to do

- Do not tune D17's 1.75 ATR trail, 1.25R BE or 2R/25% TP1 on the already-inspected sample.
- Do not combine strategy scores into one opaque super-score.
- Do not rescue USDJPY ORB by adding filters before independent confirmation.
- Do not use D032 Doji as a trend filter merely because it is confirmed.
- Do not reopen D035's 2026 reserve to rescue the old family.
- Do not call the Deribit expiry sleeve validated on FTMO/FundedNext until target-CFD bid/ask replication passes.

## Bottom line

The best candidate is not “one more indicator strategy”. It is a **four-mechanism stack** where the strongest immediate unknown is whether D17's native ratchet manager is itself creating robust lift. The most novel external candidate is the BTC 0DTE expiry reversal because it is event-clocked, mechanically motivated, high-frequency enough to matter, and orthogonal to our existing trend/reversal/session sleeves.

---

# External references used for V1 design

- Fan, J.H. & Zhang, T. (2024), *Commodity premia and risk management*, Journal of Futures Markets, DOI: 10.1002/fut.22507.
- Kaminski, K.M. & Lo, A.W. (2014), *When do stop-loss rules stop losses?*, Journal of Financial Markets, DOI: 10.1016/j.finmar.2013.07.001.
- Weiss, D., Gaudiosi, R., Zhou, Z.I. & Webb, R.I. (2026), *Bitcoin option expiration, gamma exposure, and intraday price reversals*, Finance Research Letters 107, 110340, DOI: 10.1016/j.frl.2026.110340.
- Shen, D., Urquhart, A. & Wang, P. (2022), *Bitcoin intraday time series momentum*, Financial Review 57(2), 319–344, DOI: 10.1111/fire.12290.
- Deribit official Contract Introduction Policy and Settlement documentation, accessed 2026-09-06.
- Binance official derivatives documentation: `openInterestHist` is limited to the latest 30 days, accessed 2026-09-06.
