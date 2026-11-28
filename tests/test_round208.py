# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 208 tests: doctor --deep invariant verification (MCP <-> TOOL_SOURCES parity, recipe docs, metadata manifest)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_doctor_deep_invariants_pass():
    proc = subprocess.run(
        [sys.executable, "-m", "census", "doctor", "--deep", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    dc = rep["deep_checks"]
    assert dc["ok"] is True
    assert dc["mcp_tool_count"] == dc["tool_sources_count"] >= 84
    assert dc["missing_in_tool_sources"] == []
    assert dc["missing_in_mcp_server"] == []
    assert dc["missing_recipe_docs"] == []
    assert dc["metadata_manifest_ok"] is True


def test_r208_release_hygiene_passes_at_v0204():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.204.0"
