# PRE-OOS ECONOMIC FEASIBILITY SCREEN — frozen owner revision 2

The final owner decisions in OWNER_DECISIONS.md override revision 1. This is a
conditional cost-survival screen for allocating realistic-backtest effort. PASS
does not establish historical executable fills, deployable profitability, new
independent evidence, portfolio profitability or prop-firm compliance. No tuning.

## Population and signal

Ingest all 500 published R4 survivors with their complete frozen rule fields. IDs
R4P-0001 through R4P-0500 follow original array order. Canonical signature uses
dataset, feature, operator, quantile, cutpoint, horizon_bars, direction, hour_start
and hour_width; SHA256 over sorted compact JSON. The 32 frozen rules are optional
structural annotations only. No feature, threshold, session or horizon refitting.
The feature functions are copied verbatim into a pure module, without R4 loader,
inventory, main, publisher or discovery. AST parity and causal perturbation tested.

## Causal replay

All timestamps are original server-clock labels, not a claimed UTC conversion.
Signal on source bar i is available at its timestamp plus 60 seconds (M1) or 300
seconds (M5). Entry uses the first manifested raw M1 opening timestamp >= that
availability. No extra 60-second latency. M1 10:00 enters at 10:01 when present;
M5 10:00 enters at 10:05 when present. Gaps defer to the next available raw M1
reference in the same permitted snapshot; never another source/file.

The original horizon counter starts from source signal bar i. Exit becomes due
when the next h source bars have closed. RAW counts raw source bars; NEWS-CLEAN
counts retained clean source bars. Entry prices always come from raw M1. No
future clean-bar position is inspected. The replay decrements an integer counter
on each subsequent source close and schedules the exit only at zero. A pending/open position
with an unresolved end-of-history exit continues to suppress subsequent signals.
Exit uses the first raw M1 open >= that causal completion timestamp.

News-clean is accepted causal under the owner's frozen provenance: MT5 USD HIGH
calendar events, -5/+5 minute windows, bar/mask temporal intersection, no economic
surprise or subsequent price-based suppression. No new calendar is read. Clean
rows must exactly match the corresponding raw rows. Mask timing is tested with
synthetic events; provenance causality is an owner-supplied premise, not inferred
from OHLC. No synthetic rebuilding of the historical mask.

No added hours, weekdays, midnight restrictions, SL, TP, trailing or optimized
exit. M5 remains the existing source aggregation; availability is bucket close.
Existing incomplete buckets are not silently rebuilt or dropped. Gaps and long
holds are permitted by the first-available rule. Observed-range drawdown cannot
reconstruct prices in gaps; unobserved holding seconds are explicit diagnostics.

## Positions and period boundaries

Each candidate is a separate sleeve, at most one pending/open position. Signals
while occupied are ignored and counted. Exit events precede signal/entry events
at equal timestamps, allowing causal reentry. No reversal or pyramiding, portfolio
netting or implicit combined equity. One fixed ounce XAU, USD accounting, no
leverage or compounding. The nominal 0.01 lot correspondence is cost conversion
only, not proof of broker minimum executable volume.

End-of-history signals requiring an endpoint/reference beyond admitted 2025 are
EXCLUDED_BOUNDARY, never force-closed or queried in 2026. Endpoints are sought
only in resident arrays from the four manifested files. Other year/half-year
crossing positions remain in chronological replay and suppress overlaps until
their actual modeled exit. They are omitted only from metrics whose interval
does not fully contain both entry and exit. A June/July 2025 trade remains in
annual 2025 metrics, not either half. A December 2024/January 2025 trade remains
in all-history descriptive results, not either annual metric. Report exclusions.

## Two frozen cost profiles

| Profile | Commission fraction per side | Full spread | Slippage per side |
|---|---:|---:|---:|
| FTMO COMMISSION + E1 SIMULATED EXECUTION | 0.000007 | 2 bps | 1 bp |
| CONSERVATIVE STRESS | 0.000014 | 5 bps | 2 bps |

FTMO's officially documented metals fee is 0.0007% per side, effective September
29, 2025; applied as a current fee scenario throughout, not historical tariff
reconstruction. E1 spread/slippage and all stress burdens are frozen hypothetical
assumptions, never observed fills or empirical upper bounds. FundedNext remains
UNRESOLVED / DISABLED, results null, no calculations and no gate dependency.

For direction d, reference opens Oe/Ox, commission c, full spread s, slippage l:
f=s/2+l; Pe=Oe*(1+d*f); Px=Ox*(1-d*f). Gross=d*(Ox-Oe).
Spread=(s/2)*(Oe+Ox); slippage=l*(Oe+Ox); commission=c*(Pe+Px).
Net=gross-spread-slippage-commission. All costs separate; one ounce. No additional
CSV spread deduction. No unverified tick rounding or per-deal cents rounding.
Full spread 2 bps means 1 bp per side, not 2; 5 bps means 2.5 per side.

