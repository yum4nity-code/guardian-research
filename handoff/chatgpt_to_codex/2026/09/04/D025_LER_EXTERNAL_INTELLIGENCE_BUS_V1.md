# D025 / Guardian External Intelligence Bus V1

STATUT: ACTION_REQUISE
DATE: 2026-09-04

## CONSTAT

L'utilisateur veut ajouter une troisieme strategie mid-term `Liquidity Exhaustion Reclaim (LER)` et autorise explicitement Guardian a recevoir des donnees externes pour enrichir ses decisions, notamment sur crypto.

Le concept retenu n'est pas "acheter une grosse meche" mais : niveau objectif preexistant -> sweep/cascade -> pression extreme -> impact marginal decroissant/exhaustion -> reclaim -> acceptance/retest -> signal virtuel. La couche externe vise surtout a mesurer le deleveraging crypto avec spot/perp, open interest et liquidations.

Le preregistration complet est dans :
`research/campaigns/D025_LIQUIDITY_EXHAUSTION_RECLAIM_PREREGISTRATION.md`

## ETAT IMPLEMENTATION AU 2026-09-04

ChatGPT a deja code et pousse la premiere implementation V1. **Ne pas la reecrire avant smoke test.**

Fichiers :
- `research/external_intelligence/collector_v1.py`
- `research/external_intelligence/replay_v1.py`
- `research/external_intelligence/schema_v1.json`
- `research/external_intelligence/manifest_v1.json`
- `research/external_intelligence/requirements.txt`
- `research/external_intelligence/COLLECTOR_V1.md`
- `research/external_intelligence/tests/test_eib_v1.py`
- `research/external_intelligence/smoke_v1.py`
- `research/external_intelligence/START_EIB_SMOKE_V1.cmd`

Provider V1 : Bybit public, sans cle API.

Donnees collectees pour BTCUSDT/ETHUSDT :
- spot last price;
- USDT perpetual last price;
- open interest courant;
- funding rate courant;
- toutes les liquidations publiques via `allLiquidation.{symbol}`;
- health/staleness.

Le notional liquidation est explicitement une estimation `size * bankruptcy_price`, car le flux public Bybit fournit le bankruptcy price et non un notional execute officiel.

Commits principaux :
- collector : `83bd4245b9de1a8c8893b3acf1f7867c07e6132e`
- replay : `1a27d6269912af1c16f65f2afa5b9027eae2d834`
- manifest : `8718bfaca7da256a09b73bbf1d38a27ad2ffd321`
- tests : `144d78199f4f701948247f1604adcab77f652f91`
- timed smoke runner : `e75cb71490aa471f517137b06d85ddf5e1e0b1ed`
- Windows one-click launcher : `732ecf3e10860a627b65155c6811ba55d2c9f839`

Validation deja faite par ChatGPT hors reseau :
- `python -m py_compile collector_v1.py replay_v1.py` : OK;
- 4 tests unitaires offline : OK;
- test explicite du gate replay `available_at_ms <= simulated_time_ms` : OK.

## PREUVE / SOURCES PROVIDER

Bybit documente publiquement :
- `GET /v5/market/tickers` pour spot et linear, avec lastPrice et, pour linear, openInterest/fundingRate;
- websocket public `wss://stream.bybit.com/v5/public/linear`;
- topic `allLiquidation.{symbol}`; `S=Buy` signifie liquidation d'une position long, `S=Sell` liquidation d'une position short; push jusqu'a 500 ms.

Voir `COLLECTOR_V1.md` pour les URLs officielles.

## IMPACT

Le jalon "code du collecteur" est atteint. Le prochain gate est **validation live du flux sur le PC**, pas integration Guardian et pas moteur LER.

Le bus reste strictement read-only et Guardian production n'en depend pas.

## LANCEMENT SMOKE 35 MIN

Apres synchronisation du repo, le smoke peut etre lance sans autre code avec :

`research\external_intelligence\START_EIB_SMOKE_V1.cmd`

Le lanceur :
- cree un `.venv` local s'il n'existe pas;
- installe/verifie `aiohttp` via `requirements.txt`;
- lance BTC+ETH pendant 35 minutes;
- ecrit dans `D:\MT5_Backtests\Research\ExternalIntelligence`;
- produit `health.json`, le JSONL quotidien et un `smoke_summary_<timestamp>.json`;
- affiche `PASS` ou `REVIEW` en fin de run.

Le runner verifie au minimum : canaux core presents, zero duplicate event_id dans la fenetre, JSON valide et aucune violation d'availability future. Un compteur de liquidations a zero n'est pas a lui seul un echec si le websocket est sain pendant une periode calme.

## ACTION_CODEX

1. Synchroniser le repo; ne pas reecrire V1 sans bug concret.
2. Lancer `research\external_intelligence\START_EIB_SMOKE_V1.cmd` sur le PC utilisateur.
3. Ne pas lancer un second collecteur si un smoke est deja actif.
4. Laisser le smoke aller jusqu'au resume final 35 min.
5. Pendant/apres le smoke, verifier :
   - spot/perp continuent d'arriver;
   - OI/funding parseables;
   - websocket liquidation connecte meme si zero evenement;
   - `health.json` passe correctement OK/PARTIAL/STALE/DOWN;
   - arret/restart append sans truncation;
   - reconnexion apres coupure reseau;
   - pas de duplicate liquidation event_id apres reconnect;
   - source_ts / received_ts / available_at coherents.
6. Executer les tests offline dans l'environnement local.
7. Tester `replay_v1.py` sur le JSONL produit et prouver qu'aucune observation n'est livree avant `available_at_ms`.
8. Produire un petit sample anonymise/compact + manifest de smoke + stats de compte par metric, taille fichier, taux de duplication, latence source->receive, trous/staleness.
9. Commit/push les preuves compactes et mettre la queue/status a jour.

### Gates avant etape suivante

- 30+ minutes de collecte BTC+ETH sans duplication majeure;
- timestamps UTC coherents;
- source timestamp et availability timestamp distincts;
- coupure/reconnexion testee;
- staleness detectable;
- fichier rejouable;
- replay prouve fail-closed sur `available_at <= simulated_time`;
- limitations provider explicites;
- hash/commit du code consignes.

Apres ce gate seulement, preparer D025 LER Observer en mode virtuel MT5 Core. Ne pas sauter directement a un EA live.

## NE_PAS_FAIRE

- Ne pas toucher silencieusement `production/guardian/`.
- Ne pas ajouter de cle API privee/trading.
- Ne pas appeler une API externe depuis une boucle de trading critique comme dependance obligatoire.
- Ne pas utiliser de donnees futures en replay/backtest.
- Ne pas transformer les donnees externes en score opaque ou en modele ML avant event study.
- Ne pas lancer une optimisation de seuils ou de poids.
- Ne pas confondre le notional liquidation estime avec un notional execute officiel.
- Ne pas dupliquer/reprendre des workers non lies a D025 si le PC a deja une tache saine en cours; verifier l'etat reel avant lancement.

## PRIORITE

Nouvelle priorite utilisateur, mais travail incremental. Le code V1 existe; prochaine action = smoke/validation locale, puis checkpoint GitHub. Le LER trading reste bloque tant que le bus n'est pas valide et l'event study non faite.