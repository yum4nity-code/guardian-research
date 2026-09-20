# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-20**

## Current decision
The V32–V37 volatility-regime × price-shock lineage is **CLOSED BEFORE LOCKED OOS**.

Pipeline:
- V32 discovery 2010–2013: 192 cells, 56 screen survivors, 16 frozen.
- V33 replication 2014–2017: 9/16 passed.
- V34 pre-validation robustness: 1/9 passed.
- V35 immutable freeze: XAGUSD / normal regime / M15 shock reversal / H240. Manifest SHA256 `9438361bd3e8112619c1f0214d621ce57b4db04929e23a6423b69408cbe60369`.
- V36 independent validation 2018–2022: PASS, gross +3.375 bp/trade; 4/5 years positive; +0.327 bp after best-1% trim; +0.369 bp non-overlap.
- V37 final forensic 2010–2022: **FAIL**. Baseline +4.539 bp; best-1% trim +0.911; best-2% trim **-1.339**. Day bootstrap 95% CI [2.069, 6.867], daily sign-flip p≈0.00020, but the predeclared 2% tail gate failed.
- Locked OOS 2023–2025: **UNOPENED**.
- 2026: **UNOPENED**.

Do not loosen the 2% trim gate, retune the regime/shock definition, or spend locked OOS to rescue this lineage.

## Next primary research
Move to a genuinely new information source: **families 7–8, implied volatility state / volatility term structure** using Cboe/CFE plus spot data. This is preferred over another nearby price transform because it adds external information.

Then: rates/real yields/breakevens → CFTC → macro/FOMC → Treasury auctions.

## Temporal discipline
Discovery 2010–2013; replication 2014–2017; validation 2018–2022; locked OOS 2023–2025; protected 2026. Freeze definitions before each new temporal period.

## Hard operating rules
- Causal availability timestamps only.
- Progress x/y, %, elapsed, ETA for nontrivial jobs.
- Inspect current code/provenance before modifying runners.
- Preserve failed lineages; no post-hoc rescue.
- Costs/non-overlap/tail dependence before promotion.
- No automatic locked-OOS opening and no live deployment without explicit approval.
- CFTC publication lag; ALFRED vintage correctness; EIA blocked until AVAILABLE_AT exists.

## Canonical navigation
`GUARDIAN_MASTER_MANDATE.md` → `EDGE_FAMILY_MAP.md` → this handoff → `START_HERE_NEXT_AI.md` → `docs/RESEARCH_PROTOCOL.md`.

Historical D0xx/Rxx/GEF artifacts remain provenance, not current instructions.
