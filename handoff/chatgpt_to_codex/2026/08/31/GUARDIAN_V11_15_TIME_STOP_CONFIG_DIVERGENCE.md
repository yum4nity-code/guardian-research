# Guardian v11.15 — divergence de configuration time-stop

STATUT: URGENT

CONSTAT:
- Le preset de production `production/presets/FTMO_D017_v11_15_SAFE.set` fixe `InpEnableStrategyTimeStop=false`.
- Le source v11.15 a par défaut `InpEnableStrategyTimeStop=true`, avec `InpMomentumMaxMinutes=60` et `InpMomentumMinProgressR=0.40`.
- Le Strategy Tester affiché par l'utilisateur le 2026-08-31 montre `InpEnableStrategyTimeStop=true`, ainsi que BlackBox/Ledger à true, donc le preset SAFE n'était clairement pas chargé sur ce test.
- L'utilisateur a également observé en live une position Momentum fermée à environ 60 minutes, cohérente avec un time-stop actif.

PREUVE:
- Preset GitHub SAFE: `InpEnableStrategyTimeStop=false`.
- Source v11.15: condition de fermeture time-stop uniquement si `InpEnableStrategyTimeStop && managed_minutes >= StrategyMaxMinutes(...) && profit_r < StrategyMinProgressR(...)`; Momentum: 60 min / 0.40R.
- Bootstrap source: `BootstrapPortfolioCharts()` sauvegarde le chart courant comme template `Guardian_D017_Observation.tpl` puis applique ce template aux autres symboles M15. Si le chart source est attaché avec les valeurs par défaut au lieu du SAFE set, la mauvaise configuration peut être propagée.

IMPACT:
- Le live peut diverger du D017 validé/backtesté, dont la modification centrale était précisément la suppression du time-stop fixe de 60 minutes.
- Les résultats live/backtests lancés avec les defaults ne sont pas directement comparables aux résultats D017 sans time-stop.

ACTION_CODEX:
1. Au prochain GO, vérifier localement comment v11.15 a été attaché aux charts EURUSD/GBPUSD et quel `.set`/template est réellement appliqué.
2. Auditer le mécanisme `BootstrapPortfolioCharts()` et le fichier/template `Guardian_D017_Observation.tpl` pour déterminer si les defaults ont été sauvegardés/propagés.
3. Vérifier les inputs effectifs live EURUSD M15 et GBPUSD M15, notamment `InpEnableStrategyTimeStop`, BlackBox, Ledger et les autres écarts avec `FTMO_D017_v11_15_SAFE.set`.
4. Proposer une prévention robuste empêchant une instance production de démarrer silencieusement avec des defaults incompatibles avec le preset gelé (sans modifier production directement sans handoff ChatGPT/utilisateur).

NE_PAS_FAIRE:
- Ne pas modifier silencieusement `production/guardian/`.
- Ne pas considérer les defaults du source comme équivalents au preset D017 SAFE.
- Ne pas relancer de campagne avant réconciliation de la configuration réelle.
