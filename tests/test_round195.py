# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 195 tests: live neural claim-grounding audit artifact, routing R92-R94 (94 rows), and v0.191.0 hygiene."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r195_manuscript_claim_grounding_artifact_and_routing():
    audit = (ROOT / "docs/audits/r195_manuscript_claim_grounding.md").read_text(encoding="utf-8")
    assert "BAAI/bge-small-en-v1.5" in audit
    assert "exploratory_hypothesis_seed" in audit
    assert "5/5" in audit

    txt = (ROOT / "docs/agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R92 |", "| R93 |", "| R94 |"):
        assert row_id in txt


def test_r195_release_hygiene_passes_at_v0191():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.191.0"
