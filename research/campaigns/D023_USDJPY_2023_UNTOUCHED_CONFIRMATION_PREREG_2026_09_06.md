# D023 USDJPY London ORB — untouched 2023 confirmation preregistration — 2026-09-06

Purpose: confirm or reject the USDJPY-specific D023 clue on a calendar year not opened during the 2024-2026 discovery/control work.

## Frozen sample
- USDJPY only
- M15 / Every tick
- 2023-01-02 through 2023-12-29
- FundedNext server clock conformance identical to v1.04
- FundedNext Stellar 1-Step/2-Step Forex commission = USD 5 per lot per side

## Frozen strategy
No changes from D023 V0:
1. Europe/London-local opening range = 08:00 inclusive to 09:00 exclusive, exactly four M15 bars.
2. First M15 close strictly above/below range between 09:00 inclusive and 11:00 exclusive.
3. Entry next M15 open, executable spread side.
4. Stop opposite OR edge.
5. No take profit.
6. Exit stop or final M15 close finishing at 16:00 London.
7. One trade per day maximum; no reversal.
8. No EMA/RSI/ATR/range/day/news/direction filters.

## Frozen confirmation gates
All must pass for CONFIRM:
- n >= 150 trades;
- mean net R > 0;
- net PF >= 1.10;
- 5-day moving-block bootstrap lower 5% bound of zero-filled weekday daily mean net R > 0;
- total/mean result remains positive with commission multiplied by 1.5.

Failure of any gate => USDJPY D023 remains unconfirmed. No rescue filters or parameter tuning on 2023.

## Manager rule
Do not test Guardian ratchet/trail variants until this untouched entry confirmation has been scored. If entry confirms, manager variants may then be tested as a separate experiment with their own held-out validation.

Prepared executable diagnostic:
`D023_USDJPY_LondonORB_M15_v1_05_FUNDEDNEXT_2023_CONFIRM_20260906.mq5`
SHA256 `4fab801a484d7a7fe7a3c234808336adedd6cd5ff5b9b0a27551d8c19ffa9bf7`

The EA has a hard calendar-year guard and writes a distinct CSV:
`D023_USDJPY_ORB_V105_FUNDEDNEXT_2023_CONFIRMATION.csv`
