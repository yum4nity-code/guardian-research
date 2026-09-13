#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import lzma
import struct
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "r15_dukascopy_xauusd_boundary_export_v1_01.py"

spec = importlib.util.spec_from_file_location("r15duka101", ENGINE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def ok(v, msg):
    if not v:
        raise AssertionError(msg)

def rec(sec: int, op: int) -> bytes:
    return struct.pack(">IIIIIf", sec, op, op, op, op, 1.0)

def valid_payload_for_2010_06_01() -> bytes:
    # New York is UTC-4 on 2010-06-01.
    raw = b"".join([
        rec(15*3600 + 30*60, 1000),
        rec(16*3600, 1010),
        rec(19*3600 + 30*60, 1020),
        rec(20*3600, 1030),
    ])
    return lzma.compress(raw)

def test_fallback_then_cache():
    d = date(2010, 6, 1)
    payload = valid_payload_for_2010_06_01()

    old_exe = m._curl_exe
    old_curl = m._curl_fetch
    old_url = m._urllib_fetch
    try:
        m._curl_exe = lambda: "curl.exe"
        m._curl_fetch = lambda url, timeout: (None, None, "simulated WinError 10054")
        m._urllib_fetch = lambda url, timeout: (200, payload, None)

        with tempfile.TemporaryDirectory() as td:
            cache = Path(td)
            status, got, transport = m.fetch_payload(
                d,
                cache_dir=cache,
                retries=1,
                timeout=1,
                request_delay_seconds=0.0,
            )
            ok(status == "ok", "fallback did not recover")
            ok(transport == "urllib", f"wrong fallback transport: {transport}")
            ok(got == payload, "payload changed")
            cp = m.cache_path(cache, d)
            ok(cp.exists() and cp.read_bytes() == payload, "payload was not cached")

            def must_not_call(*args, **kwargs):
                raise AssertionError("network called despite valid cache")

            m._curl_fetch = must_not_call
            m._urllib_fetch = must_not_call
            status2, got2, transport2 = m.fetch_payload(
                d,
                cache_dir=cache,
                retries=1,
                timeout=1,
                request_delay_seconds=0.0,
            )
            ok(status2 == "ok" and got2 == payload and transport2 == "cache", "cache resume failed")
    finally:
        m._curl_exe = old_exe
        m._curl_fetch = old_curl
        m._urllib_fetch = old_url

def test_404_is_missing():
    d = date(2010, 12, 24)
    old_exe = m._curl_exe
    old_curl = m._curl_fetch
    old_url = m._urllib_fetch
    try:
        m._curl_exe = lambda: "curl.exe"
        m._curl_fetch = lambda url, timeout: (404, b"", None)
        m._urllib_fetch = lambda url, timeout: (_ for _ in ()).throw(AssertionError("urllib should not follow a real 404"))
        with tempfile.TemporaryDirectory() as td:
            status, payload, transport = m.fetch_payload(
                d,
                cache_dir=Path(td),
                retries=1,
                timeout=1,
                request_delay_seconds=0.0,
            )
            ok(status == "missing" and payload is None and transport == "curl", "404 semantics wrong")
    finally:
        m._curl_exe = old_exe
        m._curl_fetch = old_curl
        m._urllib_fetch = old_url

def test_protected_year_guards():
    for fn in (
        lambda: m.day_url(date(2026, 1, 1)),
        lambda: m.cache_path(Path("."), date(2026, 1, 1)),
    ):
        try:
            fn()
        except RuntimeError:
            pass
        else:
            raise AssertionError("2026 guard missing")

def test_source_is_sequential_and_resumable():
    src = ENGINE.read_text(encoding="utf-8")
    ok("ThreadPoolExecutor" not in src, "concurrent downloader reintroduced")
    ok('"curl_http1.1_primary_urllib_fallback_sequential_cached"' in src, "transport policy missing")
    ok("payload_cache" in src, "resume cache missing")
    ok("--retry-all-errors" in src, "curl retry-all-errors missing")
    ok('"Connection: close"' in src, "connection-close transport guard missing")

def main():
    for fn in [
        test_fallback_then_cache,
        test_404_is_missing,
        test_protected_year_guards,
        test_source_is_sequential_and_resumable,
    ]:
        fn()
    print('{"status":"PASS","tests":"R15 Dukascopy resilient transport/cache/protection preflight"}')

if __name__ == "__main__":
    main()
