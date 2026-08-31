# ChatGPT -> Codex — Guardian v11.15 migration audit

STATUT: INFO
DATE: 2026-08-31
SOURCE: audit direct de `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5` + logs utilisateur

## CONSTAT
1. La v11.15 reprend correctement une position AUTO ouverte par la v11.14 sur le même symbole parce que le Magic auto est calculé uniquement à partir du symbole via `GenerateAutoMagicNumber(_Symbol)`. La version du Guardian n'entre pas dans le Magic.
2. Les états de position (`RISK`, `RISKUSD`, `TP1`, `BE`, `MFE`, `MAE`, `STRAT`) utilisent des Global Variables MT5 avec des clés stables `FTMO_PRO_V9_<position_id>_<field>` ; un simple remplacement de v11.14 par v11.15 sur le même terminal conserve donc normalement l'état.
3. Si `RISK` manque mais qu'un SL existe, v11.15 reconstruit `RISK` et `RISKUSD` depuis `abs(open_price - sl)`.
4. Si `STRAT` manque, v11.15 tente de reconstruire la stratégie depuis `POSITION_COMMENT` (`Pullback`, `Sweep`, `Momentum`). Si état + commentaire sont perdus, le fallback actuel est `STRAT_BREAKOUT`.
5. Si les Global Variables `TP1`/`BE` sont perdues, la v11.15 ne peut pas reconstruire de façon certaine qu'un TP partiel ou BE a déjà été exécuté ; une reprise après perte complète d'état peut donc tenter une action déjà réalisée.
6. Ne jamais laisser une v11.14 et une v11.15 actives simultanément sur le même symbole : elles partagent le même Magic. L'élection OWNER/STANDBY de v11.15 ne protège pas contre une ancienne v11.14 qui ignore ce mécanisme.

## PREUVE
- Source production : `production/guardian/Guardian_D017_PropFirmAuto_v11_15.mq5`
- Fonction clé : `GenerateAutoMagicNumber(string symbol)`
- Gestion auto : une position est acceptée si `POSITION_SYMBOL == _Symbol` et `POSITION_MAGIC == g_auto_magic`.
- Persistance : fonctions `TicketGV`, `SetTicketState`, `GetTicketState`.
- Repli stratégie : `GetPositionStrategy(...)`.

## IMPACT
Aucune correction urgente pour la migration normale actuelle v11.14 -> v11.15 sur le même terminal. Les deux faiblesses concernent surtout une reprise après perte des Global Variables/état MT5. Le risque opérationnel immédiat est plutôt la coexistence d'une ancienne instance v11.14 sur le même symbole.

## ACTION_CODEX
Aucune action obligatoire immédiate. Lors d'un futur travail de robustesse/maintenance Guardian, considérer un mécanisme explicite de reconstruction de l'état historique (notamment TP1/BE) et un fallback de stratégie plus sûr que BREAKOUT lorsque l'origine est indéterminable.

## NE_PAS_FAIRE
- Ne pas modifier maintenant `production/guardian/` uniquement pour cette note.
- Ne pas laisser v11.14 et v11.15 gérer simultanément le même symbole.
