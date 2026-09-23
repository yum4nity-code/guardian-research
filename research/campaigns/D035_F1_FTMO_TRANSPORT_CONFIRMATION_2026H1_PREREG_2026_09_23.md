# D035-F1 — FTMO transport confirmation 2026-H1

Date: 2026-09-23
Status: FROZEN BEFORE FTMO TARGET-OUTCOME ACCESS
Parent: D035-E1 causal BTC+ETH dual-source -> XLMUSD
Classification: FRESH TARGET-FEED TRANSPORT CONFIRMATION

## Why this branch exists

The historical D035 family used FundedNext CFD quotes. That feed produced very large spreads on several crypto CFDs and is no longer the intended deployment environment.

D035-F1 therefore tests whether the exact frozen D035-E1 XLMUSD response transports to FTMO, the intended EA-capable environment.

This is NOT a retune:
- target remains XLMUSD;
- direction remains SHORT;
- source event remains causal BTC+ETH dual shock;
- signal timestamp remains the later/second source shock;
- primary horizon remains +15m.

Only the target execution feed changes from FundedNext to FTMO.

## Scientific caveat

The 2026-H1 Binance source side has already been partially inspected operationally:
- the frozen source-event engine reported 254 causal dual-source events.

No 2026-H1 FTMO XLMUSD target outcomes have been inspected.
Therefore F1 is a fresh **target-outcome / feed-transport** confirmation, not a claim that the entire source window is untouched.

No rule change is permitted based on the known event count.

## Frozen source rule

Same D035/E1 source definitions:
- Binance Vision BTCUSDT and ETHUSDT USD-M;
- 5m return <= strictly-prior rolling 30d 10th percentile and negative;
- 5m sum_open_interest change <= strictly-prior rolling 30d 10th percentile and negative;
- minimum 4000 prior observations;
- 30-minute per-source cooldown;
- BTC and ETH both qualify within <=5 minutes;
- signal timestamp = later/second qualifying source shock.

## Frozen target rule

Feed: FTMO CFD
Target: XLMUSD only
Direction: SHORT
Entry: first FTMO XLMUSD BID at/after causal signal timestamp, tolerance <=2m
Exit: first FTMO XLMUSD ASK at/after +15m
Diagnostic exit: +30m only

BTCUSD FTMO is used only for server->UTC clock calibration.

No other FTMO crypto target may be opened by this experiment.

## FTMO transaction cost treatment

Spread is embedded directly by BID entry / ASK exit.

Crypto commission frozen from the FTMO published model:
- 0.0325% per side of notional.

For each trade the exact commission-adjusted short return is:

net PnL = entry_bid - exit_ask
          - 0.000325 * entry_bid
          - 0.000325 * exit_ask

net_bps = net PnL / entry_bid * 10000

The primary existence/economic test uses this commission-adjusted net return.

Matched-control returns use the identical FTMO commission treatment.

## Evaluation window

2026-01-01 00:00 UTC through 2026-06-30 23:59 UTC.
Jul-Dec 2026 remains forbidden.

## Doctrine V2 fresh classification

Support:
- n >=100 executable FTMO XLM events: ADEQUATE
- n <100: SPARSE

Existence:
- NEGATIVE: mean FTMO net +15m <=0
- POSITIVE_UNCERTAIN: mean >0 but one-sided 90% day-cluster lower bound <=0
- POSITIVE_CONFIRMED: mean >0 and one-sided 90% day-cluster lower bound >0
- SPARSE_POSITIVE: n<100 and mean>0

Economic:
- MINI_EDGE if mean commission-adjusted +15m >0
- otherwise NO_POSITIVE_EXECUTABLE_EDGE

Diagnostics only, not death gates:
- raw spread-only executable mean
- median
- +30m
- matched-control differential
- month means
- trim-best 1%
- entry spread distribution

## Prohibited

- no target substitution
- no BTCUSD/ETHUSD target promotion
- no horizon change
- no direction change
- no source threshold/window/cooldown change
- no session/hour filter
- no subgroup selection
- no commission override
- no Jul-Dec 2026
- no rescue after result

## Interpretation

A positive F1 result would show that the previously observed causal dual-source XLM response transports to the FTMO execution feed after FTMO spread and commission.

A negative F1 result closes the exact XLM FTMO transport hypothesis. It does not invalidate the existence of the historical conditional response on other feeds.
