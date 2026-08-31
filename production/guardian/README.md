# Guardian production

Cette zone contient uniquement des versions de production/auditables. Ce n'est pas un laboratoire de recherche.

## Version courante préparée
`Guardian_D017_PropFirmAuto_v11_15.mq5`

Manifest de référence : `production/manifests/Guardian_D017_v11_15.json`
Preset : `production/presets/FTMO_D017_v11_15_SAFE.set`

Le source v11.15 est désormais présent directement sous `production/guardian/`.

Hashes attendus :
- source : `bbcfae9426838eef655d5ac11eaf1530d872d117eb840f6c15ceb0c69843fe86`
- preset : `82d6d1ada0e6785382e5a0e9555480e85f2d16bd4106dfd9210dffee502486b3`

Au premier bootstrap local, Codex doit vérifier ces SHA256 après clone/synchronisation. Aucun fichier diff v11.14 -> v11.15 n'est requis pour le fonctionnement normal du labo ou du Guardian.

Ne jamais considérer v11.15 comme compilée/déployée tant que MetaEditor et les contrôles de non-régression ne l'ont pas confirmé.
