# R21-R25 second cold-audit FAIL and v1.02 corrective record — 2026-09-16

## Independent audit verdict

Commit \`68bdd511a86eefc16597e6d2b207d40d376e9248\` (v1.01 / generation 82) received independent verdict **FAIL**.

Findings:
- HIGH: R22 jackknife silently dropped undefined delete-one-day replications, permitting artificial significance.
- HIGH: engine still accepted an arbitrary CSV path and could physically open a future-data CSV before rejecting its rows.
- MEDIUM: absolute M5 grid was not enforced; e.g. 08:20:30 NY could be accepted as an 08:20 anchor.
- LOW: supplied R24 10:00 boundary test did not actually reach 10:00.

No real historical backtest was authorized or run from that audited commit.

## v1.02 corrective design

File:
\`research/phenomenon_discovery/xau_edge_discovery_r21_r25_v1_02.py\`

v1.02 is a thin fail-closed wrapper around only those v1.01 phenomenon definitions the independent audit found coherent on valid M5 input.

### H1 correction — R22 jackknife

\`r22_complete_estimator_day_jackknife\` now treats every day in the union of baseline days and event days as a required delete-one-day replication.

If **any** required deletion makes the estimator undefined:
- \`cluster_se = None\`;
- \`cluster_t = None\`;
- no reduced-sample jackknife is computed;
- \`undefined_delete_days\` records the exact failing day(s);
- \`baseline_days\`, \`event_days\`, \`required_replicates\`, and \`valid_replicates\` are reported separately.

The independent-audit counterexample with one event day is explicitly covered by v1.02 regression tests.

### H2 correction — physical input provenance

v1.02 no longer accepts \`--input\` or any arbitrary M5 CSV.

CLI accepts only:
- the immutable R15 master payload index via \`--index\`;
- an output JSON path.

The engine internally:
1. creates a private temporary path;
2. calls the sealed \`build_xau_m5_discovery_slice_v1_01.build()\`;
3. validates the builder receipt against the frozen discovery contract;
4. opens only the generated discovery CSV;
5. deletes that temporary workspace automatically.

Therefore the engine has no CLI path capable of pointing at a 2019H2/2025 market CSV. The sealed builder remains responsible for refusing to decode post-2019-06-30 payloads.

### M1 correction — absolute M5 grid

Before event logic, every generated \`server_epoch\` must satisfy:

\`server_epoch % 300 == 0\`

Any off-grid bar hard-fails. A 30-second-shifted bar is covered by regression test.

### L1 correction — R24 boundary tests

v1.02 regression tests explicitly construct bars from 08:20 through 10:00 New York:
- 09:55 breakout must be accepted;
- 10:00-open breakout must be rejected.

## Control plane

Generation 82 base/append are archived as failed-audit provenance.

Canonical queue is now generation 83:
- \`human_approved_2026=false\`;
- 3 effective jobs;
- 0 enabled jobs;
- discovery executor is v1.02;
- no \`--input\` argument exists;
- discovery window ends exclusively at \`2019-07-01T00:00:00Z\`.

## Gate state

- Third independent cold audit: **PENDING**.
- Real historical discovery: **NOT AUTHORIZED / NOT RUN**.
- Confirmation: **INACCESSIBLE**.
- 2025: **INACCESSIBLE / NOT OPENED**.
- 2026+: **HARD-SEALED / NOT OPENED**.
- Guardian integration: **NOT AUTHORIZED**.
- Live/real trading: **NOT AUTHORIZED**.
