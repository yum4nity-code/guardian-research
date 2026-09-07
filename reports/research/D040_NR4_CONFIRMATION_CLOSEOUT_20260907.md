# D040 NR4 — prospective confirmation closeout

Date: 2026-09-07 Europe/Paris
Status: **CLOSED / UNCONFIRMED**
Experiment: `D040-NR4-VOLATILITY-CONTRACTION-BREAKOUT-V0`

## Scientific verdict

D040 passed every frozen 2024-2025 development gate, so the untouched 2026-01-02..2026-06-30 confirmation window was legitimately opened without changing the strategy.

The confirmation batch is integrity-clean and the frozen confirmation scorer produced **UNCONFIRMED**.

Confirmation metrics:
- aggregate n: **191**;
- mean net R: **+0.0096440117R/event**;
- profit factor: **1.0309836077**;
- positive symbols: **3/6** (`BTCUSD`, `GBPUSD`, `XAUUSD`);
- aggregate total net: **+1.84200623R**;
- commission x1.5 stress total: **-0.16245865R**;
- integrity events: **0**.

Per-symbol total net R:
- BTCUSD: +5.38630573R;
- ETHUSD: -1.96832422R;
- EURUSD: -4.28421602R;
- GBPUSD: +2.08902919R;
- USDJPY: -0.59417846R;
- XAUUSD: +1.21339001R.

Frozen confirmation gates:
- aggregate n >= 120: PASS;
- mean net R > 0: PASS;
- PF >= 1.08: **FAIL**;
- >=3 positive symbols: PASS;
- commission-stress aggregate > 0: **FAIL**;
- integrity events <= 0: PASS.

Evidence:
- score event: `backtests/d040/live/events/confirmation/score/20260907T071519Z`;
- confirmation batch: `backtests/d040/live/events/confirmation/batch/20260907T070952Z`;
- campaign event: `backtests/d040/live/events/confirmation/campaign/20260907T071540Z`;
- all six native Trade Path validators passed.

## Interpretation boundary

The strong development result did not survive the untouched 2026 H1 gate. The mean remained slightly positive, but PF collapsed below the frozen threshold and the stressed result became slightly negative. This materially lowers production confidence in the NR4 contraction-breakout candidate.

Do **not** retune NR4 on the now-seen 2026 H1 confirmation sample. D040 V0 is closed and cannot be rescued or relabeled.

D038 NR7 and D039 Inside-Day remain separate development-only evidence. Their attractive development results do not override D040's failed prospective confirmation.

## Tooling note — does not affect the verdict

The confirmation campaign correctly completed compile, six-market Model=0 batch, native Trade Path validation and frozen confirmation scoring. It then raised `v1 rich scorer currently supports development only` while attempting post-decision descriptive analytics.

This is an orchestration/analytics limitation **after** the authoritative frozen score. It does not invalidate the batch, Trade Path evidence or UNCONFIRMED verdict, and it must not trigger an MT5 rerun. The runner should be corrected so descriptive confirmation analytics can be generated from the already-existing batch and so a post-decision analytics failure is not mislabeled as an experiment engineering failure.
