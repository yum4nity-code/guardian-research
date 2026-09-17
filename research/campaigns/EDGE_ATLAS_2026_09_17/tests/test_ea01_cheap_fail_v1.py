import json
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).parents[1] / "ea01_cheap_fail_v1.py"

def test_preflight_only(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"status":"ADMITTED","files":[{"asset":"XAUUSD","coverage":"2004-2025"}]}))
    p = subprocess.run([sys.executable,str(RUNNER),"--manifest",str(manifest),"--output",str(tmp_path/"o")],capture_output=True,text=True)
    assert p.returncode == 0
    assert "PREFLIGHT_ONLY" in p.stdout

def test_execute_refuses_missing_adapter(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"status":"ADMITTED","files":[{"asset":"XAUUSD","coverage":"2004-2025"}]}))
    p = subprocess.run([sys.executable,str(RUNNER),"--manifest",str(manifest),"--output",str(tmp_path/"o"),"--execute"],capture_output=True,text=True)
    assert p.returncode != 0
    assert "adapter" in (p.stderr+p.stdout).lower()

def test_rejects_2026(tmp_path):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"status":"ADMITTED","files":[{"asset":"XAUUSD","coverage":"2004-2026"}]}))
    p = subprocess.run([sys.executable,str(RUNNER),"--manifest",str(manifest),"--output",str(tmp_path/"o")],capture_output=True,text=True)
    assert p.returncode != 0
