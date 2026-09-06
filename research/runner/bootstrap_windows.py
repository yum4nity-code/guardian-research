#!/usr/bin/env python3
"""Bootstrap Guardian Research Runner paths on the local Windows MT5 machine.

The bootstrap is intentionally conservative: it only auto-selects an MT5 root
when it can find a coherent installation containing MetaEditor and MQL5/Experts.
It never edits MT5 files and never starts the terminal.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "local" / "guardian_runner.json"


def norm(path: Path) -> str:
    return path.resolve().as_posix()


def candidate_roots(explicit: str | None = None) -> list[Path]:
    candidates: list[Path] = []

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            return
        if resolved not in candidates:
            candidates.append(resolved)

    if explicit:
        add(Path(explicit))

    for env_name in ("GUARDIAN_MT5_ROOT", "MT5_ROOT"):
        if os.environ.get(env_name):
            add(Path(os.environ[env_name]))

    for fixed in (
        Path("D:/MT5_FundedNext"),
        Path("D:/MT5"),
        Path("C:/MT5_FundedNext"),
        Path("C:/MT5"),
        Path("C:/Program Files/MetaTrader 5"),
        Path("C:/Program Files (x86)/MetaTrader 5"),
    ):
        add(fixed)

    for base in (Path("C:/Program Files"), Path("C:/Program Files (x86)"), Path("D:/")):
        if not base.exists():
            continue
        for pattern in ("*MetaTrader*", "*FundedNext*", "*MT5*"):
            try:
                for entry in base.glob(pattern):
                    if entry.is_dir():
                        add(entry)
            except OSError:
                pass

    return candidates


def find_case_insensitive(root: Path, names: Iterable[str]) -> Path | None:
    if not root.is_dir():
        return None
    wanted = {name.lower() for name in names}
    try:
        for child in root.iterdir():
            if child.is_file() and child.name.lower() in wanted:
                return child.resolve()
    except OSError:
        return None
    return None


def inspect_root(root: Path) -> dict[str, str | bool | None]:
    metaeditor = find_case_insensitive(root, ("metaeditor64.exe", "metaeditor.exe"))
    terminal = find_case_insensitive(root, ("terminal64.exe", "terminal.exe"))
    experts = root / "MQL5" / "Experts"
    coherent = bool(metaeditor and terminal and experts.is_dir())
    return {
        "root": norm(root),
        "coherent": coherent,
        "metaeditor_exe": norm(metaeditor) if metaeditor else None,
        "terminal_exe": norm(terminal) if terminal else None,
        "experts_dir": norm(experts) if experts.is_dir() else None,
    }


def choose_installation(explicit: str | None) -> tuple[dict[str, str | bool | None], list[dict[str, str | bool | None]]]:
    inspected = [inspect_root(root) for root in candidate_roots(explicit)]
    coherent = [item for item in inspected if item["coherent"]]

    if explicit:
        exact = inspect_root(Path(explicit))
        if not exact["coherent"]:
            raise RuntimeError(f"explicit MT5 root is not coherent: {explicit}")
        return exact, inspected

    if len(coherent) == 1:
        return coherent[0], inspected
    if not coherent:
        raise RuntimeError("no coherent MT5 installation found; pass --mt5-root explicitly")
    roots = ", ".join(str(item["root"]) for item in coherent)
    raise RuntimeError(f"multiple coherent MT5 installations found; pass --mt5-root: {roots}")


def default_workspace() -> Path:
    preferred = Path("D:/MT5_Backtests")
    if preferred.is_dir():
        return preferred / "guardian-runner"
    return ROOT / "local" / "guardian-runner-workspace"


def default_common_files() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is unavailable; cannot resolve MetaTrader common files folder")
    return Path(appdata) / "MetaQuotes" / "Terminal" / "Common" / "Files"


def build_config(installation: dict[str, str | bool | None]) -> dict[str, str]:
    experts = Path(str(installation["experts_dir"])) / "GuardianResearch"
    return {
        "mt5_root": str(installation["root"]),
        "metaeditor_exe": str(installation["metaeditor_exe"]),
        "terminal_exe": str(installation["terminal_exe"]),
        "mt5_experts_dir": norm(experts),
        "common_files_dir": norm(default_common_files()),
        "workspace_dir": norm(default_workspace()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Autodetect local MT5 paths for Guardian Research Runner")
    parser.add_argument("--mt5-root", help="explicit MT5 installation/data root")
    parser.add_argument("--dry-run", action="store_true", help="show detection result without writing config")
    parser.add_argument("--force", action="store_true", help="replace an existing local config")
    args = parser.parse_args()

    if os.name != "nt" and not args.dry_run:
        print("ERROR: bootstrap writes config only on Windows; use --dry-run elsewhere", file=sys.stderr)
        return 1

    try:
        chosen, inspected = choose_installation(args.mt5_root)
        config = build_config(chosen)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(json.dumps({"inspected": [inspect_root(p) for p in candidate_roots(args.mt5_root)]}, indent=2))
        return 1

    report = {"chosen": chosen, "config": config, "config_path": norm(CONFIG)}
    if args.dry_run:
        report["inspected"] = inspected
        print(json.dumps(report, indent=2))
        return 0

    if CONFIG.exists() and not args.force:
        print(f"ERROR: config already exists: {CONFIG}; use --force to replace it", file=sys.stderr)
        return 1

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    Path(config["mt5_experts_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["common_files_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["workspace_dir"]).mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("NEXT: python research/runner/runner.py doctor D037")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
