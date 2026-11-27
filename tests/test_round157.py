# SPDX-License-Identifier: AGPL-3.0-or-later
"""Round 157 tests: census/manifest/methods.py modularization into methods_epi.py & METHODS parity."""
from pathlib import Path

from census.manifest import methods, methods_epi

ROOT = Path(__file__).resolve().parents[1]


def test_r157_methods_slimmed_and_registry_intact():
    n_lines = len((ROOT / "census/manifest/methods.py").read_text(encoding="utf-8").splitlines())
    assert n_lines < 2260, f"Expected methods.py < 2260 lines, got {n_lines}"
    assert len(methods.METHODS) == 28
    assert methods._run_estimate_effect is methods_epi._run_estimate_effect
    assert methods._check_estimate_effect is methods_epi._check_estimate_effect
