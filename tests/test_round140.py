# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 140 tests: routing R45-R48, Layer B gap-matrix CLI & v0.135.0 full-series release hygiene."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r140_routing_table_contains_r45_through_r48():
    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R45 |", "| R46 |", "| R47 |", "| R48 |"):
        assert row_id in txt, f"Missing routing row {row_id}"


def test_r140_release_hygiene_passes_at_v0135():
    proc = subprocess.run([sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.135.0"
