# Guardian Research

Dépôt privé de coordination entre Codex, MiMo/MT5 et ChatGPT pour la recherche, la validation et l'intégration des stratégies Guardian.

## Reprise rapide

**Toujours commencer par `CURRENT_PROJECT_HANDOFF.md`.** Il contient l'état courant validé, les composants live, la version active et la prochaine action sûre. Il doit être mis à jour après chaque jalon matériel afin qu'une nouvelle instance puisse reprendre sans dépendre de l'historique de conversation.

## Obligation quotidienne de journal de travail

**Toute IA/agent qui travaille matériellement sur Guardian un jour donné doit vérifier et mettre à jour `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` pour cette date avant de terminer sa session ou de passer le relais.** Cette règle s'applique à ChatGPT, Codex et à toute future IA entrant dans le dépôt.

- Journaliser le travail réellement effectué, les décisions/rejets importants et la prochaine action.
- Journaliser le temps humain de façon conservatrice ; si la durée active exacte n'est pas prouvable, utiliser un span observé / minimum observé / non quantifié plutôt que d'inventer.
- Les backtests, collectors et calculs tournant seuls ne comptent pas comme temps humain et doivent rester séparés.
- Au début d'une reprise, vérifier si la date courante possède déjà une entrée ; si du travail matériel a eu lieu et qu'elle manque, la créer avant la fin de la session.
- Cette obligation quotidienne ne doit pas être repoussée en supposant qu'une autre IA s'en chargera plus tard.

## Principe

- `D:\MT5_Backtests` reste le laboratoire local et conserve les gros historiques, ticks, clones MT5 et sorties volumineuses.
- GitHub est la source de vérité pour le code utile, les `.set`, manifests, résultats synthétiques, décisions et handoffs.
- `production/` contient la branche Guardian de production et ne doit pas être modifiée par la recherche sans handoff explicite.
- `research/` est libre pour Codex/MiMo et les campagnes expérimentales.
- `candidates/for_guardian/` contient uniquement les stratégies ayant franchi les gates de validation.
- `handoff/YYYY/MM/DD/` est l'interface formelle Codex -> ChatGPT.

Voir `AGENTS.md`, `CURRENT_PROJECT_HANDOFF.md`, `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md`, `docs/CODEX_RESEARCH_DIRECTOR.md` et `docs/RESEARCH_PROTOCOL.md`.
