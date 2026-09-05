# Strategy Research Slate — 2026-09-05

Status: ACTIVE / EVIDENCE-FIRST RESET

## Objective

Stop inventing or rescuing indicator stacks. Prefer strategy families with an external empirical or long practitioner evidence base, freeze one V0 before results, then kill quickly if it fails our broker/cost/robustness constraints.

User production preference remains materially large recurring edge, roughly >= +0.15R/trade and ideally +0.20R+, rather than accepting statistically positive crumbs.

## Literature screen

### 1. D023 London ORB M15 — PRIORITY 1
Basis:
- Holmberg, Lonnback & Lundstrom (2013), Finance Research Letters, "Assessing the profitability of intraday opening range breakout strategies", DOI 10.1016/j.frl.2012.09.001.
- Classic ORB practitioner literature including Toby Crabel.

Why today:
- mechanical;
- intraday;
- up to one trade/day/symbol;
- four directly accessible markets;
- rules and engine already prepared before the current results;
- no indicator-stack degrees of freedom.

Frozen V0 is already documented in `handoff/chatgpt_to_codex/2026/09/01/D023_LONDON_ORB_M15_PREREG_AND_ENGINE.md`.

### 2. D022 Relative-Value Pair Reversion M15 — PRIORITY 2
Basis:
- Gatev, Goetzmann & Rouwenhorst (2006), Review of Financial Studies, "Pairs Trading: Performance of a Relative-Value Arbitrage Rule", DOI 10.1093/rfs/hhj020.

Why today:
- economically distinct from directional breakout/momentum;
- two-leg relative-value logic can work while broad market direction is noisy;
- frozen AUDUSD/NZDUSD and EURUSD/GBPUSD V0 already exists;
- engine v2 already prepared with OOS/exit-semantics fix.

Transfer risk: the famous paper uses daily equities, while D022 is an M15 FX adaptation. Therefore the literature justifies testing the family, not assuming the exact adaptation works.

### 3. D027 NR7 Contraction Breakout — PRIORITY 3
Basis:
- Toby Crabel, 1990, narrow-range contraction/expansion framework;
- Crabel 2026 working draft extends ORB/contraction evidence over a very long futures history.

Why today:
- simple price-only setup;
- materially different conditioning from D023: only trades after a prior full-day NR7 contraction;
- frequency across four markets should still be adequate for a 2-year cheap-fail;
- no RSI/EMA/ADX/news filter in V0.

Preregistration: `research/campaigns/D027_NR7_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_05.md`.

### 4. D028 Intraday Session Momentum — PRIORITY 4
Basis:
- Gao, Han, Li & Zhou (2018), Journal of Financial Economics, DOI 10.1016/j.jfineco.2018.05.009;
- Elaut, Frommel & Lampaert (2018), Journal of Financial Markets, DOI 10.1016/j.finmar.2016.09.002, explicit FX intraday momentum;
- Jin et al. (2020), Journal of Futures Markets, DOI 10.1002/fut.22084, commodity futures intraday time-series momentum.

Counter-evidence deliberately retained:
- Rosa (2022), Journal of Futures Markets, DOI 10.1002/fut.22375, finds related intraday momentum predictability disappearing out of sample for one implementation.

Why today:
- one trade/day/symbol;
- very cheap to falsify;
- no stop/target tuning;
- genuinely different from D017 impulse Momentum.

Preregistration: `research/campaigns/D028_INTRADAY_SESSION_MOMENTUM_V0_PREREGISTRATION_2026_09_05.md`.

### 5. D029 Classic Time-Series Momentum Benchmark — PRIORITY 5 / BENCHMARK
Basis:
- Moskowitz, Ooi & Pedersen (2012), Journal of Financial Economics, DOI 10.1016/j.jfineco.2011.11.003;
- Hurst, Ooi & Pedersen (2017), Journal of Portfolio Management, DOI 10.3905/jpm.2017.44.1.015.

Why not priority 1 for the challenge:
- strongest external evidence of the slate, but slow holding horizons;
- useful as a research sanity benchmark/diversifier rather than a fast challenge engine.

Preregistration: `research/campaigns/D029_CLASSIC_TSMOM_BENCHMARK_V0_PREREGISTRATION_2026_09_05.md`.

## Deprioritized today

D021 MICRO-REV stays available but drops behind the evidence-based slate. It is mechanically well preregistered, but has a weaker direct external strategy pedigree than D023/D022/D027/D028/D029.

Legacy RSI, D017 broad Momentum, D025 broad branches and D026 are not to be retuned today.

## How many strategies to test today?

Target: **4 independent V0 families**, not 20 parameter variants.

Recommended execution order:
1. D023 London ORB;
2. D022 Pair Reversion if all four pair legs are available;
3. D027 NR7 Contraction Breakout;
4. D028 Intraday Session Momentum.

D029 is a fifth optional benchmark if data/export capacity is cheap after the four primary tests.

Reason: four independent families gives meaningful breadth in one day while preserving enough attention to data integrity, costs, year split and diagnostics. Testing ten loosely defined ideas would mainly multiply false discoveries and debugging.

## New shared analysis engine

`research/analysis/analyze_d027_d028_price_action_v1.py`

SHA-256 of locally syntax-checked/smoke-tested implementation before commit:
`627a4202d0af971c530c737241ab4f192d6a9ca7babc53326799b97d7160d376`

The engine:
- consumes exactly EURUSD/GBPUSD/USDJPY/XAUUSD M15 bid OHLC + spread-in-price-units CSVs;
- is DST-aware via Europe/London;
- includes a fail-closed pre-OOS guard;
- runs D027 and D028 independently;
- repeats both with 1.5x spread + commission stress;
- applies a frozen 5-day moving-block bootstrap, 5000 reps, seed 20260905;
- persists provenance hashes;
- refuses a fully costed candidate verdict when round-trip commission price-unit inputs are missing.

Synthetic smoke before commit:
- Python syntax compile PASS;
- four-symbol synthetic M15 end-to-end run PASS;
- both D027 and D028 emitted trade files and summary;
- cost-stress path PASS;
- OOS guard active.

Synthetic profitability has no research meaning; it only validates plumbing.
