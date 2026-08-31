# Research Status

Document vivant maintenu par Codex.

## Active

- `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE` — `WAITING_CHATGPT`. Le preset SAFE fige `InpEnableStrategyTimeStop=false`, mais une fermeture live a ete observee par time-stop. Aucun changement silencieux de production n'est autorise.
- `D017-V11-16-PROVENANCE-AUDIT` — `CANDIDATE`. Parite du coeur Momentum confirmee; la non-regression empirique n'etait pas comparable car les flux differaient.
- `D017-V11-16-EXACT-FEED-CONTROL` — `READY`. Controle unique sur EURUSD_BT/GBPUSD_BT, parametres D017 geles, sans OOS.
- `AUTONOMY-RECOVERY-001` — `READY`. Les statuts MiMo sont obsoletes; aucun processus MiMo/testeur n'est actif.

## Candidates

- Guardian v11.16 Momentum PROD — candidat nouveau, non equivalent a une non-regression exacte D017 tant que la provenance n'est pas reconciliee.

## Validated

- Aucun nouveau candidat valide pendant ce bootstrap.

## Rejected / quarantined

- USDJPY v11.16 manuel: quarantaine, car le test jusqu'au 2026-08-30 traverse l'OOS verrouille.
- SOLUSD v11.16 manuel: incomplet, donc inexploitable.
- MiMo deep walk-forward METHOD/COSTS/DATA: echecs techniques par timeout; contre-audit partiel/interrompu.

## Etat du laboratoire au 2026-08-31 20:22Z

- Depot synchronise: `ee5ad9914156cb66462ee321d40632a38d3714bf`.
- Terminaux ouverts: FTMO normal et FundedNext; aucun `metatester64` actif.
- PropFirmGuard est actif. Aucun orchestrateur MiMo actif.
- Aucun job n'a ete relance durant le bootstrap.
