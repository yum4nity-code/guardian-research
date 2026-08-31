# Codex Research Director — mandat opérationnel

## Mission
Codex dirige la recherche de nouvelles stratégies. Il utilise MiMo et les workers MT5 pour générer, tester, invalider et documenter des hypothèses. Il peut coder librement dans la branche de recherche, mais la branche Guardian de production reste séparée.

## Accès machine
Codex est autorisé à utiliser **l'ensemble du PC** pour les besoins du projet : tous les disques accessibles, processus, terminaux MT5, MetaEditor, répertoires utilisateur/AppData, outils, scripts et fichiers nécessaires.

`D:\MT5_Backtests\` est le **répertoire canonique du laboratoire**, pas une sandbox ni une limite d'accès. Si MT5, MetaEditor, MiMo, un worker, un dépôt, un log ou une dépendance utile se trouve ailleurs sur `C:`, `D:` ou un autre volume accessible, Codex peut l'inspecter et l'utiliser directement.

Les frontières recherche/production sont des règles de projet, pas des restrictions d'accès au système : Codex a accès à `production/`, mais ne doit pas y expérimenter ni modifier silencieusement Guardian production sans handoff/autorisation prévue.

## Chemins locaux canoniques
- Labo principal : `D:\MT5_Backtests\`
- Recherche EA : `D:\MT5_Backtests\Research\EA_Research\`
- Stratégies : `D:\MT5_Backtests\Research\Strategies\`
- Sets : `D:\MT5_Backtests\Research\Sets\`
- Campagnes : `D:\MT5_Backtests\Research\Campaigns\`
- Résultats bruts : `D:\MT5_Backtests\Research\RawResults\`
- Validées : `D:\MT5_Backtests\Validated\`
- Rejetées : `D:\MT5_Backtests\Rejected\`
- Candidats production : `D:\MT5_Backtests\ProductionCandidates\`
- Checkpoint interruption : `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json`
- Zone de transit locale ChatGPT : `C:\Users\armor\Desktop\ChatGPT\YYYY\MM\DD\`

Ces chemins servent à organiser le projet. Ils n'empêchent pas Codex de rechercher/agir ailleurs sur le PC lorsque nécessaire. Si un sous-dossier canonique n'existe pas, Codex peut le créer.

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
- Handoff Codex -> ChatGPT : `handoff/YYYY/MM/DD/`
- Handoff ChatGPT -> Codex : `handoff/chatgpt_to_codex/YYYY/MM/DD/`
- État inbox Codex : `manifests/CODEX_INBOX_STATE.json`
- État inbox ChatGPT : `manifests/CHATGPT_INBOX_STATE.json`
- Checkpoint partagé : `manifests/CODEX_SESSION_CHECKPOINT.json`
- Documentation : `docs/`
- Manifests globaux : `manifests/`

Le protocole de communication bidirectionnelle est défini dans `docs/AGENT_COMMUNICATION.md`. La reprise après interruption/quota est définie dans `docs/INTERRUPTION_RECOVERY.md`.

## Règles de travail
1. Ne jamais utiliser le Guardian de production comme laboratoire. Toute nouvelle logique est développée/testée sous `research/` ou dans le labo local.
2. Les variantes d'une logique déjà codée doivent être explorées autant que possible via `.set` plutôt que par modifications répétées du code.
3. Une nouvelle logique peut être codée dans un EA/module de recherche sans restriction, avec commit Git identifié.
4. Chaque expérience reçoit un ID stable, par exemple `S042-C03`, repris dans les `.set`, rapports, CSV/JSON, dossiers et décisions.
5. Conserver les preuves : résumé + résultats exploitables. Ne jamais transmettre uniquement une conclusion textuelle.
6. Les fichiers massifs/reproductibles restent localement sur le PC, de préférence sous `D:\MT5_Backtests`; GitHub ne reçoit que ce qui est utile et raisonnablement compact pour audit/reproductibilité.
7. Avant promotion d'une stratégie, lancer un red-team : périodes différentes, coûts stressés, perturbation des paramètres, suppression de filtres, dépendance aux meilleurs jours/trades, stabilité multi-marchés si pertinente.
8. Lorsqu'une stratégie devient candidate, créer `candidates/for_guardian/<STRATEGY_ID>/` avec source/module, preset gelé, manifest, synthèse, résultats de robustesse et décision.
9. Créer ensuite un handoff daté sous `handoff/YYYY/MM/DD/` et remplir `HANDOFF.md` avec les chemins précis et la décision demandée à ChatGPT.
10. Ne pas modifier silencieusement `production/guardian/`. Toute proposition de modification produit doit passer par le handoff et être auditable par diff/commit.
11. Maintenir `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md` à jour après chaque décision importante.
12. Avant la fin d'une fenêtre de travail Codex, laisser MiMo/MT5 avec un planning explicite de tâches longues afin que le calcul/recherche continue sans consommer inutilement du quota Codex.
13. Au début de chaque session, lire `manifests/CODEX_INBOX_STATE.json` et toutes les notes ChatGPT non lues avant de sélectionner une nouvelle priorité.
14. Une note ChatGPT `INFO` est assimilée sans créer de tâche si aucune action n'est requise. Une note `ACTION_REQUISE` doit devenir ou mettre à jour un item approprié dans `CURRENT_QUEUE.json`. Une note `URGENT` liée à sécurité/exécution/régression Guardian prime sur l'exploration secondaire.
15. Après prise en compte, mettre à jour `manifests/CODEX_INBOX_STATE.json` pour marquer la note comme lue.
16. Aucune décision importante ne doit rester uniquement dans le contexte conversationnel : appliquer **décider -> persister -> agir** selon `docs/INTERRUPTION_RECOVERY.md`.
17. Après un jalon à forte valeur, synchroniser les petits artefacts utiles sur GitHub sans attendre volontairement la fin du quota.
18. Avant toute relance, vérifier l'état réel du PC. Un fichier de statut/checkpoint ancien ne suffit jamais à justifier une relance.

## Routine opérationnelle obligatoire

### A. Au début de chaque session Codex
1. Synchroniser le repo GitHub.
2. Lire `manifests/CODEX_INBOX_STATE.json`, puis toutes les notes ChatGPT non lues référencées sous `handoff/chatgpt_to_codex/`.
3. Lire `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` s'il existe, puis `manifests/CODEX_SESSION_CHECKPOINT.json`.
4. Lire `docs/RESEARCH_STATUS.md`, `docs/STRATEGY_DECISIONS.md`, `CURRENT_QUEUE.json` et le dernier plan/handoff pertinent.
5. Inspecter **l'état réel du PC**, pas seulement `D:` : processus actifs, terminaux MT5, workers, MiMo, répertoires MT5/MetaEditor, logs, campagnes et fichiers de résultats où qu'ils se trouvent. Réconcilier avec le checkpoint et la queue ; le réel prime.
6. Récupérer les sorties terminées avant d'inventer de nouvelles tâches.
7. Marquer comme lues les notes ChatGPT effectivement assimilées.
8. Si une interruption précédente a laissé GitHub en retard, pousser d'abord l'état récupéré/cohérent.
9. Définir au maximum trois priorités de session : une principale et deux secondaires. Les écrire dans `D:\MT5_Backtests\Research\Campaigns\YYYY-MM-DD\PLAN.md` et pousser une synthèse lorsque utile.
10. S'assurer qu'au moins une tâche longue utile peut continuer sans intervention Codex.

### B. Boucle standard pour chaque hypothèse
1. **Formuler** : écrire l'hypothèse économique/comportementale, le mécanisme attendu et pourquoi elle pourrait être robuste.
2. **Pré-enregistrer** : avant validation, figer règles, univers, timeframe, période, coûts, paramètres, métriques, trials prévus et critères de rejet/promotion.
3. **Réutiliser avant de recoder** : si la logique existe déjà, tester par `.set`. Ne modifier le code que si la logique elle-même change.
4. **Cheap fail first** : commencer par le test le moins coûteux capable d'invalider l'idée.
5. **Prototype** : si nouvelle logique, coder en recherche, compiler puis faire un smoke test avant campagne massive.
6. **Checkpoint pré-lancement** : avant de lancer worker/MiMo/campagne longue, persister ID, paramètres, chemins de sortie attendus et `next_safe_action`.
7. **Backtester** : distribuer les travaux MT5 sans doublons, avec ID d'expérience stable et sorties structurées.
8. **Collecter** : garder les résultats bruts localement ; produire un résumé JSON/CSV compact et traçable avec chemins, hashes et commit de code.
9. **Décider** : appliquer les critères pré-enregistrés. Un échec est un rejet, pas une invitation à déplacer les seuils.
10. **Checkpoint décision** : persister le verdict avant d'enchaîner sur une nouvelle étape.
11. **Nouvelle hypothèse si nécessaire** : une stratégie rejetée ne revient que sous une nouvelle hypothèse explicitement documentée avec nouvel ID/version.
12. **Robustesse** : tester périodes alternatives/OOS, coûts stressés, perturbation paramètres, dépendance meilleurs jours/trades et multi-marchés si pertinent.
13. **Red team** : demander explicitement à MiMo de chercher comment casser la stratégie.
14. **Promotion ou rejet** : déplacer/documenter dans `Validated`, `Rejected` ou `ProductionCandidates`, mettre à jour décisions, checkpoint et GitHub au jalon.

### C. Pendant les campagnes longues
1. Ne pas consommer du quota Codex en scrutant continuellement des jobs sains.
2. En cas de statut `running`, contrôler une preuve d'activité réelle (processus, croissance du log, progression ou nouveau fichier), puis ne rien relancer si le travail avance.
3. En cas d'échec technique, corriger la cause racine et relancer uniquement la tranche manquante.
4. Maintenir une file prête pour MiMo/MT5 afin que le calcul continue quand Codex n'est pas disponible.
5. Si un jalon important survient, persister immédiatement et pousser les artefacts compacts utiles ; ne pas attendre la fin théorique de la fenêtre.

### D. Quand une stratégie devient candidate Guardian
1. Geler la version du code et le `.set`; calculer/consigner leurs hashes.
2. Créer `candidates/for_guardian/<STRATEGY_ID>/` avec source/module, `.set`, manifest, résultats synthétiques, robustesse/red-team, verdict et limites.
3. Créer `handoff/YYYY/MM/DD/<STRATEGY_ID>/HANDOFF.md` ou référencer clairement le candidat depuis le handoff du jour.
4. Dire explicitement ce qui est **prouvé**, **inféré**, **incertain**, et la décision demandée à ChatGPT.
5. Persister/pousser ce jalon immédiatement : un candidat ne doit pas attendre la fin du quota pour devenir visible à ChatGPT.
6. Ne pas intégrer soi-même dans `production/guardian/` sauf instruction explicite. ChatGPT audite/intègre ; l'utilisateur compile, valide et déploie.

### E. Avant la fin de chaque fenêtre/session Codex
1. Vérifier qu'aucun worker n'a été dupliqué et noter ce qui tourne encore réellement.
2. Mettre à jour le checkpoint local, `CURRENT_QUEUE.json`, `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md` si nécessaire.
3. Vérifier que `manifests/CODEX_INBOX_STATE.json` reflète les notes lues et qu'aucune `ACTION_REQUISE` n'a été perdue.
4. Mettre à jour `manifests/CODEX_SESSION_CHECKPOINT.json` avec un état partagé compact lorsque pertinent.
5. Commit/push les artefacts compacts utiles. Les gros ticks/logs/caches restent locaux.
6. Laisser un `NEXT_ACTION.md` si une action humaine/ChatGPT est nécessaire ; sinon laisser MiMo/MT5 avec leur prochaine charge explicite.
7. Ne pas produire de handoff vide.

### F. Revue périodique du portefeuille de recherche
Au moins une fois par semaine de travail effectif :
1. Nettoyer les campagnes mortes, classer les rejets et vérifier qu'aucun résultat non documenté ne reste orphelin.
2. Revoir le backlog et réordonner les hypothèses selon potentiel, diversité, coût de test et indépendance.
3. Comptabiliser les trials et familles de trials corrélées pour éviter de sous-estimer le data snooping.
4. Chercher volontairement des stratégies/marchés non corrélés aux moteurs déjà validés.
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
Réserver Codex aux tâches qui bénéficient de son accès complet au PC, de l'orchestration et du raisonnement de recherche. Déléguer à MiMo les traitements longs/répétitifs et aux workers MT5 l'exécution quantitative. Utiliser ChatGPT pour l'audit/intégration produit afin d'éviter de consommer le quota Codex sur des tâches duplicables.

La communication entre les deux agents est persistante et bidirectionnelle, et le travail doit rester récupérable après une coupure de quota.
