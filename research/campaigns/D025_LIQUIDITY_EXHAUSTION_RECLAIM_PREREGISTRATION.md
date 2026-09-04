# D025 — Liquidity Exhaustion Reclaim (LER) — preregistration

Date: 2026-09-04
Status: PREREGISTERED / RESEARCH ONLY / NO LIVE ORDERS

## Hypothese

Une cassure de niveau n'est pas un signal contrarian en soi. L'hypothese testee est plus precise : apres le balayage d'un niveau objectif et une phase de pression/cascade anormale, l'edge eventuel apparait lorsque l'impact marginal de cette pression diminue, que le marche reintegre le niveau, puis montre une acceptation/retest compatible avec une cassure echouee.

La strategie doit rester distincte de Momentum et RSI Sniper :
- RSI Sniper = mean reversion court terme.
- Momentum = continuation.
- D025 LER = capitulation/exhaustion/reclaim mid-term.

## Architecture temporelle preregistree

- H4 : contexte.
- H1 : structure et niveaux objectifs.
- M15 : sweep, cascade, exhaustion, reclaim, acceptance/retest.
- M5 : autorise uniquement comme couche d'execution future, pas pour redefinir le setup de recherche.

Aucun time-stop ni plan de TP n'est fixe avant l'etude MFE/MAE.

## Niveaux admissibles V0

Les niveaux doivent exister avant l'evenement :
- Previous Day High / Low.
- Previous Week High / Low.
- Swing H1/H4 confirme par une regle mecanique definie avant validation.
- Extremes de range H1/H4 si la regle de range est definie ex ante.

Les nombres ronds sont exclus de V0 pour eviter de melanger les familles d'hypotheses.

## Machine d'etat conceptuelle

`IDLE -> LEVEL_WATCH -> SWEEP -> CASCADE -> EXHAUSTION -> RECLAIM -> RETEST/ACCEPTANCE -> VALID_SIGNAL`

V0 research peut s'arreter a `VALID_SIGNAL` et enregistrer un trade virtuel. Aucun ordre reel n'est autorise.

## Variables MT5 Core

Pour chaque evenement, enregistrer au minimum :
- symbole, side, type/niveau L, timestamp UTC;
- ATR H1;
- profondeur du sweep en ATR;
- range shock normalise;
- vitesse/return normalise;
- tick-volume relatif;
- temps passe hors du niveau;
- temps jusqu'au reclaim;
- acceptance M15 au-dessus/dessous du niveau;
- presence/qualite du retest;
- prix d'entree virtuelle et SL structurel sous/au-dessus de l'extreme du sweep avec buffer ATR preregistre;
- MFE/MAE et temps vers 1R/2R/3R/4R/5R a 1h/4h/8h/24h/48h.

## External Intelligence Bus — enrichissement crypto

Le bus externe est facultatif pour D025 Core et obligatoire uniquement pour les features `Crypto+` qui en dependent.

Donnees cibles V1 :
- spot price/return;
- perpetual price/return;
- open interest;
- liquidations long/short;
- funding;
- provenance/source;
- timestamp source;
- timestamp reception/availability;
- age de la donnee et indicateur de qualite/staleness.

Les donnees externes ne doivent jamais appeler directement une fonction de trading. Elles alimentent uniquement des observations normalisees consommees par une strategie.

## Principes fail-safe

1. Guardian production ne doit jamais dependre du bus externe pour ses fonctions de protection/risk/compliance.
2. Si le flux externe tombe, le Core MT5 continue de fonctionner.
3. Une feature Crypto+ qui exige une donnee absente/stale devient indisponible; aucune valeur ancienne ne doit etre reutilisee silencieusement.
4. Chaque echantillon externe doit etre horodate et rejouable. En backtest, l'invariant anti-lookahead porte sur le moment ou l'information etait effectivement disponible pour le systeme : `available_at_timestamp <= simulation_timestamp`. Un `source_timestamp` anterieur ne suffit pas si la donnee n'a ete recue que plus tard.
5. Pas de `WebRequest()` dans le coeur de decision si cela empeche la reproductibilite Strategy Tester; privilegier un collecteur/recorder local et un cache/fichier rejouable.
6. Les API externes sont lecture seule pour le projet; aucun token donnant le droit de trader n'est requis ni accepte.

## Metriques Crypto+ a etudier, sans poids fige

- chute d'open interest normalisee;
- z-score des liquidations longues/courtes;
- divergence de return perp vs spot;
- ratio liquidations / impact prix;
- decroissance de l'impact marginal malgre persistance du flux;
- funding comme contexte, pas comme signal suffisant.

Aucun score final ni poids n'est fixe avant event study. Interdit de choisir post hoc les poids qui maximisent le PnL.

## News / choc exogene

Les evenements macro/fondamentaux majeurs doivent etre etiquetes et etudies separement. V0 ne doit pas conclure qu'une cassure est une simple purge lorsque l'information fondamentale peut justifier une revalorisation durable.

## Plan incremental

### Etape 1 — External Intelligence Bus V1
Construire uniquement le collecteur/recorder et le schema de donnees. Aucun ordre et aucune integration de signal Guardian.

Gate de sortie :
- timestamps coherents UTC;
- source timestamp et availability timestamp distincts;
- reprise apres coupure;
- deduplication;
- staleness mesurable;
- historique compact rejouable;
- aucune cle de trading;
- tests sur BTC et ETH.

### Etape 2 — D025 observer
Implementer la machine d'etat LER en mode observation/trade virtuel avec uniquement les donnees MT5 Core. Enregistrer les evenements et MFE/MAE.

### Etape 3 — Crypto+ event study
Joindre les donnees externes aux evenements D025 sans fuite temporelle. Comparer Core vs Core+OI vs Core+liquidations vs Core+spot/perp vs combinaison preregistree.

### Etape 4 — Robustesse
Multi-actifs, periodes alternatives/OOS ferme, couts stresses, perturbation raisonnable des parametres, dependance aux meilleurs jours/trades, red-team.

### Etape 5 — Candidat Guardian
Uniquement si edge positif, stable, explicable et survivant aux couts. La gestion des sorties sera choisie a partir des distributions MFE/MAE preregistrees, pas avant.

## Interdits V0

- Aucun ordre live.
- Aucun tuning sur OOS.
- Aucun seuil choisi apres observation d'une performance favorable.
- Aucun poids opaque de type "IA score" non explicable.
- Aucun remplacement du Core par une dependance Internet.
- Aucune modification silencieuse de `production/guardian/`.

## Verdict initial

`PREREGISTERED / BUILD DATA INFRA FIRST`.

La prochaine action utile n'est pas de coder un BUY/SELL LER dans Guardian, mais de construire un bus externe V1 fiable et enregistrable, puis de collecter les observations qui permettront de falsifier ou confirmer l'hypothese.