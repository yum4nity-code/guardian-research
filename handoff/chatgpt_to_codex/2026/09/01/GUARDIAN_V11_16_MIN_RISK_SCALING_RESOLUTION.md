# Guardian v11.16 — plancher minimum de risque

STATUT: ACTION_REQUISE / SUPERSEDE LA VERSION PRECEDENTE DE CETTE NOTE

## CONSTAT
La divergence est confirmee : v11.16 calcule 2,50 USD sur 10k et 25 USD sur 100k au lieu de 25/250.

## DECISION
ChatGPT a pris la correction en charge directement. **Codex ne doit plus concevoir, coder, auditer ni rejouer un protocole de correction du plancher.** Les anciennes consignes longues de cette note sont annulees.

Invariant corrige : plancher auto-trade self-contained = **0,25 % du capital de reference** : 10k -> 25 USD ; 100k -> 250 USD. Si le quality/risk scaling tombe sous ce plancher, l'ordre est bloque, jamais remonte artificiellement.

La candidate produite par ChatGPT est :
`Guardian_D017_PropFirmAuto_v11_16_1_RISKFIX.mq5`
Version interne `11.161`.
SHA256 source ChatGPT : `E44BF3D4EAB8EFF9F5807B6D5A346C0D3F34C57D9FA29F8067EE8A870F983CB6`.
Elle contient deja le self-test 10k=25 / 100k=250 et fail-closed si le capital/plancher est invalide.

## ACTION_CODEX — COURTE
Quand cette source RISKFIX apparait sur le PC utilisateur :
1. ne pas la redesigner ni la repatcher ;
2. faire seulement la compilation normale necessaire aux workers ;
3. si compilation OK et le log `RISK_FLOOR_SELFTEST PASS` apparait, lancer directement la campagne pre-OOS deja autorisee sur AUDUSD, EURJPY, NZDUSD, USDCAD, USDCHF et XAUUSD avec les workers libres ;
4. zero tuning, fin de periode 2026-06-28, OOS verrouille.

**Le rerun EURUSD/GBPUSD n'est plus un gate avant les six marches.** Il pourra etre fait plus tard si utile. MiMo continue independamment.

NE_PAS_FAIRE : ne pas lancer les six marches avec le binaire v11.16 legacy ; ne pas modifier le Guardian live automatiquement.