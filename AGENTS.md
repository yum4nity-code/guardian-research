# Instructions obligatoires pour Codex

Ce dépôt est la source de vérité partagée entre Codex et ChatGPT pour Guardian Research.

## Accès machine
Codex est autorisé à utiliser **l'ensemble du PC** pour les besoins du projet : tous les disques accessibles, processus, terminaux MT5, MetaEditor, AppData, outils, scripts et fichiers nécessaires. `D:\MT5_Backtests\` est le répertoire canonique du laboratoire, **pas une limite d'accès ni une sandbox**. Les restrictions ci-dessous concernent la séparation logique recherche/production, pas les droits d'accès au système.

### Lecture des protocoles
Au **premier bootstrap**, lire intégralement et comprendre :
1. `CURRENT_PROJECT_HANDOFF.md`
2. `docs/CODEX_RESEARCH_DIRECTOR.md`
3. `docs/RESEARCH_PROTOCOL.md`
4. `docs/GO_PROTOCOL.md`
5. `docs/GITHUB_SYNC_POLICY.md`
6. `docs/AGENT_COMMUNICATION.md`
7. `docs/INTERRUPTION_RECOVERY.md`
8. `manifests/CODEX_INBOX_STATE.json` puis les notes ChatGPT non lues qu'il référence
9. le checkpoint local `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` s'il existe, puis `manifests/CODEX_SESSION_CHECKPOINT.json`
10. `CURRENT_QUEUE.json`
11. `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md`

`CURRENT_PROJECT_HANDOFF.md` est le point d'entrée canonique de reprise rapide. Il doit refléter la version active, les composants réellement live, les gates récemment validés, les contraintes de sécurité/science et la prochaine action sûre.

Après bootstrap terminé, ne pas relire intégralement les six protocoles statiques à chaque `GO` s'ils n'ont pas changé. Le `GO` normal doit privilégier les fichiers dynamiques : `CURRENT_PROJECT_HANDOFF.md`, inbox, checkpoint, queue, statut, décisions, plan/handoff actifs et état réel du PC. Rouvrir un protocole statique seulement s'il a changé, si le checkpoint indique qu'il n'a jamais été assimilé, ou si une ambiguïté opérationnelle l'exige.

## Commande GO
Quand l'utilisateur dit simplement `GO` à Codex, cela signifie que le quota est revenu : reprendre le laboratoire immédiatement et de façon autonome selon `docs/GO_PROTOCOL.md`. Ne pas demander quoi faire si l'état du labo permet de le déterminer.

### Priorité absolue tant que le premier bootstrap est incomplet
Si le checkpoint indique `BOOTSTRAP_IN_PROGRESS`, si aucun checkpoint de bootstrap complet n'existe, ou si la mission/répartition des rôles n'a pas encore été entièrement assimilée, la **première tâche du prochain `GO` est de terminer le bootstrap et de comprendre/reconstruire la mission**, pas de commencer la recherche ni d'exécuter les audits secondaires présents dans l'inbox.

Pendant ce bootstrap incomplet :
- synchroniser et **trier** l'inbox, mais ne pas approfondir chaque note secondaire ;
- ne lancer aucune nouvelle campagne MT5, tâche MiMo, modification de stratégie ou exploration ;
- terminer d'abord la compréhension des rôles, la réconciliation du repo, du checkpoint, de la queue et de l'état réel de la machine ;
- reprendre au `next_safe_action` du checkpoint au lieu de recommencer tout le bootstrap ;
- une urgence Guardian ne préempte le bootstrap que si elle concerne un risque actif immédiat sur une instance en cours ; dans ce cas faire le minimum de sécurisation, persister, puis revenir au bootstrap.

Le bootstrap n'est déclaré `BOOTSTRAP_COMPLETE` qu'une fois au minimum : mission/rôles assimilés, repo local synchronisé, checkpoint durable créé, queue réconciliée, processus/workers/MiMo/MT5 réels inventoriés, chemins/outils principaux localisés et état production/candidats compris. Ensuite seulement commence le fonctionnement autonome normal.

## Résistance aux coupures de quota
Aucune décision importante ne doit rester uniquement dans le contexte conversationnel.

Appliquer `docs/INTERRUPTION_RECOVERY.md` avec la règle : **décider -> persister -> agir**.

Avant une transition importante ou le lancement d'une opération longue/conséquente, mettre à jour le checkpoint local `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json`. Après un jalon à forte valeur, synchroniser les petits artefacts utiles sur GitHub sans attendre volontairement la fin du quota.

**Règle de continuité conversationnelle :** après tout jalon matériel — nouvelle version active, compilation/déploiement validé par l'utilisateur, gate PASS/FAIL, changement d'architecture, nouveau composant live, changement de prochaine action sûre — mettre à jour `CURRENT_PROJECT_HANDOFF.md` dans la même session. Aucun état courant important ne doit exister uniquement dans une conversation ChatGPT/Codex.

**Cas spécial premier bootstrap :** si aucun `SESSION_CHECKPOINT.json` n'existe encore, ne pas attendre la fin de l'inventaire réel. Après synchronisation + lecture des protocoles + inbox, créer immédiatement un checkpoint minimal `BOOTSTRAP_IN_PROGRESS` avant les audits/inventaires longs, avec `no_new_jobs_launched=true` et `next_safe_action=inspect_real_machine_state`. L'enrichir ensuite à mesure que les preuves réelles arrivent.

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
- Une note `URGENT` liée à sécurité/exécution/régression Guardian prime sur une exploration secondaire, mais pendant un bootstrap incomplet elle ne doit détourner la reprise que si le risque est actif et immédiat.

## Synchronisation GitHub
Respecter `docs/GITHUB_SYNC_POLICY.md`. MiMo peut préparer les synthèses, manifests et drafts de handoff, mais Codex reste responsable de vérifier la cohérence, décider qu'un paquet mérite d'être envoyé, puis commit/push.

## Bootstrap initial obligatoire
Au premier passage sur ce dépôt :
- vérifier/créer les chemins locaux décrits dans le mandat ;
- cloner/synchroniser `yum4nity-code/guardian-research` ;
- lire d'abord `CURRENT_PROJECT_HANDOFF.md` pour récupérer l'état courant ;
- lire et **trier** la boîte `manifests/CODEX_INBOX_STATE.json` sans laisser les audits secondaires interrompre la compréhension initiale de la mission ;
- si aucun checkpoint local n'existe, créer **immédiatement** le checkpoint minimal `BOOTSTRAP_IN_PROGRESS` avant tout inventaire/audit long ;
- inspecter ensuite l'état réel du projet et enrichir/réconcilier `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` ;
- initialiser/réconcilier `CURRENT_QUEUE.json` à partir de l'état réel du projet ;
- inspecter l'ensemble du PC si nécessaire pour localiser terminaux MT5, MetaEditor, MiMo, workers, processus, dépôts, logs et sorties ;
- vérifier les workers/processus réellement actifs avant tout nouveau lancement ;
- vérifier localement les SHA256 de `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5` et `production/presets/FTMO_D017_v11_15_SAFE.set` contre `production/manifests/Guardian_D017_v11_15.json` ;
- ne pas chercher ni créer un diff v11.14 -> v11.15 : il n'est pas requis pour le bootstrap ou le fonctionnement normal ;
- persister explicitement `BOOTSTRAP_COMPLETE` et la prochaine action sûre lorsque cette initialisation est réellement terminée.

Ne jamais remplacer une preuve réelle par une supposition ou un résumé non vérifié.
