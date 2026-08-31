STATUT: INFO

CONSTAT
L'utilisateur a exécuté manuellement les backtests de non-régression de Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5 sur la fenêtre D017 (M15, ticks réels, dépôt 100000 USD).

RESULTATS OBSERVES
- EURUSD: net +8 545.98 USD, 191 trades, PF 1.56, equity DD max 1.61%, 100% history quality.
- GBPUSD: net +4 482.53 USD, 188 trades, PF 1.24, equity DD max 2.65%, 100% history quality.
- Agrégat simple net: +13 028.51 USD, 379 trades.

REFERENCE HISTORIQUE D017
- EURUSD: +7 075.53 USD, 176 trades, PF 1.65, DD 1.54%.
- GBPUSD: +5 529.75 USD, 166 trades, PF 1.44, DD 2.10%.
- Agrégat: +12 605.28 USD, 342 trades.

IMPACT
La v11.16 reste économiquement positive sur les deux marchés et dépasse les anciens seuils économiques principaux (PF >1.15 par marché, DD <6%, >275 trades agrégés, contribution EURUSD ~65.6% du profit positif agrégé). En revanche, elle ne reproduit pas le D017 historique: +15 trades EURUSD et +22 GBPUSD, avec dégradation notable du PF GBPUSD (1.44 -> 1.24).

ACTION_CODEX
Auditer la provenance exacte des différences d'exécution entre l'ancien exécutable D017 (FTMO_Guardian.11.10_RECOVERY_CRYPTOFIX_v2) et la v11.16. Expliquer les trades supplémentaires sans optimisation ex post. Vérifier notamment gates/signaux/session/owner/risk/exposure/position-count/entry timing/management AUTO. Ne modifier aucun seuil pour rapprocher artificiellement les résultats.

NE_PAS_FAIRE
Ne pas considérer la v11.16 comme non-régression validée uniquement parce que l'agrégat net est légèrement supérieur. Ne pas tuner GBPUSD après lecture des résultats.
