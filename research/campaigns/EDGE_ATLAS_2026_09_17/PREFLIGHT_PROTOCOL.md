# Edge Atlas data preflight protocol v1

This gate validates data admission only. It must not compute a strategy signal, PnL, parameter score or historical result.

The sole authority is `ADMITTED_DATA_MANIFEST.json`. Every source path and SHA-256 must match. Paths or rows containing 2026, R30-derived XAU CSVs, FundedNext XAU, OI, funding, perpetual or derivative fields fail closed as `BLOCKED_DATA`.

Dukascopy input is the immutable two-root XAUUSD BID M1 `.bi5` union. The index and every payload used must be hash-verified. Records are decoded one day at a time, must be ordered on an exact UTC M1 grid and become available only at the end of their minute. Higher timeframes are formed only from complete prior M1 buckets; an M5 bar stamped at its opening minute becomes available five minutes later.

Binance input is spot OHLCV only. The loader streams the entire file so a later protected row cannot be hidden, but yields only the exact 2024–2025 window. The admitted slice must be UTC, monotone, unique and on an exact five-minute grid. No complete history is retained in memory.

Partition gates are fixed before execution: XAU discovery 2017–2022, confirmation 2023–2024, pre-OOS 2025; crypto spot discovery 2024 and confirmation 2025. Any timestamp outside those partitions fails. Nominal and stress costs are separate immutable objects; stress cannot silently reuse or undercut nominal assumptions.

The preflight output reports files inspected/admitted/rejected, rejection causes, coverage, granularity, timezone, hashes, 2026 presence, causal availability and one of `PREFLIGHT_PASS_NO_RUN`, `BLOCKED_DATA`, `PREFLIGHT_FAIL` or `INFRASTRUCTURE_ERROR`.

For this implementation step only `py_compile` and synthetic tests may run. The real admitted histories must not be opened. A PASS authorizes only a later, separately requested read-only cheap-fail after cold review; it is not a strategy or data-result PASS.
