# Guardian — historique du projet et travail accompli

## Objet

Guardian est un projet personnel de recherche quantitative et d’exécution automatisée sur marchés financiers. Son objectif a évolué : au départ, trouver une stratégie rentable et la faire fonctionner sur un compte prop firm ; ensuite, construire un laboratoire capable de tester proprement des hypothèses, d’écarter les faux edges et de protéger l’exécution réelle.

Ce document distingue :

- les éléments vérifiables dans GitHub ;
- les éléments documentés dans les échanges de travail ;
- les estimations ;
- les éléments encore impossibles à chiffrer précisément.

GitHub ne marque pas le début de Guardian. Il marque le passage à une organisation versionnée, traçable et collaborative.

## 1. Avant GitHub : naissance et première phase

Avant la création du dépôt, Guardian a été construit progressivement autour de plusieurs besoins :

- automatiser les entrées et sorties ;
- tester des stratégies sur MT5 ;
- respecter les contraintes de comptes prop firm ;
- gérer le risque, les stops, les take-profits et les limites de drawdown ;
- éviter qu’un problème technique transforme une position en risque incontrôlé ;
- comprendre si les résultats venaient réellement d’un edge ou d’un artefact de données, de timing ou de backtest.

Cette première période comprend les premières versions de l’EA, les essais manuels, les premiers backtests, les adaptations aux comptes FTMO/FundedNext, les tests de risque et les premières recherches sur XAU, FX et crypto.

La durée exacte de cette période n’est pas reconstituable uniquement par GitHub. Elle doit être présentée comme une période de travail réelle documentée par les échanges, mais avec un temps humain à confirmer.

## 2. Passage à une architecture de recherche

Le projet s’est ensuite séparé en plusieurs couches :

1. Guardian production : exécution et protections live.
2. Recherche : hypothèses, scanners, backtests et expériences.
3. Données : historiques, provenance, hashes et contrôles de couverture.
4. Orchestration : queue de tâches, workers, checkpoints et reprise après interruption.
5. Audit : cold reviews, tests synthétiques, contrôle de fuite et validation indépendante.
6. Handoffs : transmission durable entre l’utilisateur, ChatGPT et Codex.

Cette séparation a permis de faire évoluer le projet sans modifier silencieusement l’EA utilisée en production.

## 3. Évolution technique majeure

### Vitesse de calcul

Au début, environ une année de backtest demandait environ 25 minutes.

Après les évolutions du pipeline :

- lecture plus directe des historiques ;
- pré-agrégation des données ;
- séparation des scanners et de MT5 ;
- exécution Python lorsque MT5 n’apporte pas d’information supplémentaire ;
- parallélisation contrôlée ;
- sorties compactes et standardisées ;
- checkpoints et reprises par tranches ;

une année représentative peut désormais être traitée en quelques secondes dans les scanners adaptés.

| Indicateur | Ancienne phase | Phase récente |
|---|---:|---:|
| Temps pour une année de backtest | environ 25 min | quelques secondes sur les scanners optimisés |
| Mode de travail | souvent manuel et monolithique | loaders, scanners, workers et artefacts séparés |
| Reprise après interruption | coûteuse ou manuelle | checkpoint et reprise contrôlée |
| Résultats | rapports hétérogènes | CSV/JSON/Markdown auditables |
| Contrôle de causalité | partiel | gate explicite et tests synthétiques |
| Production/recherche | risque de mélange | séparation formelle |

Le chiffre « quelques secondes » doit être associé au moteur et au jeu de données concernés ; il ne signifie pas que tous les backtests MT5 complets ont cette vitesse.

### Tests et contrôle qualité

Le projet est passé d’une logique principalement orientée résultat à une logique de preuve :

- tests synthétiques de causalité ;
- tests de timestamp ;
- contrôle de disponibilité des données ;
- contrôle de cadence et de doublons ;
- hashes de fichiers ;
- séparation découverte/confirmation/OOS ;
- cold reviews indépendantes ;
- refus fermé en cas d’ambiguïté ;
- interdiction de l’accès opportuniste à 2026.

Sur l’infrastructure Edge Atlas récente :

- preflight : 14/14 tests synthétiques réussis ;
- adaptateur EA01 : 28/28 tests synthétiques réussis ;
- py_compile : réussi ;
- cold review : réussie ;
- aucune donnée historique réelle lue pendant le preflight ;
- aucune donnée 2026 ouverte.

## 4. Données accumulées et contrôlées

### XAUUSD

