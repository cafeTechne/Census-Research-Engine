# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 148 tests: mcp_server.py modularization line-count reduction, symbol parity & rule-text sync."""
import subprocess
import sys
from pathlib import Path

import mcp_server as srv
from census import mcp_helpers, mcp_instructions

ROOT = Path(__file__).resolve().parents[1]


def test_r148_mcp_server_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "mcp_server.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1150, f"Expected mcp_server.py < 1150 lines, got {n_lines}"
    assert srv.INSTRUCTIONS == mcp_instructions.INSTRUCTIONS
    assert srv.calculate_cv is mcp_helpers.calculate_cv
    assert srv.calculate_significance is mcp_helpers.calculate_significance
    assert srv.adjust_inflation is mcp_helpers.adjust_inflation

    proc = subprocess.run([sys.executable, str(ROOT / "scripts/sync_rule_text.py"), "--check"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
