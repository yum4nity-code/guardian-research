# Politique de synchronisation GitHub

GitHub sert de source de vérité compacte entre Codex et ChatGPT. `D:\MT5_Backtests` est le stockage canonique du labo lourd, mais Codex peut utiliser l'ensemble du PC pour le projet ; les gros fichiers reproductibles restent localement là où le workflow les exige.

Le protocole de communication bidirectionnelle est défini dans `docs/AGENT_COMMUNICATION.md`. La persistance avant coupure/quota est définie dans `docs/INTERRUPTION_RECOVERY.md`.

## 1. Push immédiat Codex -> ChatGPT — événement critique
Codex doit synchroniser GitHub immédiatement lorsqu'un des événements suivants survient :
- une stratégie devient `CANDIDATE` pour Guardian ;
- une anomalie de sécurité, risque, exécution ou régression Guardian est détectée ;
- une décision méthodologique nécessite un audit ou arbitrage ChatGPT ;
- un fichier/code/preset doit être audité ou intégré par ChatGPT ;
- `CURRENT_QUEUE.json` contient un item `WAITING_CHATGPT`.

Dans ces cas, créer/mettre à jour le handoff daté et pousser les artefacts utiles sans attendre la fin de session.

## 2. Push immédiat ChatGPT -> Codex — découverte utile
ChatGPT doit synchroniser GitHub lorsqu'un audit ou travail produit révèle un élément qui peut modifier le labo ou éviter une erreur :
- faiblesse/anomalie Guardian à connaître ;
- contrainte de compatibilité ou migration entre versions ;
- correction méthodologique ;
- fait nouveau qui change une hypothèse ou un protocole ;
- vérification/test qui nécessite l'accès local de Codex au PC/MT5.

La note est créée sous `handoff/chatgpt_to_codex/YYYY/MM/DD/` et référencée dans `manifests/CODEX_INBOX_STATE.json` comme non lue.

Si aucune action Codex n'est nécessaire, la note reste `INFO` et ne crée pas d'item de queue. Si une action est réellement requise, ChatGPT peut ajouter/signaler un item `WAITING_CODEX` dans `CURRENT_QUEUE.json`.

## 3. Checkpoint transactionnel avant transition
La synchronisation GitHub ne remplace pas le checkpoint local.

Avant une transition importante ou le lancement d'un travail long, Codex doit d'abord persister localement selon `docs/INTERRUPTION_RECOVERY.md` : **décider -> persister -> agir**.

Le checkpoint local canonique est `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json`. `manifests/CODEX_SESSION_CHECKPOINT.json` peut refléter le dernier état partagé compact.

Une décision importante ne doit jamais rester uniquement dans le contexte conversationnel en attendant un futur push.

## 4. Push par jalon à forte valeur
Ne pas attendre volontairement la fin du quota après un changement important. Dès qu'un état cohérent existe, synchroniser les petits artefacts utiles après :
- verdict `VALIDATED` / `REJECTED` / `CANDIDATE` / `BLOCKED` ;
- lancement d'une nouvelle campagne longue qui change la queue ;
- résultat terminé qui change la décision ;
- nouvelle hypothèse formelle/pré-enregistrée ;
- changement méthodologique ;
- handoff ou transition `WAITING_CHATGPT` / `WAITING_CODEX` ;
- anomalie Guardian.

Ce n'est pas un push périodique : c'est un push déclenché par une transition utile.

## 5. Push obligatoire — fin de GO / fin de fenêtre Codex
Si la fenêtre arrive normalement à son terme, Codex doit au minimum :
- mettre à jour le checkpoint local et, lorsque pertinent, `manifests/CODEX_SESSION_CHECKPOINT.json` ;
- mettre à jour `CURRENT_QUEUE.json` avec l'état réel ;
- mettre à jour `docs/RESEARCH_STATUS.md` ;
- mettre à jour `docs/STRATEGY_DECISIONS.md` si une décision a changé ;
- mettre à jour `manifests/CODEX_INBOX_STATE.json` pour les notes ChatGPT effectivement lues ;
- pousser les nouveaux code `.mq5/.mqh`, `.set`, manifests, synthèses JSON/CSV et handoffs utiles ;
- indiquer clairement ce qui continue réellement à tourner.

Si le quota tombe avant cette étape, le prochain `GO` doit réconcilier checkpoint + état réel du PC puis pousser le retard avant de lancer une nouvelle action conséquente.

## 6. Pas de spam périodique
Il n'existe pas de règle du type « push toutes les 30 minutes ». Si MiMo/MT5 calculent normalement et qu'aucune décision/transformation d'état n'a eu lieu, ne rien pousser juste pour produire de l'activité.

## 7. Rôle de MiMo dans l'envoi
MiMo peut préparer :
- synthèses JSON/CSV ;
- tableaux de résultats ;
- manifests ;
- inventaires/hashes ;
- draft de `HANDOFF.md` ;
- recherche de contradictions/anomalies.

MiMo ne décide pas seul qu'un résultat est prêt pour ChatGPT. Codex doit vérifier la cohérence, appliquer les gates, décider du statut, persister la décision, puis effectuer ou déclencher le commit/push GitHub.

Résumé recherche : **MiMo prépare le colis -> Codex vérifie/décide/persiste -> GitHub transporte -> ChatGPT audite/agit.**

## 8. États de lecture et de reprise
- `manifests/CHATGPT_INBOX_STATE.json` évite que ChatGPT retraite inutilement les mêmes livraisons Codex.
- `manifests/CODEX_INBOX_STATE.json` évite que Codex retraite inutilement les mêmes découvertes ChatGPT.
- `manifests/CODEX_SESSION_CHECKPOINT.json` est le dernier état partagé compact de reprise, pas une preuve qu'un processus tourne encore.
- Le checkpoint local + l'état réel du PC priment pour décider d'une relance.

## 9. Contenu à ne pas pousser
Ne pas versionner les fichiers massifs ou reproductibles : historiques ticks volumineux, bases MT5, caches, clones workers, gros rapports temporaires, exécutables intermédiaires. Les référencer par chemin local + SHA256 lorsque nécessaire.