Le projet a construit une base Dukascopy XAUUSD de longue durée.

Chiffre vérifié dans les artefacts R15 :

- 5 518 journées de données BID M1 validées ;
- couverture allant jusqu’à 2025 ;
- contrôle des jours admissibles ;
- hashes conservés ;
- 2026 protégée et exclue des recherches courantes.

Les données XAU ont aussi révélé une difficulté importante : un historique disponible n’est pas automatiquement un historique causalement fiable. Les conventions de serveur, les blocs HCC, les timestamps et la disponibilité réelle des OHLC doivent être vérifiés séparément.

### Crypto

Le projet a utilisé plusieurs sources crypto selon les phases :

- BTC et ETH ;
- données spot et dérivées ;
- open interest, funding et liquidations dans certaines infrastructures ;
- données Bybit et Binance selon la provenance et la période.

Une ancienne phase Bybit/OI a documenté :

- 210 528 lignes alignées par symbole ;
- 100 % de couverture OI sur la phase concernée ;
- aucun doublon temporel ;
- aucune rupture non expliquée de cadence 5 minutes ;
- 2026 maintenue hors du jeu de recherche.

Pour Edge Atlas, les sources présentant une contamination 2026 ou une provenance ambiguë ont été exclues. La source actuellement admise est plus restrictive : XAUUSD Dukascopy pré-2026 et Binance spot BTC/ETH M5 sur 2024–2025.

## 5. Recherche de stratégies

Le projet n’a pas seulement cherché à maximiser un PnL. Il a testé des familles entières et les a parfois fermées.

### Familles étudiées ou documentées

- momentum et continuation ;
- breakout ;
- ORB et effets de session ;
- TSMOM ;
- réversion ;
- volatilité et compression ;
- structures de bougies ;
- RSI et oscillateurs ;
- relative value BTC/ETH ;
- saisonnalité ;
- chocs négatifs ;
- liquidité et exhaustion ;
- open interest, funding et liquidations ;
- effets cross-asset ;
- stratégies spécifiques XAU et crypto.

### Volume de recherche

Une campagne de recherche a exploré 250 000 combinaisons dans un espace gelé.

Ce nombre ne doit pas être présenté comme 250 000 edges indépendants : beaucoup de variantes appartenaient aux mêmes familles corrélées. Cette expérience a conduit à une correction méthodologique importante : rechercher davantage de mécanismes réellement distincts plutôt que multiplier les paramètres d’une même idée.

### Résultats négatifs utiles

Plusieurs branches ont été fermées après confirmation ou audit :

- R4/R5 XAU ;
- R8 relative value ;
- R9 saisonnalité/session crypto ;
- R10 tendance multi-jours ;
- R11 lead-lag ;
- R12 compression breakout ;
- R13 failed-breakout rejection ;
- R14 réplication du choc négatif Bitcoin ;
- R15 réplication intraday GLD/XAU ;
- plusieurs familles D017, D021, D022, D023, D025 et anciennes familles de recherche.

Ces rejets ne sont pas du temps perdu. Ils ont permis d’identifier :

- les effets qui disparaissent hors échantillon ;
- les résultats dépendants d’un flux particulier ;
- les coûts qui détruisent un avantage brut ;
- les sorties mal adaptées à une bonne entrée ;
- les faux effets liés à la disponibilité des données ;
- les erreurs de synchronisation et de look-ahead.

## 6. Guardian lui-même a évolué

L’EA est passé d’un système de règles et d’exécution à une architecture davantage contrôlée :

- moteurs séparables ;
- switches de stratégies ;
- gestion du risque ;
- limites de volume ;
- protections de compte ;
- diagnostics explicites ;
- notifications de cycle de vie ;
- contrôle des requêtes et retries ;
- invariants compilés fail-closed ;
- refus d’exécution lorsqu’un preset ou une configuration critique est incohérent ;
- séparation des recherches expérimentales et du Guardian live.

Des validations techniques ont également porté sur :

- les entrées et sorties ;
- les stops ;
- les take-profits ;
- le break-even ;
- le trailing ;
- les time-stops ;
- les volumes minimum et maximum ;
- les différences entre flux de données ;
- les contraintes de comptes prop firm.

Un résultat de backtest positif n’a jamais suffi à autoriser une modification de production.

## 7. Le tournant scientifique

Le projet a connu plusieurs erreurs ou limites qui ont changé sa méthode :

