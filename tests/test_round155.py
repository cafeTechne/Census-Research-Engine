# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 155 tests: routing R57-R60 (60 rows) & v0.150.0 milestone release hygiene."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r155_routing_table_contains_r57_through_r60():
    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R57 |", "| R58 |", "| R59 |", "| R60 |"):
        assert row_id in txt, f"Missing routing row {row_id}"


def test_r155_release_hygiene_passes_at_v0150():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.150.0"
