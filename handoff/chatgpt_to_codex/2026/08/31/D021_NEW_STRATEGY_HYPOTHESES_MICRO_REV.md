# D021 — Nouvelles hypotheses de strategie

STATUT: ACTION_REQUISE

## CONSTAT

La file D021 attend une hypothese independante preregistree. ChatGPT avait deja identifie plusieurs directions de recherche distinctes du Momentum D017, et une nouvelle hypothese concrete a ete definie avant tout test: `MICRO-REV M1`.

Le but n'est pas de sauver ETH post hoc ni d'ajuster une strategie aux resultats deja vus. Il faut tester un phenomene distinct, multi-crypto, avec criteres geles avant observation des resultats.

## HYPOTHESE PRIORITAIRE — MICRO-REV M1

Phenomenologie visee: `shock -> exhaustion -> confirmation -> reversal court`.

Horizon: tres court, M1, quelques dizaines de secondes a quelques minutes.

Capteurs V0 a preregistrer avant event study/backtest:
- RSI(7) M1 — choix deja gele;
- amplitude/chute ou hausse anormale sur 1-3 minutes normalisee par ATR M1;
- extension du prix par rapport a une moyenne courte/EMA, normalisee par ATR;
- signe d'epuisement/rejet: meche, ralentissement du mouvement ou incapacité a prolonger le plus bas/haut;
- retournement du RSI, pas seulement niveau surachete/survendu;
- confirmation microstructurelle de reprise dans le sens du reversal;
- spread/execution acceptable.

Principe essentiel: `RSI bas = achat` est interdit. Un RSI qui continue d'accelerer vers le bas ne doit pas etre interprete comme une opportunite croissante. Le moteur doit chercher la transition de capitulation vers reprise.

## PREMIERE ETAPE SCIENTIFIQUE

Avant de coder un EA complet ou d'optimiser un seuil de score:
1. preregistrer les definitions d'evenement;
2. lancer une event study sur plusieurs cryptos liquides, au minimum BTCUSD, ETHUSD et SOLUSD si les historiques valides existent;
3. mesurer pour chaque evenement: MFE/MAE et comportement a +1/+3/+5/+10 minutes;
4. mesurer la probabilite d'atteindre +0.5 ATR avant -0.5 ATR (et symetriquement pour SELL), avec variantes de seuil preregistrees uniquement;
5. verifier si le phenomene existe sur plusieurs actifs et regimes avant toute integration Guardian;
6. ne pas utiliser l'OOS verrouille et ne pas ajuster les definitions apres observation des resultats sans nouvelle campagne explicitement separee.

Le score 0-100 peut etre construit ensuite comme representation continue des composants, mais il ne doit pas etre calibre apres coup pour rendre la courbe belle.

## AUTRES DIRECTIONS IDENTIFIEES

Directions secondaires deja identifiees lors de la recherche externe, a garder comme backlog si MICRO-REV ne passe pas le cheap-fail:
- relative-value / pairs / spread mean-reversion entre actifs crypto liquides;
- regime/volatility-aware momentum, distinct d'un simple empilement d'indicateurs;
- short mean-reversion / liquidity reversal autour de mouvements anormaux.

Ne pas prioriser pour Guardian MT5: HFT market making, MEV, funding arbitrage/cash-and-carry, qui sont mal adaptes a l'environnement prop/MT5 et a nos contraintes d'execution.

## IMPACT

D021 n'est plus sans hypothese. `MICRO-REV M1` fournit une piste independante du Momentum D017 et une logique potentiellement complementaire sur crypto.

## ACTION_CODEX

- Finir/recolter proprement le job MiMo actif sans doublon.
- Ensuite transformer `MICRO-REV M1` en protocole preregistre minimal et cheap-fail, en deleguant a MiMo l'analyse/preparation repetitives.
- Ne lancer un long backtest MT5 qu'apres preuve minimale de signal dans l'event study.
- Conserver le controle exact `_BT` D017 separe: il ne doit pas bloquer indefiniment la recherche de nouvelles strategies si son cout est disproportionne.

## NE_PAS_FAIRE

- Ne pas modifier Momentum D017 pour forcer des resultats crypto.
- Ne pas tuner RSI(7): il est gele pour cette V0.
- Ne pas choisir des seuils apres avoir vu quels seuils gagnent.
- Ne pas conclure qu'une strategie est bonne parce qu'elle marche sur un seul actif.
- Ne pas ouvrir ni exploiter l'OOS verrouille.
