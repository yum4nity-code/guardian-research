# Guardian — installation reproductible et cycle de vie des donnees externes

Date initiale: 2026-09-04
Statut: documentation produit/recherche vivante

## Objectif

Documenter des maintenant toute procedure necessaire pour installer, reproduire, diagnostiquer et, a terme, distribuer commercialement Guardian avec son External Intelligence Bus (EIB).

Principe: aucune etape importante ne doit dependre de la memoire d'une conversation. Une machine neuve doit pouvoir etre reconstruite a partir du depot, des dependances et de cette documentation.

## 1. Architecture actuelle de recherche

Deux emplacements sont volontairement separes:

- code Git local: `D:\MT5_Backtests\guardian-research\`
- donnees externes runtime/recherche: `D:\MT5_Backtests\Research\ExternalIntelligence\`

Le depot Git contient le code, le schema, les tests, les manifests et la documentation. Les donnees de marche volumineuses restent locales et ne doivent pas etre poussees en masse sur GitHub.

Le collecteur EIB V1 est read-only. Il utilise les interfaces publiques Bybit et n'accepte aucune cle API de trading.

## 2. Bootstrap Windows depuis une machine sans Git

### 2.1 Installer Git

Ouvrir PowerShell puis executer:

```powershell
winget install --id Git.Git -e --source winget
```

Fermer puis rouvrir PowerShell afin que `git.exe` soit visible dans le `PATH`.

Verification:

```powershell
git --version
```

### 2.2 Recuperer le depot prive

```powershell
cd D:\MT5_Backtests
git clone https://github.com/yum4nity-code/guardian-research.git guardian-research
```

Le depot etant prive, GitHub peut demander une authentification dans le navigateur ou via le gestionnaire d'identifiants Git.

Pour une machine deja clonee:

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
```

`git pull` signifie simplement: synchroniser la copie locale avec la version courante du depot GitHub.

## 3. Lancer le smoke EIB V1

Depuis PowerShell:

```powershell
cd D:\MT5_Backtests\guardian-research\research\external_intelligence
.\START_EIB_SMOKE_V1.cmd
```

Le lanceur:

