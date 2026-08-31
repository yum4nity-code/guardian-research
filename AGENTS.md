# Instructions obligatoires pour Codex

Ce dépôt est la source de vérité partagée entre Codex et ChatGPT pour Guardian Research.

## Accès machine
Codex est autorisé à utiliser **l'ensemble du PC** pour les besoins du projet : tous les disques accessibles, processus, terminaux MT5, MetaEditor, AppData, outils, scripts et fichiers nécessaires. `D:\MT5_Backtests\` est le répertoire canonique du laboratoire, **pas une limite d'accès ni une sandbox**. Les restrictions ci-dessous concernent la séparation logique recherche/production, pas les droits d'accès au système.

Avant toute action, lire et respecter :
1. `docs/CODEX_RESEARCH_DIRECTOR.md`
2. `docs/RESEARCH_PROTOCOL.md`
3. `docs/GO_PROTOCOL.md`
4. `docs/GITHUB_SYNC_POLICY.md`
5. `docs/AGENT_COMMUNICATION.md`
6. `docs/INTERRUPTION_RECOVERY.md`
7. `manifests/CODEX_INBOX_STATE.json` puis toutes les notes ChatGPT non lues qu'il référence
8. le checkpoint local `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` s'il existe, puis `manifests/CODEX_SESSION_CHECKPOINT.json`
9. `CURRENT_QUEUE.json`
10. `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md`

## Commande GO
Quand l'utilisateur dit simplement `GO` à Codex, cela signifie que le quota est revenu : reprendre le laboratoire immédiatement et de façon autonome selon `docs/GO_PROTOCOL.md`. Ne pas demander quoi faire si l'état du labo permet de le déterminer.

Au début de chaque `GO`, traiter d'abord la boîte ChatGPT -> Codex, puis le checkpoint d'interruption, puis réconcilier ces informations avec l'état réel du PC avant toute relance.

## Résistance aux coupures de quota
Aucune décision importante ne doit rester uniquement dans le contexte conversationnel.

Appliquer `docs/INTERRUPTION_RECOVERY.md` avec la règle : **décider -> persister -> agir**.

Avant une transition importante ou le lancement d'une opération longue/conséquente, mettre à jour le checkpoint local `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json`. Après un jalon à forte valeur, synchroniser les petits artefacts utiles sur GitHub sans attendre volontairement la fin du quota.

Au prochain réveil, ne jamais relancer depuis le checkpoint seul : vérifier d'abord processus, workers, MiMo, logs et résultats réels sur l'ensemble du PC. Le réel prime sur un statut ancien.

## Frontière recherche / production
- Codex peut coder, casser et tester librement sous `research/` et dans le labo de recherche local.
- Il peut inspecter et utiliser les installations/fichiers nécessaires où qu'ils se trouvent sur le PC.
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
- créer/réconcilier `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` avec l'état réel du labo ;
- initialiser `CURRENT_QUEUE.json` à partir de l'état réel du projet ;
- inspecter l'ensemble du PC si nécessaire pour localiser terminaux MT5, MetaEditor, MiMo, workers, processus, dépôts, logs et sorties ;
- vérifier les workers/processus réellement actifs avant tout nouveau lancement ;
- vérifier localement les SHA256 de `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5` et `production/presets/FTMO_D017_v11_15_SAFE.set` contre `production/manifests/Guardian_D017_v11_15.json` ;
- ne pas chercher ni créer un diff v11.14 -> v11.15 : il n'est pas requis pour le bootstrap ou le fonctionnement normal.

Ne jamais remplacer une preuve réelle par une supposition ou un résumé non vérifié.
