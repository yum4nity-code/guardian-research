# GEF V104.1 taxonomy patch — 2026-09-22

V104.0 stopped before discovery because it searched for a literal V85 family named `cftc`.

The frozen V84C/V85 taxonomy intentionally assigns CFTC features to market-specific families:
`cftc_XAUUSD`, `cftc_EURUSD`, `cftc_GBPUSD`, etc.

V104.1 changes only the eligible-family selector from equality with `cftc` to `family.startswith("cftc_")`.

No market data after 2013 was accessed by the failed V104.0 run. No scientific result was produced.
No threshold, temporal split, multiplicity rule, target, direction rule or robustness gate changed.