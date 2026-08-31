# Instructions obligatoires pour Codex

Ce dépôt est la source de vérité partagée entre Codex et ChatGPT pour Guardian Research.

Avant toute action, lire et respecter :
1. `docs/CODEX_RESEARCH_DIRECTOR.md`
2. `docs/RESEARCH_PROTOCOL.md`
3. `docs/GO_PROTOCOL.md`
4. `docs/GITHUB_SYNC_POLICY.md`
5. `docs/AGENT_COMMUNICATION.md`
6. `manifests/CODEX_INBOX_STATE.json` puis toutes les notes ChatGPT non lues qu'il référence
7. `CURRENT_QUEUE.json`
8. `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md`

## Commande GO
Quand l'utilisateur dit simplement `GO` à Codex, cela signifie que le quota est revenu : reprendre le laboratoire immédiatement et de façon autonome selon `docs/GO_PROTOCOL.md`. Ne pas demander quoi faire si l'état du labo permet de le déterminer.

Au début de chaque `GO`, traiter d'abord la boîte ChatGPT -> Codex : lire `manifests/CODEX_INBOX_STATE.json`, ouvrir toutes les notes non lues sous `handoff/chatgpt_to_codex/`, intégrer leur contenu à la décision de session, puis marquer les notes comme lues après prise en compte.

## Frontière recherche / production
- Codex peut coder, casser et tester librement sous `research/` et dans `D:\MT5_Backtests\Research\`.
- Ne jamais utiliser `production/guardian/` comme laboratoire.
- Une stratégie ne passe dans `candidates/for_guardian/` qu'après les gates prévues et le red-team.
- ChatGPT audite/intègre dans Guardian production ; l'utilisateur compile, valide et déploie.

## Communication bidirectionnelle
Respecter `docs/AGENT_COMMUNICATION.md`.
- Codex -> ChatGPT : handoffs/candidats + `manifests/CHATGPT_INBOX_STATE.json` côté lecture ChatGPT.
- ChatGPT -> Codex : `handoff/chatgpt_to_codex/YYYY/MM/DD/` + `manifests/CODEX_INBOX_STATE.json` côté lecture Codex.
- Un item `WAITING_CODEX` dans `CURRENT_QUEUE.json` signifie qu'une action Codex est requise ; une note `INFO` peut être simplement assimilée sans créer de tâche.
- Une note `URGENT` liée à sécurité/exécution/régression Guardian prime sur une exploration secondaire.

## Synchronisation GitHub
Respecter `docs/GITHUB_SYNC_POLICY.md`. MiMo peut préparer les synthèses, manifests et drafts de handoff, mais Codex reste responsable de vérifier la cohérence, décider qu'un paquet mérite d'être envoyé, puis commit/push.

## Bootstrap initial obligatoire
Au premier passage sur ce dépôt :
- vérifier/créer les chemins locaux décrits dans le mandat ;
- cloner/synchroniser `yum4nity-code/guardian-research` ;
- lire et traiter la boîte `manifests/CODEX_INBOX_STATE.json` ;
- initialiser `CURRENT_QUEUE.json` à partir de l'état réel de `D:\MT5_Backtests` ;
- vérifier les workers/processus réellement actifs avant tout nouveau lancement ;
- vérifier localement les SHA256 de `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5` et `production/presets/FTMO_D017_v11_15_SAFE.set` contre `production/manifests/Guardian_D017_v11_15.json` ;
- ne pas chercher ni créer un diff v11.14 -> v11.15 : il n'est pas requis pour le bootstrap ou le fonctionnement normal.

Ne jamais remplacer une preuve réelle par une supposition ou un résumé non vérifié.
