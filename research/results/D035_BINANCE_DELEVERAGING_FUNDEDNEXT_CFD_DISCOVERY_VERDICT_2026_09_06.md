# D035 — Binance BTC/ETH deleveraging -> FundedNext crypto CFD lead-lag — development verdict

Date: 2026-09-06 Europe/Paris
Status: **DISCOVERY_REJECT / 2026 CONFIRMATION REMAINS UNTOUCHED**

Canonical campaign: `research/campaigns/D035_BINANCE_DELEVERAGING_FUNDEDNEXT_CFD_LEADLAG_PREREGISTRATION_2026_09_05.md`.

## Returned development pack

User returned `D35 OUTPUT.zip` containing:
- `D035_SOURCE_EVENTS.csv`
- `D035_EVENT_TARGET_RETURNS.csv`
- `D035_SUMMARY_BY_TARGET.csv`
- `D035_OFFSET_QA.csv`
- `D035_VERDICT.json`
- `D035_REPORT.md`

Development sample remained hard-locked to 2024-01-01 through 2025-12-31. The reserved 2026-01-01 through 2026-06-30 confirmation sample was not touched.

## Data integrity / coverage

- merged BTC/ETH source events: **5,558**
- pooled target-event rows: **38,622**
- eligible FundedNext crypto CFDs: **9** — ADAUSD, BTCUSD, DOGUSD, ETHUSD, LNKUSD, LTCUSD, XLMUSD, XMRUSD, XRPUSD
- Binance BTC metrics files: 793; missing days 0; duplicate metric rows 0
- Binance ETH metrics files: 793; missing days 0; duplicate metric rows 0
- Binance BTC/ETH 1m monthly files: 27 each; missing months 0; duplicate kline rows 0
- server->UTC alignment: **114/114 weeks usable**
- weekly alignment correlation: mean about **0.9962**, minimum about **0.9658**

The timing join is therefore not the reason for the negative economic result.

## Frozen primary gate

1. >=80 merged source events: **PASS**
2. >=2 eligible CFD targets with >=40 events: **PASS**
3. pooled executable SHORT +15m >= +15 bps: **FAIL** — **-25.448 bps**
4. pooled event-control differential +15m >= +10 bps: **FAIL** — **+5.179 bps**
5. day-cluster bootstrap 95% lower bound of +15m differential > 0: **PASS** — **[+3.033, +7.385] bps**
6. pooled executable SHORT +30m > 0: **FAIL** — **-25.438 bps**
7. BTC-source-only and ETH-source-only +15m differentials both > 0: **FAIL** — BTC-only **-3.281 bps**, ETH-only **+3.283 bps**
8. no month >35% of positive +15m differential contribution: **PASS** — max **8.08%**

Final frozen gate: **4/8 -> DISCOVERY_REJECT**.

## Economic interpretation

There is a small but statistically detectable conditional timing effect: the pooled event-minus-control differential is +5.18 bps and its day-cluster bootstrap interval is wholly above zero. However the effect is far too small to overcome the executable FundedNext CFD cost structure in the broad target pool.

Entry spreads averaged approximately:
- BTCUSD 2.30 bps
- ETHUSD 5.58 bps
- XLMUSD 7.94 bps
- LNKUSD 23.88 bps
- XRPUSD 26.27 bps
- ADAUSD 34.17 bps
- DOGUSD 36.51 bps
- XMRUSD 67.62 bps
- LTCUSD 70.06 bps

The mid-price response of many secondary CFDs is positive after a BTC/ETH shock, but the executable short return is negative once BID entry / ASK exit is respected. BTCUSD and ETHUSD remain positive at +15m (+5.86 and +5.43 bps respectively) because their spreads are much narrower, but both are still far below the preregistered +15 bps economic hurdle.

Therefore D035 is not a standalone executable strategy in its frozen broad form.

## Important post-hoc audit finding — do not misread the dual-source subgroup

A post-hoc split of rows labelled `BTCUSD+ETHUSD` appears superficially very strong in the returned development table. This must **not** be treated as valid tradable evidence from the current output.

The v1.01 merge routine groups BTC and ETH source events occurring within five minutes but retains `event_time_utc` from the **first** event while later adding both sources to the group label. Selecting `sources == BTCUSD+ETHUSD` and measuring from that first timestamp would therefore use information that can arrive up to five minutes later. That subgroup is look-ahead contaminated if interpreted as a dual-confirmation trading rule.

Any dual-source follow-up must be a new explicitly labelled exploratory test where the signal becomes available only at the timestamp of the **second/opposite source shock**. The original D035 verdict remains REJECT regardless of any such follow-up.

## Next safe research action

If this family is pursued once more, use a separate D035-E1 exploratory diagnostic on the already inspected 2024-2025 development sample:
- same frozen BTC/ETH shock definitions and 30-minute per-source cooldown;
- require both BTC and ETH shocks within five minutes;
- causal signal timestamp = later/second qualifying source event;
- no threshold/horizon mining;
- retain 2026-H1 untouched;
- only if the causal second-confirmation version remains economically large should a fresh D035-C1 preregistration consume 2026-H1.

Do not reinterpret this as a rescue of the failed D035 primary gate.