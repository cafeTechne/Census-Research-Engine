# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 150 tests: routing R53-R56, recipe parity & v0.145.0 full-series release hygiene."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r150_routing_table_contains_r53_through_r56():
    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R53 |", "| R54 |", "| R55 |", "| R56 |"):
        assert row_id in txt, f"Missing routing row {row_id}"


def test_r150_release_hygiene_passes_at_v0145():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.145.0"
