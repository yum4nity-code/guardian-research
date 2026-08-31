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
4. vérifier l'état réel **sur l'ensemble du PC** : processus, terminaux MT5, workers, MiMo, logs, répertoires de données, fichiers produits et éventuels dépôts/outils hors `D:` ;
5. réconcilier : le réel prime sur un statut ancien ;
6. récolter les résultats terminés ;
7. mettre à jour checkpoint + `CURRENT_QUEUE.json` ;
8. pousser l'état récupéré si GitHub était en retard ;
9. seulement ensuite lancer une nouvelle action.

Un checkpoint ne justifie jamais de relancer automatiquement un job : vérifier d'abord s'il tourne ou s'il a déjà terminé.

## Si le quota tombe avant le push
Ce n'est pas une perte de projet si le checkpoint local a été écrit. Au prochain `GO`, Codex reconstruit l'état depuis le checkpoint + l'état réel du PC puis synchronise GitHub.

Le seul état considéré comme inacceptable est une décision importante restée uniquement dans le raisonnement/conversation et jamais persistée.

## Règle courte
**Avant une transition importante : écrire. Avant une relance : vérifier. Après un jalon : synchroniser.**