1. Des résultats pouvaient être rentables à cause d’un flux particulier.
2. Une donnée pouvait être présente dans un fichier sans être disponible au moment de la décision.
3. Une belle performance pouvait disparaître en confirmation indépendante.
4. Une stratégie pouvait avoir une bonne entrée mais une mauvaise sortie.
5. Des millions de variantes ne constituaient pas des millions d’hypothèses indépendantes.
6. Un résultat MT5 et un résultat Python n’étaient comparables qu’avec une provenance et un feed équivalents.
7. Les données 2026 doivent rester protégées jusqu’à ce que toutes les étapes précédentes soient franchies.

Le laboratoire fonctionne maintenant selon :

IDÉE → PRÉ-ENREGISTREMENT → TEST SYNTHÉTIQUE → CHEAP-FAIL → DÉCOUVERTE → CONFIRMATION → ROBUSTESSE → PRÉ-OOS → OOS PROTÉGÉ → EXÉCUTION → CANDIDAT PRODUCTION.

## 8. Edge Atlas et EA01

La phase actuelle cherche dix hypothèses réellement distinctes, sans reprendre les familles déjà fermées.

La première hypothèse activée est EA01 :

- XAUUSD ;
- réversion courte sur M5 ;
- trois barres de même direction ;
- entrée opposée au prochain open ;
- stop fixe 1,5 ATR ;
- sortie temporelle après trois barres ;
- découverte 2017–2022 ;
- confirmation et 2025 non ouverts ;
- 2026 interdit ;
- deux variantes maximum ;
- exécution bornée à quelques minutes.

L’adaptateur EA01 a passé :

- 28/28 tests synthétiques ;
- compilation Python ;
- cold review ;
- contrôle de manifest, hashes, période et protection 2026.

La génération 115 a ensuite été activée dans le control-plane. Son résultat devra être traité comme un cheap-fail, pas comme une validation.

## 9. Temps passé

Le temps total exact ne peut pas être déduit de GitHub seul, car Guardian a commencé avant le dépôt.

La présentation honnête doit séparer :

| Catégorie | État |
|---|---|
| Temps humain avant GitHub | réel, mais à reconstituer par échanges et souvenirs |
| Temps humain documenté dans les journaux | partiel ; plusieurs entrées indiquent NOT QUANTIFIED |
| Temps humain depuis GitHub | calculable par sessions et commits, avec prudence |
| Temps machine/backtests | partiellement documenté par campagnes et logs |
| Temps workers autonomes | à distinguer du temps humain |
| Temps total projet | estimation basse et fourchette, pas un chiffre exact |

Aucune durée humaine ne doit être inventée. Le document final pourra fournir :

- un minimum prouvé ;
- une estimation prudente ;
- une fourchette probable ;
- une liste des périodes non quantifiables.

## 10. Ce que le projet a réellement produit

Même si aucun edge final n’est encore validé, Guardian a produit :

- une EA capable d’opérer avec des protections dédiées ;
- une architecture de recherche autonome ;
- une base XAU longue et contrôlée ;
- des données crypto alignées et auditées ;
- des dizaines de protocoles et campagnes ;
- des centaines de milliers de variantes explorées dans des espaces gelés ;
- des tests de causalité et de provenance ;
- une séparation recherche/production ;
- un mécanisme de queue et de reprise ;
- des audits indépendants ;
- une méthode pour fermer proprement les faux edges ;
- un nouveau pipeline Edge Atlas avec EA01 activé comme premier cheap-fail.

La réalisation principale n’est donc pas encore « une stratégie magique ». C’est la transformation d’une idée de trading en laboratoire capable de distinguer :

- un vrai phénomène ;
- un résultat descriptif ;
- un artefact de données ;
- une erreur de timing ;
- une stratégie non robuste ;
- une hypothèse qui mérite une confirmation.

## Conclusion

Guardian représente plusieurs phases de travail :

1. construire une EA utilisable ;
2. la tester sur des marchés et des comptes réels ou simulés ;
3. découvrir ses limites ;
4. créer un laboratoire de données ;
5. automatiser la recherche ;
6. formaliser les protocoles ;
7. apprendre à rejeter les résultats trompeurs ;
8. chercher maintenant des mécanismes vraiment indépendants.

Le projet n’est pas arrivé au bout de son objectif financier, mais il a franchi un changement de nature : il ne dépend plus seulement de l’intuition ou d’un backtest isolé. Il dispose désormais d’une infrastructure capable de documenter, tester, invalider et éventuellement confirmer un edge de manière beaucoup plus sérieuse.
