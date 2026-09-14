#!/usr/bin/env python3
from __future__ import annotations

import importlib.util, lzma, struct, tempfile, hashlib
from datetime import date
from pathlib import Path

HERE=Path(__file__).resolve().parent

def load(name,p):
    s=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

inv=load("inv",HERE/"inventory_r15_xau_cache_before_fastfill_v1_00.py")
ff=load("ff",HERE/"r15_xau_dukascopy_fastfill_v1_00.py")
merge_src=(HERE/"build_r15_xau_union_from_two_caches_v1_00.py").read_text(encoding="utf-8")

def ok(x,msg):
    if not x: raise AssertionError(msg)

def rec(sec,op):
    return struct.pack(">IIIIIf",sec,op,op,op,op,1.0)

def payload():
    raw=b"".join([rec(0,1000),rec(60,1001),rec(120,1002)])
    return lzma.compress(raw)

def test_inventory_validation_and_hash():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        p=root/"2005"/"06"/"01.bi5"; p.parent.mkdir(parents=True)
        b=payload(); p.write_bytes(b)
        m=inv.validate_payload(date(2005,6,1),p)
        ok(m["records"]==3,"inventory record count")
        ok(m["sha256"]==hashlib.sha256(b).hexdigest(),"inventory hash mismatch")

def test_fastfill_2026_guard():
    try: ff.url_for(date(2026,1,1))
    except RuntimeError: pass
    else: raise AssertionError("2026 URL guard missing")

def test_fastfill_existing_cache_skip():
    with tempfile.TemporaryDirectory() as td:
        dest=Path(td)
        p=dest/"2010"/"06"/"01.bi5"; p.parent.mkdir(parents=True)
        b=payload(); p.write_bytes(b)
        r=ff.fetch_one("2010-06-01",dest,1)
        ok(r["status"]=="ok" and r["transport"]=="cache_fastfill","existing fast cache not reused")
        ok(r["sha256"]==hashlib.sha256(b).hexdigest(),"fast cache hash mismatch")

def test_fastfill_404_marker():
    old_curl,old_url=ff.curl_fetch,ff.urllib_fetch
    try:
        ff.curl_fetch=lambda url,timeout:(404,None,None)
        ff.urllib_fetch=lambda url,timeout:(_ for _ in ()).throw(AssertionError("urllib should not run after 404"))
        with tempfile.TemporaryDirectory() as td:
            dest=Path(td)
            r=ff.fetch_one("2011-12-26",dest,1)
            ok(r["status"]=="missing","404 not classified missing")
            marker=dest/"2011"/"12"/"26.missing.json"
            ok(marker.exists(),"missing marker not persisted")
    finally:
        ff.curl_fetch,ff.urllib_fetch=old_curl,old_url

def test_static_union_guards():
    ok("duplicate date hash mismatch" in merge_src,"union duplicate mismatch guard missing")
    ok("unresolved weekday neither payload nor missing marker" in merge_src,"union completeness guard missing")
    ok("protected 2026 boundary created" in merge_src,"union 2026 guard missing")
    ok("cache_roots" in merge_src and "payload_index_csv_sha256" in merge_src,"union provenance manifest missing")

def test_source_cache_immutability():
    s=(HERE/"r15_xau_dukascopy_fastfill_v1_00.py").read_text(encoding="utf-8")
    ok("source-cache" not in s.lower(),"fastfill unexpectedly writes/accepts source cache")
    ok("dest-cache" in s,"separate destination cache missing")
    ok("ThreadPoolExecutor" in s,"parallel fastfill missing")
    ok("max_workers=workers" in s,"worker control missing")
    ok("CREATE_NO_WINDOW" in s,"Windows curl suppression missing")

def main():
    for fn in [test_inventory_validation_and_hash,test_fastfill_2026_guard,test_fastfill_existing_cache_skip,
               test_fastfill_404_marker,test_static_union_guards,test_source_cache_immutability]:
        fn()
    print('{"status":"PASS","tests":"R15 XAU stop-inventory-fastfill-union deterministic preflight"}')

if __name__=="__main__":
    main()
