# Guardian v11.16.12 — RSI Fill Reconcile

Base: v11.16.11 Strategy Switches.

## Bug corrigé

Un BUY RSI pouvait être accepté alors que `ResultDeal()` / la position n'étaient pas encore visibles immédiatement. L'ancienne logique ne posait `g_rsi_cycle_id` et les tags ticket que si `pos_id > 0` dans la même fenêtre d'exécution. Une position broker RSI pouvait donc exister avec commentaire `RSI_SNIPER C... L1`, mais sans cycle interne actif pour RSI50/RSI70.

Cas live déclencheur: USDCAD, `RSI_FILL_PRICE_FALLBACK deal=0 pos=0`, puis `AUTO_ENTRY_FILLED` quelques millisecondes plus tard; plusieurs clôtures M1 > RSI50 sans TP1.

## Corrections

- cycle logique persisté dès que `g_trade.Buy()` est accepté, sans attendre la visibilité du deal;
- réconciliation `OnTradeTransaction(DEAL_ADD)` avec commentaire broker comme identité canonique;
- retag ticket/cycle/leg/strategy, vrai `DEAL_PRICE`, volume, stop et risque;
- nouveau log `RSI_FILL_RECONCILED ... RSI management ACTIVE`;
- marker fallback Ask repositionnable sur le vrai fill;
- récupération de triggers RSI50/RSI70 manqués depuis les M1 fermées depuis l'ouverture de la position;
- recovery au fill, au cycle recovery, au startup, et recovery RSI70 après TP1;
- une position déjà ouverte par 11.16.10/11 avec cycle orphelin doit être récupérable au chargement de 11.16.12.

## Invariants non modifiés

Momentum, RSI 30/reset 40, TP1 RSI50 40%, TP2 RSI70, BUY2, divergence, retest, SL, spread, cooldown, sizing et switches stratégie sont inchangés.

## Source candidate

Expected source path: `production/guardian/Guardian_D017_PropFirmAuto_v11_16_12_RSI_FILL_RECONCILE.mq5`

SHA256 exact généré par ChatGPT: `9307f5daf09c243b4997fb59f82a71e5baa85992a5f348fd3bf9e5f841b8122b`

Compilation MetaEditor: **PENDING USER COMPILE**.
