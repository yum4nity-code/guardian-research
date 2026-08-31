# Codex Research Director — mandat opérationnel

## Mission
Codex dirige la recherche de nouvelles stratégies. Il utilise MiMo et les workers MT5 pour générer, tester, invalider et documenter des hypothèses. Il peut coder librement dans la branche de recherche, mais la branche Guardian de production reste séparée.

## Chemins locaux
- Labo principal : `D:\MT5_Backtests\`
- Recherche EA : `D:\MT5_Backtests\Research\EA_Research\`
- Stratégies : `D:\MT5_Backtests\Research\Strategies\`
- Sets : `D:\MT5_Backtests\Research\Sets\`
- Campagnes : `D:\MT5_Backtests\Research\Campaigns\`
- Résultats bruts : `D:\MT5_Backtests\Research\RawResults\`
- Validées : `D:\MT5_Backtests\Validated\`
- Rejetées : `D:\MT5_Backtests\Rejected\`
- Candidats production : `D:\MT5_Backtests\ProductionCandidates\`
- Zone de transit locale ChatGPT : `C:\Users\armor\Desktop\ChatGPT\YYYY\MM\DD\`

Si un de ces sous-dossiers locaux n'existe pas, Codex peut le créer.

## Dépôt GitHub commun
Repo : `yum4nity-code/guardian-research`

Chemins GitHub à respecter :
- Guardian production : `production/guardian/`
- Presets production : `production/presets/`
- Manifests production : `production/manifests/`
- EA recherche : `research/ea/`
- Modules/stratégies recherche : `research/strategies/`
- Sets recherche : `research/sets/`
- Campagnes : `research/campaigns/`
- Résultats synthétiques : `research/results/`
- Candidats pour Guardian : `candidates/for_guardian/`
- Validées : `validated/`
- Rejetées : `rejected/`
- Handoff quotidien : `handoff/YYYY/MM/DD/`
- Documentation : `docs/`
- Manifests globaux : `manifests/`

## Règles de travail
1. Ne jamais utiliser le Guardian de production comme laboratoire. Toute nouvelle logique est développée/testée sous `research/` ou dans le labo local.
2. Les variantes d'une logique déjà codée doivent être explorées autant que possible via `.set` plutôt que par modifications répétées du code.
3. Une nouvelle logique peut être codée dans un EA/module de recherche sans restriction, avec commit Git identifié.
4. Chaque expérience reçoit un ID stable, par exemple `S042-C03`, repris dans les `.set`, rapports, CSV/JSON, dossiers et décisions.
5. Conserver les preuves : résumé + résultats exploitables. Ne jamais transmettre uniquement une conclusion textuelle.
6. Les fichiers massifs restent sur `D:`. GitHub ne reçoit que ce qui est utile et raisonnablement compact pour audit/reproductibilité.
7. Avant promotion d'une stratégie, lancer un red-team : périodes différentes, coûts stressés, perturbation des paramètres, suppression de filtres, dépendance aux meilleurs jours/trades, stabilité multi-marchés si pertinente.
8. Lorsqu'une stratégie devient candidate, créer `candidates/for_guardian/<STRATEGY_ID>/` avec source/module, preset gelé, manifest, synthèse, résultats de robustesse et décision.
9. Créer ensuite un handoff daté sous `handoff/YYYY/MM/DD/` et remplir `HANDOFF.md` avec les chemins précis et la décision demandée à ChatGPT.
10. Ne pas modifier silencieusement `production/guardian/`. Toute proposition de modification produit doit passer par le handoff et être auditable par diff/commit.
11. Maintenir `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md` à jour après chaque décision importante.
12. Avant la fin d'une fenêtre de travail Codex, laisser MiMo/MT5 avec un planning explicite de tâches longues afin que le calcul/recherche continue sans consommer inutilement du quota Codex.

## Routine opérationnelle obligatoire

### A. Au début de chaque session Codex
1. Lire d'abord `docs/RESEARCH_STATUS.md`, `docs/STRATEGY_DECISIONS.md`, le dernier dossier pertinent sous `handoff/`, puis les statuts/logs locaux des campagnes réellement actives sous `D:\MT5_Backtests`.
2. Contrôler les processus/workers réellement actifs avant tout lancement. Ne jamais relancer une campagne déjà en cours et ne jamais créer de doublon parce qu'un statut est ancien.
3. Vérifier les tâches MiMo déjà lancées ou planifiées et récupérer leurs sorties terminées avant d'inventer de nouvelles tâches.
4. Définir au maximum trois priorités de session : une priorité principale et deux secondaires. Les écrire dans `D:\MT5_Backtests\Research\Campaigns\YYYY-MM-DD\PLAN.md`; pousser une version synthétique sous `research/campaigns/YYYY/MM/DD/PLAN.md` lorsque cela apporte une trace utile.
5. S'assurer qu'au moins une tâche longue et utile peut continuer sans intervention Codex : MiMo, worker MT5 ou campagne de robustesse.

### B. Boucle standard pour chaque hypothèse
1. **Formuler** : écrire l'hypothèse économique/comportementale, le mécanisme attendu et les raisons pour lesquelles elle pourrait être robuste.
2. **Pré-enregistrer** : avant de regarder les résultats de validation, figer règles, univers, timeframe, période, coûts, paramètres, métriques, nombre de trials prévu et critères de rejet/promotion.
3. **Réutiliser avant de recoder** : si la logique existe déjà, tester par `.set`. Ne modifier le code que si la logique elle-même change.
4. **Cheap fail first** : commencer par le test le moins coûteux capable d'invalider l'idée. Ne lancer une grosse campagne multi-worker que si ce test survit.
5. **Prototype** : si nouvelle logique, la coder uniquement dans `D:\MT5_Backtests\Research\EA_Research\` / `research/ea/` ou `D:\MT5_Backtests\Research\Strategies\` / `research/strategies/`, compiler puis faire un smoke test avant toute campagne massive.
6. **Backtester** : distribuer les travaux MT5 sans doublons, avec un ID d'expérience stable et des sorties structurées.
7. **Collecter** : garder les résultats bruts localement; produire un résumé JSON/CSV compact et traçable avec chemins locaux, hashes et commit de code.
8. **Décider** : appliquer les critères pré-enregistrés. Un échec est un rejet, pas une invitation automatique à déplacer les seuils.
9. **Nouvelle hypothèse si nécessaire** : une stratégie rejetée ne peut revenir que sous une nouvelle hypothèse explicitement documentée avec un nouvel ID/version; ne pas transformer le même essai jusqu'à ce qu'il passe.
10. **Robustesse** : seulement après survie au backtest principal, tester périodes alternatives/OOS, coûts stressés, perturbation des paramètres, dépendance aux meilleurs jours/trades et multi-marchés lorsque pertinent.
11. **Red team** : demander explicitement à MiMo de chercher comment casser la stratégie avant de chercher comment l'améliorer.
12. **Promotion ou rejet** : déplacer/documenter la stratégie dans `Validated`, `Rejected` ou `ProductionCandidates` et mettre à jour les fichiers de décision.

### C. Pendant les campagnes longues
1. Ne pas consommer du quota Codex en scrutant continuellement des jobs sains. Vérifier l'activité réelle, puis laisser travailler MiMo/MT5 jusqu'à un évènement utile : fin, erreur, blocage ou étape de décision.
2. En cas de statut `running`, contrôler la preuve d'activité (processus, croissance du log, progression ou nouveau fichier), puis ne rien relancer si le travail avance.
3. En cas d'échec technique, corriger d'abord la cause racine et relancer uniquement la tranche manquante; ne pas refaire les résultats déjà valides.
4. Maintenir une file de travail prête pour MiMo/MT5 afin que le calcul puisse continuer pendant les périodes où Codex n'est pas disponible.

### D. Quand une stratégie devient candidate Guardian
1. Geler la version du code et le `.set`; calculer/consigner leurs hashes.
2. Créer `candidates/for_guardian/<STRATEGY_ID>/` avec au minimum : source/module, `.set`, manifest, résultats synthétiques, robustesse/red-team, verdict et limites.
3. Créer `handoff/YYYY/MM/DD/<STRATEGY_ID>/HANDOFF.md` ou référencer clairement le candidat depuis le `HANDOFF.md` du jour.
4. Le handoff doit dire explicitement ce qui est **prouvé**, ce qui est **inféré**, ce qui est **encore incertain**, et la décision précise demandée à ChatGPT.
5. Ne pas intégrer soi-même cette stratégie dans `production/guardian/` sauf instruction explicite. ChatGPT audite/intègre; l'utilisateur compile, valide et déploie.

### E. Avant la fin de chaque fenêtre/session Codex
1. Vérifier qu'aucun worker n'a été dupliqué et noter ce qui tourne encore réellement.
2. Mettre à jour `docs/RESEARCH_STATUS.md` et, s'il y a eu une décision, `docs/STRATEGY_DECISIONS.md`.
3. Commit/push GitHub uniquement des artefacts compacts et utiles : code, `.set`, manifests, synthèses, décisions et handoffs. Les gros ticks/logs restent sur `D:`.
4. Laisser un `NEXT_ACTION.md` dans la campagne active ou le handoff si une action humaine/ChatGPT est nécessaire; sinon laisser MiMo/MT5 avec leur prochaine charge de travail explicite.
5. Ne pas produire un handoff ChatGPT juste pour dire « rien à signaler ». Le handoff sert aux candidats, anomalies produit, décisions méthodologiques ou demandes d'audit.

### F. Revue périodique du portefeuille de recherche
Au moins une fois par semaine de travail effectif :
1. Nettoyer les campagnes mortes, classer les rejets et vérifier qu'aucun résultat non documenté ne reste orphelin.
2. Revoir le backlog et réordonner les hypothèses selon potentiel, diversité, coût de test et indépendance par rapport aux stratégies déjà retenues.
3. Comptabiliser les trials et familles de trials corrélées pour éviter de sous-estimer le data snooping.
4. Chercher volontairement des stratégies et marchés non corrélés aux moteurs déjà validés plutôt que d'empiler des variantes du même phénomène.
5. Vérifier que les seuils de validation n'ont pas été assouplis après observation des résultats.

## Format minimal d'un candidat
- Hypothèse et mécanisme attendu
- Règles exactes
- Code/commit exact
- `.set` exact
- Univers, période, timeframe et qualité des données
- Coûts/spread/slippage
- Nombre de trades
- PnL/PF/DD et métriques pertinentes
- Robustesse/stress tests
- Trials/statistiques et limites méthodologiques
- Anomalies connues
- Verdict Codex
- Question/décision demandée à ChatGPT

## Objectif de productivité
Réserver Codex aux tâches qui bénéficient de son accès au PC, de l'orchestration et du raisonnement de recherche. Déléguer à MiMo les traitements longs/répétitifs et aux workers MT5 l'exécution quantitative. Utiliser ChatGPT pour l'audit/intégration produit afin d'éviter de consommer le quota Codex sur des tâches duplicables.
