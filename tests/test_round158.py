# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 158 tests: census/models.py modularization into models_eiv.py & re-export parity."""
from pathlib import Path

from census import models, models_eiv

ROOT = Path(__file__).resolve().parents[1]


def test_r158_models_slimmed_and_reexports_preserved():
    n_lines = len((ROOT / "census/models.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 1050, f"Expected models.py < 1050 lines, got {n_lines}"
    for name in ("fit_eiv", "simex", "cluster_labels", "_cluster_jackknife", "_design_deviations"):
        assert getattr(models, name) is getattr(models_eiv, name)
