# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 205 tests: Layer B allow_subprocess_neural hook, routing R101-R103, and v0.201.0 hygiene."""
from __future__ import annotations

import inspect
import json
import subprocess
import sys
from pathlib import Path

from layer_b_openscholar.rag import query_hybrid_rag

ROOT = Path(__file__).resolve().parents[1]


def test_r205_rag_subprocess_neural_param_and_routing():
    sig = inspect.signature(query_hybrid_rag)
    assert "allow_subprocess_neural" in sig.parameters
    assert sig.parameters["allow_subprocess_neural"].default is False

    rt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R101 |", "| R102 |", "| R103 |"):
        assert row_id in rt


def test_r205_release_hygiene_passes_at_v0201():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.201.0"
