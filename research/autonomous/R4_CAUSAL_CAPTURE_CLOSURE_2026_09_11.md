# R4 causal-capture closure — 2026-09-11

Status: **CLOSED — SCIENTIFIC/ECONOMIC FAILURE**

Evidence source: `phenomenon-discovery/r4-causal-capture-forensic-audit/LATEST.json` on `backtest-results`, generated 2026-09-11T14:13:39Z from main commit `a920c03b32c6a685e7d045dea9f377637fcecc6f`.

The immutable 500-candidate R4 close-to-close conditional-edge family is closed. The forensic audit passed its mapping/integrity checks and showed that the apparent close-to-close edge is overwhelmingly lost when translated to the earliest causal entry reference after the source bar closes.

Aggregate forensic evidence:

- 2024: close-to-close B positive 500/500, causal open-to-open C positive 252/500, E1 net positive 0/500.
- 2025: close-to-close B positive 500/500, causal open-to-open C positive 194/500, E1 net positive 4/500.
- Aggregate entry delta removes essentially the entire close-to-close gain in both years; fixed E1 costs then make the family deeply negative.
- M5 raw -> M1 raw, M5 clean -> M1 raw, and clean-subset mapping all PASS.
- The audit explicitly authorized no downstream R4 research phase.

Scientific decision:

1. Do not retune, resize, filter, rescue, or open protected 2026 for any R4 survivor.
2. Do not reactivate the existing two-state interaction jobs in their current form because they use the same close-based forward-return representation that the forensic audit invalidated as an execution proxy.
3. A genuinely new search may proceed only with causal signal availability encoded before discovery. The next family uses features known after bar t closes, entry at the next available bar open, exit at a future bar open, calendar-boundary purging, 2024-only threshold fitting, untouched 2025 confirmation, HAC/BH-FDR control and no 2026 access.

This closure is not evidence that the underlying markets have no exploitable edge; it closes this specific non-causal return representation and its selected R4 candidates.
