# EA01 recovery cold review — 2026-09-17

Verdict: PASS, local cold review (no independent reviewer claimed).

Compared final adapter and tests against d0451c1; inspected actual executor/receipt deduplication and frozen engine paths. The earlier interrupted draft was rejected: missing PID was treated as absence, os.kill(pid, 0) was unsafe on Windows, and automatic recovery could move a live legacy marker. Final code has no automatic quarantine. Offline recovery requires affirmative process-inventory evidence, terminal receipt identity/time, raw-byte SHA256, and a dead PID if present; unknown access remains BLOCKED. Windows rename preserves the source or archives without replacement.

Exclusive file creation prevents overwrite races. A persistent ATTEMPT_CONSUMED claim precedes engine execution, so even a later main commit cannot cause a second engine run. It is intentionally never rearmed automatically. Existing RUNNING markers always block main(). Interruption or timeout may leave a marker; the receipt and process inventory must then be reconciled offline.

Actual marker was already archived before this session; SHA256 and timestamps reverified. Prior BI5 error archived separately without deletion to prevent its old terminal filename blocking error reporting. Prior receipt preserved. Existing orchestrator stays running and queue generation 115 remains unchanged. No engine/data-loader/preregistration change, no protected 2026 data opened, no R33/R34/R35 write.

Validation: py_compile PASS; 37 synthetic tests PASS, including BI5 layout, missing process evidence, live PID, older receipt, quarantine collision, no status overwrite and no second attempt. Initial sandbox run failed on Windows temporary-directory permissions; identical tests passed outside that restriction. This is infrastructure validation, not a scientific EA01 verdict.
