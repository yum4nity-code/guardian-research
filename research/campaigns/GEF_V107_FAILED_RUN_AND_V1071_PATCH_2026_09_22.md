# GEF V107.0 failed-run note — 2026-09-22

Observed failure:
`RuntimeError: No finite ALFRED discovery tests`.

Facts:
- 13 revision-summary files were eligible under the strict first_vintage + first_value rule;
- 52 causal transformed features were constructed;
- no finite ALFRED discovery test survived the original support requirement;
- no discovery p-value table or candidate freeze was produced;
- no scientific alpha result exists for V107.0.

Design issue:
- MIN_DISC=18 extreme-state release events over 2010-2012 plus a separate 2013 holdout was inappropriate for sparse monthly/quarterly macro releases.

Additional infrastructure issue:
- V107.0 loaded market price histories through 2022 before discovery even though later windows were not scored.
- This violated the intended physical temporal firewall.

V107.1 repairs both issues before any finite alpha test:
- discovery 2010-2013;
- fixed sparse-event support gates;
- stage-specific price loading: <=2013, then <=2017, then <=2022;
- one release event remains one statistical observation;
- 2023-2025 and 2026 remain forbidden.
