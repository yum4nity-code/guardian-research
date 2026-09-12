# R6 protected-2026 OOS r4 invalidation — 2026-09-12

Status: **INVALID TECHNICAL RUN — NOT A SCIENTIFIC FAIL**

The published r4 artifact reported `0/12` passing candidates, but no candidate outcome was actually evaluated. All 12 frozen candidates produced 2026 signals, while the inherited R5 economic replay rejected every 2026 signal before entry because that replay is intentionally hard-coded for pre-OOS 2024/2025 use.

Exact inherited guards responsible:

- `signal_year not in (2024, 2025)` -> reject
- modeled trade exit must satisfy `exit_ns < PROTECTED`, where `PROTECTED = 2026-01-01T00:00:00Z`

Observed r4 consequence:

- protected 2026 input was opened under explicit human authorization;
- candidate definitions and pass/fail gates were unchanged;
- signal counts were computed for the frozen candidates;
- `executable_trades = 0` for every candidate;
- PnL, PF, drawdown, bootstrap outcome evidence and post-cost robustness were therefore not evaluated;
- the `FAIL: 0/12` scientific label is invalid and must not be used to close R6.

This defect is an execution-semantic/infrastructure bug, not market evidence.

Permitted repair:

1. Preserve all 12 frozen R6 candidate definitions exactly.
2. Preserve preregistration-v2 OOS window and every statistical/economic gate exactly.
3. Replace only the inherited pre-OOS replay guard with a dedicated authorized 2026 Jan-Aug replay that:
   - accepts signals only inside the frozen 2026-01-01 -> 2026-09-01 window;
   - enters at the first raw-M1 open at/after the source M5 bar becomes available;
   - exits at the first raw-M1 open at/after the frozen horizon boundary;
   - enforces one chronological position per candidate;
   - rejects only true frozen-window boundary/reference failures;
   - never reads outside the frozen Jan-Aug 2026 window.
4. Cold-audit the repair with synthetic data only before a new scientific run.
5. No retuning, parameter rescue, candidate replacement, gate change or live deployment.

Because r4 exposed signal counts but no returns/outcomes, the repair must remain strictly mechanical and must not use those counts to modify any scientific choice.
