# Guardian v11.16 — divergence critique du plancher de risque

STATUT: URGENT / WAITING_CHATGPT

## Constat reproductible

L'utilisateur a explicitement corrige le plancher attendu a **25 USD sur 10k** et **250 USD sur 100k**.

La source candidate canonique et la copie installee dans D0E sont identiques, SHA256 brut :

`C90B85E867C5CE043954ECC90E17D13495997D145BAEF67560E9575DEC2E0D3A`

Dans les deux copies :

```cpp
input double InpMinTradeRiskUSD = 25.0;
input bool InpScaleMinTradeRiskWithCapital = true;
...
return configured*(g_detected_base_cap/100000.0);
```

Le calcul produit donc :

- capital 10 000 USD -> plancher 2,50 USD ;
- capital 100 000 USD -> plancher 25 USD.

Cela est un facteur 10 sous l'intention utilisateur. Le journal historique local confirmait d'ailleurs encore l'ancienne interpretation : « plancher configure 25 USD redimensionne a 2,50 USD ».

## Impact

Ce plancher intervient apres le scaling de qualite du signal. A 0,25 % de risque nominal, les cibles sont 25 USD sur 10k et 250 USD sur 100k, mais les facteurs de qualite peuvent les reduire. Le code actuel peut donc autoriser des trades reduits que le plancher corrige devait bloquer. Corriger ce point peut changer le nombre de trades, le PnL et la comparabilite empirique.

## Mesure fail-closed prise par Codex

- Aucun nouveau backtest v11.16 sur AUDUSD/EURJPY/NZDUSD/USDCAD/USDCHF/XAUUSD n'a ete lance.
- La campagne `D017-V11-16-GENERALIZATION-PREOOS` est bloquee avant import/resultat.
- L'OOS reste ferme.
- Aucun fichier production, candidat ou instance MT5 n'a ete modifie.

## Action demandee a ChatGPT

1. Confirmer que l'invariant voulu est bien 0,25 % du capital de reference, soit 25 USD sur 10k et 250 USD sur 100k.
2. Produire une nouvelle version candidate (ne pas reecrire silencieusement v11.16) avec invariant self-contained et test unitaire 10k/100k.
3. Preciser si les anciens resultats v11.16 doivent etre classes comme non comparables a la version corrigee.
4. Publier source/manifeste/hashes et une instruction de reprise a Codex.

