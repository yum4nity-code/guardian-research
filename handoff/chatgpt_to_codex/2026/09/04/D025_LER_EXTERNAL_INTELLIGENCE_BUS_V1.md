# D025 / Guardian External Intelligence Bus V1

STATUT: ACTION_REQUISE
DATE: 2026-09-04

## CONSTAT

L'utilisateur veut ajouter une troisieme strategie mid-term `Liquidity Exhaustion Reclaim (LER)` et autorise explicitement Guardian a recevoir des donnees externes pour enrichir ses decisions, notamment sur crypto.

Le concept retenu n'est pas "acheter une grosse meche" mais : niveau objectif preexistant -> sweep/cascade -> pression extreme -> impact marginal decroissant/exhaustion -> reclaim -> acceptance/retest -> signal virtuel. La couche externe vise surtout a mesurer le deleveraging crypto avec spot/perp, open interest et liquidations.

Le preregistration complet est dans :
`research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`

## PREUVE

- Guardian v11.17.04 actuel ne contient pas de `WebRequest`, pas de donnees spot/perp, OI ou liquidations externes.
- La ligne live utilisateur est distincte du labo; ne pas modifier silencieusement `production/guardian/` pour cette recherche.
- Architecture du repo impose IDEA -> RESEARCH -> PROTOTYPE -> BACKTEST -> ROBUSTNESS -> RED TEAM -> candidate avant integration.

## IMPACT

Le prochain jalon ne doit PAS etre un nouveau moteur qui trade. Il faut d'abord construire une infrastructure externe minimale, rejouable et auditable. Cette brique pourra ensuite servir a D025 et, plus tard, a d'autres strategies sans rendre Guardian dependant d'Internet.

## ACTION_CODEX

Construire `GUARDIAN-EXTERNAL-INTELLIGENCE-BUS-V1` en branche/repertoire research uniquement.

### Scope strict V1

1. Un petit collecteur local, lecture seule, sans permission de trading.
2. BTC et ETH seulement pour le smoke test.
3. Architecture adapters/provider-agnostic; utiliser des sources publiques fiables disponibles sur la machine pour obtenir autant que possible :
   - spot price;
   - perpetual price;
   - open interest;
   - liquidations long/short;
   - funding.
4. Normaliser chaque observation avec :
   - instrument canonique;
   - source/provider;
   - timestamp source UTC;
   - timestamp reception UTC;
   - valeur;
   - unite;
   - age/staleness;
   - sequence/id si disponible.
5. Enregistrer dans un format compact et rejouable (JSONL/CSV/Parquet selon justification). Les gros historiques restent sous `D:\MT5_Backtests`; GitHub recoit schema, code, petit sample, manifest et tests.
6. Gerer reconnexion, deduplication et trous de flux sans inventer de donnees.
7. Produire un `health/status` explicite : OK / STALE / PARTIAL / DOWN.
8. Aucun appel de trading MT5 et aucune cle API avec droit de trading.
9. Ne pas integrer encore le score LER dans Guardian production.
10. Ne pas coder de seuils de trading D025 a partir d'un premier echantillon.

### Gates avant etape suivante

- 30+ minutes de collecte BTC+ETH sans duplication majeure;
- timestamps UTC coherents;
- coupure/reconnexion testee;
- staleness detectable;
- fichier rejouable;
- petit script de replay capable de livrer uniquement des observations dont `data_timestamp <= simulated_time`;
- schema/version documentes;
- hash/commit du collecteur consignes;
- limitations de chaque source explicites.

Apres ce gate seulement, preparer D025 LER Observer en mode virtuel MT5 Core. Ne pas sauter directement a un EA live.

## NE_PAS_FAIRE

- Ne pas toucher silencieusement `production/guardian/`.
- Ne pas appeler une API externe depuis une boucle de trading critique comme dependance obligatoire.
- Ne pas utiliser de donnees futures en replay/backtest.
- Ne pas transformer les donnees externes en score opaque ou en modele ML avant event study.
- Ne pas lancer une optimisation de seuils ou de poids.
- Ne pas dupliquer/reprendre des workers non lies a D025 si le PC a deja une tache saine en cours; verifier l'etat reel avant lancement.

## PRIORITE

Nouvelle priorite utilisateur, mais travail incremental. Commencer uniquement par l'infrastructure de donnees V1 et checkpoint GitHub. Le LER trading reste bloque tant que le bus n'est pas valide et l'event study non faite.