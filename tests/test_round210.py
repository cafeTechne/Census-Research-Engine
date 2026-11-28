# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 210 tests: census/workflows_geo_helpers modularization & re-export parity."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from census import workflows_geo, workflows_geo_helpers

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_geo_helpers_reexport_parity():
    for name in (
        "_LEVELS", "_MAP_KINDS", "_GEO_ERRORS", "_release_replicates",
        "_per_state", "_fetch_boundaries", "_with_boundaries", "_weights_for", "_paths",
    ):
        assert getattr(workflows_geo, name) is getattr(workflows_geo_helpers, name)


def test_r210_release_hygiene_passes_at_v0206():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.206.0"
