# Guardian — Cross-strategy edge-decay autopsy

Date: 2026-09-06 Europe/Paris
Status: **META-ANALYSIS COMPLETE / PAUSE BLIND FAMILY HUNTING AFTER D035-E1**

## Executive conclusion

The recent sequence does **not** support the conclusion that the project has discovered “there is no edge anywhere.” It supports a narrower and more useful conclusion:

> The spectacular short-window P/L seen earlier was often a mixture of **local market regime, account/Guardian selection, native trade management, market/symbol selection and optimistic execution context**, rather than a large unconditional entry edge that transports unchanged across years and markets.

Once the research process began separating those components, broadening the history, enforcing untouched confirmation and measuring executable BID/ASK results, most apparent edges shrank. That is a methodological improvement, not evidence that all earlier backtests were fabricated.

The evidence now separates into five different failure modes rather than one generic “strategy failed” bucket:

1. **Regime-local edge that decays through time** — D017 broad Momentum, D029 TSMOM, D034 Gold, several D025 branches.
2. **Profitable managed short-window strategy whose raw entry edge is weak/negative** — legacy RSI and, to a lesser degree, D017 Momentum. This means manager/account-state selection may have been doing material work.
3. **Discovery anomaly that fails untouched confirmation** — D030 ETH H4 Engulfing is the cleanest example.
4. **Statistically real signal that is economically killed by the CFD vehicle/cost structure** — D035.
5. **Real entry edge that survives confirmation but is not yet converted into an executable high-frequency strategy** — D032 Bullish Doji Star.

A sixth category also matters: **data-provenance instability**, most clearly D025 crypto tick-volume. That family cannot be interpreted normally until the feed/model issue is resolved.

## 1. Where the apparent edge went

### Legacy RSI — short-window P/L did not come from a robust unconditional entry edge

Short-window BTC baseline on 2026-09-02:
- RSI-only net profit +9,451.57 USD;
- PF 1.19;
- 621 trades;
- max equity DD 4.20%.

The long-history 2024-2025 entry-path audit then measured 5,104 BTC virtual legs and 4,416 ETH legs. Fixed first-touch expectancy was negative across the complete target ladder:
- BTC +1R EV -0.143R, +3R EV -0.115R;
- ETH +1R EV -0.106R, +3R EV -0.104R;
- both BTC years negative; both ETH years negative.

This does **not** prove the old managed P/L was impossible. The long-history observer deliberately did not replay the complete native v11.16.11 RSI lifecycle after RSI50. The evidence instead says the profitable short sample cannot be attributed to a large raw RSI recross entry edge. If the old P/L generalizes at all, the lift must come from some combination of:
- native 40% RSI50 partial / BE / trailing / RSI70 / runner management;
- account-state and Guardian selection;
- short-window regime;
- interaction with other gating and execution logic.

This is the most important decomposition question still unanswered.

### D017 Momentum — genuine short-window strength, broad signal mostly disappears in 2025

Short-window BTC Momentum-only baseline:
- +7,353.28 USD;
- PF 1.68;
- DD 1.80%;
- 115 trades.

Long-history virtual intrinsic signal, 2024-2025:
- BTC n=1,710: +3R EV only +0.074R pooled;
- ETH n=1,144: +3R EV -0.031R;
- BTC broad +3R EV falls from +0.118R in 2024 to +0.014R in 2025;
- ETH +3R EV falls from +0.047R in 2024 to -0.167R in 2025.

This is strong evidence of **regime dependence** in the broad engine.

However one branch was predeclared and recurs:
- BTC SELL pooled n=761;
- EV +2.5R ≈ +0.131R;
- EV +3R ≈ +0.125R;
- descriptive native-like manager ≈ +0.109R;
- positive in both 2024 and 2025.

That is below the project’s current standalone +0.15R preference and still lacks full cost cushion, but it is not “nothing.” It is a legitimate Tier-B hypothesis if confirmed prospectively.

### D023 London ORB — broad family fails, USDJPY is unusually persistent

Broad four-market D023 V0 failed, but USDJPY was materially different:
- n=489;
- gross mean +0.1499R;
- approximately commission-adjusted mean +0.1179R;
- PF ~1.234 after approximate commission;
- positive gross mean in 2024 (+0.1963R), 2025 (+0.1246R), and 2026 (+0.1009R);
- both LONG and SHORT positive.

