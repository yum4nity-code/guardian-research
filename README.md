# Guardian Research

Dépôt privé de recherche, validation, orchestration et intégration des stratégies Guardian.

## Reprise rapide

Toujours commencer par :

1. `CURRENT_PROJECT_HANDOFF.md`
2. `START_HERE_NEXT_AI.md`
3. le handoff daté canonique indiqué par `CURRENT_PROJECT_HANDOFF.md`
4. `docs/REPO_MAP.md`

L'état courant ne doit pas être reconstruit à partir des anciens handoffs, campagnes D0xx ou échanges Codex historiques.

## Source de vérité

- `D:\MT5_Backtests` reste le laboratoire local et conserve les gros historiques, ticks, clones MT5 et sorties volumineuses.
- GitHub est la source de vérité pour le code utile, protocoles, manifests, décisions, résultats synthétiques, receipts et handoffs.
- La branche `backtest-results` contient les publications de l'orchestrateur.
- `production/` ne doit pas être modifié par la recherche sans changement de production explicite et validé.
- `research/` contient les campagnes expérimentales et leur infrastructure.
- `candidates/` ne doit contenir que des stratégies ayant réellement franchi les gates de promotion applicables.
- `handoff/` conserve la continuité et la provenance; voir `handoff/README.md`.

## Règle de provenance

Le dépôt privilégie un nettoyage **non destructif** :
- un point d'entrée courant clair ;
- les anciens états archivés ;
- les résultats/receipts/protocoles historiques conservés ;
- pas de suppression d'évidence scientifique simplement parce qu'elle est ancienne ou négative.

Voir `docs/REPO_MAP.md` pour les conventions current / historical.

## Journal de travail

Toute IA/agent qui travaille matériellement sur Guardian un jour donné doit vérifier et mettre à jour `GUARDIAN_PROJECT_PLANNING_AND_TIMELOG.md` avant de terminer sa session ou de passer le relais.

- Journaliser le travail réellement effectué, les décisions/rejets importants et la prochaine action.
- Ne pas inventer du temps humain. Si la durée active n'est pas prouvable, utiliser un span observé / minimum observé / non quantifié.
- Les calculs/backtests autonomes ne comptent pas comme temps humain.
- Ne pas repousser cette obligation en supposant qu'un autre agent la fera plus tard.

## Documents structurants

- `CURRENT_PROJECT_HANDOFF.md` — état courant.
- `START_HERE_NEXT_AI.md` — reprise opérationnelle.
- `GUARDIAN_MASTER_MANDATE.md` — règles durables / architecture.
- `docs/RESEARCH_PROTOCOL.md` — discipline scientifique.
- `docs/REPO_MAP.md` — navigation du dépôt.
- `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md` — contrat de l'automatisation de recherche.
