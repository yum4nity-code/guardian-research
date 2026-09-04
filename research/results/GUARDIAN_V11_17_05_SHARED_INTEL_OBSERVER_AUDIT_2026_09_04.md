# Guardian v11.17.05 — Shared Intelligence Observer Candidate Audit

Status: **STATIC AUDIT PASS / METAEDITOR COMPILE PENDING**

## Provenance

- Base live-working source: `Guardian_D017_PropFirmAuto_v11_17_04_MANUAL_PROTECTION_HOTFIX_PLAN80_RUNNER20.mq5`
- Base SHA256: `74834d0e6ee16ea61047e64d9f496ad8929203cdffbd6684d2691ab3925ab757`
- Candidate: `Guardian_D017_PropFirmAuto_v11_17_05_SHARED_INTEL_OBSERVER_CANDIDATE.mq5`
- Candidate SHA256: `2d790a633a615cdf8b40e3b2c90142685958e0031e75854821c470e118fdad9a`

## Intended change only

v11.17.05 adds a **read-only FILE_COMMON consumer** for the already validated Shared Intelligence bridge.

It parses exactly the 33 bridge columns for BTCUSD and ETHUSD: generation/computed timestamp/freshness, status/core age, spot/perpetual price, open interest, funding, basis, 1m/5m returns, perp-minus-spot dislocation, OI change, long/short/net liquidation notional, and explicit coverage flags.

Null CSV cells remain **unavailable**, not zero. Numeric zero remains a real zero.

## Safety invariants

1. **No trading decision consumes Shared Intelligence in this candidate.**
2. The observer block contains no `CTrade` call, `OrderSend`, `PositionOpen`, `PositionModify`, `PositionClose`, `Buy` or `Sell`.
3. File/read failure is fail-open for trading: observer state becomes `NO DATA`; no existing entry/risk/protection/compliance flag is changed.
4. Stale data (>15 s default) becomes `OBSERVE/STALE`; it does not veto or permit any trade.
5. Live `FILE_COMMON` is explicitly disabled in Strategy Tester so live external data cannot contaminate historical tests.
6. Existing Momentum and RSI defaults remain unchanged (`true`).
7. Base prop-firm, risk, manual protection, RSI and Momentum parameter validation is unchanged.
8. Reads are throttled to 1 s by default and use `FILE_SHARE_READ|FILE_SHARE_WRITE`.

## Audit

- Brace balance: PASS.
- Parenthesis balance: PASS.
- Bracket balance: PASS.
- Forbidden trading calls inside Shared Intelligence observer block: 0.
- Diff inspection: only observer structs/inputs/globals/functions, startup/HUD labels, and read-only refresh hooks.
- No change to trade sizing, SL, TP, drawdown, prop-firm routing, Momentum or RSI decision functions.

## Counter-audit / failure-mode review

Checked specifically for:

- stale state silently treated as fresh: blocked by age + BTC/ETH OK requirement;
- empty liquidation/return cell silently parsed as zero: prevented by explicit availability flags;
- BTC/ETH rows from different generations: rejected;
- BTC/ETH rows from different computed timestamps: rejected;
- unexpected schema: rejected;
- unexpected symbols: rejected;
- partial CSV publication: rejected;
- loss of bridge/runtime: telemetry degrades only; trading logic remains unchanged;
- accidental live-data use in backtest: disabled;
- journal flood: periodic 60 s + state transitions only.

Residual operational effect: each Guardian instance performs a short local FILE_COMMON read at most once per second. The already validated bridge retry/serialization logic handles transient Windows file-sharing contention.

## Cold-read conclusion

The candidate is suitable for the next gate: **MetaEditor compile + observer-only live validation**.

It is **not production-approved** and Shared Intelligence must not be allowed to affect RSI, Momentum, LER, sizing or risk until separate preregistered event studies and OOS validation are complete.

## Next gates

1. User MetaEditor compile: `0 errors, 0 warnings`.
2. FTMO demo observer smoke with Shared Intelligence runtime active.
3. Verify advancing generation IDs and plausible OI/funding/basis/returns/liquidations/coverage.
4. Stop runtime intentionally: candidate must show stale/no-data while trading logic remains unchanged.
5. Restart runtime: candidate must recover automatically.
6. Only after those gates: preregister enriched RSI / Momentum / LER research.
