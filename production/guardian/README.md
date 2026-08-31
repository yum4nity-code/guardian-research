# Guardian production

Cette zone contient uniquement des versions de production/auditables. Ce n'est pas un laboratoire de recherche.

## Version courante préparée
`Guardian_D017_PropFirmAuto_v11_15.mq5`

Manifest de référence : `production/manifests/Guardian_D017_v11_15.json`
Preset : `production/presets/FTMO_D017_v11_15_SAFE.set`

Au 2026-08-31, le connecteur ChatGPT a pu publier le preset et le manifest mais ne doit pas retranscrire manuellement un gros `.mq5` au risque d'altérer le code. Le premier bootstrap Codex doit donc copier depuis le fichier local exact :

- `Guardian_D017_PropFirmAuto_v11_15.mq5`
- `Guardian_v11_14_to_v11_15.diff`

puis vérifier leurs SHA256 contre le manifest avant commit.

Hashes attendus :
- source : `bbcfae9426838eef655d5ac11eaf1530d872d117eb840f6c15ceb0c69843fe86`
- preset : `82d6d1ada0e6785382e5a0e9555480e85f2d16bd4106dfd9210dffee502486b3`
- diff : `ef5bc0ed1c3d7cf6379829497143d7d784deb19c4d4aa2d40ef448f075558e76`

Ne jamais considérer v11.15 comme compilée/déployée tant que MetaEditor et les contrôles de non-régression ne l'ont pas confirmé.
