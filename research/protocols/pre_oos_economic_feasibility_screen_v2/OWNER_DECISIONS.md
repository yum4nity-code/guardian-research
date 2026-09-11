Reprends le travail Issue #3 dans :

D:\MT5_Backtests\guardian-economic-audit-issue3

Le design méthodologique du PRE-OOS ECONOMIC FEASIBILITY SCREEN est maintenant FIGÉ.
Ne rediscute pas les choix ci-dessous et ne les optimise pas en fonction des résultats.

OBJECTIF

Mettre à jour le protocole local avec les décisions finales ci-dessous, implémenter le validator économique, écrire et exécuter les tests obligatoires, effectuer un smoke test sans calibration, puis réaliser un cold audit du CODE RÉEL.

Seulement si tout est PASS :
- commit/push
- incrémenter proprement la queue
- ajouter le job immutable
- laisser l’orchestrateur Guardian déjà actif le lancer automatiquement

Ne lance aucun doublon manuel.

AUCUN LIVE.
AUCUN REAL ACCOUNT.
AUCUN ACCÈS AUX DONNÉES 2026.

==================================================
DÉCISIONS MÉTHODOLOGIQUES FINALES
==================================================

POPULATION

- Tester les 500 survivants publiés R4.
- Les 32 frozen representatives sont uniquement des annotations structurelles.
- Ne pas limiter le screen aux 32.
- Ne supprimer aucun candidat parce qu’il n’appartient pas aux 32.

DOMAINE TEMPOREL

SUPPRIMER du protocole principal :
- filtre général 08h–20h
- restriction générale lundi–vendredi ajoutée artificiellement
- interdiction générale de franchir minuit

Ces restrictions ne faisaient pas partie des règles R4 et ne doivent pas casser artificiellement un edge.

Respecter les timestamps et sessions réellement disponibles dans le dataset d’origine du candidat.

Un trade peut franchir minuit.

Mesurer descriptivement :
- overnight exposure
- weekend exposure si applicable

Protection absolue :
aucun trade ne peut demander une donnée ou une sortie en 2026.

Pour les métriques par année / semestre :
un trade traversant une frontière d’évaluation ne doit pas être liquidé artificiellement.
Il est simplement exclu de la métrique de sous-période concernée si nécessaire.

==================================================
TIMING CAUSAL D’ENTRÉE
==================================================

AUCUNE latence artificielle +60 secondes dans le scénario principal.

Définition :

signal_available_at = bar_open_time + timeframe

entry_reference =
première ouverture M1 RAW dont le timestamp est >= signal_available_at

Exemples obligatoires :

Signal M1 :
barre 10:00–10:01
signal disponible 10:01
entrée de référence = open M1 raw 10:01

Signal M5 :
barre 10:00–10:05
signal disponible 10:05
entrée de référence = open M1 raw 10:05

La latence supplémentaire +60 s peut être calculée comme analyse descriptive/stress secondaire si utile,
mais ne doit PAS être un critère éliminatoire principal.

Ajouter tests explicites anti-lookahead et anti-off-by-one M1/M5.

==================================================
NEWS-CLEAN
==================================================

Le mécanisme news-clean existant est considéré causal pour ce screen :

- calendrier économique MT5
- événements USD
- importance HIGH
- fenêtre preregistrée -5/+5 minutes
- suppression d’une barre selon intersection temporelle avec le masque
- aucune utilisation du résultat économique ou du mouvement de prix futur pour décider de la suppression

Pour un candidat NEWS-CLEAN :

- conserver son signal sur dataset news-clean
- conserver son horizon R4 en nombre de barres news-clean admissibles
- compter ces barres causalement au fil du temps
- ne pas utiliser de connaissance anticipée de la position future de la h-ième barre clean

La grille de prix économique entrée/sortie reste M1 RAW admissible.

Documenter clairement cette distinction.

==================================================
SORTIE
==================================================

Préserver l’horizon original R4 du candidat.

RAW :
horizon en barres du dataset raw d’origine.

NEWS-CLEAN :
horizon en barres admissibles du dataset news-clean d’origine.

Une fois le moment de sortie causalement déterminé :
utiliser la première référence de prix M1 RAW admissible correspondante.

Ne pas inventer SL, TP, trailing ou time-stop.

Aucune optimisation de sortie.

==================================================
OVERLAP
==================================================

Chaque candidat est testé séparément.

Par candidat :
- maximum une position ouverte ou pending
- nouveau signal du même candidat pendant cette position = ignoré
- pas de pyramiding
- pas de portefeuille implicite entre candidats

Documenter le nombre de signaux ignorés pour overlap.

==================================================
SIZING
==================================================

Taille fixe :
1 once XAU.

Aucun levier.
Aucune capitalisation.
Aucun risk sizing optimisé.

Le but est de mesurer l’épaisseur économique de l’edge, pas la rentabilité d’un compte.

==================================================
COÛTS
==================================================

FUNDEDNEXT :
UNRESOLVED / DISABLED.

Ne calculer aucun résultat FundedNext.
Ne pas inventer ses commissions.

PROFIL A :

FTMO COMMISSION + E1 SIMULATED EXECUTION

- commission métaux FTMO : 0.0007 % du notional PAR CÔTÉ
- spread simulé COMPLET : 2 bps
- slippage : 1 bp par côté

IMPORTANT :
“full spread 2 bps” =
1 bp défavorable à l’entrée
+
1 bp défavorable à la sortie

Ne pas facturer 2 bps à chaque côté.

PROFIL B :

CONSERVATIVE STRESS

- commission : 0.0014 % du notional par côté
- full spread : 5 bps
- slippage : 2 bps par côté

Pour full spread 5 bps :
2.5 bps défavorables à l’entrée
+
2.5 bps défavorables à la sortie.

