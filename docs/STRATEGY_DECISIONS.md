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

## 2026-08-31 — D017 / v11.16 provenance verdict

- Strategy ID: `D017-GUARDIAN-V11-16-CANDIDATE`
- Campaign ID: `D017-V11-16-PROVENANCE-AUDIT`
- Verdict: `SEMANTIC_CORE_PARITY_CONFIRMED / EXACT_FEED_CONTROL_REQUIRED`
- Preuves: le moteur Momentum, la session, le volume, le scoring, le ranking et la gestion AUTO sont identiques apres normalisation. D017 utilisait `EURUSD_BT` (17,040,615 ticks; 20,351 bars), alors que le test manuel v11.16 utilisait `EURUSD` FTMO-Demo (13,846,176 ticks; 20,638 bars).
- Limites: les deux resultats ne sont pas une non-regression empirique comparable; v11.16 ajoute des gardes PropFirm/ownership susceptibles de bloquer des entrees.
- Source: `results/audits/D017_V11_16_PROVENANCE_AUDIT.md`; base commit `bed7a2537f636fcd27a4a12bf152c1749dad97dc`.
- Raison: l'ecart 176 -> 191 trades est compatible avec une difference de flux et ne justifie aucune modification de strategie. Un controle unique sur les memes historiques `_BT` est preregistre.

## 2026-08-31 — Cloture de la divergence v11.15

- Strategy ID: `D017-GUARDIAN-V11-15`
- Campaign ID: `GUARDIAN-V11-15-SAFE-RUNTIME-DIVERGENCE`
- Verdict: `REJECTED AS LEGACY / SUPERSEDED BY V11.16`
- Preuves: ChatGPT confirme une divergence d'inputs persistes, pas une derive du coeur Momentum. v11.16 compile les moteurs rejetes et le time-stop en invariants, avec CryptoSweep OFF et diagnostics OFF par defaut.
- Limites: cette resolution traite la securite de configuration, pas la robustesse statistique de v11.16.
- Source: `handoff/chatgpt_to_codex/2026/08/31/GUARDIAN_V11_15_RUNTIME_DIVERGENCE_RESOLUTION.md`, commit recu `40f874cf561dafc261c55c3d13723bfcc956cb35`.
- Raison: ne pas patcher/redeployer v11.15. Pour v11.17+, aucun invariant strategique valide ne doit dependre d'un `.set`; les ecarts configurables doivent provoquer un demarrage fail-closed et etre journalises.
