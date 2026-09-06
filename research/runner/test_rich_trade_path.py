#!/usr/bin/env python3
"""Regression checks for native Trade Path rich analytics."""

from __future__ import annotations

import rich_score


def make_row(symbol: str, net_r: float, gross_r: float, reached: set[str], exit_reason: str) -> dict:
    row = {
        "trade_id": f"{symbol}_T",
        "symbol": symbol,
        "mfe_r": "2.4" if "2r" in reached else "0.8",
        "mae_r": "0.35",
        "time_to_mfe_minutes": "120",
        "time_to_mae_minutes": "20",
        "max_retracement_from_mfe_r": "1.1",
        "path_ambiguous": "0",
        "path_ambiguity_reason": "",
        "exit_reason": exit_reason,
        "_net_r": net_r,
        "_gross_r": gross_r,
    }
    for suffix, _label in rich_score.TRADE_PATH_MILESTONES:
        hit = suffix in reached
        row[f"reached_{suffix}"] = "1" if hit else "0"
        row[f"first_touch_{suffix}_time"] = "2025.01.02 10:00:00" if hit else ""
        row[f"time_to_{suffix}_minutes"] = "60" if hit else ""
        row[f"mae_before_{suffix}"] = "0.25" if hit else ""
    for suffix in ("1r", "2r", "3r"):
        row[f"min_r_after_first_{suffix}_before_exit"] = "0.4" if suffix in reached else ""
        row[f"max_r_after_first_{suffix}_before_exit"] = "2.4" if suffix in reached else ""
    return row


def main() -> int:
    rows = [
        make_row("BTCUSD", 1.2, 1.25, {"0_5r", "1r", "2r"}, "EOD"),
        make_row("BTCUSD", -0.4, -0.35, {"0_5r"}, "EOD"),
        make_row("XAUUSD", -1.02, -1.0, set(), "STOP"),
    ]
    result = rich_score.trade_path_summary(rows)
    assert result["available"] is True
    assert result["path_rows"] == 3
    assert result["path_ambiguous_rows"] == 0
    assert result["milestones"]["0.5R"]["reached_n"] == 2
    assert result["milestones"]["1R"]["reached_n"] == 1
    assert result["milestones"]["2R"]["reached_n"] == 1
    assert result["milestones"]["3R"]["reached_n"] == 0
    assert result["losers_that_previously_reached_milestone"]["0.5R"]["n"] == 1
    assert result["by_symbol"]["BTCUSD"]["milestones"]["0.5R"]["reached_n"] == 2
    assert result["by_symbol"]["XAUUSD"]["milestones"]["0.5R"]["reached_n"] == 0
    print("RICH_TRADE_PATH_TESTS_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
