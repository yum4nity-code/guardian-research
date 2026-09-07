# D051 NR7 Equity-Index Cluster Confirmation — closeout

Date: 2026-09-07

## Scientific identity

D051 was a new, preregistered hypothesis derived from D047 development discovery. It did not rewrite D038 or D047. The unchanged D038/D047 NR7 semantics were tested only on SPX500, NDX100, GER30 and US30 over the previously reserved 2026-H1 confirmation window.

Entry/management remained unchanged:
- previous completed broker D1 bar must be strict NR7;
- next broker day, first executable tick breakout of the NR7 high/low wins;
- stop at the opposite NR7 extreme;
- no TP, break-even, partial, trailing, indicator or regime filter;
- exit at stop, EOD, or tester end.

## Confirmation result

**D051_UNCONFIRMED_CLOSE**

- aggregate n: 61 (gate >=60 PASS)
- per-symbol n: SPX500 14, NDX100 10, GER30 17, US30 20 (each >=10 PASS)
- aggregate mean net R: **-0.0429737102R/trade** (FAIL)
- aggregate PF: **0.8784327734** (FAIL vs >=1.10)
- aggregate total net R: **-2.62139632R** (FAIL)
- positive symbols: **2/4** (FAIL vs >=3)
- SPX500: -3.37654527R
- NDX100: +2.38774232R
- GER30: -4.10663601R
- US30: +2.47404264R
- max positive-symbol contribution share: 0.5088753740 (PASS <=0.60)
- integrity events: 0 (PASS)

Trade Path validation passed for all 61 trades with zero path-calculation failures and zero ambiguous path rows.

Authoritative immutable event:
`backtests/d051/live/events/confirmation/d051-confirm-score/20260907T135932Z`

## Decision

D051 is **UNCONFIRMED and closed**. The July-August 2026 reserved holdout remains unopened under the preregistered rule `LOCKED_UNLESS_CONFIRM_PASS`; it is not used to rescue D051.

The D047 2024-2025 index-cluster discovery remains discovery evidence only. D051 demonstrates that the apparent NR7 index-cluster edge did not survive the preregistered 2026-H1 confirmation.

## Management-research boundary

This closeout does not establish that every alternative management rule would fail. It does establish that any management rule designed after inspecting D051 cannot be used to retroactively convert D051 into a confirmed strategy. Any further management work must be a separate hypothesis with its own frozen rules and validation sample.
