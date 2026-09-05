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

## Fidélité à l'évidence externe — exigence obligatoire
- Ne plus employer « stratégie prouvée » pour une simple famille documentée puis librement adaptée.
- Avant de lancer une nouvelle campagne, classer explicitement la stratégie comme :
  1. `EXACT_REPLICATION` : règles opérationnelles récupérées avec suffisamment de précision pour reproduire l'étude d'origine ;
  2. `CLOSE_REPLICATION` : même mécanisme, classe d'actifs et horizon proches, avec divergences mineures documentées ;
  3. `ADAPTATION` : transfert vers un autre marché, horizon, session, stop, sortie ou convention d'exécution.
- Priorité désormais à `EXACT_REPLICATION`, puis `CLOSE_REPLICATION`. Une `ADAPTATION` reste testable, mais ne doit jamais être présentée comme une stratégie déjà démontrée sur nos marchés.
- Avant chaque nouveau D0xx, documenter précisément : source primaire, univers de l'étude, période, timeframe/horizon, règle d'entrée, règle de sortie, stop éventuel, sizing/normalisation, coûts et toute convention manquante.
- Si une règle essentielle de l'article manque (entrée, sortie, stop, session, filtre, sizing), ne pas l'inventer et ne pas coder la campagne comme réplication. Chercher la méthodologie exacte ou reclasser explicitement en `ADAPTATION`.
- Préférer les études dont l'actif, le timeframe et le mécanisme sont aussi proches que possible de FTMO/FundedNext FX, métaux ou crypto réellement disponibles.
- Une anomalie trouvée ex post sur un seul symbole, un seul sens ou une seule période n'est pas une validation. Elle peut uniquement générer une nouvelle hypothèse pré-enregistrée sur données intactes.

## Phase setup-first avant stratégie complète
- Pour les nouvelles pistes graphiques, commencer par un scanner d'entrée léger et virtuel, sans Guardian, sans HUD, sans gestion de prop-firm et sans ordres réels.
- Le but de cette phase est de répondre à : « le setup contient-il une asymétrie exploitable ? », pas encore « la stratégie complète gagne-t-elle chez FTMO ? ».
- Si l'entrée ne montre pas d'edge, arrêter avant de construire la gestion.
- Si l'entrée montre un edge, figer une gestion simple sur une période de discovery puis valider sur données intactes ; ne pas choisir ex post le meilleur TP au centième de R.
- Guardian redevient obligatoire à l'étape de validation prop-firm : drawdown journalier/maximal, exposition simultanée, coûts, news, requêtes, corrélations et non-régression.

## Diagnostics obligatoires des moteurs de recherche
- Les diagnostics ne doivent pas se limiter au PnL final de la règle publiée. Ils doivent permettre de distinguer « mauvaise entrée » de « bonne entrée, mauvaise sortie ».
- Pour toute stratégie possédant un stop initial naturel, chaque pseudo-trade doit exporter au minimum : `initial_risk`, `MFE_R`, `MAE_R`, `exit_R`, ainsi que les indicateurs de franchissement de `0.5R`, `1R`, `1.5R`, `2R`, `2.5R` et `3R` avant la sortie/stop.
- Les synthèses doivent donner, par symbole, année, sens et agrégé, le pourcentage de trades ayant touché chacun de ces niveaux R.
- Quand c'est techniquement possible, enregistrer aussi l'ordre des événements et les timestamps de chaque niveau afin d'évaluer les sorties sans modifier rétroactivement l'entrée.
- Pour une stratégie sans stop naturel, ne pas inventer un R artificiel. Exporter à la place `MFE`, `MAE`, excursion favorable/adverse normalisée (ATR, volatilité ou bps selon le protocole) et les extrema atteints pendant la fenêtre de détention.
- Les CSV doivent conserver suffisamment d'information pour une analyse postérieure sans nécessiter un rerun uniquement pour calculer MFE/MAE ou les taux de franchissement R.
- Les coûts réalistes et stressés restent séparés de la qualité brute de l'entrée : fournir brut, coûts, net et stress de coûts.
- Les diagnostics de type London/NR7/ORB/TSMOM futurs doivent produire des CSV auditables dans `FILE_COMMON` et, si zéro trade ou problème de données, un diagnostic explicite plutôt qu'un fichier silencieusement vide.

## Standard des dossiers de backtest MT5
- Chaque backtest doit créer son propre dossier reconnaissable sous `FILE_COMMON\\GuardianResearch\\SETUP_SCANS\\`.
- Arborescence standard : `<strategy_id>\\<symbol>\\RUN_<first_simulated_tick>_<unique_suffix>\\` ; un `InpRunTag` facultatif peut remplacer le tag automatique.
- Chaque dossier de run doit contenir au minimum : `EVENTS.csv`, `SUMMARY.csv`, `RUN_INFO.csv`.
- `RUN_INFO.csv` doit inclure l'identifiant de stratégie, la classification de réplication, le symbole, le timeframe de signal, le timeframe du testeur, la source primaire, les paramètres gelés, la date du premier/dernier tick traité et l'indication `guardian_used` / `orders_sent`.
- Ne pas concaténer silencieusement plusieurs backtests dans le même CSV. Un run = un dossier.

## Transfert vers CFD
- Une preuve obtenue sur spot, futures ou exchange ne vaut pas automatiquement preuve sur CFD.
- Les setups documentés servent à sélectionner l'hypothèse ; l'edge doit être répliqué sur le feed CFD cible avant toute validation Guardian.
- Éviter tout filtre dépendant d'un « volume » CFD ambigu, sauf source externe synchronisée et auditée.

## Données
Les gros historiques, ticks, clones MT5 et sorties massives restent localement sous `D:\\MT5_Backtests`. GitHub reçoit le code, les `.set`, les manifests, les synthèses CSV/JSON, les décisions et les handoffs nécessaires à l'audit.
