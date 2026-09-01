# D022 PAIR-REV M15 — engine v2 OOS/exit-semantics fix

STATUT: SUPERSEDE d022_pair_rev_eventstudy.py

ChatGPT re-audited the prepared D022 engine before real-data execution and found two implementation issues in the first script:

1. The first engine used `PREOOS_END = 2026-06-28 23:59:59`, which could include the first locked OOS day. D022 V0 must use data strictly before `2026-06-28 00:00:00`.
2. When one M15 close simultaneously crossed the zero target and exceeded the opposite `|z| >= 3.5` level, the code checked the statistical stop before the zero-return condition. The preregistration defines the stop only if it occurs before return to zero, so target crossing must have precedence.

Corrected file prepared by ChatGPT:

`d022_pair_rev_eventstudy_v2.py`

SHA256: `29f17859acfd7c78ba8eac5e677a6763eea0aab7233474625e4bdd5578b3ed45`

Corrections:
- `OOS_START = 2026-06-28 00:00:00`;
- `PREOOS_END = OOS_START - 1 second`;
- fail-closed if ANY input timestamp is `>= OOS_START` instead of silently trimming OOS rows;
- zero-return target crossing checked before statistical stop on each observation;
- syntax check passed.

ACTION_CODEX:
- DO NOT execute the old `d022_pair_rev_eventstudy.py`.
- Use only `D:\MT5_Backtests\automation\d022_pair_rev_eventstudy_v2.py` once the user copies the refreshed bundle.
- Produce physically PRE-OOS-only AUDUSD/NZDUSD/EURUSD/GBPUSD M15 inputs ending before 2026-06-28.
- Run once, no tuning, no OOS.
