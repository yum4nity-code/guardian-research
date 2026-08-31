# Protocole de la commande `GO`

`GO` est une commande opérationnelle courte. Elle ne demande pas de clarification : elle déclenche immédiatement la routine prévue pour l'agent concerné.

## Quand l'utilisateur dit `GO` à Codex

Cela signifie : **le quota Codex est revenu ; reprendre le labo maintenant de façon autonome**.

Codex doit, dans cet ordre :

1. Synchroniser le repo GitHub.
2. Lire `manifests/CODEX_INBOX_STATE.json` et toutes les notes ChatGPT non lues sous `handoff/chatgpt_to_codex/`. Une note `URGENT` Guardian prime sur l'exploration ; une note `ACTION_REQUISE` doit être reflétée dans `CURRENT_QUEUE.json` sans doublon ; une note `INFO` doit être assimilée sans forcément créer de tâche.
3. Lire le checkpoint local `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` s'il existe, puis `manifests/CODEX_SESSION_CHECKPOINT.json` comme dernier état partagé. Appliquer `docs/INTERRUPTION_RECOVERY.md`.
4. **Si aucun checkpoint local n'existe encore et que le bootstrap initial n'est pas terminé, créer immédiatement un checkpoint minimal `BOOTSTRAP_IN_PROGRESS` avant tout audit/inventaire long ou parallèle.** Il doit au minimum dire que le bootstrap est en cours, qu'aucun nouveau job ne doit être lancé avant réconciliation et que `next_safe_action=inspect_real_machine_state`.
5. Lire `docs/RESEARCH_STATUS.md`, `docs/STRATEGY_DECISIONS.md`, `CURRENT_QUEUE.json`, le dernier `PLAN.md` actif et le dernier handoff pertinent.
6. Vérifier les processus/workers MT5 réellement actifs, les tâches MiMo déjà lancées, les logs/statuts et les résultats présents. **Le réel prime sur le checkpoint et la queue s'ils sont anciens.** Ne jamais créer de doublon ni relancer depuis un simple statut.
7. Récolter en priorité tous les résultats MiMo/MT5 terminés depuis la dernière session, les normaliser et mettre à jour checkpoint + `CURRENT_QUEUE.json`.
8. Marquer dans `manifests/CODEX_INBOX_STATE.json` les notes ChatGPT effectivement lues/prises en compte afin de ne pas les retraiter au prochain `GO`.
9. Si GitHub était en retard à cause d'une interruption précédente, pousser l'état récupéré/cohérent avant de lancer une nouvelle étape conséquente.
10. Exécuter **l'action READY de priorité la plus élevée** dans la file, sauf urgence Guardian ou action `WAITING_CODEX` devenue prioritaire après lecture de l'inbox. Ne pas demander à l'utilisateur quoi faire si la suite est déterminable.
11. Avant toute transition importante ou lancement d'une opération longue/conséquente, appliquer le checkpoint transactionnel : **décider -> persister -> agir**. Écrire l'intention, les IDs/chemins et la prochaine action sûre avant de lancer ce qui pourrait survivre à la fenêtre Codex.
12. Si la priorité principale attend encore un calcul sain, ne pas gaspiller le quota à la surveiller : passer à la prochaine action non conflictuelle utile.
13. Si aucune action READY n'existe, sélectionner la meilleure hypothèse suivante selon le mandat, créer/pré-enregistrer son plan, checkpoint-er, puis lancer le cheap-fail approprié.
14. Utiliser Codex pour l'orchestration, les décisions et le code de recherche ; déléguer les travaux longs/répétitifs à MiMo et l'exécution quantitative aux workers MT5.
15. Après chaque jalon à forte valeur (verdict, candidat, anomalie Guardian, nouvelle campagne longue lancée, changement majeur de queue, handoff), persister immédiatement l'état et synchroniser les petits artefacts utiles sur GitHub. Ne pas attendre volontairement la fin du quota.
16. Avant de terminer sa fenêtre, laisser au moins une charge longue utile à MiMo/MT5 si possible, puis mettre à jour checkpoint, `CURRENT_QUEUE.json`, `RESEARCH_STATUS.md` et `STRATEGY_DECISIONS.md` lorsque nécessaire.
17. Si quelque chose nécessite ChatGPT (candidat Guardian, anomalie produit, audit méthodologique, question d'intégration), créer/mettre à jour le handoff du jour avec les chemins exacts et signaler `WAITING_CHATGPT` lorsque son action est requise. Sinon, ne pas produire de handoff vide.

En résumé : **`GO` = inbox -> checkpoint minimal si nécessaire -> checkpoint courant -> état réel -> récolter -> décider -> persister -> agir -> synchroniser les jalons -> laisser une trace récupérable.**

## Si le quota tombe brutalement

Le travail local et les workers ne sont pas supposés disparaître. Au prochain `GO`, Codex doit reprendre depuis le checkpoint local + l'état réel du PC, réconcilier, récolter et pousser ce qui n'avait pas pu être synchronisé.

Si la coupure survient pendant le **premier bootstrap avant la création du premier checkpoint**, la reprise doit rester conservatrice : synchroniser, lire l'inbox, constater l'absence de checkpoint, créer immédiatement `BOOTSTRAP_IN_PROGRESS`, inspecter la machine réelle et ne lancer aucun nouveau travail avant réconciliation.

Une décision importante restée uniquement dans la conversation de Codex et non écrite est considérée comme une erreur de procédure.

## Quand l'utilisateur dit `GO` à ChatGPT

Cela signifie : **vérifier immédiatement si Codex a envoyé de nouveaux éléments sur `yum4nity-code/guardian-research` et traiter ce qui attend ChatGPT**.

ChatGPT doit :

1. Lire `CURRENT_QUEUE.json` et `manifests/CHATGPT_INBOX_STATE.json`.
2. Vérifier les nouveaux/derniers éléments sous `handoff/YYYY/MM/DD/`, `candidates/for_guardian/`, ainsi que les modifications pertinentes de `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md`.
3. Identifier ce qui est nouveau depuis le dernier passage ChatGPT : nouveau candidat, nouveau handoff, nouvelle décision, demande d'audit ou anomalie Guardian.
4. S'il n'y a rien de nouveau pour ChatGPT, répondre simplement qu'aucun nouvel élément ne nécessite d'action.
5. S'il y a du nouveau, lire les preuves et artefacts associés, puis effectuer l'action demandée : audit, critique méthodologique, revue du code, intégration Guardian, préparation d'une nouvelle version, etc.
6. Ne jamais considérer le résumé Codex comme une preuve suffisante si les artefacts bruts/synthétiques référencés sont disponibles : vérifier les éléments nécessaires indépendamment.
7. Après traitement, mettre à jour `manifests/CHATGPT_INBOX_STATE.json` afin de marquer les éléments examinés et éviter de retraiter inutilement la même livraison.
8. Si l'audit ChatGPT produit une découverte qui doit être connue de Codex, publier immédiatement une note sous `handoff/chatgpt_to_codex/YYYY/MM/DD/`, l'ajouter à `manifests/CODEX_INBOX_STATE.json`, et ajouter `WAITING_CODEX` à `CURRENT_QUEUE.json` uniquement si une action Codex est réellement nécessaire.

En résumé : **`GO` à ChatGPT = ouvrir la boîte de réception GitHub Codex -> détecter le nouveau -> auditer/agir -> marquer comme traité -> renvoyer à Codex toute découverte utile.**

## Règle de priorité partagée

La production Guardian et les décisions de déploiement ne doivent jamais être bloquées par une exploration secondaire. Un problème de sécurité/exécution/régression Guardian passe avant une nouvelle recherche. Hors urgence produit, Codex reste concentré sur la recherche et ChatGPT sur l'audit/intégration des éléments qui lui sont transmis.

Le protocole détaillé de communication bidirectionnelle est défini dans `docs/AGENT_COMMUNICATION.md`. La reprise après interruption est définie dans `docs/INTERRUPTION_RECOVERY.md`.