Its commission-adjusted block-bootstrap lower bound was slightly below zero, and USDJPY emerged inside a broader failed multi-market campaign, so it remains discovery evidence only. But among all rejected broad families this is one of the strongest stable branches and should not be mentally grouped with “zero edge.”

### D025 — apparent edge change is contaminated by data provenance

D025 is not a normal regime-failure case. Its crypto signal population changed by roughly half between apparently similar historical runs because the M15 tick-volume input became abnormally flat in large blocks under generated `Every tick` history.

Examples:
- BTC 1.03 recovered only 499 virtual trades versus 1,117 in earlier 1.01 sessions;
- ETH 553 versus 1,172;
- August/September 2024 relative tick volume collapsed near 1.0 and mechanically disabled CASCADE events;
- XAU and USDJPY populations remained much closer to prior runs.

The current 1.03 population contains interesting branches such as BTC SHORT, but year splitting already shows regime collapse: BTC SHORT EV2 was ~+0.364R in 2024 and ~-0.077R in 2025.

D025 therefore demonstrates two separate dangers:
1. real regime dependence;
2. historical-data/model provenance changing the signal population itself.

No conclusion about a stable crypto volume-dependent edge is safe until the input provenance is controlled.

### D029 TSMOM — textbook temporal decay / transfer weakness

The 2018-2023 eight-market CFD transfer produced:
- 540 monthly events;
- pooled executable mean -6.93 bps/event;
- source-scaled mean essentially flat (+0.0075%/month/event);
- bootstrap crossing zero widely.

Most revealing is the temporal split:
- 2018-2020: +0.315%/month/event;
- 2021-2023: -0.262%/month/event.

This is the clearest long-horizon example of an effect that can look respectable in one multi-year slice and reverse in another. It also shows that an academic family can be genuine in its source setting but fail a later CFD transport.

### D030 ETH H4 Engulfing — discovery -> untouched confirmation collapse

ETH 2024-2026 discovery was about +0.161R/trade, enough to look like it met the project target.

The untouched PRE2024 confirmation then returned:
- n=321;
- mean executable +0.0396R;
- bootstrap lower ~-0.0845R;
- LONG -0.0257R;
- 2019-2021 slightly negative;
- clean no-gap subset only +0.0127R.

This is almost a textbook demonstration of why symbol selection after discovery cannot be treated as validation. The apparent +0.16R did not transport to independent history.

### D032 Bullish Doji Star — the counterexample: a real entry edge survived

D032 is critical because it falsifies the idea that the stricter process automatically kills everything.

Untouched PRE2024 BTC+ETH+DOG confirmation:
- n=79;
- mean executable +24h +133.52 bps;
- median +93.43 bps;
- win 64.56%;
- mean +0.588R/event;
- same-trend control +32.13 bps;
- Doji-control differential +101.38 bps;
- month-block bootstrap lower >0;
- 7/7 primary gate PASS.

So the process **can** confirm an edge when one is large enough.

The problem is downstream:
- sparse frequency;
- 2023 pooled edge weakened to +13.6 bps;
- ETH became negative in 2022-2023;
- the tested -1R/+3R management produced only +0.118R and bootstrap crossed zero;
- subsequent localization/management variants failed.

D032 therefore separates **entry alpha** from **tradable management** very cleanly.

### D034 Gold abnormal return — recent-regime illusion

Pooled 2024-2026 XAU result was only +1.89 bps/event. Year means:
- 2024 -1.50 bps;
- 2025 -4.16 bps;
- 2026 H1 +13.97 bps.

Looking mainly at current 2026 behavior would have created a much more optimistic impression than the full sample. The LONG branch was +9.64 bps pooled but still below the economic gate and temporally inconsistent.

### D035 Binance deleveraging -> FundedNext CFD — signal exists, vehicle kills it

D035 is a different failure again. Data timing quality was excellent (114/114 UTC-alignment weeks usable, mean correlation ~0.996). The event-control differential at +15m was statistically positive:
- +5.179 bps;
- day-cluster bootstrap [+3.033,+7.385] bps.

