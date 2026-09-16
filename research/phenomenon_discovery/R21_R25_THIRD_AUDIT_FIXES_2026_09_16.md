# R21–R25 third-audit corrections — 2026-09-16

The independent audit of `cd40d686e002792753dd5e1a4d562340108de04d` returned FAIL:
an arbitrary market CSV could be physically opened when passed as `--index`,
and R22 reported zero baseline days when no event had a usable response.
The owner then explicitly requested implementation of the corrections.

## Physical input admission

The corrected v1.02 admits only this canonical R15 metadata path:

`D:/MT5_Backtests/Research/Autonomous/r15_dukascopy_xauusd_union_v1/xauusd_dukascopy_master_payload_index.csv`

Its pinned SHA256 is:

`d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566`

Provenance: the existing R15 union PASS manifest
`r15_dukascopy_market_manifest.json`, generated `2026-09-14T11:53:03.736860+00:00`,
records that same path and digest. Only that manifest and index **metadata** were
read to verify the pin. No source BI5 or market boundary CSV was opened.

Admission order:

1. Reject any different absolute path before any file open or builder call.
2. Reject a canonical path redirected by a symlink/junction.
3. Read the admitted metadata once and require its pinned digest.
4. Write exactly those checked bytes into the private temporary workspace.
5. Run the sealed builder against that snapshot, validate its receipt, then
   analyze only its internally generated discovery CSV.

The CLI cannot override the trusted path or digest through an argument or an
environment variable. A source relocation or index rebuild requires a reviewed
pin change. The CLI also refuses to overwrite the canonical index as its output.
The invariant assumes the canonical R15 source remains under the project's
immutable-cache controls; it is not protection against an adversary modifying
the program or operating system. A digest mismatch blocks the builder.

## R22 coverage diagnostics

Baseline observations are now counted before the no-valid-events return.
For three baseline days and zero usable event labels, the diagnostics are:

- `baseline_days=3`, `event_days=0`;
- `required_replicates=3`, `valid_replicates=0`;
- `undefined_delete_days` contains all three dates, since deleting any day
  still leaves no events;
- mean, SE and t remain unavailable.

The zero-baseline/zero-event case remains all-zero counts with an empty date list.
The regular estimator, its variance formula, phenomenon definitions, horizons,
compression states, signs, stage boundaries and promotion rules are unchanged.

## Verification

Native Python synthetic tests pass for the corrected v1.02, inherited v1.01,
sealed builder, and effective generation-83 queue. New coverage includes:

- 2019H2/2025/2026 CSV paths and a same-name index in an untrusted directory:
  zero opens, zero temporary directories and zero builder calls;
- CLI admission, redirected canonical path, wrong digest, and output collision;
- private index snapshot remaining unchanged after a later source modification;
- real R15 decode/hash/aggregate integration on a tiny synthetic BI5 fixture,
  with no opens of the out-of-discovery references and temporary cleanup;
- empty-event horizon diagnostics through the real R22 summary;
- analytical regular jackknife SE and R24 gap regression.

Generation 83 is unchanged: three effective jobs, zero enabled,
`human_approved_2026=false`. No historical discovery, confirmation, pre-OOS,
protected-period or live job was launched. Test success is implementation
verification by the correcting author, **not a new independent cold-audit PASS**.
Next safe action: independent review of the corrective commit before any queue
generation authorizes historical execution.