The cost scope supplied by the owner contains no financing/swap schedule. Do not
invent one. Report overnight-trade holding seconds and weekend seconds explicitly;
net means specified spread/slippage/commission net, not all-in overnight net.
Financing and real quote/session execution remain requirements of later realistic
backtesting. No additional elimination criterion is introduced for exposure.

## Exact gates and reports

All of: >=100 trades in each of 2024 and 2025, >=40 in each 2025 half;
E1 net >0 in 2024/2025/H1 2025/H2 2025; stress net >0 in 2024/2025;
stress 2025 net minus largest positive trade still >0. No stress half-year gate,
PF/DD/win-rate threshold, ranking cap or 32-only filter. Insufficient count is
FAIL with exact count reason. Data/infrastructure problems are BLOCKED_DATA/ERROR,
not scientific FAIL. Overall scientific PASS means at least one candidate PASS,
all 500 processed, and no infrastructure/data failure. No downstream OOS job.

Per-candidate JSON preserves signature, ID, dataset/timeframe/raw-clean identity,
all counts, excluded boundaries, missing references, separate profile costs,
required annual/half-year metrics, expectancy, PF, win rate, best/worst trade,
stress ex-best net, and exact fail reasons. Complete deterministic trade ledgers
preserve availability, reference and modeled prices, exits, periods and exposure.
No-loss PF is null with a flag. Realized drawdown starts from equity zero.
Observed-adverse-mark drawdown additionally marks held raw M1 lows (long) or highs
(short), charging modeled liquidation costs; it does not include unobserved gaps
or assert exact tick/floating equity drawdown. Exit-minute range is excluded.

## Read boundary and provenance

DATA_MANIFEST contains exactly four certified pre-2026 paths and byte hashes.
The validator independently embeds these same four pins; policy/source data cannot
add a path. Membership is rejected before metadata/open; aliases/reparse points
are rejected. Windows CreateFile uses read sharing only, excluding concurrent
write/delete. Verify final handle path before reading, hash bytes before parsing,
and parse the same immutable bytes through BytesIO. No read-then-filter repair.
Validate strictly increasing unique timestamps, dates, units, OHLC and rows.

Supporting inputs use a fixed seven-path code/document allowlist, sealed by
PRE_REGISTRATION. No arbitrary supporting path can be injected. Runtime dependencies
are trusted Python/NumPy/pandas, loaded before the audit fence; exact versions
recorded. Application audit fence rejects unlisted Python reads, discovery,
network/subprocess/dynamic DLL loads and writes outside dedicated outputs. The
only native market reader is the reviewed fixed verified-byte function. This is
a code/dataflow restriction plus defense in depth, not an OS security sandbox
against hostile native code. No claim of native library sandboxing is made.

Source R4/frozen hashes, actual input hashes, validator and feature code hashes,
protocol/policy/evidence hashes, environment, supplied immutable code commit,
version and access trace accompany results. Published R4/consolidation never
modified. R4 historical access uncertainty remains subject to the separate
recertification procedure before any protected OOS authorization.

## Infrastructure and test gates

Unique output/progress paths; refuse an existing run namespace. Atomic JSON has
six PermissionError-only replace attempts and delays .05/.10/.20/.20/.20 seconds;
explicit chained exhaustion error, other exceptions propagate. Background
heartbeat every five seconds, plus phase/candidate transitions. Writer errors
propagate; failures produce ERROR/BLOCKED_DATA artifacts and nonzero exit.

Mandatory tests cover denied paths without opening real protected files, hashes,
native verified reader, M1/M5 timing and lookahead, exact R4 AST, RAW/clean horizon,
news temporal mask, boundaries, overlap, invalid contradictory direction, cost
identities, count/net gates, ex-best, attribution, drawdown/PF, deterministic replay,
retry/exhaustion/other exceptions, malformed inputs, 500/32 population and heartbeat.

Smoke: first two original IDs per dataset (eight total), first five available
weekdays per half-year for signal admission only. Retain full admitted source for
feature warmup/horizon; no parameter calibration, ranking or candidate gate use.
Write SMOKE_NOT_FOR_SELECTION records; inspect only invariants and functioning.
Synthetic tests must pass first. Code fixes invalidate the affected smoke; preserve
failed attempts and use a new output path. Any methodological change requires a
new owner decision/version. Full run only after code cold audit/tests/smoke PASS,
commit/push and unique queue entry; existing orchestrator launches, never manually.
