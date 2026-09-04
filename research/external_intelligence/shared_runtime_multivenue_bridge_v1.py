#!/usr/bin/env python3
"""Guardian Shared Intelligence multi-venue runtime V1 (research/read-only).

One process per PC:
- one validated Bybit public collector;
- one Binance public collector;
- one venue-separated multi-venue market-state engine;
- one atomic bridge into MT5 FILE_COMMON.

No API key, account endpoint, order endpoint, MT5 trade call, strategy signal,
or risk action. External data remain observational only.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import signal
import time
from dataclasses import dataclass
from pathlib import Path

from binance_collector_v1 import BinanceCollector, BinanceJsonlRecorder
from collector_v1 import JsonlRecorder, default_data_dir
from collector_v1_healthfix import BybitCollectorHealthFixed
from market_state_multivenue_v1 import MultiVenueMarketStateService
from mt5_common_bridge_multivenue_v1 import default_common_files_dir, publish_once as publish_bridge

STATE_RETRY_ATTEMPTS = 25
STATE_RETRY_DELAY_SECONDS = 0.01
SHUTDOWN_GRACE_SECONDS = 3.0


@dataclass
class RuntimeStats:
    state_publishes: int = 0
    bridge_publishes: int = 0
    distinct_generations: int = 0
    last_generation: int = 0
    review_errors: int = 0
    started_monotonic: float = 0.0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Guardian shared multi-venue runtime V1")
    p.add_argument("--data-dir", type=Path, default=default_data_dir())
    p.add_argument("--common-files-dir", type=Path, default=None)
    p.add_argument("--poll-seconds", type=float, default=5.0)
    p.add_argument("--health-seconds", type=float, default=5.0)
    p.add_argument("--state-interval-seconds", type=float, default=1.0)
    p.add_argument("--run-seconds", type=float, default=0.0,
                   help="0 = run until Ctrl+C; >0 = bounded gate/smoke duration")
    p.add_argument("--gate", action="store_true",
                   help="At bounded shutdown validate generations and final MT5 CSV")
    p.add_argument("--log-seconds", type=float, default=15.0)
    return p.parse_args()


def _read_bridge_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="ascii", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _validate_final_bridge(path: Path, stats: RuntimeStats, observed_seconds: float) -> list[str]:
    failures: list[str] = []
    if stats.review_errors:
        failures.append(f"runtime review errors={stats.review_errors}")
    if stats.distinct_generations < 2:
        failures.append("fewer than 2 distinct state/bridge generations")
    if observed_seconds >= 30.0 and stats.distinct_generations < 10:
        failures.append("generation rate unexpectedly low")
    try:
        rows = _read_bridge_rows(path)
    except Exception as exc:
        failures.append(f"cannot read final FILE_COMMON bridge: {type(exc).__name__}: {exc}")
        return failures
    if len(rows) != 2:
        failures.append(f"expected 2 bridge rows, got {len(rows)}")
        return failures
    if {r.get("symbol") for r in rows} != {"BTCUSD", "ETHUSD"}:
        failures.append("unexpected bridge symbols")
    for row in rows:
        sym = row.get("symbol", "?")
        if row.get("bridge_schema_version") != "2":
            failures.append(f"{sym} bridge schema != 2")
        if row.get("bybit_status") != "OK":
            failures.append(f"{sym} Bybit status != OK")
        if row.get("binance_status") != "OK":
            failures.append(f"{sym} Binance status != OK")
        if row.get("both_core_ok") != "1":
            failures.append(f"{sym} both_core_ok != 1")
        if row.get("generation_id") != str(stats.last_generation):
            failures.append(f"{sym} final generation mismatch")
    return failures


async def _publish_state_with_retry(state: MultiVenueMarketStateService) -> dict:
    last_exc: PermissionError | None = None
    for attempt in range(STATE_RETRY_ATTEMPTS):
        try:
            return state.publish_once()
        except PermissionError as exc:
            last_exc = exc
            if attempt + 1 < STATE_RETRY_ATTEMPTS:
                await asyncio.sleep(STATE_RETRY_DELAY_SECONDS)
    assert last_exc is not None
    raise last_exc


async def run_state_bridge(
    state: MultiVenueMarketStateService,
    source: Path,
    output: Path,
    stop_event: asyncio.Event,
    stats: RuntimeStats,
    log_seconds: float,
) -> None:
    last_log = 0.0
    while not stop_event.is_set():
        try:
            snapshot = await _publish_state_with_retry(state)
            stats.state_publishes += 1
            result = publish_bridge(source, output)
            stats.bridge_publishes += 1
            generation = int(result["generation_id"])
            if generation != stats.last_generation:
                stats.distinct_generations += 1
                stats.last_generation = generation
            now = time.monotonic()
            if last_log == 0.0 or now - last_log >= max(5.0, log_seconds):
                cross = snapshot.get("cross_venue") or {}
                btc_ok = ((cross.get("BTCUSD") or {}).get("quality") or {}).get("both_core_ok")
                eth_ok = ((cross.get("ETHUSD") or {}).get("quality") or {}).get("both_core_ok")
                print(
                    f"[MULTIVENUE][OK] gen={generation} distinct={stats.distinct_generations} "
                    f"BTC_both={btc_ok} ETH_both={eth_ok}"
                )
                last_log = now
        except Exception as exc:  # runtime must surface and continue transient failures
            stats.review_errors += 1
            print(f"[MULTIVENUE][REVIEW] {type(exc).__name__}: {exc}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(0.25, state.interval_seconds))
        except asyncio.TimeoutError:
            pass


async def _bounded_shutdown(tasks: list[asyncio.Task]) -> None:
    if not tasks:
        return
    done, pending = await asyncio.wait(tasks, timeout=SHUTDOWN_GRACE_SECONDS)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    # Consume exceptions from tasks that completed during shutdown.
    for task in done:
        if task.cancelled():
            continue
        try:
            task.result()
        except Exception:
            pass


async def async_main(args: argparse.Namespace) -> int:
    data_dir: Path = args.data_dir
    common_dir: Path = args.common_files_dir or default_common_files_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    bybit = BybitCollectorHealthFixed(
        ["BTCUSD", "ETHUSD"], JsonlRecorder(data_dir), args.poll_seconds, args.health_seconds
    )
    binance = BinanceCollector(
        ["BTCUSD", "ETHUSD"], BinanceJsonlRecorder(data_dir), args.poll_seconds, args.health_seconds
    )
    state = MultiVenueMarketStateService(
        data_dir,
        snapshot_name="market_state_multivenue_v1.json",
        interval_seconds=args.state_interval_seconds,
    )

    runtime_stop = asyncio.Event()
    source = data_dir / "market_state_multivenue_v1.json"
    output = common_dir / "GuardianSharedIntelligence" / "market_state_multivenue_v1.csv"
    stats = RuntimeStats(started_monotonic=time.monotonic())

    loop = asyncio.get_running_loop()

    def stop_all() -> None:
        bybit.stop_event.set()
        binance.stop_event.set()
        state.stop_event.set()
        runtime_stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_all)
        except NotImplementedError:
            pass

    print("Guardian Shared Intelligence MULTI-VENUE Runtime V1 START")
    print(f"data={data_dir}")
    print(f"FILE_COMMON output={output}")
    print("BYBIT + BINANCE / VENUE-SEPARATED / READ ONLY / NO TRADING EFFECT")

    components = [
        asyncio.create_task(bybit.run(), name="bybit_collector"),
        asyncio.create_task(binance.run(), name="binance_collector"),
        asyncio.create_task(
            run_state_bridge(state, source, output, runtime_stop, stats, args.log_seconds),
            name="multivenue_state_bridge",
        ),
    ]

    timer_task: asyncio.Task | None = None
    if args.run_seconds > 0:
        async def timer() -> None:
            await asyncio.sleep(max(1.0, args.run_seconds))
            stop_all()
        timer_task = asyncio.create_task(timer(), name="bounded_timer")

    stop_waiter = asyncio.create_task(runtime_stop.wait(), name="stop_waiter")
    watchers = components + [stop_waiter]
    try:
        done, _ = await asyncio.wait(watchers, return_when=asyncio.FIRST_COMPLETED)
        if stop_waiter not in done:
            # A component ended before a requested stop: this is abnormal.
            for task in done:
                if task in components:
                    stats.review_errors += 1
                    if task.cancelled():
                        print(f"[MULTIVENUE][REVIEW] component cancelled unexpectedly: {task.get_name()}")
                    else:
                        exc = task.exception()
                        print(f"[MULTIVENUE][REVIEW] component ended unexpectedly: {task.get_name()} exc={exc}")
            stop_all()
    finally:
        stop_all()
        if timer_task is not None:
            timer_task.cancel()
            await asyncio.gather(timer_task, return_exceptions=True)
        stop_waiter.cancel()
        await asyncio.gather(stop_waiter, return_exceptions=True)
        await _bounded_shutdown(components)

    observed_seconds = time.monotonic() - stats.started_monotonic
    print(
        f"Guardian Shared Intelligence MULTI-VENUE Runtime V1 STOP | "
        f"seconds={observed_seconds:.3f} state={stats.state_publishes} "
        f"bridge={stats.bridge_publishes} generations={stats.distinct_generations} "
        f"review_errors={stats.review_errors}"
    )

    if args.gate:
        failures = _validate_final_bridge(output, stats, observed_seconds)
        summary = {
            "observed_seconds": round(observed_seconds, 3),
            "state_publishes": stats.state_publishes,
            "bridge_publishes": stats.bridge_publishes,
            "distinct_generations": stats.distinct_generations,
            "last_generation": stats.last_generation,
            "review_errors": stats.review_errors,
            "output": str(output),
            "failures": failures,
            "gate": "PASS" if not failures else "REVIEW",
        }
        print("=== GUARDIAN SHARED MULTI-VENUE RUNTIME GATE ===")
        print(json.dumps(summary, indent=2, sort_keys=True))
        if failures:
            print("[Guardian] SHARED MULTI-VENUE RUNTIME V1 GATE: REVIEW.")
            return 2
        print("[Guardian] SHARED MULTI-VENUE RUNTIME V1 GATE: PASS.")

    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
