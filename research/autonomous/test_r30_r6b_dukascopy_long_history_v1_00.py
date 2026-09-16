#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import r30_build_dukascopy_xau_yearly_v1_00 as build
import r30_r6b_dukascopy_long_history_v1_00 as bt


def test_candidate_definitions_frozen():
    assert bt.CANDIDATES["R6B-347"] == {
        "candidate_id":"R6B-347",
        "lookback_bars":96,
        "buffer_atr":0.1,
        "horizon_bars":96,
        "session":"UTC00_08",
        "session_start":0,
        "session_end":8,
        "direction":1,
        "direction_name":"LONG",
    }
    assert bt.CANDIDATES["R6B-307"] == {
        "candidate_id":"R6B-307",
        "lookback_bars":96,
        "buffer_atr":0.0,
        "horizon_bars":48,
        "session":"UTC00_08",
        "session_start":0,
        "session_end":8,
        "direction":1,
        "direction_name":"LONG",
    }


def trade(entry: float, net: float, t: str) -> dict:
    return {
        "entry_time":t,
        "exit_time":t,
        "entry_open":entry,
        "profiles":{
            "E1":{"net":net},
            "STRESS":{"net":net},
        },
    }


def test_capital_compounding_is_one_x_notional():
    xs=[
        trade(100.0,10.0,"2020-01-01T00:00:00+00:00"),  # +10%
        trade(100.0,-5.0,"2020-01-02T00:00:00+00:00"),  # -5%
    ]
    out=bt.capital_path(xs,"E1",10000.0)
    assert abs(out["ending_capital"]-10450.0)<1e-9
    assert abs(out["return_pct"]-4.5)<1e-9
    assert out["trades"]==2


def test_capital_drawdown_trade_close():
    xs=[
        trade(100.0,10.0,"2020-01-01T00:00:00+00:00"),
        trade(100.0,-10.0,"2020-01-02T00:00:00+00:00"),
    ]
    out=bt.capital_path(xs,"E1",10000.0)
    assert abs(out["max_drawdown_trade_close_pct"]-10.0)<1e-9


def test_cagr():
    a=pd.Timestamp("2020-01-01",tz="UTC")
    b=pd.Timestamp("2021-01-01",tz="UTC")
    x=bt.cagr(10000.0,11000.0,a,b)
    assert x is not None
    assert 9.9 < x < 10.1


def test_builder_refuses_existing_manifest():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        index=root/"index.csv"
        index.write_text("x\n",encoding="utf-8")
        out=root/"out"; out.mkdir()
        manifest=root/"manifest.json"
        manifest.write_text("{}",encoding="utf-8")
        with patch("sys.argv",[
            "r30-build",
            "--index",str(index),
            "--output-dir",str(out),
            "--manifest",str(manifest),
        ]):
            try:
                build.main()
            except RuntimeError as exc:
                assert "refusing overwrite" in str(exc)
            else:
                raise AssertionError("existing manifest was overwritten")


def test_result_refuses_existing_output_before_market_load():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        out=root/"out"; out.mkdir()
        (out/"r30_r6b_dukascopy_long_history_result.json").write_text(
            "{}",encoding="utf-8"
        )
        manifest=root/"manifest.json"
        manifest.write_text(json.dumps({
            "status":"PASS",
            "research":"R30",
            "source_index_sha256":bt.PINNED_INDEX_SHA256,
            "protected_2026_opened":False,
            "yearly":{"2004":{},"2025":{}},
        }),encoding="utf-8")
        with patch("sys.argv",[
            "r30-bt",
            "--manifest",str(manifest),
            "--output-dir",str(out),
        ]):
            try:
                bt.main()
            except RuntimeError as exc:
                assert "refusing overwrite" in str(exc)
            else:
                raise AssertionError("existing R30 result was overwritten")


def main():
    test_candidate_definitions_frozen()
    test_capital_compounding_is_one_x_notional()
    test_capital_drawdown_trade_close()
    test_cagr()
    test_builder_refuses_existing_manifest()
    test_result_refuses_existing_output_before_market_load()
    print("PASS: R30 Dukascopy long-history tests")


if __name__=="__main__":
    main()
