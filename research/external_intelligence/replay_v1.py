#!/usr/bin/env python3
"""Strict replay reader for Guardian External Intelligence Bus V1 JSONL.

The replay gate is availability-based: an observation is visible only when
available_at_ms <= simulated_time_ms. This prevents lookahead from exchange
source timestamps that arrived later at the collector.
"""

from __future__ import annotations

import argparse
import heapq
import json
import sys
from pathlib import Path
from typing import Any, Iterator


def iter_records(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if "available_at_ms" not in rec:
                raise ValueError(f"{path}:{line_no}: missing available_at_ms")
            yield rec


class ReplayReader:
    def __init__(self, paths: list[Path]):
        self._iterators = [iter_records(p) for p in paths]
        self._heap: list[tuple[int, int, dict[str, Any]]] = []
        for idx, it in enumerate(self._iterators):
            self._push_next(idx, it)

    def _push_next(self, idx: int, it: Iterator[dict[str, Any]]) -> None:
        try:
            rec = next(it)
        except StopIteration:
            return
        heapq.heappush(self._heap, (int(rec["available_at_ms"]), idx, rec))

    def pop_available(self, simulated_time_ms: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        while self._heap and self._heap[0][0] <= simulated_time_ms:
            _, idx, rec = heapq.heappop(self._heap)
            out.append(rec)
            self._push_next(idx, self._iterators[idx])
        return out

    def peek_next_available_at(self) -> int | None:
        return self._heap[0][0] if self._heap else None


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Replay Guardian EIB V1 JSONL with strict available_at gate")
    p.add_argument("paths", nargs="+", type=Path)
    p.add_argument("--until-ms", type=int, required=True, help="Simulated time; records after this availability time are hidden")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    reader = ReplayReader(args.paths)
    for rec in reader.pop_available(args.until_ms):
        print(json.dumps(rec, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
