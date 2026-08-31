# Politique de synchronisation GitHub

GitHub sert de source de vérité compacte entre Codex et ChatGPT. Le labo lourd reste local sous `D:\MT5_Backtests`.

Le protocole de communication bidirectionnelle est défini dans `docs/AGENT_COMMUNICATION.md`.

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
- vérification/test qui nécessite l'accès local de Codex à MT5/au PC.

La note est créée sous `handoff/chatgpt_to_codex/YYYY/MM/DD/` et référencée dans `manifests/CODEX_INBOX_STATE.json` comme non lue.

Si aucune action Codex n'est nécessaire, la note reste `INFO` et ne crée pas d'item de queue. Si une action est réellement requise, ChatGPT peut ajouter/signaler un item `WAITING_CODEX` dans `CURRENT_QUEUE.json`.

## 3. Push normal — jalon de recherche
Synchroniser dans la session lorsqu'une campagne importante se termine ou lorsqu'une stratégie change d'état : `VALIDATED`, `REJECTED`, nouvelle hypothèse formelle, nouveau plan de campagne, résultat de robustesse/red-team qui change la décision.

Pas besoin de pousser chaque sortie intermédiaire.

## 4. Push obligatoire — fin de GO / fin de fenêtre Codex
Avant de terminer chaque fenêtre de quota ou cycle `GO`, Codex doit au minimum :
- mettre à jour `CURRENT_QUEUE.json` avec l'état réel ;
- mettre à jour `docs/RESEARCH_STATUS.md` ;
- mettre à jour `docs/STRATEGY_DECISIONS.md` si une décision a changé ;
- mettre à jour `manifests/CODEX_INBOX_STATE.json` pour les notes ChatGPT effectivement lues ;
- pousser les nouveaux code `.mq5/.mqh`, `.set`, manifests, synthèses JSON/CSV et handoffs utiles ;
- laisser les gros ticks, caches, clones et logs massifs sur `D:` ;
- indiquer clairement ce qui continue réellement à tourner.

## 5. Pas de spam périodique
Il n'existe pas de règle du type « push toutes les 30 minutes ». Si MiMo/MT5 calculent normalement et qu'aucune décision n'a changé, ne rien pousser juste pour produire de l'activité.

## 6. Rôle de MiMo dans l'envoi
MiMo peut préparer :
- synthèses JSON/CSV ;
- tableaux de résultats ;
- manifests ;
- inventaires/hashes ;
- draft de `HANDOFF.md` ;
- recherche de contradictions/anomalies.

MiMo ne décide pas seul qu'un résultat est prêt pour ChatGPT. Codex doit vérifier la cohérence, appliquer les gates, décider du statut, puis effectuer ou déclencher le commit/push GitHub.

Résumé recherche : **MiMo prépare le colis -> Codex vérifie et décide -> GitHub transporte -> ChatGPT audite/agit.**

## 7. États de lecture
- `manifests/CHATGPT_INBOX_STATE.json` évite que ChatGPT retraite inutilement les mêmes livraisons Codex.
- `manifests/CODEX_INBOX_STATE.json` évite que Codex retraite inutilement les mêmes découvertes ChatGPT.
- Les deux fichiers sont des états de lecture, pas des substituts aux preuves ni à `CURRENT_QUEUE.json`.

## 8. Contenu à ne pas pousser
Ne pas versionner les fichiers massifs ou reproductibles : historiques ticks volumineux, bases MT5, caches, clones workers, gros rapports temporaires, exécutables intermédiaires. Les référencer par chemin local + SHA256 lorsque nécessaire.
