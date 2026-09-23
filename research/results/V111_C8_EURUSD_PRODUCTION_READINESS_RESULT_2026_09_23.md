# V111 C8 EURUSD H11 SHORT 120m — Production-Readiness Result

Date: 2026-09-23
Status: COMPLETE / FRAGILE_FORWARD_SHADOW / NOT PRODUCTION READY

## Frozen candidate
- EURUSD
- SHORT
- source H11 -> H13
- 120-minute hold
- existing FTMO alignment: +2h
- 717 executable events from existing 2023-2025 ledger
- no retiming / no rescue filters
- 2026 historical market data not opened

## Net result after observed spread + FTMO commission
Commission assumption used:
- USD 2.50 per lot per side
- USD 5.00 round trip
- mean normalized commission: 0.455522 bp

Result:
- n: 717
- mean: +0.550043 bp/trade
- median: +0.541379 bp
- win rate: 52.02%

Yearly:
- 2023: +1.423109 bp
- 2024: -0.176102 bp
- 2025: +0.611551 bp

## Robustness
Month-block bootstrap:
- q2.5: -0.449436 bp
- q10: -0.101934 bp
- median bootstrap mean: +0.549426 bp
- P(mean <= 0): 13.945%

Best-trade sensitivity:
- trim best 1%: +0.110826 bp
- trim best 2%: -0.153618 bp
- trim best 5%: -0.796166 bp
- remove best 10: +0.026269 bp
- remove best 20: -0.323483 bp

Path:
- cumulative max drawdown: -247.866337 bp
- max consecutive losing trades: 8

## Friction budget
- break-even extra friction: +0.550043 bp round trip
- equivalent at mean EURUSD price: ~0.604539 pips

Illustrative Volume-Band stress only:
- band 1 scenario: +0.550043 bp
- band 2 scenario (+0.4 pips RT): +0.186101 bp
- band 3 scenario (+0.8 pips RT): -0.177842 bp
- band 4 scenario (+1.2 pips RT): -0.541784 bp

These band stresses use FTMO's published illustrative EURUSD example only; they are not claims about current guaranteed execution.

## Classification
**FRAGILE_FORWARD_SHADOW**

Reason:
- mean after observed spread + current commission remains positive;
- q10 month bootstrap is slightly negative;
- trim-best-1% remains positive but only narrowly;
- 2024 is negative;
- friction budget is only ~0.55 bp / ~0.60 pip.

## Decision
- preserve exact rule;
- do not deploy live;
- do not retime, add filters or optimize;
- move to a true forward shadow from future data only;
- future shadow should record exact BID/ASK execution, commission, news-window collision flag, and volume-band/order-size context without altering the signal.
