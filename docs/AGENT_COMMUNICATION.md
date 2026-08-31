# Communication bidirectionnelle Codex <-> ChatGPT

GitHub est l'interface de communication persistante entre Codex et ChatGPT. Aucun agent ne doit dépendre de la mémoire d'une conversation pour transmettre une découverte importante à l'autre.

## Canaux

### Codex -> ChatGPT
- État de lecture ChatGPT : `manifests/CHATGPT_INBOX_STATE.json`
- Handoffs : `handoff/YYYY/MM/DD/` et `candidates/for_guardian/`
- Signal de file : item `WAITING_CHATGPT` dans `CURRENT_QUEUE.json` lorsque l'intervention de ChatGPT est réellement nécessaire.

### ChatGPT -> Codex
- État de lecture Codex : `manifests/CODEX_INBOX_STATE.json`
- Notes : `handoff/chatgpt_to_codex/YYYY/MM/DD/`
- Signal de file : item `WAITING_CODEX` dans `CURRENT_QUEUE.json` lorsqu'une action Codex est réellement demandée.

## Quand ChatGPT doit écrire à Codex
ChatGPT publie une note lorsqu'il découvre quelque chose qui peut modifier le travail du labo ou éviter une erreur :
- faiblesse ou anomalie du Guardian de production ;
- contrainte de compatibilité/migration entre versions ;
- fait nouveau qui change une hypothèse ou un protocole de recherche ;
- correction méthodologique ;
- décision d'intégration qui implique un futur travail de recherche ;
- élément que Codex doit vérifier localement sur le PC/MT5.

Une observation purement cosmétique ou sans conséquence n'a pas besoin d'être transmise.

## Format minimal ChatGPT -> Codex
Chaque note doit contenir :
- `STATUT` : INFO / ACTION_REQUISE / URGENT ;
- `CONSTAT` : ce qui a été trouvé ;
- `PREUVE` : code, logs, commit, chemin ou élément vérifié ;
- `IMPACT` : ce que cela change ;
- `ACTION_CODEX` : aucune, vérifier, tester, corriger en branche research, etc. ;
- `NE_PAS_FAIRE` si une action dangereuse doit être explicitement évitée.

Si aucune action n'est nécessaire, la note reste `INFO` et ne doit pas polluer `CURRENT_QUEUE.json`.

## Routine Codex
Au début de chaque session et de chaque `GO`, Codex doit :
1. lire `manifests/CODEX_INBOX_STATE.json` ;
2. ouvrir toutes les notes ChatGPT non lues référencées ;
3. intégrer leur contenu avant de choisir une nouvelle action ;
4. si une note demande une action, la refléter dans `CURRENT_QUEUE.json` sans dupliquer un item existant ;
5. après lecture/prise en compte, mettre à jour `CODEX_INBOX_STATE.json` pour éviter de retraiter inutilement la même note.

Une note `URGENT` liée à sécurité/exécution/régression Guardian passe avant une exploration secondaire.

## Routine ChatGPT
Lorsqu'il découvre un élément utile à Codex, ChatGPT doit publier la note sans attendre un `GO` de Codex. Il met ensuite `CODEX_INBOX_STATE.json` à jour avec la note non lue. Si une action concrète est nécessaire, il peut aussi ajouter ou signaler un item `WAITING_CODEX` dans `CURRENT_QUEUE.json`.

## Principe
**Codex et ChatGPT ne se parlent pas par supposition : ils se parlent par GitHub, avec état de lecture et preuves.**
