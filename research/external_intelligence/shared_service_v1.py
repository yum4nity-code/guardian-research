#!/usr/bin/env python3
"""Guardian Shared Intelligence Service V1.

Runs exactly one read-only Bybit collector and one strategy-neutral market-state
engine per machine. Guardian instances consume market_state_v1.json; this
service has no MT5 order capability and no trading credentials.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_v1 import MarketStateService


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian Shared Intelligence Service V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    p.add_argument("--state-interval-seconds", type=float, default=1.0)
    return p.parse_args(argv)


async def run_service(args: argparse.Namespace) -> int:
    args.data_dir.mkdir(parents=True, exist_ok=True)
    recorder = JsonlRecorder(args.data_dir)
    collector = BybitCollectorHealthFixed(
        ["BTCUSD", "ETHUSD"],
        recorder,
        args.poll_seconds,
        args.health_seconds,
    )
    market_state = MarketStateService(
        args.data_dir,
        interval_seconds=args.state_interval_seconds,
    )

    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        collector.stop_event.set()
        market_state.stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, request_stop)
        except NotImplementedError:
            pass

    print("Guardian Shared Intelligence Service V1 START")
    print(f"data={args.data_dir}")
    print("1 collector + 1 market-state engine for all local Guardian instances.")
    print("Public read-only data only. No API key. No MT5 orders.")
    print(f"shared snapshot={args.data_dir / 'market_state_v1.json'}")

    collector_task = asyncio.create_task(collector.run(), name="eib_collector")
    state_task = asyncio.create_task(market_state.run(), name="market_state")

    try:
        done, pending = await asyncio.wait(
            [collector_task, state_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in done:
            exc = task.exception()
            if exc is not None:
                raise exc
    finally:
        request_stop()
        await asyncio.gather(collector_task, state_task, return_exceptions=True)

    print("Guardian Shared Intelligence Service V1 STOP")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return asyncio.run(run_service(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
