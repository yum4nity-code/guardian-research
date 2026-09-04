# Guardian Research

Dépôt privé de coordination entre Codex, MiMo/MT5 et ChatGPT pour la recherche, la validation et l'intégration des stratégies Guardian.

## Reprise rapide

**Toujours commencer par `CURRENT_PROJECT_HANDOFF.md`.** Il contient l'état courant validé, les composants live, la version active et la prochaine action sûre. Il doit être mis à jour après chaque jalon matériel afin qu'une nouvelle instance puisse reprendre sans dépendre de l'historique de conversation.

## Principe

- `D:\MT5_Backtests` reste le laboratoire local et conserve les gros historiques, ticks, clones MT5 et sorties volumineuses.
- GitHub est la source de vérité pour le code utile, les `.set`, manifests, résultats synthétiques, décisions et handoffs.
- `production/` contient la branche Guardian de production et ne doit pas être modifiée par la recherche sans handoff explicite.
- `research/` est libre pour Codex/MiMo et les campagnes expérimentales.
- `candidates/for_guardian/` contient uniquement les stratégies ayant franchi les gates de validation.
- `handoff/YYYY/MM/DD/` est l'interface formelle Codex -> ChatGPT.

Voir `CURRENT_PROJECT_HANDOFF.md`, `docs/CODEX_RESEARCH_DIRECTOR.md` et `docs/RESEARCH_PROTOCOL.md`.
