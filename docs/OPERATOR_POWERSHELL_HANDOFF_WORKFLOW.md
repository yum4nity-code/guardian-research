# Guardian Research — Operator PowerShell Handoff Workflow

Date: 2026-09-07 Europe/Paris
Status: **CANONICAL OPERATOR UX**

## Purpose

The preferred user experience is deliberately simple: the assistant does all research preparation, repository/state work, result interpretation and stage transitions; the user only runs short PowerShell commands on the Windows MT5 research PC.

This workflow is now part of the project contract and should be preserved by future assistants unless the user explicitly asks to change it.

## Canonical interaction

1. Assistant reads `GUARDIAN_STATE.json`, the active experiment manifest and this workflow before proposing local actions.
2. Assistant prepares/preregisters the experiment in GitHub, freezes source identity, updates state/views and waits for CI green.
3. Assistant gives the user the **smallest possible PowerShell command block**, normally:

```powershell
git pull
py -3 .\research\runner\guardian_research.py campaign D0XX --stage smoke --no-finalize
```

or, after engineering smoke PASS:

```powershell
git pull
py -3 .\research\runner\guardian_research.py campaign D0XX --stage development
```

4. The local runner performs compile, MT5 tests, integrity validation and Trade Path validation. Development campaigns also perform frozen scoring, rich analytics and result publication.
5. Runner publishes machine-readable evidence automatically to the isolated `backtest-results` branch and updates `backtests/<d0xx>/live/latest.json`.
6. The user should **not need to copy/paste logs or JSON**. The preferred completion message is simply:

`fini`

7. On `fini`, the assistant must read `backtests/<d0xx>/live/latest.json` and the referenced event/bundle directly from GitHub, determine success/failure, update manifest/state/views, and provide the next minimal PowerShell command.
8. If result transport fails but local evidence is valid, do not rerun MT5 solely for transport. Diagnose/publish the existing local evidence instead.

## User-facing rules

- Prefer one command block over step-by-step manual instructions.
- Do not ask the user to inspect JSON, paths, SHAs or logs when GitHub transport can provide them.
- Do not ask the user to manually run score/rich-score/finalize after a normal development campaign; `campaign ... --stage development` should do that automatically.
- Use `--no-finalize` for smoke because smoke is engineering-only and must not create an alpha verdict.
- Do not expose unnecessary infrastructure details unless something fails.
- After a successful run, the user should normally only have to say `fini`.

## Scientific safeguards remain mandatory

The simplified UX must never weaken research discipline:

- preregistration before result inspection;
- exact source SHA identity;
- Model=0 reference tester;
- engineering smoke before DEV;
- frozen DEV gates before rich interpretation;
- no post-hoc rescue of rejected V0;
- confirmation remains locked unless every preregistered DEV gate passes;
- previously seen windows are never relabeled OOS/confirmation.

## Multi-strategy mode

When several experiments are fully preregistered, source-complete and READY for the same stage, prefer one unattended campaign command:

```powershell
py -3 .\research\runner\guardian_research.py campaign D041 D042 D043 --stage smoke --no-finalize
```

MT5 remains sequential until concurrent `FILE_COMMON`/terminal isolation is explicitly proven safe.

## Handoff requirement for future assistants

A future assistant joining this project should treat this document as the canonical operator interface. The target is not to make the user operate the research stack; the target is to make the stack operate itself while the user only launches the approved PowerShell command and reports `fini`.

If another document conflicts with this workflow on operator ergonomics, prefer this workflow unless `GUARDIAN_STATE.json` explicitly records a newer replacement.
