# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 187 tests: doctor CLI self-check, dual-MCP config/quickstart, and README two-layer docs."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from census.workflows_reporting import doctor_report

ROOT = Path(__file__).resolve().parents[1]


def test_doctor_report_and_cli_no_secret_leak(monkeypatch):
    secret = "SUPER_SECRET_CENSUS_KEY_187"
    monkeypatch.setenv("CENSUS_API_KEY", secret)
    rep = doctor_report()
    assert rep["ok"] is True
    assert rep["bundled_data_ok"] is True
    assert rep["has_census_api_key"] is True
    assert rep["recipe_count"] >= 33
    assert rep["manifest_method_count"] >= 28
    assert "publication" in rep["mcp_profiles"]
    assert "epidemiology" in rep["mcp_profiles"]
    assert secret not in json.dumps(rep)

    env = dict(os.environ, CENSUS_API_KEY=secret)
    proc = subprocess.run(
        [sys.executable, "-m", "census", "doctor", "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert secret not in proc.stdout
    assert secret not in proc.stderr
    parsed = json.loads(proc.stdout)
    assert parsed["ok"] is True
    assert parsed["has_census_api_key"] is True


def test_dual_mcp_config_and_quickstart_and_readme():
    cfg_path = ROOT / "examples" / "mcp" / "dual_mcp_config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "mcpServers" in cfg
    assert "census-research-engine" in cfg["mcpServers"]
    assert "layer-b-openscholar" in cfg["mcpServers"]

    guide = (ROOT / "docs" / "dual_mcp_quickstart.md").read_text(encoding="utf-8")
    assert "python -m census doctor" in guide
    assert "verify-bundle" in guide
    assert "exploratory_hypothesis_seed" in guide

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Two-Layer Architecture" in readme
    assert "dual_mcp_config.json" in readme
    assert "python -m census doctor" in readme
