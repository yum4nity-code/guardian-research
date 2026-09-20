# GUARDIAN — EDGE FAMILY MAP

Status: **UNTOUCHED / EXPLORING / EXHAUSTED / PROMISING**  
Rule: a family is not PROMISING because discovery is attractive; it must survive independent replication and robustness. Locked OOS 2023–2025 and protected 2026 remain unopened unless the mandate gate is explicitly passed.

| # | Family | Mechanism / examples | Data available | Status | Guardian evidence / next action |
|---|---|---|---|---|---|
| 1 | Price momentum / continuation | Breakout, impulse, past return -> future return | HistData | EXHAUSTED | Broad simple-price searches incl. Mega Atlas I / V14 lineage produced no robust deployable alpha. Do not recycle simple variants without a new mechanism. |
| 2 | Price mean reversion | Extreme return, z-score, reversal after shock | HistData | EXHAUSTED | GBP lineage invalidated by M5 lookahead; XAG statistical phenomenon failed tail robustness; V29–V31 XAG-only: 7 replicated, 0 robust. |
| 3 | Volatility regime × price shock | Continuation/reversal conditional on compressed/normal/expanded realized vol | HistData | EXPLORING | V32 discovery: 192 cells, 56 screen survivors, 16 frozen. Next: exact 2014–2017 replication of all 16. |
| 4 | Intraday / calendar structure | Open/close, overlap, hour, weekday, month-end | HistData | UNTOUCHED | Session/hour diagnostics exist, but no clean family-level campaign. |
| 5 | Cross-asset lead/lag | Driver market predicts target | HistData multi-market | EXHAUSTED | V20–V28. XAU/XAG passed validation but temporal/attribution forensics showed little incremental XAU information. Closed before locked OOS. |
| 6 | Relative value / spreads | Ratios, spreads, cointegration/stat-arb, relative dislocations | HistData multi-market | UNTOUCHED | Simple return divergence touched in V20–V28; genuine spread/stat-arb family not tested. |
| 7 | Implied volatility -> spot | VIX/VIX9D/VVIX/GVZ/OVX states predict returns/realized vol | Cboe + HistData | UNTOUCHED | High-priority external-information family. |
| 8 | Volatility term structure | VIX9D/VIX, futures curve, contango/backwardation | Cboe/CFE + HistData | UNTOUCHED | High-priority. |
| 9 | Volume / open interest | Volume/OI changes, price×OI states | CFE + HistData | UNTOUCHED | CFE archive available <=2022. |
| 10 | CFTC positioning | Crowding, extremes, weekly changes | CFTC + HistData | UNTOUCHED | Must enforce publication lag. |
| 11 | Nominal rates | Yield level/change/curve -> FX/equity/gold | Treasury/FRED + HistData | UNTOUCHED | High-priority causal macro family. |
| 12 | Real yields / breakevens | Real rates/inflation compensation -> gold/risk assets | Treasury/FRED/ALFRED + HistData | UNTOUCHED | High-priority, especially XAU. |
| 13 | Financial conditions / stress | Tightening/easing regimes -> asset behavior | FRED/ALFRED + HistData | UNTOUCHED | Vintage correctness where revisions matter. |
| 14 | Macro releases / surprises | CPI/jobs/GDP etc. information shock | ALFRED + release schedules + HistData | UNTOUCHED | Requires exact causal availability/release timestamp. |
| 15 | FOMC events | Decision-day/pre/post-announcement behavior | Fed/FOMC + HistData | UNTOUCHED | 1,868 Fed/FOMC documents available. |
| 16 | Fed communication | Minutes/speeches/text/event state | Fed corpus + HistData | UNTOUCHED | Separate event timing from later document revisions. |
| 17 | Treasury auctions | Auction outcomes/tenor/demand -> rates/USD/gold | Treasury auctions + HistData | UNTOUCHED | 9,496 rows available. |
| 18 | Energy fundamentals | EIA inventories -> WTI/Brent | EIA + HistData | UNTOUCHED | Do not test until AVAILABLE_AT is causally built. |
| 19 | Macro × market interactions | e.g. real yields + USD state -> gold | Macro + HistData | UNTOUCHED | Test only after component families to control multiplicity. |
| 20 | Macro regime × technical signal | Price signal conditional on macro state | Macro + HistData | UNTOUCHED | Later-stage interaction family. |
| 21 | Correlation / dispersion regimes | Correlation breakdown, rolling dispersion | HistData multi-market | UNTOUCHED | Distinct from direct lead/lag. |
| 22 | Cross-sectional relative strength | Relative abnormal strength/weakness across basket | HistData multi-market | UNTOUCHED | Needs predeclared universe and ranking. |
| 23 | Liquidity / microstructure proxies | Quote gaps, activity, stale prints, market speed | Raw HistData M1 | UNTOUCHED | Proxy-only; no true order book. |
| 24 | Event × initial price reaction | Scheduled event plus first reaction predicts follow-through/reversal | Event data + HistData | UNTOUCHED | Strong causal design candidate. |
| 25 | Positioning × event | Crowding changes reaction to macro/Fed events | CFTC + events + HistData | UNTOUCHED | Later interaction; avoid before base effects tested. |
| 26 | Implied vol × macro × price | Fear/vol state changes event response | Cboe + macro + HistData | UNTOUCHED | Later interaction. |
| 27 | FX carry / rate differentials | Yield differential/carry and unwind | Rates + FX HistData | UNTOUCHED | High-priority for FX. |
| 28 | Economically directed intermarket | Real yields->gold, oil->CAD, USD->commodities | Macro + HistData | UNTOUCHED | Unlike V20 broad price-only cross-market search: driver chosen by economic mechanism. |

## Closed lineages / contamination ledger
- GBP60 local P90 V3–V10: **DEAD** — confirmed left-labeled M5 timestamp lookahead. V11 causal rebuild negative.
- XAG zret_12b H240 P97.5: **DEAD as exploitable alpha** — V19 remove-best-1% flips mean negative. Locked OOS not opened.
- XAU/XAG cross-market V20–V28: **CLOSED before OOS** — apparent effect persisted but V28 found divergence added only ~0.28 bp over same-event XAG mean reversion; do not retrofit V28 quadrants into an independent claim.
- XAG-only V29–V31: **CLOSED before validation** — 12 frozen, 7 replicated, 0/7 passed robustness.
- V32 regime/shock: **ACTIVE** — discovery only; 16 frozen candidates awaiting exact replication.

## Research queue
1. Finish V32 lineage without changing its frozen definitions.
2. Implied-volatility state / term structure (families 7–8).
3. Rates / real yields / breakevens (11–12).
4. CFTC positioning (10).
5. FOMC / macro-event families (14–16).
6. Treasury auctions (17).
7. Energy fundamentals only after EIA causal AVAILABLE_AT is solved (18).
8. Interactions (19,20,24–26) only after constituent families have standalone evidence.

## Global gates
Discovery -> independent replication -> pre-validation robustness -> immutable freeze -> independent validation -> pre-OOS forensic -> **human review** -> locked OOS 2023–2025.  
No retuning on replication/validation. No automatic OOS opening. 2026 protected. Exact causal availability timestamps are mandatory. Costs and non-overlap sensitivity are mandatory before promotion.
