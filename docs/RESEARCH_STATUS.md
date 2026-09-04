# Research Status

Document vivant maintenu par Codex.

## Active

- `D017-V11-16-MIN-RISK-SCALING-DIVERGENCE` — `VALIDATED / RESOLVED`. La candidate v11.16.1 RISKFIX correspond au hash ChatGPT, compile sans erreur ni avertissement et son auto-test runtime confirme 25 USD sur 10k / 250 USD sur 100k.
- `D017-V11-16-GENERALIZATION-PREOOS` — `RUNNING_MT5 / IMPORT`. Manifeste et criteres geles avant resultat; trois workers isoles importent AUDUSD, EURJPY, NZDUSD, USDCAD, USDCHF et XAUUSD en excluant tout timestamp a partir du 2026-06-28. Aucun tuning et OOS ferme.
- `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE` — `REJECTED / SUPERSEDED`. La ligne v11.15 est close et remplacee par v11.16; elle ne doit plus etre patchee, testee ni redeployee.
- `D017-V11-16-PROVENANCE-AUDIT` — `CANDIDATE`. Parite du coeur Momentum confirmee; la non-regression empirique n'etait pas comparable car les flux differaient.
- `D017-V11-16-EXACT-FEED-CONTROL` — `READY`. Controle unique sur EURUSD_BT/GBPUSD_BT, parametres D017 geles, sans OOS.
- `AUTONOMY-RECOVERY-001` — `RUNNING_MIMO`. Orchestrateur PID 9188; worker `MIMO-DEEP-WALKFORWARD-COUNTEREVIDENCE` repris sans doublon. Le controle `_BT` long n'a pas ete lance.
- `GUARDIAN-V11-16-11-LIVE-RSI-MOMENTUM` — `LIVE_VALIDATION / RESEARCH`. Baseline utilisateur actuelle: v11.16.11 avec switches `InpEnableMomentum` / `InpEnableRSISniper`, RSI Sniper integre, notifications lifecycle, under-risk max-volume >=50 USD et diagnostics BUY1/BUY2 explicites. Voir `docs/GUARDIAN_V11_16_5_TO_11_16_11_CHANGELOG.md` et `docs/RSI_SNIPER_IMPLEMENTED_ADDENDUM_2026_09_02.md`.
- `BTC-ENGINE-ISOLATION-2026-09-02` — `RUNNING_MANUAL_MT5`. Meme fenetre/ticks/depot que le baseline combo. Combo reproduit exactement +17499.93 USD / PF 1.35 / equity DD 3.76% / 628 trades. RSI-only: +9451.57 USD / PF 1.19 / equity DD 4.20% / 621 trades. Momentum-only baseline (`InpCryptoPostShockBars=2`) en cours.
- `GUARDIAN-EXTERNAL-INTELLIGENCE-BUS-V1` — `WAITING_CODEX / RESEARCH INFRA`. Nouvelle priorite utilisateur du 2026-09-04. Construire d'abord un collecteur/recorder externe lecture seule pour BTC/ETH (spot, perp, OI, liquidations, funding si disponible), avec timestamps UTC, provenance, staleness, reconnexion/deduplication et replay sans lookahead. Aucun ordre live et aucune mutation silencieuse de `production/guardian/`.

## Candidates

- Guardian v11.16 Momentum PROD — candidat nouveau, non equivalent a une non-regression exacte D017 tant que la provenance n'est pas reconciliee.
- `D021-MICRO-REV-M1-V0` — hypothese crypto independante preregistree pour event study cheap-fail sur `BTCUSD_BT` et `ETHUSD_BT`. Aucun EA ni backtest long autorise; execution seulement apres audit fail-closed des donnees/couts et recolte du job MiMo actif.
- RSI Sniper integrated sleeve — candidate active, profitable on BTC isolated over current two-month research window, not yet validated cross-market. BUY2/SL architecture and exit distribution remain open research questions.
- `D025-LIQUIDITY-EXHAUSTION-RECLAIM` — `PREREGISTERED / BLOCKED BEFORE OBSERVER`. Strategie mid-term distincte de RSI/Momentum : niveau objectif -> sweep/cascade -> exhaustion/impact marginal decroissant -> reclaim -> acceptance/retest. V0 doit rester observation/trade virtuel; sorties non fixees avant MFE/MAE. Crypto+ pourra utiliser le bus externe, mais LER Core doit rester autonome MT5.

