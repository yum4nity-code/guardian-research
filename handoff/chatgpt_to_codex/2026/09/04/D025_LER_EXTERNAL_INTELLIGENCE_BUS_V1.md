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

Provider V1 : Bybit public, sans cle API.

Donnees collectees pour BTCUSDT/ETHUSDT :
- spot last price;
- USDT perpetual last price;
- open interest courant;
- funding rate courant;
- toutes les liquidations publiques via `allLiquidation.{symbol}`;
- health/staleness.

Le notional liquidation est explicitement une estimation `size * bankruptcy_price`, car le flux public Bybit fournit le bankruptcy price et non un notional execute officiel.

Hashes LF locaux ChatGPT :
- `collector_v1.py` SHA256 `761329daa74cdb31dd80f136b0f37e1df759956e13e6ea0b3bc3c7bd6c73874e`
- `replay_v1.py` SHA256 `4a8b1ef7a80bbf2a898b996f5b86b38475ec88695a673591f49f3a158bb2b034`
- `tests/test_eib_v1.py` SHA256 `d1f65cb2b08f73a6e6b06c5cc131372520e4534984102dd58bd237d501083948`

Commits principaux :
- collector : `83bd4245b9de1a8c8893b3acf1f7867c07e6132e`
- replay : `1a27d6269912af1c16f65f2afa5b9027eae2d834`
- manifest : `8718bfaca7da256a09b73bbf1d38a27ad2ffd321`
- tests : `144d78199f4f701948247f1604adcab77f652f91`

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

## ACTION_CODEX

1. Synchroniser le repo; ne pas reecrire V1 sans bug concret.
2. Installer/executer le collecteur sous `D:\MT5_Backtests\Research\ExternalIntelligence\` selon `COLLECTOR_V1.md`.
3. Faire un smoke reel de 30+ minutes BTC+ETH.
4. Pendant le smoke, verifier :
   - spot/perp continuent d'arriver;
   - OI/funding parseables;
   - websocket liquidation connecte meme si zero evenement;
   - `health.json` passe correctement OK/PARTIAL/STALE/DOWN;
   - arret/restart append sans truncation;
   - reconnexion apres coupure reseau;
   - pas de duplicate liquidation event_id apres reconnect;
   - source_ts / received_ts / available_at coherents.
5. Executer les tests offline dans l'environnement local.
6. Tester `replay_v1.py` sur le JSONL produit et prouver qu'aucune observation n'est livree avant `available_at_ms`.
7. Produire un petit sample anonymise/compact + manifest de smoke + stats de compte par metric, taille fichier, taux de duplication, latence source->receive, trous/staleness.
8. Commit/push les preuves compactes et mettre la queue/status a jour.

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