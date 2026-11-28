# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 192 tests: doctor --verbose diagnostics, routing R89-R91 (91 rows), and v0.188.0 release hygiene."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r192_doctor_verbose_and_routing_r89_r91():
    proc = subprocess.run(
        [sys.executable, "-m", "census", "doctor", "--verbose", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["version"] >= "0.188.0"
    assert rep["diagnostics"]["crosswalks_valid"] is True
    assert isinstance(rep["diagnostics"]["acs_2025_archived"], bool)

    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R89 |", "| R90 |", "| R91 |"):
        assert row_id in txt


def test_r192_release_hygiene_passes_at_v0188():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.188.0"
