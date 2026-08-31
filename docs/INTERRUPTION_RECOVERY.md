# Reprise après interruption / quota Codex

Le laboratoire doit rester reconstructible même si le quota Codex tombe sans avertissement, si une session est interrompue ou si un push GitHub n'a pas eu le temps de partir.

Codex a accès à l'ensemble du PC. `D:\MT5_Backtests\` est le stockage canonique du labo, pas une frontière d'inspection : une reprise peut nécessiter de vérifier processus, terminaux MT5, MetaEditor, AppData, dépôts, scripts ou sorties situés ailleurs sur la machine.

## Principe : checkpoint avant transition
Aucune décision importante ne doit exister uniquement dans le contexte conversationnel de Codex.

Avant de passer à l'étape suivante après une décision ou avant de lancer une opération longue/conséquente, Codex doit matérialiser l'état courant localement. C'est un checkpoint transactionnel : **décider -> persister -> agir**.

Le checkpoint local canonique est :
`D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json`

Une copie compacte GitHub peut être maintenue dans :
`manifests/CODEX_SESSION_CHECKPOINT.json`

Le fichier local est prioritaire pour la reprise après coupure ; la copie GitHub sert de dernier état partagé connu.

## Cas spécial : premier bootstrap sans checkpoint existant
Le premier bootstrap est lui-même vulnérable à une coupure de quota. Il ne faut donc pas attendre la fin de l'inventaire réel pour créer le premier checkpoint.

Si `SESSION_CHECKPOINT.json` n'existe pas encore, Codex doit créer **immédiatement après la synchronisation GitHub + lecture des protocoles obligatoires + lecture de l'inbox** un checkpoint minimal `BOOTSTRAP_IN_PROGRESS`, avant de lancer les audits/inventaires parallèles.

Ce checkpoint minimal peut contenir uniquement ce qui est déjà certain à cet instant :
- `updated_at` ;
- `phase: BOOTSTRAP_IN_PROGRESS` ;
- repo synchronisé ou état de synchronisation ;
- notes inbox lues/non encore persistées ;
- `active_primary: BOOTSTRAP_GITHUB_RECONCILIATION` ;
- audits prévus mais **pas encore supposés terminés** ;
- `next_safe_action: inspect_real_machine_state` ;
- `no_new_jobs_launched: true` tant que la réconciliation n'est pas terminée.

Il est ensuite enrichi progressivement à mesure que l'inventaire réel apporte des preuves.

But : même si le quota tombe 30 secondes après le démarrage du bootstrap, la session suivante sait que le bootstrap avait commencé, qu'aucun nouveau job n'était autorisé avant réconciliation, et quelle est la prochaine action sûre.

Ne jamais inventer dans ce checkpoint un worker, résultat ou état qui n'a pas encore été vérifié.

## Quand checkpoint-er immédiatement
Créer/mettre à jour le checkpoint AVANT ou IMMÉDIATEMENT APRÈS chacune de ces transitions, avant d'enchaîner :
- choix/changement de priorité principale ;
- décision `VALIDATED`, `REJECTED`, `CANDIDATE`, `BLOCKED` ou changement méthodologique ;
- lancement d'un worker MT5, d'une campagne longue ou d'une tâche MiMo ;
- fin d'une campagne donnant un résultat exploitable ;
- création d'une nouvelle hypothèse/version ;
- modification de code qui change la sémantique d'une expérience ;
- découverte Guardian / sécurité / exécution / régression ;
- création d'un handoff ou passage à `WAITING_CHATGPT` / `WAITING_CODEX` ;
- toute action dont la répétition accidentelle serait coûteuse ou dangereuse.

Ne pas checkpoint-er chaque ligne de log ou chaque tick : le but est la durabilité des transitions, pas le spam.

## Contenu minimal du checkpoint
Le JSON local doit permettre à une nouvelle session de reprendre sans dépendre de la mémoire de la précédente :
- `updated_at` ;
- `active_primary` ;
- jusqu'à trois priorités ;
- décisions prises depuis le checkpoint précédent ;
- travaux MT5 réellement lancés avec ID de campagne, symbole, worker/processus si connu, chemins de statut/log/résultats attendus ;
- tâches MiMo réellement lancées et sorties attendues ;
- résultats terminés non encore intégrés ;
- `next_safe_action` ;
- fichiers locaux modifiés/non poussés et, si pertinent, hashes/commit ;
- éléments `WAITING_CHATGPT` / `WAITING_CODEX` ;
- toute hypothèse nécessaire pour comprendre l'état.

Écrire le checkpoint de façon sûre : produire un fichier temporaire puis remplacer le fichier canonique lorsque possible, afin d'éviter qu'une interruption laisse un JSON tronqué.

## Push GitHub par jalon
La fin de session n'est pas le seul moment où pousser.

Après un **jalon à forte valeur** (verdict, candidat, anomalie Guardian, nouvelle campagne longue lancée, changement majeur de queue, handoff), pousser les petits fichiers utiles dès que l'état est cohérent. Ne pas attendre volontairement la toute fin du quota.

Pendant un calcul sain sans nouvelle décision, ne pas pousser périodiquement juste pour faire du bruit.

## Reprise au prochain GO
Au début de chaque session/`GO` :
1. synchroniser GitHub ;
2. lire l'inbox ChatGPT -> Codex ;
3. lire `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` s'il existe, puis `manifests/CODEX_SESSION_CHECKPOINT.json` comme dernier état partagé ;
4. si aucun checkpoint local n'existe encore et que le bootstrap n'est pas terminé, créer immédiatement le checkpoint minimal `BOOTSTRAP_IN_PROGRESS` avant les audits longs ;
5. vérifier l'état réel **sur l'ensemble du PC** : processus, terminaux MT5, workers, MiMo, logs, répertoires de données, fichiers produits et éventuels dépôts/outils hors `D:` ;
6. réconcilier : le réel prime sur un statut ancien ;
7. récolter les résultats terminés ;
8. mettre à jour checkpoint + `CURRENT_QUEUE.json` ;
9. pousser l'état récupéré si GitHub était en retard ;
10. seulement ensuite lancer une nouvelle action.

Un checkpoint ne justifie jamais de relancer automatiquement un job : vérifier d'abord s'il tourne ou s'il a déjà terminé.

## Si le quota tombe avant le push
Ce n'est pas une perte de projet si le checkpoint local a été écrit. Au prochain `GO`, Codex reconstruit l'état depuis le checkpoint + l'état réel du PC puis synchronise GitHub.

Si le quota tombe pendant le **tout premier bootstrap avant même qu'un checkpoint ait pu être écrit**, la reprise reste conservatrice : synchroniser GitHub, relire l'inbox, constater l'absence de checkpoint, créer le checkpoint minimal `BOOTSTRAP_IN_PROGRESS`, vérifier la machine réelle, et **ne lancer aucun nouveau job avant réconciliation**.

Le seul état considéré comme inacceptable est une décision importante restée uniquement dans le raisonnement/conversation et jamais persistée.

## Règle courte
**Au premier bootstrap : checkpoint minimal avant inventaire. Ensuite : avant une transition importante, écrire. Avant une relance, vérifier. Après un jalon, synchroniser.**
