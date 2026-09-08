# Phenomenon Discovery — Current Handoff — 2026-09-08

This file is the current canonical handoff for the active Phenomenon Discovery campaign.

## Read this before doing anything

Repository: `yum4nity-code/guardian-research`

Branches:
- `main` = code / governance
- `backtest-results` = published run evidence

Local research worktree used by the owner:
- `D:\MT5_Backtests\guardian-phaseA-20260908`

Never ask the owner to copy/paste run output if the launcher publishes to GitHub. Read `backtest-results` directly.

## Scientific chronology already completed

Protected final OOS rule:
- Discovery/internal confirmation uses 2024 and 2025 only.
- **2026 is still sealed and must not be opened without an explicit promotion gate.**

Completed families:
- Phase A: Bybit BTCUSDT/ETHUSDT 5m price + OI dataset, PASS.
- Phase B: coarse static state atlas. 38 survivors, but robust effects were mainly low-movement regimes.
- Phase C: robustness/multiple-testing. **18 distinct robust low-movement / no-trade phenomena.** No directional survivor.
- Phase D: exhaustive exact 3-clause directional states. **0 survivors.** Closed.
- Phase E-A: derivative context dataset (mark/index/premium/funding), PASS.
- Phase E-B: derivative temporal transition atlas. **0 survivors.** Closed.
- Phase F-A: Binance spot + USD-M aggressive-flow dataset, PASS.
- Phase F-B: univariate order-flow atlas. **0 survivors.** Closed.
- Phase F-C: order-flow outside Phase-C dead regimes. **0 survivors.** Closed.
- Phase G: constrained stable ensemble frozen on 2024 then tested on 2025. **0 survivors.** Closed.
- Phase H-A: rare-event shock matrix, 15m/30m/1h/2h/4h, PASS.
- Phase H-B: 1,140 rare-event hypotheses, 257 discovery-eligible, 75 frozen before 2025, **0 survivors at every horizon and every target.** Closed.

Conclusion from A-H:
- Do **not** reopen BTC/ETH 5m directional alpha by stacking more filters, adding more tails, or inventing another named strategy.
- Keep Phase C as a possible no-trade / low-amplitude filter.
- Directional BTC/ETH 5m research on this information family is closed unless genuinely new information appears.

## Active pivot

Current active branch:
- **Phase I-A — Historical Prop-Firm News Mask for XAUUSD**

Then, if I-A passes:
- **Phase I-B — clean XAUUSD 1m/5m historical dataset with news contamination excluded**
- **Phase I-C — XAU phenomenon discovery**

Research news policy for XAU:
- high-impact USD events
- exclude +/-5 minutes around each event
- conservative research policy applies even when a particular prop-firm account type allows news trading
- live prop-firm promotion remains fail-closed until the exact target prop-firm rule is mapped

## Critical MT5 session rule for Phase I-A / I-B

**Use the one and only MT5 session that is already open on the owner's PC as the reference terminal.**

Do not select another inactive MT5 installation merely because it is convenient.
Do not silently use an FTMO/FundedNext/MetaQuotes installation different from the currently open session.
Do not open 2026.

The open MT5 session defines:
- broker / trade server identity
- terminal installation/data directory to use as the canonical XAU source
- server-time basis / account context for the XAU research chain

If exactly one `terminal64.exe` is running, bind I-A/I-B to that terminal's executable/data directory.
If zero or more than one terminal is running, fail closed and report the ambiguity.

Important technical boundary:
- MT5 command-line `[StartUp] Script=` is a terminal-start mechanism; do not assume it can inject a script into an already-running GUI instance.
- If calendar extraction cannot be executed inside the existing session automatically, preserve the existing session as the canonical terminal/server anchor and choose a technically valid method without switching to another MT5 installation. Do not fake execution in the running instance.

## Phase I-A current files

- `research/phenomenon_discovery/phase_ia_news_policy_v1.json`
- `research/phenomenon_discovery/export_mt5_high_impact_calendar_v1_00.mq5`
- `research/phenomenon_discovery/build_propfirm_news_mask_v1_00.py`
- `research/phenomenon_discovery/check_propfirm_news_mask_v1_00.py`
- `research/phenomenon_discovery/START_PHASE_IA_NEWS_MASK_V1_00.ps1`

Current launcher v1.00 was originally written to choose an inactive MT5 installation. **That behavior is now superseded by the rule above and must not be treated as canonical.** Patch/revise it before asking the owner to run I-A.

## Publication

Phase I-A expected publication path:
- `phenomenon-discovery/phase-ia-news-mask/LATEST.json`
- branch `backtest-results`

On `published` / `fini` / `résultat ?`, fetch GitHub directly. Do not ask the owner for console output.

## Research governance

- No candidate is called validated alpha from 2024/2025 alone.
- 2025 is internal confirmation, not independent final OOS.
- 2026 is the untouched final OOS.
- Do not use sizing / Challenge Probability Lab to rescue failed alpha.
- If XAU discovery produces a real candidate, freeze exact rule + mapping before opening 2026.
