# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 199 tests: Dockerfile, external reviewer checklist, routing R95-R97 (97 rows), and v0.195.0 hygiene."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_r199_dockerfile_reviewer_checklist_and_routing():
    df = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "python:3.12-slim" in df and "doctor" in df

    chk = (ROOT / "docs" / "external_review_checklist.md").read_text(encoding="utf-8")
    assert "release_hygiene_check.py" in chk and "verify-bundle" in chk and "docker build" in chk

    rt = (ROOT / "docs" / "agent_routing.md").read_text(encoding="utf-8")
    for row_id in ("| R95 |", "| R96 |", "| R97 |"):
        assert row_id in rt


def test_r199_release_hygiene_passes_at_v0195():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.195.0"
