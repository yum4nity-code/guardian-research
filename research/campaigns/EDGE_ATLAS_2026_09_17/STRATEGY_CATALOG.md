# Edge Atlas — catalogue pré-enregistré

Campaign: EDGE-ATLAS-2026-09-17
Status: PREREGISTERED / NO RESULTS OPENED
Protected year: 2026 — forbidden.

## Exclusions

Closed or quarantined: R4/R5 XAU, R8-R15, D017, D021, D022, D023, D025 trading construction, all R33/R34/R35 outputs, FundedNext XAU signal feed and all 2026 files. No rescue, renaming or parameter continuation is allowed.

## Catalogue des 20 phénomènes

| ID | Mécanisme | Classe | Données / TF | Entrée / sortie gelées | Chronologie | Rejet | Variantes |
|---|---|---|---|---|---|---|---:|
| EA01 | Réversion courte après autocorrélation signée | CLOSE_REPLICATION | XAU M5 | 3 barres même sens, inverse next-open; 3 barres ou stop 1.5 ATR | 2017-22 / 2023-24 / 2025 | N<60, PF stress<1, signe instable | 2 |
| EA02 | Réversion gérée par état de volatilité | ADAPTATION | XAU M15 | EA01 filtrée par ratio vol court/long fixé; 4 barres ou stop | 2017-22 / 2023-24 / 2025 | fuite, N insuffisant, aucun mécanisme incrémental | 2 |
| EA03 | Rejet après choc et clôture en queue | CLOSE_REPLICATION | XAU M5 | range >=3 ATR, clôture dans queue opposée; inverse next-open; 4 barres/stop | 2017-22 / 2023-24 / 2025 | duplication breakout, N insuffisant, coût | 2 |
| EA04 | Persistance d’une transition de volatilité | EXACT_REPLICATION | XAU H1 | vol 3 barres > baseline 20; continuation next-open; 6 barres/stop | 2017-22 / 2023-24 / 2025 | signe instable ou coût | 2 |
| EA05 | Distribution conditionnelle au weekday | CLOSE_REPLICATION | XAU H1 | effet weekday pré-déclaré, premier H1 après frontière UTC; 4 barres | 2017-22 / 2023-24 / 2025 | disparaît par année ou overlap session | 2 |
| EA06 | Divergence prix-open interest | ADAPTATION | BTC Bybit M5+OI | high prix 20 barres sans high OI; inverse next-bar; 12 barres/stop | 2024 / 2025 | OI stale, N<100, stress | 2 |
| EA07 | Flush OI avec acceptation du prix | ADAPTATION | BTC Bybit M5+OI | baisse OI fixe, prix dans range 3 barres; direction next-bar; 12 barres/stop | 2024 / 2025 | overlap D025, causalité, N | 2 |
| EA08 | État de volatilité relative ETH/BTC | ADAPTATION | ETH+BTC Bybit M5 | ratio vol relatif fixé; trade état prédéfini; 12 barres | 2024 / 2025 | désalignement ou N | 2 |
| EA09 | État de liquidité weekend crypto | ADAPTATION | BTC Bybit M5 | weekend + range 12 barres > baseline; continuation; 12 barres | 2024 / 2025 | faible N ou masque venue | 2 |
| EA10 | Transmission de volatilité BTC vers XAU | ADAPTATION | BTC+XAU M15 | choc vol BTC, XAU calme, XAU confirme sa propre clôture; 8 barres | 2017-22 / 2023-24 / 2025 | duplication R11, timing, N | 2 |
| EA11 | Imbalance corps/mèche en rejet | CLOSE_REPLICATION | XAU M15 | bandes corps/mèche préfixées; inverse next-open; 4 barres/stop | 2017-22 / 2023-24 / 2025 | duplication, sensibilité, coût | 2 |
| EA12 | Clustering de volatilité directionnel | EXACT_REPLICATION | XAU H1 | vol 5 > médiane 50 et signe précédent; continuation; 6 barres/stop | 2017-22 / 2023-24 / 2025 | instable ou PF stress<1 | 2 |
| EA13 | Réversion close-to-open hors session | CLOSE_REPLICATION | XAU H1 | rendement UTC précédent extrême; inverse premier H1 suivant; 4 barres | 2017-22 / 2023-24 / 2025 | duplication session ou frontière | 2 |
| EA14 | Dépendance sérielle normalisée multi-horizon | ADAPTATION | XAU M15 | motif de 4 rendements fixé; direction next-bar; horizon fixe | 2017-22 / 2023-24 / 2025 | correction multiplicité échoue | 2 |
| EA15 | Divergence prix-OI ETH | ADAPTATION | ETH Bybit M5+OI | même définition gelée que EA06; inverse next-bar; 12 barres | 2024 / 2025 | pas de réplication cross-asset ou N | 2 |
| EA16 | Choc de volatilité commun BTC/ETH et réponse relative | ADAPTATION | BTC+ETH M5 | choc commun, résidu relatif après clôture; 12 barres | 2024 / 2025 | duplication R11 ou pas de résidu | 2 |
| EA17 | Activité tick et efficacité de clôture | ADAPTATION | XAU M5 si volume prouvé | état activité + efficiency; continuation next-bar | 2017-22 / 2023-24 / 2025 | provenance volume | 2 |
| EA18 | Flux frontière mois/trimestre | CLOSE_REPLICATION | XAU H1 | derniers/premiers jours, signe antérieur fixé; next-open | 2017-22 / 2023-24 / 2025 | concentration ou frontière | 2 |
| EA19 | Asymétrie après choc bilatéral | ADAPTATION | XAU M5 | 2 grandes barres opposées + confirmation; inverse next-bar | 2017-22 / 2023-24 / 2025 | duplication EA03/R13 ou N | 2 |
| EA20 | Volatilité weekend ETH | ADAPTATION | ETH Bybit M5 | état weekend + range; direction next-bar; 12 barres | 2024 / 2025 | faible N, masque ou coût | 2 |

Shortlist gelée: EA01, EA02, EA03, EA04, EA06, EA07, EA08, EA11, EA12, EA15. Au moins six sont indépendantes des familles breakout, ORB, session momentum, TSMOM et RSI; aucune n’est validée.

Tous les scanners devront exporter événements bruts, MFE/MAE, coûts nominaux/stressés, ventilation annuelle/actif, concentration des meilleurs trades, perturbations et contrôle de fuite temporelle.