## Validated

- Aucun nouveau candidat valide pendant ce bootstrap.

## Rejected / quarantined

- Guardian v11.15: ligne production legacy, resolue et supersedee par v11.16 self-contained. Aucun patch, test supplementaire ou redeploiement.
- USDJPY v11.16 manuel: quarantaine, car le test jusqu'au 2026-08-30 traverse l'OOS verrouille.
- SOLUSD v11.16 manuel: incomplet, donc inexploitable.
- MiMo deep walk-forward METHOD/COSTS/DATA: echecs techniques par timeout; contre-audit partiel/interrompu.

## Etat du laboratoire au 2026-08-31 20:22Z

- Depot synchronise: `ee5ad9914156cb66462ee321d40632a38d3714bf`.
- Terminaux ouverts: FTMO normal et FundedNext; aucun `metatester64` actif.
- PropFirmGuard est actif. MiMo a ete relance apres reconciliation et recupere sa file persistante.
- Aucun backtest MT5 n'a ete relance durant le bootstrap ou la reprise MiMo.
- Exigence v11.17+: les invariants strategiques critiques doivent etre compiles et controles fail-closed; aucune dependance a un `.set` pour preserver la semantique validee.

## Etat ChatGPT / live au 2026-09-02

- Ligne live utilisateur: Guardian v11.16.11 `STRATEGY_SWITCHES`.
- FundedNext: l'utilisateur a confirme par appel que l'EA est autorisee sur le profil utilise; ne pas deduire une interdiction FundedNext d'un message `AutoTrading disabled by server` sans verifier d'abord l'etat Algo Trading local/compte. Un cas observe provenait simplement de l'algo desactive par l'utilisateur.
- Telegram: doit rester absent du code Guardian actuel.
- Notifications MT5/mobile validees en live avec semantique WHITE/entry, GREEN/TP1, BLUE/protected/TP2, RED/dry loss before TP, pour RSI/Momentum/manual.
- Under-risk max-volume valide en live: LNK ~32 USD bloque sous le seuil 50 USD; SOL ~192 USD autorise au max broker 5 lots.
- BUY1 silent-block diagnostic corrige en v11.16.10: toute sortie false apres signal confirme doit exposer une raison.
- BUY2: ne pas modifier pour l'instant. Mesurer le conflit potentiel entre structural SL BUY1 et second oversold episode, ainsi que l'effet du filtre de divergence.
- Cout d'entree RSI a SL tres court: a mesurer comme spread + commission en % du risque; cas USDCAD 12.45 lots / SL ~2.2 pips avec drawdown immediat important.
- Backtests: travailler principalement avec rapports synthetiques standardises; n'exiger des logs complets qu'en diagnostic cible. Ajouter plus tard un resume de Strategy Tester en fin de run.
- Optimisation performance a faire sans changer les resultats: si Momentum OFF, court-circuiter les calculs strictement Momentum; si RSI OFF, court-circuiter les calculs strictement RSI.

## Etat ChatGPT / architecture au 2026-09-04

- D025 LER preregistre dans `research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`.
- Premier gate volontairement limite a `GUARDIAN-EXTERNAL-INTELLIGENCE-BUS-V1`: collecte/record/replay, pas de signal live.
- Donnees externes visees: spot, perpetual, OI, liquidations et funding avec timestamps/provenance/age. Elles sont des observations, jamais des appels directs de trading.
- Invariant backtest: aucune observation dont le timestamp est posterieur au temps simule.
- Si flux externe indisponible/stale, Guardian Core et protections continuent; les features Crypto+ dependantes deviennent indisponibles plutot que d'utiliser une donnee ancienne silencieusement.
