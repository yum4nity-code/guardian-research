# Strategy Decisions

Journal append-only des decisions de recherche importantes.

Chaque entree doit inclure : date, Strategy ID, Campaign ID, verdict, preuves principales, limites, commit/source exacts, et raison de la decision.

## 2026-08-31 — Guardian v11.15 SAFE runtime divergence

- Strategy ID: `D017-GUARDIAN-V11-15`
- Campaign ID: `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE`
- Verdict: `BLOCKED / WAITING_CHATGPT`
- Preuves: le preset gele fixe `InpEnableStrategyTimeStop=false`; l'execution observee a ferme une position par `STRATEGY_TIME_STOP`; des profils sauvegardes referencaient encore v11.14.
- Limites: le terminal FTMO est ouvert mais aucun testeur n'est actif; les inputs live ne sont pas modifies par Codex.
- Source: commit `ee5ad9914156cb66462ee321d40632a38d3714bf`; source v11.15 LF SHA256 `bbcfae9426838eef655d5ac11eaf1530d872d117eb840f6c15ceb0c69843fe86`; preset LF SHA256 `82d6d1ada0e6785382e5a0e9555480e85f2d16bd4106dfd9210dffee502486b3`.
- Raison: la configuration executee n'est pas equivalente au protocole SAFE; une integration de production exige audit ChatGPT et validation utilisateur.

## 2026-08-31 — Guardian v11.16 and manual cross-asset results

- Strategy ID: `D017-GUARDIAN-V11-16-CANDIDATE`
- Campaign ID: `D017-V11-16-PROVENANCE-AUDIT`
- Verdict: `CANDIDATE, NOT VALIDATED`
- Preuves: EURUSD +8545.98 / 191 trades / PF 1.56 / DD 1.61%; GBPUSD +4482.53 / 188 / PF 1.24 / DD 2.65%; BTCUSD balance finale 113054.25; ETHUSD 91527.60. Les metriques D017 historiques proviennent de v11.10 et different.
- Limites: pas de rapports structures recents pour les cryptos; SOLUSD incomplet; USDJPY traverse l'OOS verrouille et est exclu; aucune conclusion comparative propre n'est possible.
- Source: candidat v11.16 LF SHA256 `6e5be9fdd58d7c6352011dd7afc758089d766f987629f06d7921d8f5f2e2ce69`, commit `ee5ad9914156cb66462ee321d40632a38d3714bf`.
- Raison: les resultats ne demontrent ni parite semantique ni robustesse; aucune optimisation post hoc n'est autorisee.
