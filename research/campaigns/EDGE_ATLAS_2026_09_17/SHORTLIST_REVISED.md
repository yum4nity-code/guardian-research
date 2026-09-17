# Edge Atlas — revised shortlist after local admission

Status: `READY_FOR_READ_ONLY_CHEAP_FAIL`; no result examined and no cheap-fail launched.

| ID | Hypothèse cataloguée | Source admise | Classe | Discovery | Confirmation |
|---|---|---|---|---|---|
| EA01 | XAU M5 réversion courte | Dukascopy BID M1 → M5 causal | CLOSE_REPLICATION | 2017–22 | 2023–24 |
| EA02 | XAU M15 réversion conditionnée par vol | Dukascopy BID M1 → M15 causal | ADAPTATION | 2017–22 | 2023–24 |
| EA03 | XAU M5 rejet de choc | Dukascopy BID M1 → M5 causal | CLOSE_REPLICATION | 2017–22 | 2023–24 |
| EA04 | XAU H1 transition de vol | Dukascopy BID M1 → H1 causal | EXACT_REPLICATION | 2017–22 | 2023–24 |
| EA08 | État de volatilité relative ETH/BTC | Binance spot M5 BTC+ETH | ADAPTATION | 2024 | 2025 |
| EA09 | État de liquidité weekend crypto | Binance spot BTC M5 | ADAPTATION | 2024 | 2025 |
| EA11 | XAU M15 rejet corps/mèche | Dukascopy BID M1 → M15 causal | CLOSE_REPLICATION | 2017–22 | 2023–24 |
| EA12 | XAU H1 clustering de vol | Dukascopy BID M1 → H1 causal | EXACT_REPLICATION | 2017–22 | 2023–24 |
| EA16 | Choc de volatilité commun BTC/ETH et réponse relative | Binance spot M5 BTC+ETH | ADAPTATION | 2024 | 2025 |
| EA20 | Volatilité weekend ETH | Binance spot ETH M5 | ADAPTATION | 2024 | 2025 |

EA06, EA07 and EA15 are removed because they require Bybit open interest, and every located OI source explicitly covers 2026. They are not replaced by tuned variants. EA09, EA16 and EA20 were already preregistered in `STRATEGY_CATALOG.md`; only their admitted venue mapping is fixed here to Binance spot M5. They use no OI or derivative field.

The revised set retains several mechanisms independent of the closed breakout, ORB, session-momentum, TSMOM and RSI families: short-horizon signed autocorrelation/reversion (EA01), shock-tail rejection (EA03/EA11), volatility-state transition/clustering (EA04/EA12), cross-asset relative volatility/residual response (EA08/EA16), and weekend liquidity/volatility state (EA09/EA20). Related variants remain separate hypotheses and must be counted in multiplicity correction; none is validated.

All original frozen entry/exit, chronology, rejection and two-variant limits from `STRATEGY_CATALOG.md` remain unchanged except that EA09/EA20 price inputs are Binance spot rather than unavailable Bybit price files. XAU derives M5/M15/H1 causally from admitted Dukascopy M1 payloads. Crypto reads exactly 2024–2025 from the admitted Binance files. Any unlisted source, timestamp at or after 2026-01-01, FundedNext XAU, OI/derivative column or derived R30 CSV must fail closed.

No Edge Atlas item was added to `CURRENT_QUEUE.json`.
