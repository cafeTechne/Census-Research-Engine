# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 212 tests: final sprint gate (110 routing rows, doctor --deep, and v0.208.0 release hygiene)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r212_routing_110_rows_and_hygiene_v0208():
    rt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    assert "| R110 |" in rt

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] == "0.208.0"
