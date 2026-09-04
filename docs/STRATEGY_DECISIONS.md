# Strategy Decisions

Journal append-only des decisions de recherche importantes.

Chaque entree doit inclure : date, Strategy ID, Campaign ID, verdict, preuves principales, limites, commit/source exacts, et raison de la decision.

## 2026-08-31 — Guardian v11.15 SAFE runtime divergence

- Strategy ID: `D017-GUARDIAN-V11-15`
- Campaign ID: `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE`
- Verdict: `BLOCKED / WAITING_CHATGPT`
- Preuves: le preset gele fixe `InpEnableStrategyTimeStop=false`; l'execution observee a ferme une position par `STRATEGY_TIME_STOP`; des profils sauvegardes referencaient encore v11.14.
- Limites: le terminal FTMO est ouvert mais aucun testeur n'est actif; les inputs live ne sont pas modifies par Codex.
- Source: commit `ee5ad9914156cb66462ee321d40632a38d3714bf`; source v11.15 LF SHA256 `bbcfae9426838eef655d5ac11eaf1530d872d117eb840f6c15ceb0c69843fe86`; preset LF SHA256 `82d6d1ada0e6785382e5a0e9555480e85f2d16bd4106dfd9210dffee502486b3`.
- Raison: la configuration executee n'est pas equivalente au protocole SAFE; une integration de production exige audit ChatGPT et validation utilisateur.

## 2026-08-31 — Guardian v11.16 and manual cross-asset results

- Strategy ID: `D017-GUARDIAN-V11-16-CANDIDATE`
- Campaign ID: `D017-V11-16-PROVENANCE-AUDIT`
- Verdict: `CANDIDATE, NOT VALIDATED`
- Preuves: EURUSD +8545.98 / 191 trades / PF 1.56 / DD 1.61%; GBPUSD +4482.53 / 188 / PF 1.24 / DD 2.65%; BTCUSD balance finale 113054.25; ETHUSD 91527.60. Les metriques D017 historiques proviennent de v11.10 et different.
- Limites: pas de rapports structures recents pour les cryptos; SOLUSD incomplet; USDJPY traverse l'OOS verrouille et est exclu; aucune conclusion comparative propre n'est possible.
- Source: candidat v11.16 LF SHA256 `6e5be9fdd58d7c6352011dd7afc758089d766f987629f06d7921d8f5f2e2ce69`, commit `ee5ad9914156cb66462ee321d40632a38d3714bf`.
- Raison: les resultats ne demontrent ni parite semantique ni robustesse; aucune optimisation post hoc n'est autorisee.

## 2026-08-31 — D017 / v11.16 provenance verdict

- Strategy ID: `D017-GUARDIAN-V11-16-CANDIDATE`
- Campaign ID: `D017-V11-16-PROVENANCE-AUDIT`
- Verdict: `SEMANTIC_CORE_PARITY_CONFIRMED / EXACT_FEED_CONTROL_REQUIRED`
- Preuves: le moteur Momentum, la session, le volume, le scoring, le ranking et la gestion AUTO sont identiques apres normalisation. D017 utilisait `EURUSD_BT` (17,040,615 ticks; 20,351 bars), alors que le test manuel v11.16 utilisait `EURUSD` FTMO-Demo (13,846,176 ticks; 20,638 bars).
- Limites: les deux resultats ne sont pas une non-regression empirique comparable; v11.16 ajoute des gardes PropFirm/ownership susceptibles de bloquer des entrees.
- Source: `results/audits/D017_V11_16_PROVENANCE_AUDIT.md`; base commit `bed7a2537f636fcd27a4a12bf152c1749dad97dc`.
- Raison: l'ecart 176 -> 191 trades est compatible avec une difference de flux et ne justifie aucune modification de strategie. Un controle unique sur les memes historiques `_BT` est preregistre.

## 2026-08-31 — Cloture de la divergence v11.15

- Strategy ID: `D017-GUARDIAN-V11-15`
- Campaign ID: `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE`
- Verdict: `REJECTED AS LEGACY / SUPERSEDED BY V11.16`
- Preuves: ChatGPT confirme une divergence d'inputs persistes, pas une derive du coeur Momentum. v11.16 compile les moteurs rejetes et le time-stop en invariants, avec CryptoSweep OFF et diagnostics OFF par defaut.
- Limites: cette resolution traite la securite de configuration, pas la robustesse statistique de v11.16.
- Source: `handoff/chatgpt_to_codex/2026/08/31/GUARDIAN_V11_15_RUNTIME_DIVERGENCE_RESOLUTION.md`, commit recu `40f874cf561dafc261c55c3d13723bfcc956cb35`.
- Raison: ne pas patcher/redeployer v11.15. Pour v11.17+, aucun invariant strategique valide ne doit dependre d'un `.set`; les ecarts configurables doivent provoquer un demarrage fail-closed et etre journalises.

