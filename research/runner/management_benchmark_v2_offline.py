#!/usr/bin/env python3
"""Safe offline launcher for Guardian Management Benchmark V2."""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Any

import experiment
import management_benchmark as v1
import management_benchmark_v2 as v2
import runner
import state_tools

FROZEN_DATASETS: dict[str, dict[str, Any]] = {
    "D038": {"experiment_id":"D038-NR7-VOLATILITY-CONTRACTION-BREAKOUT-V0","stage":"development","rows":459},
    "D039": {"experiment_id":"D039-INSIDE-DAY-BREAKOUT-V0","stage":"development","rows":441},
    "D040": {"experiment_id":"D040-NR4-VOLATILITY-CONTRACTION-BREAKOUT-V0","stage":"development","rows":758},
    "D045": {"experiment_id":"D045-D1-DONCHIAN-20-10-BENCHMARK-V0","stage":"development","rows":145},
}

class OfflineV2SafetyError(RuntimeError): pass

def _short(identifier:str)->str:
    x=identifier.upper()
    return x if x.startswith('D') else 'D'+x

def archived_context(identifier:str):
    short=_short(identifier)
    frozen=FROZEN_DATASETS.get(short)
    if frozen is None:
        raise OfflineV2SafetyError(f"Management Benchmark V2 refuses non-frozen dataset {identifier!r}; allowed={sorted(FROZEN_DATASETS)}")
    state=state_tools.load_state()
    errs=state_tools.validate_state(state)
    if errs: raise OfflineV2SafetyError('invalid project state: '+'; '.join(errs))
    manifest_path,manifest=experiment.load_manifest(short)
    merr=experiment.validate_manifest(manifest)
    if merr: raise OfflineV2SafetyError(f"invalid archived experiment manifest {short}: "+'; '.join(merr))
    if manifest.get('experiment_id')!=frozen['experiment_id']:
        raise OfflineV2SafetyError(f"archived identity mismatch for {short}")
    if manifest.get('experiment_id')==state.get('research',{}).get('active_experiment'):
        raise OfflineV2SafetyError(f"{short} is active; V2 only accepts archived evidence")
    return state,manifest_path,manifest

def install_guard()->None:
    original_dataset=v1._dataset
    def frozen_dataset(identifier:str, stage:str, workspace:Path)->dict[str,Any]:
        short=_short(identifier); frozen=FROZEN_DATASETS.get(short)
        if frozen is None: raise OfflineV2SafetyError(f"V2 refuses dataset {identifier!r}")
        if stage!=frozen['stage']: raise OfflineV2SafetyError(f"V2 stage mismatch for {short}: expected={frozen['stage']} actual={stage}")
        ds=original_dataset(short,stage,workspace)
        if ds['experiment_id']!=frozen['experiment_id']: raise OfflineV2SafetyError(f"V2 experiment identity mismatch for {short}")
        if len(ds['rows'])!=frozen['rows']: raise OfflineV2SafetyError(f"V2 frozen row count mismatch for {short}: expected={frozen['rows']} actual={len(ds['rows'])}")
        return ds
    runner.load_context=archived_context  # type: ignore[assignment]
    v1._dataset=frozen_dataset  # type: ignore[assignment]

def main()->int:
    install_guard()
    return v2.main()

if __name__=='__main__': raise SystemExit(main())
