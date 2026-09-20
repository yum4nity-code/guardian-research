param([string]$Root="D:\MT5_Backtests")
$ErrorActionPreference="Stop"
$Repo=Join-Path $Root "guardian-research"
$Core=Join-Path $Repo "research\core\causal_time.py"
$Test=Join-Path $Repo "research\core\test_causal_time.py"
New-Item -ItemType Directory -Force (Split-Path $Core) | Out-Null
$coreCode=@'
from __future__ import annotations
import pandas as pd
import numpy as np

def causal_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate source bars into buckets labeled at AVAILABLE_AT.
    Output index is decision-safe: bucket [t-rule,t) is labeled t.
    """
    x=df.copy()
    if not isinstance(x.index,pd.DatetimeIndex):
        for c in ("datetime","time","timestamp"):
            if c in x.columns:
                x=x.set_index(pd.to_datetime(x[c])); break
        else: raise ValueError("DatetimeIndex or datetime/time/timestamp column required")
    x=x.sort_index()
    if x.index.has_duplicates or not x.index.is_monotonic_increasing:
        raise ValueError("source timestamps must be unique and monotonic")
    cols={"open":"first","high":"max","low":"min","close":"last"}
    missing=set(cols)-set(x.columns)
    if missing: raise ValueError(f"missing OHLC columns: {sorted(missing)}")
    y=x.resample(rule,label="right",closed="left").agg(cols).dropna()
    y["EVENT_TIME"]=y.index-pd.tseries.frequencies.to_offset(rule)
    y["AVAILABLE_AT"]=y.index
    return y

def assert_decision_safe(frame: pd.DataFrame, decision_time=None):
    if "AVAILABLE_AT" not in frame: raise ValueError("AVAILABLE_AT required")
    dt=pd.Series(frame.index if decision_time is None else decision_time,index=frame.index)
    av=pd.to_datetime(frame["AVAILABLE_AT"])
    if (pd.to_datetime(dt)<av).any(): raise AssertionError("look-ahead: decision_time < AVAILABLE_AT")
    return True

def rolling_bars(s: pd.Series,n_bars:int,fn:str):
    if not isinstance(n_bars,int) or n_bars<1: raise ValueError("n_bars must be positive integer")
    r=s.rolling(n_bars,min_periods=n_bars)
    if fn=="mean": return r.mean()
    if fn=="std": return r.std()
    if fn=="min": return r.min()
    if fn=="max": return r.max()
    raise ValueError("unsupported rolling function")

def forward_return_exact(close:pd.Series,minutes:int)->pd.Series:
    """Exact timestamp target; missing future timestamp => NaN, never row-shift approximation."""
    if minutes<=0: raise ValueError("minutes must be >0")
    s=close.sort_index(); future=s.reindex(s.index+pd.Timedelta(minutes=minutes))
    future.index=s.index
    return np.log(future/s)
'@
$testCode=@'
import pandas as pd, numpy as np, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from causal_time import causal_ohlc,assert_decision_safe,rolling_bars,forward_return_exact

def raw(n=20):
 t=pd.date_range("2020-01-01 00:00",periods=n,freq="1min")
 p=np.arange(n,dtype=float)+100
 return pd.DataFrame({"open":p,"high":p+.2,"low":p-.2,"close":p+.1},index=t)

x=raw()
m5=causal_ohlc(x,"5min")
r=m5.loc[pd.Timestamp("2020-01-01 00:05")]
assert r["EVENT_TIME"]==pd.Timestamp("2020-01-01 00:00")
assert r["AVAILABLE_AT"]==pd.Timestamp("2020-01-01 00:05")
assert r["close"]==x.loc[pd.Timestamp("2020-01-01 00:04"),"close"]
assert r["close"]!=x.loc[pd.Timestamp("2020-01-01 00:05"),"close"]
assert assert_decision_safe(m5)
try:
 assert_decision_safe(m5, m5.index-pd.Timedelta(minutes=1)); raise AssertionError("expected lookahead rejection")
except AssertionError as e:
 assert "look-ahead" in str(e)
z=rolling_bars(m5.close,2,"mean"); assert pd.isna(z.iloc[0]) and np.isfinite(z.iloc[1])
f=forward_return_exact(x.close,5); assert np.isclose(f.iloc[0],np.log(x.close.iloc[5]/x.close.iloc[0]))
gap=x.drop(index=pd.Timestamp("2020-01-01 00:05")); fg=forward_return_exact(gap.close,5); assert pd.isna(fg.loc[pd.Timestamp("2020-01-01 00:00")])
print("CAUSAL_CORE_TESTS_OK")
'@
Set-Content $Core $coreCode -Encoding UTF8
Set-Content $Test $testCode -Encoding UTF8
Write-Host "[V13] 1/4 25% syntax"
py -m py_compile $Core $Test
if($LASTEXITCODE -ne 0){throw "compile failed"}
Write-Host "[V13] 2/4 50% unit tests"
py $Test
if($LASTEXITCODE -ne 0){throw "tests failed"}
Write-Host "[V13] 3/4 75% hashes"
Get-FileHash $Core,$Test -Algorithm SHA256 | Format-Table -AutoSize
Write-Host "[V13] 4/4 100% complete — OOS untouched"
