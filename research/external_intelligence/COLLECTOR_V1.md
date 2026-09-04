# Guardian External Intelligence Bus V1 — Bybit collector

Research-only collector for BTC/ETH external crypto data. It uses only public Bybit market-data interfaces and requires no API key.

## What is recorded

Every observation is a JSON object compatible with `schema_v1.json` and is appended to a UTC daily JSONL file.

- BTCUSDT and ETHUSDT spot last price;
- BTCUSDT and ETHUSDT USDT-perpetual last price;
- perpetual open interest;
- perpetual funding rate;
- every public long/short liquidation received from Bybit `allLiquidation`;
- channel health/staleness.

`available_at_ms` is the local receive time. Replays must expose a record only when `available_at_ms <= simulated_time_ms`.

## Source semantics

Bybit's public ticker endpoint supports both `spot` and `linear`; linear ticker data includes current open interest and funding rate. The public `allLiquidation.{symbol}` websocket pushes all liquidations at up to 500 ms frequency. In that feed, `S=Buy` means a long position was liquidated and `S=Sell` means a short position was liquidated.

The feed supplies liquidation size and bankruptcy price. Therefore `liquidation_notional` in V1 is explicitly an **estimate**: `size * bankruptcy_price`, with unit `USDT_est_bankruptcy_price`. It must not be described later as exchange-reported executed notional.

Official docs used for V1:
- https://bybit-exchange.github.io/docs/v5/market/tickers
- https://bybit-exchange.github.io/docs/v5/websocket/public/all-liquidation
- https://bybit-exchange.github.io/docs/v5/ws/connect

## Bootstrap Windows depuis une machine sans Git

Installer Git avec PowerShell:

```powershell
winget install --id Git.Git -e --source winget
```

Fermer/reouvrir PowerShell puis verifier:

```powershell
git --version
```

Cloner le depot prive:

```powershell
cd D:\MT5_Backtests
git clone https://github.com/yum4nity-code/guardian-research.git guardian-research
```

Sur une machine deja clonee, mettre a jour la copie locale:

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
```

## Smoke Windows recommande

Le moyen le plus simple est le lanceur:

```powershell
cd D:\MT5_Backtests\guardian-research\research\external_intelligence
.\START_EIB_SMOKE_V1.cmd
```

Il cree/verifie un `.venv`, installe `aiohttp`, lance un smoke BTC+ETH de 35 minutes et produit le resume final.

## Installation manuelle Python

Si le lanceur n'est pas utilise:

```powershell
cd D:\MT5_Backtests\guardian-research\research\external_intelligence
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe collector_v1.py
```

Default output on Windows:

`D:\MT5_Backtests\Research\ExternalIntelligence\bybit_eib_v1_YYYYMMDD.jsonl`

and current health:

`D:\MT5_Backtests\Research\ExternalIntelligence\health.json`

Override the destination with `--data-dir` or `GUARDIAN_EIB_DATA_DIR`.

## Stockage / retention actuelle

Les donnees sont stockees **sur le PC local** dans le dossier de sortie. V1 n'efface actuellement aucun fichier automatiquement.

Pendant la recherche D025, cette absence de suppression automatique est volontaire: les timestamps de reception, trous de connexion et liquidations ne sont pas parfaitement reconstructibles a posteriori.

Politique cible apres validation du smoke:

- fichier du jour UTC actif en `.jsonl`;
- jours clos archives en `.jsonl.gz` apres verification d'integrite;
- suppression du raw uniquement apres validation de l'archive;
- recherche: retention indefinie/manuelle jusqu'a decision scientifique;
- futur produit: retention configurable, valeur provisoire envisagee 90 jours, mode labo 365 jours/illimite;
- ne jamais supprimer silencieusement le fichier actif ni une archive non verifiee.

Le volume reel doit etre mesure avant de figer les durees commerciales.

Voir `../../docs/GUARDIAN_PRODUCT_INSTALLATION_AND_DATA_LIFECYCLE.md` pour la procedure reproductible complete et les exigences du futur produit.

## Smoke gate

Before D025 uses these data, run at least 30 minutes and verify:

1. BTC and ETH spot/perp records continue to arrive;
2. OI and funding are parseable;
3. liquidation websocket is connected even during periods with zero liquidation events;
4. stop/restart resumes by appending, not truncating;
5. temporary network interruption causes `PARTIAL/STALE/DOWN` rather than invented values;
6. no duplicate liquidation event IDs after reconnect;
7. `replay_v1.py` never returns a record before `available_at_ms`.

## Replay example

```powershell
.\.venv\Scripts\python.exe replay_v1.py bybit_eib_v1_20260904.jsonl --until-ms 1788498000000
```

## Safety

No credentials are accepted or needed. No Bybit private/trading endpoint is called. Guardian production is not modified and does not depend on this collector.
