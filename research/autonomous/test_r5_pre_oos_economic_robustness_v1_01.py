#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import r5_pre_oos_economic_robustness_v1_00 as base
import r5_pre_oos_economic_robustness_v1_01 as repaired


def test_scientific_identity() -> None:
    assert repaired.PROTECTED == base.PROTECTED
    assert repaired.EXPECTED_R5_SHA256 == base.EXPECTED_R5_SHA256
    assert repaired.EXPECTED_AUDIT_SHA256 == base.EXPECTED_AUDIT_SHA256
    assert repaired.EXPECTED == base.EXPECTED
    assert repaired.PROFILES == base.PROFILES
    assert repaired.PERIODS == base.PERIODS
    assert repaired.cost is base.cost
    assert repaired.replay is base.replay
    assert repaired.in_period is base.in_period
    assert repaired.stats is base.stats
    assert repaired.decide is base.decide


def test_atomic_retry_then_success() -> None:
    original = repaired.os.replace
    calls = {'n': 0}

    def flaky(src, dst):
        calls['n'] += 1
        if calls['n'] <= 2:
            raise PermissionError('synthetic transient lock')
        return original(src, dst)

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'x.json'
        repaired.os.replace = flaky
        try:
            repaired.atomic_json(p, {'ok': True})
        finally:
            repaired.os.replace = original
        assert calls['n'] == 3
        assert json.loads(p.read_text(encoding='utf-8')) == {'ok': True}


def test_atomic_retry_exhaustion() -> None:
    original_replace = repaired.os.replace
    original_sleep = repaired.time.sleep
    calls = {'n': 0}

    def always_fail(src, dst):
        calls['n'] += 1
        raise PermissionError('synthetic persistent lock')

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / 'x.json'
        repaired.os.replace = always_fail
        repaired.time.sleep = lambda _: None
        try:
            try:
                repaired.atomic_json(p, {'ok': False})
            except PermissionError as exc:
                assert 'after 6 attempts' in str(exc)
            else:
                raise AssertionError('expected PermissionError')
        finally:
            repaired.os.replace = original_replace
            repaired.time.sleep = original_sleep
        assert calls['n'] == 6


def main() -> int:
    test_scientific_identity()
    test_atomic_retry_then_success()
    test_atomic_retry_exhaustion()
    print('PASS: R5 economic robustness infrastructure wrapper')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
