# Research Status

Document vivant maintenu par Codex.

## Active

- `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE` — `WAITING_CHATGPT`. Le preset SAFE fige `InpEnableStrategyTimeStop=false`, mais une fermeture live a ete observee par time-stop. Aucun changement silencieux de production n'est autorise.
- `D017-V11-16-PROVENANCE-AUDIT` — `CANDIDATE`. Parite du coeur Momentum confirmee; la non-regression empirique n'etait pas comparable car les flux differaient.
- `D017-V11-16-EXACT-FEED-CONTROL` — `READY`. Controle unique sur EURUSD_BT/GBPUSD_BT, parametres D017 geles, sans OOS.
- `AUTONOMY-RECOVERY-001` — `RUNNING_MIMO`. Orchestrateur PID 9188; worker `MIMO-DEEP-WALKFORWARD-COUNTEREVIDENCE` repris sans doublon. Le controle `_BT` long n'a pas ete lance.

## Candidates

- Guardian v11.16 Momentum PROD — candidat nouveau, non equivalent a une non-regression exacte D017 tant que la provenance n'est pas reconciliee.
- `D021-MICRO-REV-M1-V0` — hypothese crypto independante preregistree pour event study cheap-fail sur `BTCUSD_BT` et `ETHUSD_BT`. Aucun EA ni backtest long autorise; execution seulement apres audit fail-closed des donnees/couts et recolte du job MiMo actif.

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
