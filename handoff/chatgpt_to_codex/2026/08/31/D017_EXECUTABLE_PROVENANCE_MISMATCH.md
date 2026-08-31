STATUT: ACTION_REQUISE

CONSTAT
Le manifeste préenregistré historique D-017 ne référence pas Guardian v11.14/v11.15/v11.16 comme exécutable de test. Il référence explicitement `FTMO\FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2` avec overrides D-017, notamment Momentum seul, session 07-17 UTC, risque 0.25%, coûts fallback 2.50/lot/côté et `InpEnableStrategyTimeStop=false`.

PREUVE
Le manifeste D-017 récupéré depuis l'historique conversationnel indique:
- expert: `FTMO\FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2`
- period: M15
- fromDate: 2025.08.28
- toDate: 2026.06.28
- deposit: 100000 USD
- leverage: 1:100
- symbols: EURUSD_BT, GBPUSD_BT
- overrides: Momentum only, 07-17 UTC, time-stop false, commission fallback 2.50/lot/côté, etc.
Les métriques historiques D-017 sont EURUSD +7075.53 / 176 trades / PF 1.65 / DD 1.54% et GBPUSD +5529.75 / 166 trades / PF 1.44 / DD 2.10%.

Un nouveau backtest utilisateur de la candidate v11.16 MOMENTUM PROD sur EURUSD affiche 100% ticks réels, +8545.98 USD, 191 trades, PF 1.56, DD equity 1.61% (supposé même intervalle mais à confirmer). Ce résultat ne reproduit donc pas 1:1 le D-017 historique, et il ne faut pas le présenter comme une simple non-régression exacte tant que la parité sémantique entre l'ancien exécutable D-017 et la candidate v11.16 n'est pas auditée.

IMPACT
Le point critique n'est plus seulement le time-stop. Les résultats D-017 publiés ont été obtenus avec un exécutable historique différent. La production v11.16 peut rester économiquement intéressante, mais elle doit être validée comme implémentation nouvelle/parité fonctionnelle, pas supposée identique au backtest D-017 de référence.

ACTION_CODEX
Au prochain GO, localiser l'exécutable/source exact `FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2` et le manifeste D-017 local. Comparer de façon ciblée la logique AUTO Momentum et les paramètres effectifs avec `ProductionCandidates\Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5`. Identifier toute divergence capable d'expliquer le passage de 176 à 191 trades sur EURUSD. Vérifier en priorité coûts fallback, filtres qualité/volume/spread, ranking, régime, SL structurel, cooldown, horaires, règles de positions et toute évolution de signal entre v11.10 et v11.16. Ne pas modifier la prod avant audit. Si la parité est impossible ou non souhaitable, définir clairement la v11.16 comme nouveau candidat et fixer son propre baseline EURUSD/GBPUSD.

NE_PAS_FAIRE
Ne pas forcer la v11.16 à retrouver artificiellement 7075.53/176 par optimisation post hoc. Ne pas ouvrir OOS ni ajuster des paramètres à la performance. Ne pas conclure que le nouveau résultat est meilleur avant test GBPUSD et audit de provenance.