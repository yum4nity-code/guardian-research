# Handoff Codex -> ChatGPT — Guardian v11.15 SAFE runtime divergence

STATUT: URGENT / WAITING_CHATGPT

## Objet

Auditer et preparer une correction de production pour empecher Guardian de demarrer avec des defaults incompatibles avec le preset SAFE. Codex n'a modifie ni production ni terminal.

## Faits verifies

- `production/presets/FTMO_D017_v11_15_SAFE.set` fixe `InpEnableStrategyTimeStop=false` et `InpEnableBlackBox=false`.
- Les SHA256 LF normalises source/preset correspondent au manifeste v11.15.
- Une position live heritee a ete fermee par `STRATEGY_TIME_STOP` vers 60 minutes: les inputs effectifs n'etaient donc pas SAFE.
- Des profils sauvegardes referencaient v11.14 avec `expertmode=1`, ce qui cree un risque de rechargement lors d'un redemarrage.
- Au bootstrap, le terminal FTMO normal et FundedNext sont ouverts, PropFirmGuard est actif, mais aucun testeur/MiMo n'est actif.

## Action demandee a ChatGPT

1. Auditer le template `Guardian_D017_Observation.tpl`, le bootstrap des charts et les profils sauvegardes.
2. Proposer une prevention fail-closed qui detecte un preset non SAFE avant tout auto-trading.
3. Preparer uniquement un candidat/audit tracable; ne pas editer silencieusement `production/guardian/`.
4. Laisser a l'utilisateur la compilation, la validation finale et le deploiement.

## Ne pas faire

- Ne pas redemarrer/redeployer Guardian automatiquement.
- Ne pas faire coexister v11.14 et v11.15 sur le meme symbole.
- Ne pas traiter les defaults source comme equivalents au preset gele.
- Ne pas ouvrir l'OOS ni utiliser le run USDJPY contamine.

## Tracabilite

- Commit de base: `ee5ad9914156cb66462ee321d40632a38d3714bf`
- Queue: `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE`
- Note source: `handoff/chatgpt_to_codex/2026/08/31/GUARDIAN_V11_15_TIME_STOP_CONFIG_DIVERGENCE.md`
