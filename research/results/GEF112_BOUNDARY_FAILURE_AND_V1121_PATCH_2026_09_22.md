# V112.0 locked-OOS boundary failure — 2026-09-22

Run attempted after explicit human approval.

Observed failure:
RuntimeError: V112 loaded 2026+ data

Root cause:
- raw files opened were only 2023, 2024 and 2025;
- raw rows were already filtered to UTC < 2026-01-01;
- pandas resample(..., label="right", closed="left") can assign the final 2025 minutes to a synthetic output bin labelled 2026-01-01 00:00;
- the old guard checked the resampled label and falsely classified it as 2026 raw data.

Scientific status:
- locked OOS 2023-2025 has now been opened and is considered consumed;
- no V112 candidate scoring completed before the failure;
- no 2026 raw market file was opened;
- no candidate, horizon, orientation, gate, bootstrap rule or family rule is changed.

V112.1 correction:
- assert raw UTC max < 2026-01-01;
- clip right-labelled resampled output to [2023-01-01, 2026-01-01);
- keep every scientific rule unchanged.
