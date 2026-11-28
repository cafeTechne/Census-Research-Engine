# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 206 tests: Multi-component & island BYM2 finite-sample simulation calibration."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from census.simulation_multicomponent_bym2 import build_multicomponent_graph, run_multicomponent_bym2_calibration

ROOT = Path(__file__).resolve().parents[1]


def test_multicomponent_bym2_calibration_beats_raw_smr():
    n, edges = build_multicomponent_graph(grid_side=4, n_islands=2)
    assert n == 34 and len(edges) == 48
    rep = run_multicomponent_bym2_calibration(n_draws=6, median_e=40.0, seed=206)
    assert rep["ok"] is True
    assert rep["n_components"] == 4 and rep["n_islands"] == 2
    assert rep["bym2_beats_raw_smr"] is True
    assert 0.65 <= rep["coverage_connected_90"] <= 1.0


def test_r206_release_hygiene_passes_at_v0202():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/release_hygiene_check.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rep = json.loads(proc.stdout)
    assert rep["ok"] is True and rep["version"] >= "0.202.0"
