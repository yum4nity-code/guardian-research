#!/usr/bin/env python3
"""Guardian Shared Intelligence runtime V1 candidate.

One process per PC:
- one read-only Bybit EIB collector;
- one coverage-aware market-state engine;
- one atomic bridge into MetaTrader FILE_COMMON.

No trading credentials and no MT5 order capability.
"""

from __future__ import annotations

import argparse
import asyncio
import signal
from pathlib import Path

from collector_v1 import JsonlRecorder, default_data_dir
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_v1_coveragefix import MarketStateServiceCoverageFixed
from mt5_common_bridge_v1 import default_common_files_dir, publish_once

STATE_WRITE_RETRY_ATTEMPTS = 25
STATE_WRITE_RETRY_DELAY_SECONDS = 0.01


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian shared runtime coverage+bridge V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--common-files-dir", type=Path, default=None)
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    p.add_argument("--state-interval-seconds", type=float, default=1.0)
    p.add_argument("--bridge-interval-seconds", type=float, default=0.5)
    return p.parse_args()


async def run_state(
    state: MarketStateServiceCoverageFixed,
    stop_event: asyncio.Event,
    io_lock: asyncio.Lock,
) -> None:
    """Publish coverage state without racing the bridge reader on Windows.

    Python/Windows may reject os.replace() while another task has the target
    snapshot open. The shared lock removes the in-process state-writer/bridge-
    reader race; a short bounded retry also tolerates transient external access.
    """
    while not stop_event.is_set():
        published = False
        last_exc: PermissionError | None = None
        retries_used = 0

        for attempt in range(STATE_WRITE_RETRY_ATTEMPTS):
            try:
                async with io_lock:
                    state.publish_once()
                published = True
                retries_used = attempt
                break
            except PermissionError as exc:
                last_exc = exc
                if attempt + 1 < STATE_WRITE_RETRY_ATTEMPTS:
                    await asyncio.sleep(STATE_WRITE_RETRY_DELAY_SECONDS)

        if not published and last_exc is not None:
            print(f"[RUNTIME][STATE][REVIEW] persistent PermissionError after {STATE_WRITE_RETRY_ATTEMPTS} attempts: {last_exc}")
        elif retries_used:
            print(f"[RUNTIME][STATE][OK] replace_retries={retries_used}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=state.interval_seconds)
        except asyncio.TimeoutError:
            pass


async def run_bridge(
    source: Path,
    output: Path,
    stop_event: asyncio.Event,
    interval: float,
    io_lock: asyncio.Lock,
) -> None:
    last_generation: int | None = None
    while not stop_event.is_set():
        try:
            async with io_lock:
                result = publish_once(source, output)
            generation = int(result["generation_id"])
            if generation != last_generation:
                suffix = ""
                if result.get("replace_retries", 0):
                    suffix = f" replace_retries={result['replace_retries']}"
                print(f"[RUNTIME][BRIDGE][OK] generation={generation}{suffix}")
                last_generation = generation
        except FileNotFoundError:
            pass
        except Exception as exc:  # research runtime must surface bridge problems and remain alive
            print(f"[RUNTIME][BRIDGE][REVIEW] {type(exc).__name__}: {exc}")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(0.25, interval))
        except asyncio.TimeoutError:
            pass


async def async_main(args: argparse.Namespace) -> int:
    data_dir: Path = args.data_dir
    common_dir: Path = args.common_files_dir or default_common_files_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    recorder = JsonlRecorder(data_dir)
    collector = BybitCollectorHealthFixed(
        ["BTCUSD", "ETHUSD"], recorder, args.poll_seconds, args.health_seconds
    )
    state = MarketStateServiceCoverageFixed(
        data_dir,
        snapshot_name="market_state_v1_coveragefix.json",
        interval_seconds=args.state_interval_seconds,
    )
    runtime_stop = asyncio.Event()
    io_lock = asyncio.Lock()
    source = data_dir / "market_state_v1_coveragefix.json"
    output = common_dir / "GuardianSharedIntelligence" / "market_state_v1.csv"

    loop = asyncio.get_running_loop()

    def stop_all() -> None:
        collector.stop_event.set()
        state.stop_event.set()
        runtime_stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_all)
        except NotImplementedError:
            pass

    print("Guardian Shared Intelligence Runtime V1 START")
    print(f"data={data_dir}")
    print(f"FILE_COMMON output={output}")
    print("ONE collector + ONE coverage-aware state engine + ONE bridge for all local MT5 terminals.")
    print("READ ONLY external intelligence. No order capability.")
    print("Windows state/bridge publication is serialized to avoid transient file-sharing races.")

    tasks = [
        asyncio.create_task(collector.run(), name="collector"),
        asyncio.create_task(run_state(state, runtime_stop, io_lock), name="coverage_state"),
        asyncio.create_task(
            run_bridge(source, output, runtime_stop, args.bridge_interval_seconds, io_lock),
            name="bridge",
        ),
    ]

    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exc = task.exception()
            if exc is not None:
                raise exc
    finally:
        stop_all()
        await asyncio.gather(*tasks, return_exceptions=True)

    print("Guardian Shared Intelligence Runtime V1 STOP")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
