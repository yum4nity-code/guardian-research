# M5 topology cache warning cleanup

Date: 2026-09-22

Observed during first cache build:
- RuntimeWarning: All-NaN slice encountered
- RuntimeWarning: divide by zero encountered in divide
- RuntimeWarning: invalid value encountered in divide

Cause:
endpoint excursion arrays were reduced for every timestamp before applying the existing eligibility mask.
Boundary rows, session gaps and zero-volatility rows could therefore emit warnings even though they were subsequently excluded.

Fix:
- compute excursions only for rows already satisfying the frozen eligibility conditions;
- additionally require the complete forward path to be finite before evaluating the target;
- preserve identical lookbacks, horizons, tradability rules and endpoint formula.

Scientific effect:
none on previously eligible complete-path rows.
No alpha tests involved.

Engine:
M5-MOTION-TOPOLOGY-BUILD-1.0.1
