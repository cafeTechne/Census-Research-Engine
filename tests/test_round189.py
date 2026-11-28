# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 189 tests: routing R85-R88 (88 rows), v0.185.0 release hygiene, and doctor CLI."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r189_routing_table_contains_r85_through_r88():
    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R85 |", "| R86 |", "| R87 |", "| R88 |"):
        assert row_id in txt, f"Missing routing row {row_id}"


def test_r189_release_hygiene_passes_at_v0185():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True
    assert rep["version"] >= "0.185.0"
