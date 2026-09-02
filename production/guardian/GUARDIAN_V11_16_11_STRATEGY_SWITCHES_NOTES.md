# Guardian v11.16.11 — Strategy Switches

Base: v11.16.10 BUYBLOCK DIAG.

## Nouveau
Deux interrupteurs visibles dans le groupe `STRATÉGIES AUTO — ON / OFF` :

- `InpEnableMomentum = true/false`
- `InpEnableRSISniper = true/false`

## Modes de backtest

- RSI seul : `InpEnableMomentum=false`, `InpEnableRSISniper=true`
- Momentum seul : `InpEnableMomentum=true`, `InpEnableRSISniper=false`
- Combo : les deux à `true`
- Aucun moteur auto : les deux à `false`

## Sécurité live

OFF bloque les **nouvelles entrées** de la stratégie concernée. La gestion/protection d'une position déjà ouverte reste active. Pour RSI, un cycle existant continue donc TP1/TP2/trailing, mais aucun nouveau BUY2 n'est ajouté si le switch RSI est OFF.

Aucun paramètre de signal, SL, TP, trailing, sizing, spread, cooldown ou risque n'a été modifié.

## Baseline file

Expected production source: `production/guardian/Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`

Local source SHA256 at ChatGPT handoff: `d30ff21378331f972bea947a4c6c826b6f4a2547e58878947551199b9d01c495`.
