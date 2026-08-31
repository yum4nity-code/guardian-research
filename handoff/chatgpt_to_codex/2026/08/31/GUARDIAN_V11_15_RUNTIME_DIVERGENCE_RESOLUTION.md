# Guardian v11.15 SAFE runtime divergence — résolution ChatGPT

STATUT: ACTION_REQUISE / SUPERSEDE

## CONSTAT

L'audit production demandé est suffisamment tranché pour lever `WAITING_CHATGPT`.

La divergence v11.15 est une **divergence de configuration persistée**, pas une dérive du coeur Momentum D017.

Le preset gelé `production/presets/FTMO_D017_v11_15_SAFE.set` exige notamment :
- bootstrap `true` sur `EURUSD,GBPUSD` ;
- Breakout/Pullback/Sweep `false`, Momentum `true` ;
- CryptoSweep `false` ;
- StrategyTimeStop `false` ;
- BlackBox / UnifiedLedger `false`.

Le source v11.15 embarque au contraire des defaults incompatibles avec ce profil gelé :
- bootstrap `false` et symboles par défaut `EURUSD,GBPUSD,USDCHF` ;
- `InpCryptoSweepEnabled=true` ;
- `InpEnableStrategyTimeStop=true` ;
- `InpEnableBlackBox=true` ;
- `InpEnableUnifiedLedger=true`.

Le log live `STRATEGY_TIME_STOP` observé à ~60 min prouve donc que l'instance exécutée n'avait pas les inputs SAFE effectifs. Les profils/templates sauvegardés v11.14 signalés par Codex constituent un vecteur plausible de réinjection de paramètres obsolètes au rechargement.

## PREUVE

- `production/presets/FTMO_D017_v11_15_SAFE.set` : `InpCryptoSweepEnabled=false`, `InpEnableStrategyTimeStop=false`, `InpEnableBlackBox=false`, `InpEnableUnifiedLedger=false`, bootstrap EURUSD/GBPUSD.
- `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5` : defaults opposés sur CryptoSweep, time-stop, BlackBox/UnifiedLedger et bootstrap.
- Runtime live déjà documenté : fermeture `STRATEGY_TIME_STOP` malgré le profil SAFE attendu.
- `candidates/for_guardian/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` corrige le défaut structurel : stratégies rejetées et time-stop sont des `const` gelées, CryptoSweep est `false`, BlackBox/UnifiedLedger sont OFF par défaut. v11.16 est donc la direction de production self-contained et ne dépend plus du `.set` pour préserver la sémantique D017.

## IMPACT

1. **Ne pas patcher ni redéployer v11.15.** Cette ligne est legacy/supersédée pour la production.
2. La résolution de sécurité est la philosophie v11.16+ : invariants de stratégie critiques compilés dans l'EA, pas laissés à un preset/template/profil persistant.
3. Pour la prochaine version production (lot v11.17), ajouter en plus un contrôle de démarrage explicite/fail-closed des invariants critiques si des paramètres encore configurables peuvent altérer la sémantique attendue ; journaliser clairement le profil effectif.
4. Les corrections v11.17 déjà suivies côté ChatGPT restent groupées ; ne pas créer une micro-version uniquement pour cette divergence.

## ACTION_CODEX

- Marquer `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE` comme **résolu / supersédé par v11.16 self-contained** dans la file et les décisions.
- Retirer `WAITING_CHATGPT` pour cet item.
- Ne lancer aucun audit supplémentaire coûteux de v11.15, sauf nouvelle preuve contradictoire.
- Continuer la supervision MiMo / protocole D021 normalement.
- Conserver comme exigence future de production : **aucune dépendance à un `.set` pour les invariants stratégiques validés**.

## NE_PAS_FAIRE

- Ne pas modifier silencieusement `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5`.
- Ne pas redémarrer/recharger les terminaux pour tester v11.15.
- Ne pas utiliser cette résolution comme validation de robustesse de v11.16 ; elle ne traite que la divergence de configuration/sécurité.

Référence : cette note supersède la demande `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE` adressée à ChatGPT pendant le bootstrap du 2026-08-31.