## 2026-08-31 — D021 MICRO-REV M1 preregistration

- Strategy ID: `D021-MICRO-REV-M1-V0`
- Campaign ID: `D021-MICRO-REV-M1-CHEAP-FAIL`
- Verdict: `PREREGISTERED / EVENT STUDY ONLY / NOT VALIDATED`
- Preuves: mecanisme distinct de D017 (`shock -> exhaustion -> confirmation -> reversal`); RSI(7) gele par le handoff ChatGPT; historiques locaux valides trouves pour `BTCUSD_BT` et `ETHUSD_BT`, pas pour SOLUSD.
- Limites: prior economique faible et risque eleve de selection adverse/couts; seulement deux actifs disponibles; aucun resultat n'a ete ouvert.
- Source: `handoff/chatgpt_to_codex/2026/08/31/D021_NEW_STRATEGY_HYPOTHESES_MICRO_REV.md`, commit recu `ead110e145a65a540e4f4da0c3370f9ea73d3148`; protocole `research/campaigns/D021_MICRO_REV_M1_PREREGISTRATION.md`.
- Raison: une event study stricte et peu couteuse peut falsifier le mecanisme avant tout EA ou backtest long. Les seuils, endpoints, couts stresses et portes sont geles; tout echec rejette V0 sans retuning.

## 2026-09-02 — Guardian v11.16.11 live baseline sync

- Strategy ID: `D017-GUARDIAN-V11-16-11`
- Campaign ID: `GUARDIAN-V11-16-5-TO-11-16-11-LIVE-INTEGRATION`
- Verdict: `CURRENT LIVE BASELINE / TECHNICALLY STABILIZED / STRATEGIES STILL UNDER RESEARCH`
- Preuves: BTC combo two-month control reproduit exactement apres les patches techniques: +17499.93 USD, PF 1.35, equity DD 3.76%, 628 trades. RSI-only meme fenetre: +9451.57 USD, PF 1.19, equity DD 4.20%, 621 trades. Live: under-risk max-volume valide (LNK ~32 USD bloque <50; SOL ~192 USD autorise), notifications lifecycle couleurs validees, BUY1 block reason rendu explicite.
- Limites: RSI n'est pas valide cross-market; BUY2 vs structural SL reste une question ouverte; Momentum-only isolation et POST_SHOCK A/B encore en cours; le vrai fill peut encore utiliser un fallback Ask quand deal/position ne sont pas immediatement lisibles.
- Source: `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md`; `docs/RSI_SNIPER_IMPLEMENTED_ADDENDUM_2026_09_02.md`; baseline locale SHA256 `d30ff21378331f972bea947a4c6c826b6f4a2547e58878947551199b9d01c495`.
- Raison: geler clairement l'etat reel avant de poursuivre les tests d'isolation; ne pas laisser Codex repartir d'une spec RSI obsolete ou d'une baseline v11.16.4.

## 2026-09-02 — Isolation engines / anti-curve-fitting plan

- Strategy ID: `D017-MOMENTUM` + `RSI_SNIPER`
- Campaign ID: `BTC-ENGINE-ISOLATION-2026-09-02`
- Verdict: `PREREGISTERED SCREENING / RUNNING`
- Preuves: switches strategy introduits en v11.16.11 pour produire RSI-only, Momentum-only et combo sans modifier le code. Baseline combo et RSI-only deja obtenus sur meme environnement.
- Limites: les garde-fous Guardian partages peuvent rendre les resultats non additifs; `combo - RSI` ne mesure donc pas directement la contribution Momentum.
- Source: `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md`.
- Raison: tester seulement quelques variables structurellement justifiees avec valeurs larges. Momentum: POST_SHOCK 2 bars baseline puis 0; 1/4 seulement si effet materiel. RSI: trailing activation, oversold depth, puis BUY2/SL apres mesure. Pas de grille exhaustive ni de recherche de valeur magique.

## 2026-09-04 — D025 Liquidity Exhaustion Reclaim + External Intelligence Bus

