# GEF V109 — Treasury auction event-level discovery

Status: PRE-REGISTERED / READY TO RUN
Date: 2026-09-22

## Source

Canonical normalized source:
D:\MT5_Backtests\DataLake\normalized\treasury_auctions_pre2023\treasury_auctions_PRE2023.csv

V108 proved:
- 9,496 rows;
- auction_date from 1979-10-31 to 2022-12-29;
- usable auction_date;
- bid-to-cover present;
- high yield/rate present.

V108's NOT_READY status was an audit-preview bug caused by taking head(500) before coverage measurement. No alpha trial was run.

## Causality

AVAILABLE_AT = auction_date normalized + 1 calendar day.

No same-day auction reaction is claimed. This is deliberately conservative.

## Statistical unit

One Treasury auction = one information event.

No carried-forward 5-minute state is treated as repeated independent evidence.

## Security buckets

Normalize within a frozen auction bucket:
- security_type + security_term when both exist;
- fail closed if neither can be identified.

No pooling of unrelated maturities before normalization.

## Predeclared raw feature families

Eligible raw fields are discovered only by exact semantic name patterns, not return performance:
- bid_to_cover;
- high_yield / high_investment_rate / high_discount_rate / high_price;
- avg_med_yield / avg_med_investment_rate / avg_med_discount_rate / avg_med_price;
- interest/coupon rate;
- allocation percentage;
- competitive accepted / tenders;
- direct bidder accepted / tenders;
- indirect bidder accepted / tenders;
- primary dealer accepted / tenders;
- total accepted / tendered;
- noncompetitive accepted / tenders where present.

Predeclared derived ratios when both inputs exist:
- competitive_acceptance_rate = competitive_accepted / competitive_tenders;
- total_acceptance_rate = total_accepted / total_tendered;
- direct_accepted_share = direct_bidder_accepted / competitive_accepted;
- indirect_accepted_share = indirect_bidder_accepted / competitive_accepted;
- primary_dealer_accepted_share = primary_dealer_accepted / competitive_accepted.

Columns are selected by <=2013 source support only.

## Event score

Within each frozen security bucket and raw/derived feature:

LEVEL:
sign(current value - expanding prior median), min 8 prior observations.

D1:
sign(current value - previous auction value in the same bucket).

Zero score is skipped.

For each candidate, position direction =
event score × one orientation frozen from discovery.

## Market targets

Guardian local HistData markets.

Horizons:
60, 120, 240 minutes.

Target construction is event-native:
- use actual finite 5-minute market prices;
- entry = first tradable 5-minute bar at or after AVAILABLE_AT, within 7 calendar days;
- exit = first tradable price at or after entry+horizon;
- reject if exit is more than 30 minutes later than the intended horizon, preventing weekend/closed-market gap substitution.

## Temporal firewall

Discovery:
2010-2013 market returns only.

Before reading discovery returns:
- source schema must pass;
- bucket catalog frozen from <=2013 source data;
- feature catalog frozen from <=2013 source support.

Discovery gate:
- N >= 12 auctions;
- spans >= 3 years;
- orientation from discovery mean only;
- raw p <= .05;
- BH q <= .10 across all finite bucket-feature-transform-market-horizon tests.

Freeze <=150 before any 2014+ market returns.

Replication 2014-2017:
- N >= 12;
- gross >0;
- net 1 bp >0;
- positive-year fraction >= .50;
- remove best 2 events >0.

Pre-validation robustness:
- remove best 3 events >0;
- remove best calendar month >0;
- leave-one-year-out minimum >0;
- +1 additional calendar-day delay >0;
- +2 additional calendar-day delay >0.

Freeze exact survivors before 2018+ market returns.

Validation 2018-2022:
- N >=15;
- gross >0;
- net 1 bp >0;
- positive-year fraction >=.60;
- remove best 3 >0;
- remove best 5 >0;
- remove best month >0;
- leave-one-year-out minimum >0.

STOP after validation.

Do not open 2023-2025.
Do not open 2026.

If validation survivors exist, run a separate final pre-OOS forensic before any locked OOS.
