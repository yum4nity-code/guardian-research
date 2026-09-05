# ChatGPT -> Codex — Evidence-Based Strategy Batch — 2026-09-05

## User intent

User explicitly wants the research process to stop inventing/rescuing indicator stacks and instead test several strategy families with credible published/practitioner foundations. He wants meaningful edge, not statistical crumbs, and no curve fitting.

## Do not disturb

- Do not retune legacy RSI, D017 broad Momentum, D025 broad branches or D026.
- Do not mutate Guardian production code while running this research batch.
- Do not use OOS >= 2026-06-28 in any frozen pre-OOS campaign.
- Preserve any healthy currently running local task; never duplicate-start it.
- Shared Intelligence collectors may keep archiving independently.

## Batch target

Four V0 families today, five maximum if the benchmark is cheap:

1. D023 London ORB M15
2. D022 Relative-Value Pair Reversion M15 (only if exact frozen legs are available)
3. D027 NR7 Contraction Breakout
4. D028 Intraday Session Momentum
5. Optional D029 classic TSMOM benchmark

Academic screen: `research/results/ACADEMIC_STRATEGY_SCREEN_2026_09_05.md`.
Execution plan: `research/results/TODAY_STRATEGY_EXECUTION_PLAN_2026_09_05.md`.

## First action on local PC

HARVEST BEFORE LAUNCH:
- inspect D:\MT5_Backtests workers/processes/logs;
- do not restart or duplicate anything already running/complete;
- identify whether clean M15 OHLC+spread data already exist for EURUSD, GBPUSD, USDJPY, XAUUSD and whether AUDUSD/NZDUSD exist for D022;
- preserve provenance/hashes.

### Critical timezone rule

Repo-side D023/D027/D028 engines expect UTC M15 timestamps and convert to Europe/London DST-aware session clocks. MT5 exported bars may be broker-server time. Do NOT relabel server timestamps as UTC. Establish server-time -> UTC provenance/conversion first, or use a tester-side equivalent that constructs London time correctly. Fail closed if timezone provenance cannot be established.

## D023

Frozen spec:
`handoff/chatgpt_to_codex/2026/09/01/D023_LONDON_ORB_M15_PREREG_AND_ENGINE.md`

Original prepared engine SHA256:
`3788e8963b1c3a3c4213e29cf6fa212e29437e10d3c900c9e34261f637946b27`

Repo-side independent conformance implementation:
`research/analysis/analyze_d023_orb_v1.py`

Run exactly once on the frozen four symbols after data/timezone/cost provenance is valid. No OR-window or exit modifications after seeing outcomes.

## D022

Frozen spec:
`handoff/chatgpt_to_codex/2026/09/01/D022_RELATIVE_VALUE_PAIR_REV_M15_PREREG.md`

Use ONLY corrected engine v2 SHA256:
`29f17859acfd7c78ba8eac5e677a6763eea0aab7233474625e4bdd5578b3ed45`

Frozen pairs:
- AUDUSD/NZDUSD
- EURUSD/GBPUSD

If AUDUSD or NZDUSD is unavailable on the actual account/data source, mark D022 DEFERRED_UNAVAILABLE. Do NOT substitute another pair after the fact.

## D027 + D028

Preregistrations:
- `research/campaigns/D027_NR7_CONTRACTION_BREAKOUT_V0_PREREGISTRATION_2026_09_05.md`
- `research/campaigns/D028_INTRADAY_SESSION_MOMENTUM_V0_PREREGISTRATION_2026_09_05.md`

Shared engine:
`research/analysis/analyze_d027_d028_price_action_v1.py`

Reuse the exact same clean EURUSD/GBPUSD/USDJPY/XAUUSD M15 dataset used for D023. One data preparation, three strategy families.

Supply reliable round-trip commission equivalents in PRICE UNITS for each symbol. If conversion is not reliable, allow `COST_MODEL_INCOMPLETE`; never pretend a gross result is net-valid.

## D029 optional

Preregistration:
`research/campaigns/D029_CLASSIC_TSMOM_BENCHMARK_V0_PREREGISTRATION_2026_09_05.md`

This is a slow literature benchmark, not the priority challenge engine. Execute only if daily data/cost handling is trivial after the four primary families.

## D030 reserve

`research/campaigns/D030_H4_ENGULFING_FX_REPLICATION_GATE_2026_09_05.md`

Do not code/execute yet. The published FX/H4 evidence is interesting, but exact paper methodology must be recovered first. No generic candlestick rules may be substituted and called a replication.

## Verdict discipline

- Apply frozen cheap-fail gates exactly.
- Report 2024 and 2025 separately where applicable.
- Include costs and 1.5x cost stress.
- Keep a strategy as research-only if it passes statistical gates but misses the user's stronger practical edge target (~+0.15R/trade, ideally +0.20R+ for stop-defined strategies).
- No threshold/window/side/symbol cherry-picking after outcomes.

After each completed V0, persist outputs and update `CURRENT_PROJECT_HANDOFF.md` and `CURRENT_QUEUE.json` in the same work session.