- Strategy ID: `D025-LIQUIDITY-EXHAUSTION-RECLAIM`
- Campaign ID: `D025-LER-PREREG / GUARDIAN-EXTERNAL-INTELLIGENCE-BUS-V1`
- Verdict: `PREREGISTERED / BUILD DATA INFRA FIRST / NO LIVE TRADING`
- Preuves: hypothese economique distincte des moteurs existants : niveau objectif preexistant -> sweep/cascade -> pression extreme -> impact marginal decroissant/exhaustion -> reclaim -> acceptance/retest. Les donnees externes envisagees pour crypto sont spot, perpetual, open interest, liquidations et funding, avec provenance et timestamps. Le Guardian live actuel ne possede pas encore cette couche externe.
- Limites: aucun edge n'est encore demontre; aucun seuil, score, poids ni plan de sortie n'est valide. Les donnees externes peuvent etre indisponibles, stale ou incompletes; elles ne doivent jamais devenir une dependance des protections Guardian.
- Source: `research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`; `handoff/chatgpt_to_codex/2026/09/04/D025_LER_EXTERNAL_INTELLIGENCE_BUS_V1.md`; commits initiaux `c6c08363258f04e8079a165d584c8bbcf3cac8f5` et `c09410ffd92a9380f19072978d13c668dd20cf7a`.
- Raison: construire d'abord une infrastructure read-only, horodatee, rejouable et sans lookahead permet de tester scientifiquement si OI/liquidations/spot-perp ajoutent un edge au LER Core. Aucun BUY/SELL LER n'est autorise avant event study, robustesse et red-team.

## 2026-09-04 — EIB V1 implementation gate

- Strategy ID: `D025-LIQUIDITY-EXHAUSTION-RECLAIM`
- Campaign ID: `GUARDIAN-EXTERNAL-INTELLIGENCE-BUS-V1`
- Verdict: `IMPLEMENTED / OFFLINE TESTED / LIVE SMOKE REQUIRED`
- Preuves: `collector_v1.py` collecte via Bybit public BTC/ETH spot, USDT perpetual, open interest, funding et `allLiquidation`; `replay_v1.py` impose le gate `available_at_ms <= simulated_time_ms`. `py_compile` passe; 4/4 tests unitaires offline passent (spot, perp/OI/funding, liquidation side/notional estime, anti-lookahead replay). Collector SHA256 `761329daa74cdb31dd80f136b0f37e1df759956e13e6ea0b3bc3c7bd6c73874e`; replay SHA256 `4a8b1ef7a80bbf2a898b996f5b86b38475ec88695a673591f49f3a158bb2b034`.
- Limites: ChatGPT n'a pas valide 30 minutes de flux reel dans son environnement. V1 est mono-venue Bybit. Le notional liquidation est une estimation `size * bankruptcy_price`, pas un notional execute fourni par l'exchange. Aucun edge LER n'est encore mesure.
- Source: `research/results/D025_EIB_V1_IMPLEMENTATION_REPORT.md`; commits collector `83bd4245b9de1a8c8893b3acf1f7867c07e6132e`, replay `1a27d6269912af1c16f65f2afa5b9027eae2d834`, tests `144d78199f4f701948247f1604adcab77f652f91`.
- Raison: le code est suffisamment structure pour passer au smoke data reel. Codex doit tester la collecte/reconnexion/staleness/dedup/replay sur le PC avant toute integration de signal. Ne pas reecrire V1 ni coder LER live sans preuve concrete.

## 2026-09-04 — D025 Trading 1.01 manual BTC/ETH backtest

- Strategy ID: `D025-LIQUIDITY-EXHAUSTION-RECLAIM`
- Campaign ID: `D025-LER-V0-MANUAL-MT5-TRADE-CONSTRUCTION`
- Verdict: `CURRENT TRADE CONSTRUCTION REJECTED / KEEP EVENT-STUDY ONLY`
- Preuves: manual FundedNext Strategy Tester, M1, 2025-01-01 -> 2026-06-28, initial deposit 10,000 USD, locked V0 signal chain, structural SL, no TP, forced 48h exit, 0.50% risk. BTCUSD finished at 6,695.65 USD (-3,304.35 USD; detailed report not captured). ETHUSD report: net -4,547.95 USD, PF 0.31, expected payoff -26.91, equity DD max 45.85% (4,616.03), 169 trades, 20 winners / 149 losers, win rate 11.83%, gross profit 2,001.43 vs gross loss -6,549.38, average win 100.07 vs average loss -42.81, Sharpe -5.00.
- Limites: BTC detailed PF/DD/win-rate were not captured in the supplied output. The 48h no-TP exit is a deliberately simple research construction, so these runs reject this tradable V0 construction, not every conceivable future exit policy or the existence of useful event-study information around sweeps. No threshold retuning is justified from these results.
- Source: `research/ea/D025_LER_Trading_1_01.mq5`; user manual MT5 reports on 2026-09-04; source commit creating Trading 1.01 `2fb02f7b0be451e7160604ec8f75701e74a56585`.
- Raison: both BTC and ETH lose heavily under the same frozen construction, and ETH's 11.83% hit rate is far below what its average win/loss ratio would require. Do not optimize V0 thresholds post hoc. Continue only as diagnostic/event study (funnel, MFE/MAE, failure reasons, level families) or formulate a genuinely new preregistered hypothesis.
