# D022 — RELATIVE-VALUE PAIR-REV M15 V0

STATUT: PREREGISTRE / READY APRES TRAVAUX ACTIFS

## Idée
Tester une stratégie de **mean reversion relative-value à deux jambes**, indépendante du Momentum D017 et de MICRO-REV M1.

But : exploiter une divergence temporaire entre deux marchés proches plutôt qu'une direction absolue du marché.

Aucune optimisation pour sauver un symbole. Cheap-fail d'abord, EA seulement si l'event-study passe.

## Univers V0 figé
Deux paires seulement pour le premier test :

1. `AUDUSD` / `NZDUSD`
2. `EURUSD` / `GBPUSD`

Ne pas ajouter d'autres couples après lecture des résultats V0.

Timeframe : **M15**.
Données : uniquement période commune pré-OOS, fin **2026-06-28**. OOS verrouillé.

## Construction du spread
À chaque barre M15 synchronisée :

- travailler sur `log(close)` des deux jambes ;
- estimer `alpha` et `beta` par OLS sur les **20 jours de trading précédents**, sans utiliser la barre courante ;
- résidu : `r_t = log(PA_t) - alpha - beta*log(PB_t)` ;
- moyenne et écart-type du résidu sur la même fenêtre laggée de 20 jours ;
- `z_t = (r_t - mean_r) / sd_r`.

Aucune donnée future dans beta, moyenne ou écart-type.

## Événement / pseudo-trade V0
Un événement existe uniquement au **franchissement** du seuil :

- short spread si `z` franchit **+2.0** depuis dessous ;
- long spread si `z` franchit **-2.0** depuis dessus ;
- entrée théorique à la barre M15 suivante pour éviter le look-ahead.

Sortie primaire : premier retour/croisement de `z = 0`.

Fail-stop statistique : `|z| >= 3.5` avant retour à zéro.

Time-stop : **2 jours de trading / 192 barres M15 max**.

Un seul événement actif par paire ; pas de réentrée tant que l'événement précédent n'est pas clos et que `|z|` n'est pas revenu sous 1.0.

## Coûts
Le cheap-fail doit compter **les deux jambes** : spread/exécution disponible dans les données + commission FTMO applicable. Si le modèle de coût fiable n'est pas disponible, le résultat doit être marqué `COST_MODEL_INCOMPLETE`, pas considéré comme validation.

## Mesures obligatoires
Pour chaque paire et agrégé :

- nombre d'événements ;
- % retour à zéro avant stop ;
- % retour à zéro avant time-stop ;
- durée médiane / p90 ;
- MFE / MAE du spread ;
- PnL synthétique net de coûts avec hedge beta ;
- PF net ;
- distribution mensuelle ;
- concentration du PnL ;
- stabilité du beta ;
- pire séquence ;
- comparaison long-spread vs short-spread.

## Critères cheap-fail pré-enregistrés
Le V0 peut passer en `CANDIDATE` seulement si :

- au moins **20 événements par paire** et **50 agrégés** ;
- **les deux paires** ont un PnL net positif ; une seule paire gagnante ne valide pas l'hypothèse ;
- PF agrégé net **>= 1.20** ;
- taux de retour à zéro avant stop/time-stop **>= 60 %** agrégé ;
- aucun mois unique ne représente > **60 %** du PnL net total ;
- pas de dépendance évidente à un seul sens de spread ;
- coûts disponibles et intégrés.

Si les deux paires échouent ou si les coûts détruisent l'edge : `REJECT` sans tuning de seuils/fenêtres.

Si une paire seulement passe : résultat `INCONCLUSIVE / PAIR-SPECIFIC`, pas d'EA production et pas d'optimisation post-hoc.

## Ce que Codex ne doit PAS faire

- ne pas tester une grille de z-scores, fenêtres OLS ou time-stops ;
- ne pas ouvrir l'OOS ;
- ne pas sélectionner après coup le meilleur couple parmi 20 paires ;
- ne pas coder un EA MT5 deux-jambes avant le cheap-fail ;
- ne pas mélanger cette stratégie avec D017 Momentum ou D021 MICRO-REV.

## Séquencement
D022 est une piste suivante, **sans interrompre** la campagne v11.16.2, MiMo ou D021 déjà en file. Quand une capacité d'analyse est libre, exécuter l'event-study le moins coûteux possible sur les deux couples ci-dessus.
