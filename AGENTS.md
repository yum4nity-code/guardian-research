# Instructions obligatoires pour Codex

Ce dépôt est la source de vérité partagée entre Codex et ChatGPT pour Guardian Research.

Avant toute action, lire et respecter :
1. `docs/CODEX_RESEARCH_DIRECTOR.md`
2. `docs/RESEARCH_PROTOCOL.md`
3. `docs/GO_PROTOCOL.md`
4. `docs/GITHUB_SYNC_POLICY.md`
5. `CURRENT_QUEUE.json`
6. `docs/RESEARCH_STATUS.md` et `docs/STRATEGY_DECISIONS.md`

## Commande GO
Quand l'utilisateur dit simplement `GO` à Codex, cela signifie que le quota est revenu : reprendre le laboratoire immédiatement et de façon autonome selon `docs/GO_PROTOCOL.md`. Ne pas demander quoi faire si l'état du labo permet de le déterminer.

## Frontière recherche / production
- Codex peut coder, casser et tester librement sous `research/` et dans `D:\MT5_Backtests\Research\`.
- Ne jamais utiliser `production/guardian/` comme laboratoire.
- Une stratégie ne passe dans `candidates/for_guardian/` qu'après les gates prévues et le red-team.
- ChatGPT audite/intègre dans Guardian production ; l'utilisateur compile, valide et déploie.

## Synchronisation GitHub
Respecter `docs/GITHUB_SYNC_POLICY.md`. MiMo peut préparer les synthèses, manifests et drafts de handoff, mais Codex reste responsable de vérifier la cohérence, décider qu'un paquet mérite d'être envoyé, puis commit/push.

## Bootstrap initial obligatoire
Au premier passage sur ce dépôt :
- vérifier/créer les chemins locaux décrits dans le mandat ;
- cloner/synchroniser `yum4nity-code/guardian-research` ;
- initialiser `CURRENT_QUEUE.json` à partir de l'état réel de `D:\MT5_Backtests` ;
- mirrorer dans `production/guardian/` le fichier local exact `Guardian_D017_PropFirmAuto_v11_15.mq5` si disponible ;
- mirrorer le diff exact `Guardian_v11_14_to_v11_15.diff` ;
- vérifier les SHA256 contre `production/manifests/Guardian_D017_v11_15.json` avant commit.

Ne jamais remplacer une preuve réelle par une supposition ou un résumé non vérifié.
