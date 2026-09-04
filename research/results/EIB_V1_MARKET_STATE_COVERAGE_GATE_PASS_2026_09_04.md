# EIB V1 — Market State Coverage Gate PASS

Date: 2026-09-04
Status: PASS

## Live evidence

Six-minute continuous live run using the coverage-aware market-state candidate completed successfully.

Observed:
- gate: `PASS`;
- raw collector gate: `PASS`;
- 590 unique raw events;
- 0 duplicate event IDs;
- 0 future-availability violations;
- 72 generation samples / 72 unique generations;
- BTCUSD and ETHUSD final quality: `OK`;
- final core ages ~1.9 s;
- 1m and 5m spot/perpetual/OI windows complete with fresh boundary anchors;
- 15m and 1h windows correctly remained incomplete and therefore `null`;
- liquidation 1m and 5m coverage complete and numerical zero was allowed only because websocket/health coverage was continuous;
- liquidation 15m and 1h coverage incomplete and therefore `null` rather than fake zero.

## Scientific verdict

**PASS.** The coverage fix closes the two previously identified integrity gaps:

1. price/OI rolling changes no longer silently use stale anchors from a previous collection session;
2. zero liquidation is represented as `0` only when the entire requested window has verified health/websocket coverage; otherwise the value is `null`.

This is now sufficient to begin a read-only MT5 consumer transport gate. It is still not permission to alter RSI, Momentum, LER, risk, protection or prop-firm compliance logic.

## Next gate

Expose the shared neutral state through MetaTrader 5 `FILE_COMMON`, then validate that multiple local terminals can read the same `generation_id` without launching duplicate collectors or calculations. Use a probe/consumer with no order capability before integrating the reader into Guardian itself.
