# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 177 tests: census/spatial.py modularization into spatial_regression_helpers.py & re-export parity."""
from pathlib import Path

from census import spatial, spatial_regression_helpers

ROOT = Path(__file__).resolve().parents[1]


def test_r177_spatial_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/spatial.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 900, f"Expected spatial.py < 900 lines, got {n_lines}"
    for name in ("error_model_known_variances", "_corrected_error_regression", "spatial_regression", "TRACT_ERROR_NOTE"):
        assert getattr(spatial, name) is getattr(spatial_regression_helpers, name)