But executable pooled SHORT return was -25.448 bps because secondary crypto CFD spreads were enormous:
- BTC ~2.3 bps;
- ETH ~5.6;
- XLM ~7.9;
- LINK/XRP ~24-26;
- ADA/DOG ~34-37;
- XMR/LTC ~68-70.

BTC and ETH themselves were still positive at about +5.9/+5.4 bps after executable spread, but without enough cushion for the project hurdle and remaining costs.

This is not “no information.” It is **information whose monetizable amplitude is smaller than the chosen trading vehicle’s friction**.

## 2. The root causes, ranked by evidence

### A. Regime dependence — HIGH confidence

Direct evidence exists in D017, D025 branches, D029, D030 and D034. Several signals are clearly much better in one year or multi-year block than another.

This is the main explanation for why short local backtests looked stronger.

### B. Raw-signal vs native-management/account-selection mismatch — HIGH confidence

The spectacular 2026-09-02 RSI/Momentum P/L and the later intrinsic-signal diagnostics are not identical experiments.

For RSI especially, the raw entry is substantially negative while the short managed test made money. The missing attribution must be measured rather than guessed.

For Momentum, the long-history diagnostic itself explicitly identifies account-state selection and native management as possible sources of the short-window lift.

### C. Multiple testing / branch selection — HIGH confidence

The project has now inspected many families, markets, directions and variants. Even with a nominal 5% false-positive rate, 12 independent tests would have roughly a 46% chance of at least one false positive; 20 would be roughly 64%. The actual tests are not independent, so these figures are only illustrations, but the direction is clear.

This explains why “one great symbol” inside a failed family must be treated as a new hypothesis, not proof. D030 ETH demonstrates the point empirically.

### D. Execution friction / CFD transport — HIGH confidence

D035 demonstrates this directly. D023 USDJPY also loses roughly 0.032R/trade from the approximate commission adjustment alone. Small statistical edges cannot be judged on mid-price charts.

### E. Data provenance / tester model — HIGH confidence for D025, lower relevance elsewhere

D025 crypto volume changed materially because generated tick history produced abnormal historical tick-volume behavior. This can create both false positives and false negatives.

This is a separate issue from curve fitting and must remain a hard data-quality gate.

### F. Management destroys or fails to capture valid entry alpha — HIGH confidence for D032

D032 is the cleanest example. A +0.588R +24h entry/reference edge became only +0.118R under the tested stop/target manager.

The correct conclusion is not that the entry is fake. It is that the chosen management was poorly matched to the path distribution.

## 3. Important correction to the research objective: distinguish standalone engines from portfolio sleeves

The current preference of roughly +0.15R/trade is useful as a **high bar for a standalone prop-challenge engine**, but it is too blunt as a universal research rejection rule.

A stable +0.08R to +0.12R **net** edge with hundreds of independent trades per year can be economically more useful than a +0.50R edge that appears 20 times per year. Frequency, correlation and cost matter.

This does **not** retroactively rescue any failed strategy. It means future preregistrations should have two prospectively declared classifications:

### Tier A — standalone engine candidate
- robust positive net edge;
- target around >=+0.15R/trade when R is natural;
- bootstrap lower >0;
- multi-year stability;
- sufficient challenge frequency;
- full costs/stress.

### Tier B — portfolio sleeve candidate
Suggested prospective starting gate, not retroactive validation:
- roughly >=+0.07R to +0.10R/trade **after realistic costs** when R exists;
- bootstrap lower >0;
- positive in at least two independent time blocks;
- sufficient event count;
- low enough overlap/correlation with other retained sleeves;
- independent confirmation mandatory if identified from a post-hoc branch.

For strategies without natural R, define the Tier-B hurdle in net bps relative to observed spread/slippage rather than inventing R.

This distinction prevents two opposite errors:
- accepting tiny unstable statistical effects;
- throwing away a real, frequent +0.10R edge merely because it cannot single-handedly finish a challenge fast enough.

## 4. What is genuinely still on the table

### Tier A evidence

**D032 Bullish Doji Star entry** — the only formally confirmed large entry edge so far.

Problem: frequency and risk management, not proof of entry alpha.

### Tier B research candidates — NOT validated production sleeves

**D023 USDJPY London ORB**
- ~+0.118R/trade after approximate commission;
- 489 trades;
- positive in 2024, 2025 and 2026;
- both directions positive.

