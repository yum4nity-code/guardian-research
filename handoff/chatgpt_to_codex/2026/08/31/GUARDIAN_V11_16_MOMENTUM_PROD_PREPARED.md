STATUT: INFO

CONSTAT
ChatGPT a préparé une nouvelle build production candidate locale `Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5` à partir de v11.15, suite à la divergence constatée entre les defaults source et le preset D017.

OBJECTIF
Supprimer la dépendance à un `.set` pour obtenir le comportement D017 attendu au démarrage et éviter qu'un default source réactive une règle rejetée/non validée.

CHANGEMENTS PREPARES
- version 11.16 ;
- Momentum seul autorisé en production ;
- Breakout/Pullback/Sweep hard-lockés OFF dans le gate de signal ;
- tous les réglages Breakout/Pullback/Sweep/CryptoSweep retirés des Inputs MT5 en les conservant comme constantes dormantes dans le source pour audit historique ;
- `InpCryptoSweepEnabled=false` verrouillé ;
- session D017 07:00-17:00 UTC verrouillée ;
- `InpStrategyMode=MODE_PORTFOLIO_RANKED` verrouillé ;
- `InpEnableStrategyTimeStop=false` verrouillé ;
- les paramètres legacy Momentum 60 min / 0.40R restent dans le source comme constantes inactives mais ne sont plus exposés ;
- BlackBox/Ledger restent optionnels mais passent OFF par défaut ;
- HUD/startup affichent explicitement `MOMENTUM ONLY | 07-17 UTC | TIME-STOP OFF`.

PREUVE
Fichier local ChatGPT: `/mnt/data/Guardian_D017_PropFirmAuto_v11_16_MOMENTUM_PROD.mq5`
SHA256 local: `bdd2ee0493f0a613177941de4c08e29c6453a715d13fd3b660c42cb3ac2fec09`
Le fichier n'est PAS encore considéré production/deployed : compilation MetaEditor par l'utilisateur requise.

IMPACT
Cette build vise une EA prête à l'emploi sans chargement de preset `.set`, avec les invariants D017 intégrés au source et les moteurs rejetés non activables accidentellement.

ACTION_CODEX
Aucune action immédiate requise pendant le bootstrap. Assimiler l'information. Après compilation utilisateur réussie, auditer/non-régression si ChatGPT ou l'utilisateur le demande.

NE_PAS_FAIRE
Ne pas remplacer production v11.15 par cette v11.16 tant que l'utilisateur n'a pas compilé/validé la build et que la non-régression n'est pas confirmée.
