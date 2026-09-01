# Guardian v11.16 — resolution du plancher minimum de risque

STATUT: URGENT / ACTION_REQUISE

## CONSTAT

Je confirme la divergence signalee par Codex. La source v11.16 canonique utilise actuellement :

```cpp
input double InpMinTradeRiskUSD = 25.0;
input bool InpScaleMinTradeRiskWithCapital = true;
...
return configured*(g_detected_base_cap/100000.0);
```

Cela donne 2,50 USD sur 10k et 25 USD sur 100k, ce qui est un facteur 10 sous l'invariant utilisateur.

## DECISION / INVARIANT AUTORITATIF

Pour la ligne production/candidate Guardian auto-trading, le plancher minimum de risque est **0,25 % du capital de reference** :

- 10 000 USD -> 25 USD
- 100 000 USD -> 250 USD

Cet invariant est GLOBAL pour les auto-trades de la candidate corrigee, y compris crypto. Le legacy `InpMinTradeRiskUSDCrypto=12.0` ne doit pas pouvoir abaisser ce plancher en production. Une experimentation avec un plancher crypto different devra vivre dans une branche research distincte, pas dans la candidate production.

Le plancher est un MINIMUM d'eligibilite : si le risk scaling/grade produit une cible inferieure a 0,25 % du capital de reference, l'ordre doit etre bloque, pas remonte artificiellement au plancher.

## CORRECTION DEMANDEE

Ne pas modifier silencieusement le fichier v11.16 existant. Creer une candidate distincte, proposee :

`Guardian_D017_PropFirmAuto_v11_16_1_RISKFIX.mq5`

avec une version interne distincte (par ex. `#property version "11.161"`) afin de garder v11.17 disponible pour le batch de corrections deja prevu.

La logique doit devenir self-contained, par exemple :

```cpp
const double PROD_MIN_AUTO_TRADE_RISK_PCT = 0.25;

double MinTradeRiskUSDForCapital(const double capital)
  {
   if(capital<=0.0) return -1.0;
   return capital*(PROD_MIN_AUTO_TRADE_RISK_PCT/100.0);
  }

double EffectiveMinTradeRiskUSD()
  {
   return MinTradeRiskUSDForCapital(g_detected_base_cap);
  }
```

Si le capital de reference est invalide/non resolu, fail closed : aucune nouvelle entree auto. Ne pas revenir a 25 USD fixe silencieusement.

Les anciens inputs `InpMinTradeRiskUSD`, `InpScaleMinTradeRiskWithCapital` et `InpMinTradeRiskUSDCrypto` ne doivent plus pouvoir modifier cet invariant en candidate production. Ils peuvent etre retires, convertis en constantes legacy ou explicitement ignores, mais l'UI/log ne doit pas laisser croire qu'ils gouvernent encore le plancher.

## SELF-TEST OBLIGATOIRE

Ajouter un test deterministe au demarrage avant autorisation de trading :

- `MinTradeRiskUSDForCapital(10000.0) == 25.00`
- `MinTradeRiskUSDForCapital(100000.0) == 250.00`

Tolerance flottante minime. En cas d'echec : log `RISK_FLOOR_SELFTEST_FAIL` + `INIT_FAILED`/blocage auto fail-closed.

En cas de succes, log explicite du type :

`RISK_FLOOR_SELFTEST PASS | 10k=25.00 | 100k=250.00 | current=<...>`

## IMPACT SUR LES RESULTATS EXISTANTS

Les backtests v11.16 deja obtenus restent valides uniquement comme resultats du **binaire legacy avec plancher errone**. Ils ne sont PAS transferables ni directement comparables a la candidate corrigee, car le filtre d'eligibilite des grades/risk factors peut changer le nombre de trades, le PnL et le DD.

Donc :

- ne pas supprimer l'historique v11.16 ; le marquer `LEGACY_RISK_FLOOR_BUG` ;
- ne pas utiliser ses metriques pour valider la candidate corrigee ;
- le controle EURUSD/GBPUSD doit etre rejoue avec la candidate RISKFIX avant la generalisation six marches.

## ACTION_CODEX AUTORISEE

Codex est explicitement autorise a creer cette **candidate corrigee** a partir de la source canonique/copie locale v11.16 dont il a confirme le SHA `C90B85E867C5CE043954ECC90E17D13495997D145BAEF67560E9575DEC2E0D3A`. Ceci est une modification de candidate/research, PAS un remplacement silencieux du Guardian production installe.

Sequence :

1. creer la candidate versionnee RISKFIX ;
2. compiler ;
3. executer self-test 10k/100k + smoke test sans OOS ;
4. publier SHA256 source + EX5 si pertinent + diff/manifeste ;
5. transformer le controle EURUSD/GBPUSD en controle de non-regression de la candidate RISKFIX ;
6. seulement si ce controle est propre, debloquer et lancer la campagne AUDUSD/EURJPY/NZDUSD/USDCAD/USDCHF/XAUUSD sur workers libres, periode pre-OOS fin 2026-06-28, zero tuning ;
7. garder l'OOS verrouille.

MiMo peut continuer independamment.

## NE_PAS_FAIRE

- ne pas relancer les six marches avec le binaire v11.16 legacy ;
- ne pas modifier le Guardian production/live sans validation utilisateur ;
- ne pas ajuster d'autres parametres pour compenser la baisse potentielle du nombre de trades ;
- ne pas ouvrir l'OOS.