This deserves a separately preregistered untouched confirmation if suitable data remains available. It should not be rescued inside D023 V0; it would be a new USDJPY-specific hypothesis.

**D017 BTC SELL Momentum**
- pooled EV around +0.125R to +0.131R at larger fixed targets;
- native-like descriptive management ~+0.109R;
- 761 signals;
- positive in both 2024 and 2025.

This deserves exact-native-manager attribution and, only if the net edge survives, a prospective confirmation.

**D035 BTC/ETH narrow-spread response**
- positive executable +15m response around +5-6 bps;
- very high source-event frequency.

At present the cost cushion is too thin. Keep as a microstructure observation, not a trading candidate, unless E1 produces a materially larger causal effect.

## 5. The next research step should be attribution, not another random family

After D035-E1 finishes, pause blind D036/D037 family hunting.

The highest-value experiment is a **frozen edge-attribution replay** of the strategies that once made spectacular short-window money: legacy RSI and D017 Momentum.

For each candidate signal, export one row and calculate nested layers without changing any strategy thresholds:

### L0 — raw entry population
Every intrinsic signal, regardless of account state.

### L1 — exact native strategy management
Same signal population, exact historical TP/partial/BE/trailing/time-stop lifecycle.

`management_lift = L1 realized EV - L0 reference EV`

### L2 — strategy-local gates
Spread filters, cooldowns/regime filters and other strategy-specific acceptance rules exactly as they existed.

`strategy_selection_lift = EV(accepted L2) - EV(all L1)`

### L3 — Guardian/account-state selection
Daily caps, exposure limits, simultaneous-position rules, cooldown state, portfolio interaction.

`Guardian_selection_lift = EV(accepted L3) - EV(accepted L2)`

Then decompose by year/month:
- accepted fraction;
- EV before cost;
- executable EV;
- explicit commission/slippage;
- maximum drawdown/path clustering;
- contribution concentration.

This answers the question we currently cannot answer:

> Did the old profitable backtests disappear because the **market regime changed**, or because our later diagnostics removed a genuinely useful **manager/selection layer**?

If L0 is bad but L1/L2/L3 is robust across 2024-2025, then the “strategy” is not the simple indicator entry; the alpha lives in conditional selection/path management. That is perfectly acceptable if it is causal and reproducible.

If all layers collapse outside the original short window, then the old P/L was regime-local and should be retired.

## 6. New mandatory meta-research rules recommended

1. Every strategy with a managed P/L claim must report both **raw signal EV** and **exact managed EV**. Never infer one from the other.
2. Every accepted/rejected signal must carry rejection reason so selection lift can be measured rather than hidden.
3. Maintain a **trial registry** at family / market / direction / variant level. Post-hoc subgroups are new hypotheses.
4. Every primary report must show year/time-block curve before pooled metrics.
5. Show mid-price, executable BID/ASK and final net-after-cost result separately.
6. Data provenance belongs in the gate: real ticks vs generated ticks, missing blocks, tick-volume validity, source timestamp availability.
7. A short-window profitable P/L is a **lead**, not validation, until a longer or untouched test shows where the edge comes from.
8. Stop treating +0.15R as the only possible success class. Keep it for Tier-A standalone engines; define Tier-B portfolio sleeves prospectively with stability/frequency/correlation requirements.

## 7. Bottom line

The stricter process has not taken us from “real edge” to “no edge.” It has taken us from **unattributed P/L** to a smaller set of claims we can defend.

Current evidence says:
- many broad textbook/adapted signals are indeed too weak;
- several apparent winners were regime-local;
- at least one discovery anomaly vanished on untouched data, proving the validation process is doing its job;
- CFD costs genuinely destroy some small microstructure effects;
- D025 shows historical data can alter the signal population itself;
- D032 proves a large entry edge can survive the same strict process;
- USDJPY ORB and BTC SELL Momentum remain meaningful, but unconfirmed, medium-edge branches that should be judged as prospective portfolio candidates rather than silently forgotten.

Therefore the project should **not** respond by lowering standards or by immediately generating another dozen strategies. It should first locate exactly where the old short-window profits came from, then confirm the best surviving medium-edge branches prospectively.
