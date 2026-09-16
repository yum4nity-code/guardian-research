#!/usr/bin/env python3
"""Read-only audit of published R34 outputs; no market loader or backtest.

Run with the exact published run directory as the only argument. Output JSON
goes to stdout. Windows source hashes are checked with explicit CRLF recovery
when Git's LF representation differs; no input file is modified.
"""
import ast
import csv
import hashlib
import io
import json
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def rows(path):
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def stamp(value):
    return datetime.fromisoformat(value)


def audit(root):
    status = json.loads((root / "status.json").read_text())
    expected_names = {
        "r34_signal_execution_feed_factorial_result.json", "r34_matrix_yearly.csv",
        "r34_signal_pairs.csv", "r34_fn_signals.csv", "r34_duka_signals.csv",
        *[f"r34_ledger_{s}_signal__{e}_execution.csv" for s in ("fn", "duka") for e in ("fn", "duka")],
    }
    assert {r["name"] for r in status["artifacts"]} == expected_names
    assert len(status["artifacts"]) == 9
    assert status["source_commit"] == "68e9435c37c1340588e32e96ca392e3d56de262e"
    checks = []
    for item in status["artifacts"]:
        raw = (root / item["name"]).read_bytes()
        lf = raw.replace(b"\r\n", b"\n")
        variants = [("EXACT", raw), ("LF_TO_CRLF", lf.replace(b"\n", b"\r\n"))]
        matches = [label for label, value in variants
                   if hashlib.sha256(value).hexdigest() == item["sha256"] and len(value) == item["size_bytes"]]
        assert matches, f"digest/size mismatch: {item['name']}"
        checks.append({"name": item["name"], "published_sha256": hashlib.sha256(raw).hexdigest(), "source_match": matches[0]})
    result = json.loads((root / "r34_signal_execution_feed_factorial_result.json").read_text())
    output = {"scope": "existing 2024/2025 R34 artifacts only; no replay", "hash_checks": checks, "years": {}}
    signals = {feed: rows(root / f"r34_{feed}_signals.csv") for feed in ("fn", "duka")}
    pairs = rows(root / "r34_signal_pairs.csv")
    for year in (2024, 2025):
        subsets = {feed: [r for r in values if int(r["year"]) == year] for feed, values in signals.items()}
        info = {}
        for feed, values in subsets.items():
            times = [stamp(r["time"]) for r in values]
            assert len(times) == len(set(times))
            assert all(t.year == year for t in times)
            assert all(float(r["close"]) > float(r["threshold"]) for r in values)
            assert all(abs(float(r["threshold"]) - float(r["prior_96_high"]) - .1 * float(r["atr"])) < 1e-8 for r in values)
            info[feed] = {"signals": len(values), "hours": dict(sorted(Counter(t.strftime("%H:%M") for t in times).items())),
                          "unique_dates": len(set(t.date() for t in times)),
                          "median_high_minus_close": statistics.median(float(r["high"]) - float(r["close"]) for r in values)}
        gaps = [min(abs((stamp(f["time"]) - stamp(d["time"])).total_seconds()) / 60 for d in subsets["duka"]) for f in subsets["fn"]]
        info["nearest_fn_to_duka_minutes"] = {"minimum": min(gaps), "median": statistics.median(gaps), "within_10": sum(g <= 10 for g in gaps)}
        assert sum(g <= 10 for g in gaps) == 0
        stages = Counter(r["match_stage"] for r in pairs if int(r["year"]) == year)
        assert stages == {"FN_ONLY": len(subsets["fn"]), "DUKA_ONLY": len(subsets["duka"])}
        info["pair_stages"] = dict(stages)
        info["cells"] = {}
        for signal in ("fn", "duka"):
            for execution in ("fn", "duka"):
                cell = f"{signal.upper()}_SIGNAL__{execution.upper()}_EXECUTION"
                ledger = [r for r in rows(root / f"r34_ledger_{signal}_signal__{execution}_execution.csv") if int(r["year"]) == year]
                rec = result["matrix"][cell][str(year)]
                acc = rec["accounting"]
                assert len(ledger) == acc["executable_trades"]
                assert len(subsets[signal]) == acc["signals_total"]
                assert acc["signals_total"] == sum(acc[k] for k in ("executable_trades", "ignored_overlap_signals", "excluded_boundary_signals", "missing_reference_trades"))
                valid_signals = {stamp(r["time"]) for r in subsets[signal]}
                assert all(stamp(r["signal_time"]) in valid_signals for r in ledger)
                assert all(stamp(r["signal_time"]) < stamp(r["entry_time"]) < stamp(r["exit_time"]) for r in ledger)
                metrics = {}
                for profile in ("E1", "STRESS"):
                    vals = [float(ast.literal_eval(r["profiles"])[profile]["net"]) for r in ledger]
                    net = sum(vals)
                    loss = -sum(v for v in vals if v < 0)
                    pf = sum(v for v in vals if v > 0) / loss if loss else None
                    exp = rec["metrics"][profile]
                    assert abs(net - exp["net"]) < 1e-7
                    assert pf is None and exp["PF"] is None or pf is not None and abs(pf - exp["PF"]) < 1e-9
                    metrics[profile] = {"net": net, "PF": pf}
                waits = [(stamp(r["entry_time"]) - stamp(r["signal_time"])).total_seconds() / 60 for r in ledger]
                info["cells"][cell] = {"accounting": acc, "metrics": metrics, "entry_wait_minutes": {"min": min(waits), "median": statistics.median(waits), "max": max(waits)}}
        output["years"][str(year)] = info
    return output


if __name__ == "__main__":
    print(json.dumps(audit(Path(sys.argv[1])), indent=2, sort_keys=True, allow_nan=False))
