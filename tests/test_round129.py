# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 129 tests: CLI verify-bundle subcommand and agent routing rows R41-R44."""
import json
import subprocess
import sys
from pathlib import Path

from census.manifest import run_manifest
from tests.test_manifest import FakeClient

ROOT = Path(__file__).resolve().parents[1]


def test_cli_verify_bundle_passes_and_catches_tampering(tmp_path):
    manifest = {
        "schema_version": 1,
        "title": "Round 129 CLI verify-bundle test",
        "authors": ["human:example-researcher"],
        "created": "2026-11-26T00:00:00Z",
        "releases": [2019],
        "geography": {"level": "tract", "state": "36", "codes": ["061"]},
        "variables": [
            {"name": "income", "ref": "2019:B19013_001"},
            {"name": "pop", "ref": "2019:B01003_001"},
        ],
        "missing": "complete_case",
        "confidence_level": 0.90,
        "correction": {"method": "holm", "family": "all"},
        "analyses": [{"id": "ag1", "method": "agreement", "first": "income", "second": "pop"}],
        "hypotheses": [{"id": "H1", "statement": "Non-zero CCC.", "analysis": "ag1", "statistic": "ccc", "null_value": 0.0}],
    }
    mpath = tmp_path / "m129.json"
    mpath.write_text(json.dumps(manifest), encoding="utf-8")
    out_dir = tmp_path / "out"
    res = run_manifest(str(mpath), output_dir=str(out_dir), client=FakeClient(), use_cache=False)
    assert res["success"] is True

    bdir = out_dir / "bundle"
    p_ok = subprocess.run([sys.executable, "-m", "census", "verify-bundle", str(bdir)],
                          capture_output=True, text=True, cwd=str(ROOT))
    assert p_ok.returncode == 0, p_ok.stdout + p_ok.stderr
    assert json.loads(p_ok.stdout)["ok"] is True

    (bdir / "methods.md").write_text("tampered\n", encoding="utf-8")
    p_bad = subprocess.run([sys.executable, "-m", "census", "verify-bundle", str(bdir)],
                           capture_output=True, text=True, cwd=str(ROOT))
    assert p_bad.returncode == 1
    assert json.loads(p_bad.stdout)["ok"] is False


def test_agent_routing_contains_r41_through_r44():
    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R41 |", "| R42 |", "| R43 |", "| R44 |"):
        assert row_id in txt
