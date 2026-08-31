# D017 / Guardian v11.16 provenance audit

Date: 2026-08-31

## Verdict

`SEMANTIC_CORE_PARITY_CONFIRMED / EMPIRICAL_NON_REGRESSION_NOT_YET_COMPARABLE`

The 176 versus 191 EURUSD trade count difference cannot be attributed to the Momentum signal rules. The compared tests used different symbols and feeds.

## Verified parity

After removing comments and whitespace, these functions are identical between historical v11.10 and candidate v11.16:

- `CheckSignals`
- `IsInAllowedSession`
- `IsRelativeTickVolumePresent`
- `ScoreSignalContext`
- `ModeAllowsStrategy`
- `ProfileMinATRPercent` / `ProfileMaxATRPercent`
- the AUTO section of `ManagePositionsAndManualTrades`

The v11.16 candidate additionally hard-blocks non-Momentum strategies and hard-disables strategy time-stop, which matches the D017 overrides.

## Material differences

- v11.16 adds PropFirm detection/execution authorization and instance ownership guards. These can block entries but do not create new Momentum signals.
- v11.16 uses `EffectiveMinTradeRiskUSD()`. At the tested 100,000 USD capital, the configured 25 USD floor remains 25 USD, so this does not explain the trade-count difference.
- v11.16 contains extensive manual-position safety changes; the normalized AUTO management block is unchanged.

## Non-comparable data evidence

Historical D017:

- symbol `EURUSD_BT`
- 17,040,615 ticks
- 20,351 bars
- 176 trades
- raw net 8,569.33 USD; estimated after-cost net 7,075.53 USD

Manual v11.16:

- symbol `EURUSD` on `FTMO-Demo`
- 13,846,176 ticks
- 20,638 bars
- 191 trades
- final balance 108,545.98 USD

Both used 2025-08-28 through 2026-06-28, but their feeds are demonstrably different. Exact non-regression requires the v11.16 binary on the same imported `_BT` histories and frozen D017 settings.

## Scientific constraints

- This is a technical parity control, not a parameter search.
- No threshold or rule may be changed after observing the result.
- The locked OOS remains excluded.
- The manual USDJPY run that crossed OOS remains quarantined.

## Evidence

- Historical manifest: `D:/MT5_Backtests/automation/fx-momentum-no-time-stop-d017.json`
- Historical result: `D:/MT5_Backtests/reports/validation/fx-momentum-no-time-stop-d017-decision.json`
- Historical source SHA256: `10EBBC99DECA38EA3AEDB7F22F3DD8AE2B7AB945201B9FEA7548D085F0AC4EE4`
- Candidate v11.16 raw SHA256: `C90B85E867C5CE043954ECC90E17D13495997D145BAEF67560E9575DEC2E0D3A`
- Candidate v11.16 LF SHA256: `6E5BE9FDD58D7C6352011DD7AFC758089D766F987629F06D7921D8F5F2E2CE69`
- Tester metadata: `C:/Users/armor/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/Tester/logs/20260831.log`
