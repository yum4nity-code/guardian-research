# Research Protocol

## Chaîne de travail
IDEA -> RESEARCH -> PROTOTYPE -> BACKTEST -> ROBUSTNESS -> STAT VALIDATION -> RED TEAM -> PRODUCTION CANDIDATE -> CHATGPT AUDIT -> GUARDIAN INTEGRATION -> NON-REGRESSION -> DEPLOY.

## Rôles
- Codex : directeur du labo. Planifie MiMo/MT5, formule et documente les hypothèses, code librement dans `research/`, collecte les résultats, red-team les stratégies, décide des campagnes suivantes.
- MiMo : recherche et analyse massive/répétitive selon les plans Codex.
- MT5 workers : exécution quantitative des campagnes.
- ChatGPT : audit et intégration dans Guardian de production.
- Utilisateur : compilation, validation finale et déploiement.

## Règles anti-curve-fitting
- Geler l'hypothèse et les paramètres avant d'ouvrir les résultats de validation/OOS.
- Ne pas modifier les critères de validation après observation d'un résultat défavorable.
- Conserver le nombre de trials et les familles de trials corrélées.
- Tester coûts réalistes et stressés, autres périodes, perturbations de paramètres et dépendance aux meilleurs jours/trades.
- Une stratégie rejetée ne revient en recherche que sur nouvelle hypothèse explicitement documentée.

## Données
Les gros historiques, ticks, clones MT5 et sorties massives restent localement sous `D:\MT5_Backtests`. GitHub reçoit le code, les `.set`, les manifests, les synthèses CSV/JSON, les décisions et les handoffs nécessaires à l'audit.