1. cree un environnement Python local `.venv` si necessaire;
2. installe/verifie `aiohttp` depuis `requirements.txt`;
3. lance `smoke_v1.py` pendant 35 minutes;
4. collecte BTC et ETH;
5. ecrit les donnees dans `D:\MT5_Backtests\Research\ExternalIntelligence\`;
6. produit un resume final et un `health.json`.

Aucun ordre MT5 n'est envoye par cette procedure.

## 4. Donnees actuellement stockees

Le collecteur ecrit un fichier JSONL par jour UTC:

`bybit_eib_v1_YYYYMMDD.jsonl`

Chaque ligne est une observation autonome conforme a `research/external_intelligence/schema_v1.json`.

Sont notamment enregistres:

- prix spot BTC/ETH;
- prix perpetual BTC/ETH;
- open interest;
- funding;
- liquidations long/short publiques recues;
- timestamps source, reception et `available_at`;
- qualite/staleness;
- provenance/provider.

Le fichier `health.json` contient l'etat courant du collecteur.

## 5. Politique de retention — etat actuel

**Pendant la phase de recherche D025, aucune suppression automatique n'est autorisee.**

Raison: les timestamps de reception, trous de connexion, liquidations et transitions de health sont des donnees historiques que nous ne pourrons pas reconstruire exactement a posteriori. Elles sont donc plus precieuses qu'un simple historique OHLC telechargeable.

La taille reelle journaliere sera mesuree sur le smoke puis sur plusieurs jours avant de figer une politique commerciale.

### Mesure reelle V1 du 2026-09-04

Smoke live BTC+ETH:
- duree observee: ~35 minutes;
- fichier JSONL: `1.991 MB`;
- extrapolation brute au meme rythme: ~`81.9 MB/jour` non compresse;
- ~`2.40 GB / 30 jours`;
- ~`7.20 GB / 90 jours`;
- ~`29.2 GB / an`.

Ces chiffres sont une extrapolation brute de V1 et ne constituent pas encore une taille produit definitive.

Le smoke a aussi revele un bruit de stockage: les enregistrements `health` ont ete produits toutes les ~5 secondes (420 par symbole en 35 minutes), alors que la cible logique est changement d'etat + heartbeat beaucoup plus rare. Leur suppression/reduction devrait faire baisser le volume; l'effet exact devra etre mesure apres correction plutot que suppose.

La compression gzip n'est pas encore mesuree sur ce dataset reel. Toute estimation de gain de compression reste donc provisoire jusqu'a un test empirique sur fichier ferme.

## 6. Politique d'archivage cible

Decision d'architecture retenue pour la prochaine brique, a implementer apres validation du smoke V1:

1. Le fichier du jour UTC reste en `.jsonl` non compresse pendant qu'il est actif.
2. Apres cloture du jour UTC, le fichier devient eligible a l'archivage.
3. L'archive V1 cible est `.jsonl.gz` (gzip), choisi initialement car il est standard, streamable, disponible dans la bibliotheque Python et simple a reproduire.
4. Avant suppression du `.jsonl` source, l'archive doit etre relue/testee et son hash consigne localement.
5. Une archive corrompue ne doit jamais remplacer la seule copie valide.
6. Le replay devra pouvoir lire directement les fichiers archives ou les materialiser temporairement sans modifier les timestamps.

Le ZIP n'est pas le format principal recommande pour les donnees quotidiennes: gzip correspond mieux a un flux JSONL journalier et permet un pipeline plus simple. Un ZIP de lots pourra eventuellement etre utilise pour export/sauvegarde manuelle.

## 7. Duree de retention cible

Deux politiques doivent rester distinctes.

### Recherche Guardian

- retention actuelle: **indefinie / suppression manuelle seulement** jusqu'a validation de D025 et mesure du cout disque;
- ne jamais effacer une periode ayant servi a un resultat de recherche publie sans conserver le dataset/hash necessaire a sa reproductibilite.

### Futur produit commercial

Politique provisoire a valider apres mesure reelle:

- donnees actives: fichier du jour;
- archives locales compressees: retention configurable;
- valeur par defaut envisagee: 90 jours;
- option laboratoire/recherche: 365 jours ou illimite;
- limite disque configurable en plus de la limite temporelle;
- nettoyage uniquement des archives deja validees, jamais du fichier actif;
- alerte explicite si l'espace disque devient faible.

Aucune valeur commerciale definitive ne doit etre figee avant d'avoir mesure le volume reel, le taux gzip reel et les fenetres statistiques requises par LER/Crypto+.

## 8. Separation runtime / archive

Le produit final devra distinguer:

- `runtime/current`: donnees fraiches necessaires aux decisions courantes;
- `archive`: historique compresse pour recherche, audit et replay;
- `health`: etat des providers et age des donnees;
- `manifests`: versions de schema/provider/collecteur et hashes.

Une panne, un nettoyage d'archive ou un manque de donnees externes ne doit jamais interrompre les protections Guardian, le risk manager ou la compliance prop-firm.

## 9. Reproductibilite obligatoire pour un futur produit

Avant toute distribution commerciale, fournir au minimum:

- installateur/version exacte;
- prerequis Windows et MT5;
- procedure d'installation propre;
- procedure de mise a jour et rollback;
- chemins et droits de fichiers;
- creation et migration du stockage EIB;
- sources/providers et conditions de fallback;
- procedure de diagnostic `health`;
- politique de retention/nettoyage;
- procedure de sauvegarde/restauration;
- procedure de desinstallation sans suppression accidentelle des archives utilisateur;
- version du schema de donnees;
- tests de non-regression et smoke post-installation;
- preuve qu'aucune cle de trading externe n'est necessaire au bus de donnees;
- documentation des limites et licences/conditions d'utilisation des fournisseurs de donnees avant commercialisation.

## 10. Direction produit

La procedure actuelle Git + Python est acceptable pour le laboratoire, mais **ne doit pas etre l'experience d'installation du produit final**.

Cible commerciale:

`Installateur Guardian -> verification prerequis -> installation Guardian/EIB -> creation stockage -> test health -> connexion MT5 -> mise a jour signee/versionnee`

L'utilisateur final ne devrait pas avoir a installer Git, taper `git pull`, creer un venv Python ou connaitre les chemins internes.

Cette distinction laboratoire/produit doit etre conservee dans les decisions futures.