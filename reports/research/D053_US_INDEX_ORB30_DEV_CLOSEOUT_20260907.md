# D053 — US Index ORB30 Entry-Alpha Benchmark V0 — DEV Closeout

Date: 2026-09-07 Europe/Paris
Status: **CLOSED — D053_REJECT_V0**

## Authoritative evidence

Development score event:
`backtests/d053/live/events/development/d053-development-score/20260907T162026Z`

Frozen source identity after the preregistered engineering-only v1.01 session-close amendment:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

Integrity events: **0**
Jul-Aug 2026 holdout: **UNOPENED**

## Development result

2024-01-02 through 2025-12-31, model 0 / Every tick, symbols SPX500, NDX100, US30, US2000.

- n = **2,042**
- mean net R = **+0.0619841162R/trade**
- PF = **1.1349128071**
- total = **+126.57156518R**
- 1.5x spread-stress total = **+88.56095494R**
- 2024 = **+67.53893644R**
- 2025 = **+59.03262874R**
- positive symbols = **3/4**
- max positive-symbol contribution share = **0.3662672247**
- month-block bootstrap 95% interval = **[-0.0290412996R, +0.1466959319R]** around the mean

Per symbol total:
- SPX500: **+36.99092103R**
- NDX100: **+48.08397678R**
- US30: **+46.20623668R**
- US2000: **-4.70956931R**

By side:
- LONG: n=1,053, mean **+0.0586494566R**, total **+61.75787783R**
- SHORT: n=989, mean **+0.0655345676R**, total **+64.81368735R**

Path descriptive:
- mean MFE = **1.0345879024R**
- mean MAE = **0.6770199126R**

## Gate result

D053 passed **11 of 12** frozen DEV gates.

Passed:
- aggregate n >= 1,000
- every symbol n >= 200
- mean >= +0.05R
- PF >= 1.10
- total > 0
- stress total > 0
- >=3/4 positive symbols
- 2024 > 0
- 2025 > 0
- concentration <= 0.55
- integrity = 0

Failed:
- month-block bootstrap 95% lower bound > 0

Observed lower bound: **-0.0290412996R**.

## Formal decision

Per preregistration, any failed DEV gate requires `D053_REJECT_V0` and forbids opening confirmation.

Therefore:
- D053 is formally **REJECTED V0**.
- Jul-Aug 2026 confirmation is **not opened**.
- No threshold waiver, rounding, symbol deletion, direction selection, or OR/time retune is allowed to rescue D053.

## Scientific interpretation

This is not a broadly negative result. D053 produced positive expectancy, PF >1.10, positive stress-adjusted total, both years positive, both directions positive, and 3/4 positive symbols. The failure is statistical robustness across month blocks: the frozen bootstrap interval still includes negative expectancy.

Operationally, D053 is one of the strongest unconfirmed entry-alpha candidates in Guardian research so far, but it does **not** satisfy the preregistered evidence standard required to spend untouched holdout data.

Any follow-up must be a new preregistered hypothesis with its own independent evidentiary boundary. D053 itself remains closed.
