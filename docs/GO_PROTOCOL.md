# Protocole de la commande `GO`

`GO` est une commande opérationnelle courte. Elle ne demande pas de clarification : elle déclenche immédiatement la routine prévue pour l'agent concerné.

## Quand l'utilisateur dit `GO` à Codex

Cela signifie : **le quota Codex est revenu ; reprendre le labo maintenant de façon autonome**.

Codex doit, dans cet ordre :

1. Lire `manifests/CODEX_INBOX_STATE.json` et toutes les notes ChatGPT non lues sous `handoff/chatgpt_to_codex/`. Une note `URGENT` Guardian prime sur l'exploration ; une note `ACTION_REQUISE` doit être reflétée dans `CURRENT_QUEUE.json` sans créer de doublon ; une note `INFO` doit être assimilée sans forcément créer de tâche.
2. Lire `docs/RESEARCH_STATUS.md`, `docs/STRATEGY_DECISIONS.md`, `CURRENT_QUEUE.json`, le dernier `PLAN.md` actif et le dernier handoff pertinent.
3. Vérifier les processus/workers MT5 réellement actifs et les tâches MiMo déjà lancées. Ne jamais créer de doublon.
4. Récolter en priorité tous les résultats MiMo/MT5 terminés depuis la dernière session, les normaliser et mettre à jour `CURRENT_QUEUE.json`.
5. Marquer dans `manifests/CODEX_INBOX_STATE.json` les notes ChatGPT effectivement lues/prises en compte afin de ne pas les retraiter au prochain `GO`.
6. Exécuter **l'action READY de priorité la plus élevée** dans la file, sauf urgence Guardian ou action `WAITING_CODEX` devenue prioritaire après lecture de l'inbox. Ne pas demander à l'utilisateur quoi faire si la suite est déjà déterminable par l'état du labo.
7. Si la priorité principale attend encore un calcul sain, ne pas gaspiller le quota à la surveiller : passer à la prochaine action non conflictuelle utile.
8. Si aucune action READY n'existe, sélectionner la meilleure hypothèse suivante selon le mandat, créer/pré-enregistrer son plan, puis lancer le cheap-fail approprié.
9. Utiliser Codex pour l'orchestration, les décisions et le code de recherche ; déléguer les travaux longs/répétitifs à MiMo et l'exécution quantitative aux workers MT5.
10. Avant de terminer sa fenêtre, laisser au moins une charge longue utile à MiMo/MT5 si possible, puis mettre à jour `CURRENT_QUEUE.json`, `RESEARCH_STATUS.md` et `STRATEGY_DECISIONS.md` lorsque nécessaire.
11. Si quelque chose nécessite ChatGPT (candidat Guardian, anomalie produit, audit méthodologique, question d'intégration), créer/mettre à jour le handoff du jour avec les chemins exacts et signaler `WAITING_CHATGPT` lorsque son action est requise. Sinon, ne pas produire de handoff vide.

En résumé : **`GO` = lire l'inbox ChatGPT -> récolter -> décider -> reprendre la meilleure action -> déléguer les calculs -> laisser une trace propre.**

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

Le protocole détaillé de communication bidirectionnelle est défini dans `docs/AGENT_COMMUNICATION.md`.