Spread, commission et slippage doivent apparaître séparément dans les résultats.

Les spreads/slippages sont des hypothèses de feasibility simulation.
Ne jamais les présenter comme fills historiques observés.

==================================================
GATES ÉCONOMIQUES FIGÉS
==================================================

Un candidat PASS le feasibility screen uniquement s’il satisfait TOUS les critères applicables :

TRADE COUNT

- >=100 trades exécutables en 2024
- >=100 trades exécutables en 2025
- >=40 trades exécutables H1 2025
- >=40 trades exécutables H2 2025

E1

Net > 0 :
- 2024
- 2025
- H1 2025
- H2 2025

STRESS

Net > 0 :
- 2024
- 2025

ROBUSTESSE OUTLIER

Sous STRESS en 2025 :

retirer le meilleur trade POSITIF du candidat

et exiger encore :

Net 2025 > 0

Aucun autre seuil éliminatoire.

Ne pas inventer :
- PF minimum
- drawdown maximum
- win rate minimum

PF, drawdown, win rate, expectancy, exposure etc. restent descriptifs.

==================================================
MÉTRIQUES À PRODUIRE
==================================================

Par candidat :

- stable candidate ID
- signature R4 complète
- dataset source
- raw/news-clean
- timeframe
- direction
- feature
- quantile / threshold
- horizon
- session gate R4 s’il existe

- signals total
- executable trades
- ignored overlap signals
- excluded boundary trades
- missing-reference trades
- BLOCKED_DATA occurrences

Pour chaque profil :
- gross PnL
- spread cost
- commission cost
- slippage cost
- net PnL

Par :
- 2024
- 2025
- H1 2025
- H2 2025

Plus :
- expectancy
- PF
- win rate
- max drawdown
- exposure
- overnight exposure
- weekend exposure
- best trade
- worst trade
- stress 2025 ex-best-trade net
- PASS / FAIL
- raisons exactes du FAIL

==================================================
2026 : CONTRAT ABSOLU
==================================================

Utiliser UNIQUEMENT le manifeste explicite des quatre datasets certifiés pré-2026.

- pas de recursive scan
- pas de glob
- pas de broad roots
- pas de read-then-filter d’un fichier 2026
- pas d’auto-discovery
- chemin non manifesté = refus AVANT ouverture
- hash incorrect = refus AVANT utilisation
- aucune recherche de “next quote” hors des fichiers autorisés

Un signal fin 2025 qui nécessiterait une référence en 2026 :
EXCLUDED_BOUNDARY

Aucune ouverture de fichier 2026.

==================================================
PROVENANCE
==================================================

Conserver :

- hash du résultat R4 source
- canonical candidate signature
- hashes des quatre datasets
- commit SHA
- protocol hash
- policy hash
- version du validator
- cost profile version
- mapping temporel
- overlap rule
- sizing rule

Les 500 R4 doivent rester reproductibles et accessibles.

==================================================
INFRASTRUCTURE
==================================================

Utiliser atomic JSON robuste avec retry/backoff PermissionError Windows.

Ne pas reproduire le os.replace non retrying de la consolidation initiale.

Progress file :
- heartbeat régulier
- completed / total
- candidate actuel
- phase actuelle
- survivant count provisoire si possible
- updated_at_utc

Distinguer explicitement :
- PASS scientifique
- FAIL scientifique
- ERROR infrastructure
- BLOCKED_DATA

Ne pas masquer les exceptions.

==================================================
TESTS AVANT RUN COMPLET
==================================================

Tests obligatoires au minimum :

- 2026 inaccessible
- path non manifesté refusé avant ouverture
- hash mismatch refusé
- M1 signal timing
- M5 signal timing
- anti-lookahead
- horizon RAW
- horizon NEWS-CLEAN
- masque news causal
- boundary 2025 -> exclusion sans accès 2026
- overlap
- signal contradictoire
- PnL long
- PnL short
- full spread non doublé
- commission par côté
- slippage par côté
- best-trade removal
- H1/H2 attribution
- drawdown
- PF
- deterministic rerun
- atomic PermissionError retry
- malformed dataset fail closed
- 500 candidates ingested
- 32 frozen remain annotation only

==================================================
SMOKE
==================================================

Faire un smoke test réduit sur données autorisées.

Le smoke doit vérifier :
- causal timing
- costs
- horizons
- overlap
- outputs
- heartbeat
- absence 2026

Ne regarder le smoke que pour vérifier le fonctionnement.
Ne calibrer aucun paramètre à partir de ses résultats.

==================================================
SECOND COLD AUDIT
==================================================

Après implémentation/tests/smoke, auditer le code réel.

Question obligatoire :

“Si un candidat PASS ce screen, avons-nous suffisamment démontré que son edge mérite un backtest réaliste plus coûteux, sans prétendre qu’il est déjà rentable ou validé ?”

Si NON :
- ne rien queue
- ne lancer aucun run complet
- rapporter BLOCKED

Si OUI et tous tests PASS :
- commit/push protocole + validator + policy + tests + audit
- incrémenter queue generation
- ajouter job immutable PRE-OOS ECONOMIC FEASIBILITY SCREEN
- dépendance appropriée
- aucun job OOS 2026 en dépendance automatique
- laisser l’orchestrateur existant PID 7580 lancer le job
- ne pas lancer manuellement un second process

==================================================
RETOUR ATTENDU
==================================================

Retourne uniquement :

- verdict second cold audit
- nombre tests PASS / FAIL
- smoke PASS / FAIL
- commit SHA
- queue generation
- job ID / revision
- queued ou réellement lancé
- PID si lancé
- progress path
- ETA
- anomalies restantes

Pas de long journal.

Ne déploie rien sur compte live/réel.